"""
阶段一：交易日志解码器（Trade Decoder）
完整实现版本 - 解析Polymarket OrderFilled事件
"""
import json
import sys
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal
import argparse
import logging
from dotenv import load_dotenv
from web3 import Web3
import os

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Trade:
    """交易数据结构"""
    tx_hash: str
    log_index: int
    exchange: str
    order_hash: str
    maker: str
    taker: str
    maker_asset_id: str
    taker_asset_id: str
    maker_amount: str
    taker_amount: str
    fee: str
    price: str
    token_id: str
    side: str


class TradeDecoder:
    """交易解码器 - 解析Polymarket的OrderFilled事件"""
    
    # Polymarket Exchange合约地址
    CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
    NEG_RISK_EXCHANGE = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
    
    USDC_DECIMALS = 6
    USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
    
    # OrderFilled 事件签名
    # OrderFilled(bytes32 indexed orderHash, address indexed maker, address indexed taker, 
    #             uint256 makerAssetId, uint256 takerAssetId, uint256 makerAmountFilled, 
    #             uint256 takerAmountFilled, uint256 fee)
    ORDER_FILLED_TOPIC = Web3.keccak(
        text="OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)"
    ).hex()
    
    def __init__(self, rpc_url: str) -> None:
        """初始化解码器"""
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError("无法连接到Polygon RPC")
        logger.info("成功连接到 Polygon 网络")
    
    def decode_tx_logs(self, tx_hash: str) -> List[Trade]:
        """
        解码指定交易的所有OrderFilled事件
        
        Args:
            tx_hash: 交易哈希
            
        Returns:
            Trade列表
        """
        try:
            # 规范化交易哈希
            if not tx_hash.startswith('0x'):
                tx_hash = '0x' + tx_hash
            
            # 获取交易回执
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            if not receipt:
                logger.warning(f"交易 {tx_hash} 不存在或未确认")
                return []
            
            logger.info(f"处理交易: {tx_hash}")
            logger.info(f"总日志数: {len(receipt['logs'])}")
            
            trades = []
            
            # 遍历所有日志
            for log_index, log in enumerate(receipt['logs']):
                exchange_addr = log['address'].lower()
                
                # 检查是否来自 Polymarket Exchange
                if exchange_addr not in [self.CTF_EXCHANGE.lower(), self.NEG_RISK_EXCHANGE.lower()]:
                    continue
                
                # 尝试解析日志
                trade = self._parse_order_filled_log(tx_hash, log_index, log)
                if trade:
                    trades.append(trade)
                    logger.info(f"  ✓ 交易 {log_index}: {trade.maker[:10]}... -> {trade.price} USDC")
            
            logger.info(f"解码完成: 共 {len(trades)} 笔交易")
            return trades
            
        except Exception as e:
            logger.error(f"解码交易出错: {e}", exc_info=True)
            return []
    
    def _parse_order_filled_log(self, tx_hash: str, log_index: int, log: Dict) -> Optional[Trade]:
        """
        解析单个OrderFilled日志
        
        OrderFilled 事件结构:
        - topics[0]: 事件签名
        - topics[1]: indexed orderHash (bytes32)
        - topics[2]: indexed maker (address)
        - topics[3]: indexed taker (address)
        - data: makerAssetId(32) + takerAssetId(32) + makerAmountFilled(32) + takerAmountFilled(32) + fee(32)
        
        Args:
            tx_hash: 交易哈希
            log_index: 日志索引
            log: 日志对象
            
        Returns:
            Trade对象或None
        """
        try:
            exchange = Web3.to_checksum_address(log['address'])
            data = log['data']
            topics = log.get('topics', [])
            
            # 验证是否为 OrderFilled 事件
            if len(topics) < 4:
                return None
            
            # 检查事件签名
            topic0 = topics[0].hex() if hasattr(topics[0], 'hex') else str(topics[0])
            if not topic0.startswith('d0a08e8c'):  # OrderFilled 签名前缀（不含0x）
                return None
            
            # 从 topics 提取 indexed 参数
            order_hash = topics[1].hex() if hasattr(topics[1], 'hex') else str(topics[1])
            
            # maker 和 taker 地址在 topics 中（需要取后 40 字符）
            maker_topic = topics[2].hex() if hasattr(topics[2], 'hex') else str(topics[2])
            taker_topic = topics[3].hex() if hasattr(topics[3], 'hex') else str(topics[3])
            maker = Web3.to_checksum_address('0x' + maker_topic[-40:])
            taker = Web3.to_checksum_address('0x' + taker_topic[-40:])
            
            # 从 data 提取非 indexed 参数
            # data 可能是 HexBytes 或字符串，统一转换为 hex 字符串
            if hasattr(data, 'hex'):
                data_hex = data.hex()  # HexBytes -> hex string (无 0x 前缀)
            else:
                data_hex = data[2:] if str(data).startswith('0x') else str(data)
            
            # 验证数据长度：5 个 uint256 = 5 * 32 bytes = 160 bytes = 320 hex chars
            if len(data_hex) < 320:
                logger.debug(f"Data too short: {len(data_hex)} < 320")
                return None
            
            # 解析各字段（每个 uint256 = 64 hex 字符 = 32 bytes）
            maker_asset_id = int(data_hex[0:64], 16)
            taker_asset_id = int(data_hex[64:128], 16)
            maker_amount_raw = int(data_hex[128:192], 16)
            taker_amount_raw = int(data_hex[192:256], 16)
            fee_raw = int(data_hex[256:320], 16) if len(data_hex) >= 320 else 0
            
            # 转换为字符串（保持原始值用于存储）
            maker_asset_id_str = str(maker_asset_id)
            taker_asset_id_str = str(taker_asset_id)
            maker_amount = str(maker_amount_raw)
            taker_amount = str(taker_amount_raw)
            fee = str(fee_raw)
            
            # 判断买卖方向
            # makerAssetId = 0 表示 maker 出 USDC，即 maker 在买入 token
            # takerAssetId = 0 表示 taker 出 USDC，即 maker 在卖出 token
            if maker_asset_id == 0:
                # Maker 出 USDC，买入 token -> BUY
                side = "BUY"
                token_id = taker_asset_id_str
                # 价格 = USDC 数量 / Token 数量
                price = self._calculate_price(
                    Decimal(maker_amount_raw),
                    Decimal(taker_amount_raw)
                )
            elif taker_asset_id == 0:
                # Taker 出 USDC，maker 卖出 token -> SELL
                side = "SELL"
                token_id = maker_asset_id_str
                price = self._calculate_price(
                    Decimal(taker_amount_raw),
                    Decimal(maker_amount_raw)
                )
            else:
                # 两个都不是 USDC，跳过
                logger.debug(f"Neither asset is USDC: maker={maker_asset_id}, taker={taker_asset_id}")
                return None
            
            return Trade(
                tx_hash=tx_hash,
                log_index=log_index,
                exchange=exchange,
                order_hash=order_hash,
                maker=maker,
                taker=taker,
                maker_asset_id=maker_asset_id_str,
                taker_asset_id=taker_asset_id_str,
                maker_amount=maker_amount,
                taker_amount=taker_amount,
                fee=fee,
                price=price,
                token_id=token_id,
                side=side
            )
            
        except Exception as e:
            logger.debug(f"解析日志失败: {e}")
            return None
    
    def _parse_address(self, data: str, start: int, end: int) -> str:
        """从hex数据中提取地址"""
        try:
            hex_str = data[start:end]
            # 地址是最后20字节
            addr = "0x" + hex_str[-40:]
            return Web3.to_checksum_address(addr)
        except:
            return "0x"
    
    def _parse_hex(self, data: str, start: int, end: int) -> str:
        """从hex数据中提取hex值"""
        try:
            return "0x" + data[start:end]
        except:
            return "0x"
    
    def _calculate_price(self, usdc_amount: Decimal, token_amount: Decimal) -> str:
        """
        计算交易价格
        
        Args:
            usdc_amount: USDC数量（原始单位，需要除以10^6）
            token_amount: Token数量
            
        Returns:
            价格字符串
        """
        try:
            if token_amount == 0:
                return "0"
            
            # USDC有6位小数，需要转换
            usdc = usdc_amount / Decimal(10 ** self.USDC_DECIMALS)
            price = usdc / token_amount
            
            return str(round(price, 6))
        except Exception as e:
            logger.warning(f"计算价格出错: {e}")
            return "0"


def main():
    """主函数 - 命令行入口"""
    parser = argparse.ArgumentParser(
        description="PolyMind 交易解码器 - 解析Polymarket OrderFilled事件"
    )
    parser.add_argument(
        "--tx-hash",
        type=str,
        required=True,
        help="交易哈希 (示例: 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出JSON文件路径 (可选)"
    )
    
    args = parser.parse_args()
    
    # 获取RPC_URL
    rpc_url = os.getenv("RPC_URL")
    if not rpc_url:
        logger.error("错误: 环境变量 RPC_URL 未设置")
        logger.error("请在 .env 文件中设置 RPC_URL")
        logger.error("示例: RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY")
        sys.exit(1)
    
    # 创建解码器
    try:
        decoder = TradeDecoder(rpc_url)
    except Exception as e:
        logger.error(f"初始化解码器失败: {e}")
        sys.exit(1)
    
    # 解码交易
    logger.info(f"开始解码交易...")
    trades = decoder.decode_tx_logs(args.tx_hash)
    
    # 转换为JSON
    trades_dict = [asdict(trade) for trade in trades]
    
    # 输出结果
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(trades_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ 交易数据已保存到: {args.output}")
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            sys.exit(1)
    else:
        print("\n=== 解码结果 ===")
        print(json.dumps(trades_dict, indent=2, ensure_ascii=False))
    
    logger.info("解码完成!")


if __name__ == "__main__":
    main()
