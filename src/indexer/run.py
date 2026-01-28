"""
阶段二：区块链索引器（Indexer）
持续扫描Polymarket交易事件并存储到数据库

功能：
1. 获取 OrderFilled 事件日志
2. 解析交易数据
3. 存储到数据库
4. 支持增量同步和持续监听
"""
import logging
import sys
import json
import time
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import argparse
from dotenv import load_dotenv
import os
from web3 import Web3
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from trade_decoder import TradeDecoder, Trade
from market_decoder import MarketDecoder
from db.schema import init_db, get_connection
from indexer.store import DataStore
from indexer.gamma import GammaAPIClient

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PolymarketIndexer:
    """Polymarket交易索引器"""
    
    # 交易所地址
    CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
    NEG_RISK_EXCHANGE = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
    
    # OrderFilled 事件签名
    # event OrderFilled(bytes32 indexed orderHash, address indexed maker, address indexed taker, 
    #                   uint256 makerAssetId, uint256 takerAssetId, uint256 makerAmountFilled, 
    #                   uint256 takerAmountFilled, uint256 fee)
    ORDER_FILLED_TOPIC = "0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6"
    
    # 批处理大小（区块数）- Polygon RPC 限制每次返回 10000 条日志
    # Polymarket 交易量大，需要较小的批次
    BATCH_SIZE = 50
    
    # Polygon 出块间隔（秒）
    BLOCK_TIME = 2
    
    def __init__(self, rpc_url: str, db_path: str = "data/polymarket.db"):
        """
        初始化索引器
        
        Args:
            rpc_url: Polygon RPC URL
            db_path: SQLite 数据库路径
        """
        logger.info("初始化索引器...")
        
        self.rpc_url = rpc_url
        self.db_path = db_path
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # 验证RPC连接
        if not self.web3.is_connected():
            raise ConnectionError("无法连接到 Polygon RPC")
        
        chain_id = self.web3.eth.chain_id
        logger.info(f"✓ RPC 连接成功: 链ID {chain_id}")
        
        if chain_id != 137:
            logger.warning(f"⚠ 非 Polygon 主网 (链ID: {chain_id})")
        
        # 初始化数据库
        init_db(db_path)
        logger.info(f"✓ 数据库初始化完成: {db_path}")
        
        # 初始化组件
        self.store = DataStore(db_path)
        self.trade_decoder = TradeDecoder(rpc_url)
        self.market_decoder = MarketDecoder()
        self.gamma_client = GammaAPIClient()
        
        logger.info("✓ 索引器初始化完成")
    
    def get_current_block(self) -> int:
        """获取当前区块高度"""
        return self.web3.eth.block_number
    
    def get_block_timestamp(self, block_number: int) -> Optional[datetime]:
        """获取区块时间戳"""
        try:
            block = self.web3.eth.get_block(block_number)
            return datetime.fromtimestamp(block['timestamp'])
        except Exception as e:
            logger.warning(f"获取区块时间戳失败: {e}")
            return None
    
    def fetch_order_filled_logs(self, from_block: int, to_block: int) -> List[Dict]:
        """
        获取 OrderFilled 事件日志
        
        Args:
            from_block: 开始区块
            to_block: 结束区块
            
        Returns:
            日志列表
        """
        try:
            logs = self.web3.eth.get_logs({
                'fromBlock': from_block,
                'toBlock': to_block,
                'address': [
                    Web3.to_checksum_address(self.CTF_EXCHANGE),
                    Web3.to_checksum_address(self.NEG_RISK_EXCHANGE)
                ],
                'topics': [self.ORDER_FILLED_TOPIC]
            })
            
            logger.debug(f"获取到 {len(logs)} 个 OrderFilled 事件")
            return list(logs)
        
        except Exception as e:
            logger.error(f"获取日志失败 ({from_block}-{to_block}): {e}")
            return []
    
    def parse_log_to_trade(self, log: Dict) -> Optional[Tuple[Trade, int]]:
        """
        直接解析单个日志为 Trade 对象
        
        Args:
            log: 日志对象
            
        Returns:
            (Trade 对象, block_number) 或 None
        """
        try:
            tx_hash = log.get('transactionHash')
            if hasattr(tx_hash, 'hex'):
                tx_hash = tx_hash.hex()
            
            log_index = log.get('logIndex', 0)
            block_number = log.get('blockNumber', 0)
            
            # 使用 trade_decoder 的解析方法
            trade = self.trade_decoder._parse_order_filled_log(tx_hash, log_index, log)
            
            if trade:
                return (trade, block_number)
            
            return None
            
        except Exception as e:
            logger.warning(f"解析日志失败: {e}")
            return None
    
    def process_logs_batch(self, logs: List[Dict]) -> List[Tuple[Trade, int]]:
        """
        批量处理日志
        
        Args:
            logs: 日志列表
            
        Returns:
            [(Trade, block_number), ...] 列表
        """
        trades = []
        
        for log in logs:
            result = self.parse_log_to_trade(log)
            if result:
                trades.append(result)
        
        return trades
    
    def enrich_trades_with_market(self, trades: List[Tuple[Trade, int]]) -> List[Dict]:
        """
        使用市场信息丰富交易数据，并转换为字典
        
        Args:
            trades: [(Trade, block_number), ...] 列表
            
        Returns:
            丰富后的交易字典列表
        """
        # 获取所有市场的 token ID 映射
        token_to_market = self.store.get_token_to_market_mapping()
        
        result = []
        for trade, block_number in trades:
            trade_dict = {
                'tx_hash': trade.tx_hash,
                'log_index': trade.log_index,
                'exchange': trade.exchange,
                'order_hash': trade.order_hash,
                'maker': trade.maker,
                'taker': trade.taker,
                'maker_asset_id': trade.maker_asset_id,
                'taker_asset_id': trade.taker_asset_id,
                'maker_amount': trade.maker_amount,
                'taker_amount': trade.taker_amount,
                'fee': trade.fee,
                'price': trade.price,
                'token_id': trade.token_id,
                'side': trade.side,
                'block_number': block_number,
                'market_slug': None,
                'condition_id': None,
                'outcome': None
            }
            
            # 尝试关联市场信息
            token_id = trade.token_id
            if token_id in token_to_market:
                market = token_to_market[token_id]
                trade_dict['market_slug'] = market.get('slug')
                trade_dict['condition_id'] = market.get('condition_id')
                trade_dict['outcome'] = market.get('outcome')
            
            result.append(trade_dict)
        
        return result
    
    def store_trades(self, trade_dicts: List[Dict]) -> int:
        """
        存储交易到数据库
        
        Args:
            trade_dicts: 交易字典列表
            
        Returns:
            成功存储的交易数
        """
        if not trade_dicts:
            return 0
        
        return self.store.insert_trades(trade_dicts)
    
    def sync_markets_from_gamma(self, limit: int = 100) -> int:
        """
        从 Gamma API 同步热门市场
        
        Args:
            limit: 获取市场数量
            
        Returns:
            同步的市场数量
        """
        try:
            logger.info(f"从 Gamma API 同步市场 (limit={limit})...")
            
            markets = self.gamma_client.fetch_active_markets(limit=limit)
            
            if not markets:
                logger.warning("未获取到市场数据")
                return 0
            
            synced = 0
            for market_data in markets:
                try:
                    # 使用 market_decoder 计算 token IDs
                    condition_id = market_data.get('conditionId')
                    if not condition_id:
                        continue
                    
                    # 尝试从 clobTokenIds 获取
                    clob_tokens = market_data.get('clobTokenIds')
                    if clob_tokens:
                        try:
                            token_ids = json.loads(clob_tokens) if isinstance(clob_tokens, str) else clob_tokens
                            yes_token = token_ids[0] if len(token_ids) > 0 else None
                            no_token = token_ids[1] if len(token_ids) > 1 else None
                        except:
                            yes_token = None
                            no_token = None
                    else:
                        # 使用 market_decoder 计算
                        try:
                            yes_token, no_token = self.market_decoder.derive_token_ids(condition_id)
                        except:
                            yes_token = None
                            no_token = None
                    
                    market_record = {
                        'slug': market_data.get('slug'),
                        'question': market_data.get('question'),
                        'condition_id': condition_id,
                        'yes_token_id': yes_token,
                        'no_token_id': no_token,
                        'oracle': market_data.get('marketMakerAddress'),
                        'collateral_token': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',  # USDC.e
                        'category': market_data.get('category'),
                        'end_date': market_data.get('endDate'),
                        'volume': market_data.get('volumeNum', 0),
                        'liquidity': market_data.get('liquidityNum', 0),
                        'active': market_data.get('active', True),
                        'closed': market_data.get('closed', False),
                        'resolved': False
                    }
                    
                    self.store.upsert_market(market_record)
                    synced += 1
                    
                except Exception as e:
                    logger.warning(f"同步市场失败: {e}")
                    continue
            
            logger.info(f"✓ 同步完成: {synced} 个市场")
            return synced
            
        except Exception as e:
            logger.error(f"同步市场失败: {e}")
            return 0
    
    def run_batch(self, from_block: int, to_block: int) -> Dict[str, Any]:
        """
        处理单个批次
        
        Args:
            from_block: 起始区块
            to_block: 结束区块
            
        Returns:
            批次处理结果
        """
        result = {
            'from_block': from_block,
            'to_block': to_block,
            'logs_found': 0,
            'trades_parsed': 0,
            'trades_stored': 0
        }
        
        # 1. 获取日志
        logs = self.fetch_order_filled_logs(from_block, to_block)
        result['logs_found'] = len(logs)
        
        if not logs:
            return result
        
        # 2. 解析交易
        trade_tuples = self.process_logs_batch(logs)
        result['trades_parsed'] = len(trade_tuples)
        
        if not trade_tuples:
            return result
        
        # 3. 丰富市场信息并转换为字典
        trade_dicts = self.enrich_trades_with_market(trade_tuples)
        
        # 4. 存储
        stored = self.store_trades(trade_dicts)
        result['trades_stored'] = stored
        
        return result
    
    def run_indexer(self, 
                    from_block: Optional[int] = None,
                    to_block: Optional[int] = None,
                    continuous: bool = False,
                    sync_markets: bool = True) -> Dict[str, Any]:
        """
        运行索引器
        
        Args:
            from_block: 起始区块（默认从同步状态读取）
            to_block: 结束区块（默认为最新区块）
            continuous: 是否持续运行
            sync_markets: 是否先同步市场数据
            
        Returns:
            运行结果统计
        """
        logger.info("=" * 60)
        logger.info("  🚀 启动 Polymarket 索引器")
        logger.info("=" * 60)
        
        # 同步市场数据
        if sync_markets:
            self.sync_markets_from_gamma(limit=100)
        
        # 确定区块范围
        current_block = self.get_current_block()
        
        if from_block is None:
            sync_state = self.store.get_sync_state()
            from_block = sync_state.get('last_block', current_block - 1000)
        
        if to_block is None:
            to_block = current_block
        
        logger.info(f"📊 处理区块范围: {from_block:,} - {to_block:,} ({to_block - from_block:,} 个区块)")
        
        # 统计
        stats = {
            'status': 'running',
            'start_block': from_block,
            'end_block': to_block,
            'total_logs': 0,
            'total_trades_parsed': 0,
            'total_trades_stored': 0,
            'batches_processed': 0,
            'start_time': datetime.now().isoformat()
        }
        
        # 分批处理
        batch_start = from_block
        
        while batch_start <= to_block:
            batch_end = min(batch_start + self.BATCH_SIZE - 1, to_block)
            
            try:
                logger.info(f"📦 处理批次: {batch_start:,} - {batch_end:,}")
                
                result = self.run_batch(batch_start, batch_end)
                
                stats['total_logs'] += result['logs_found']
                stats['total_trades_parsed'] += result['trades_parsed']
                stats['total_trades_stored'] += result['trades_stored']
                stats['batches_processed'] += 1
                
                if result['logs_found'] > 0:
                    logger.info(f"   ✓ 日志: {result['logs_found']}, "
                               f"解析: {result['trades_parsed']}, "
                               f"存储: {result['trades_stored']}")
                
                # 更新同步状态
                self.store.update_sync_state(batch_end, stats['total_trades_stored'])
                
                batch_start = batch_end + 1
                
            except Exception as e:
                logger.error(f"❌ 批次处理失败: {e}")
                if not continuous:
                    stats['status'] = 'error'
                    stats['error'] = str(e)
                    return stats
                else:
                    # 持续模式下跳过失败批次
                    batch_start = batch_end + 1
                    continue
        
        stats['status'] = 'completed'
        stats['end_time'] = datetime.now().isoformat()
        
        logger.info("=" * 60)
        logger.info(f"✅ 索引完成!")
        logger.info(f"   总日志: {stats['total_logs']:,}")
        logger.info(f"   解析交易: {stats['total_trades_parsed']:,}")
        logger.info(f"   存储交易: {stats['total_trades_stored']:,}")
        logger.info("=" * 60)
        
        # 持续监听模式
        if continuous:
            logger.info("🔄 进入持续监听模式...")
            last_processed_block = to_block
            
            while True:
                try:
                    time.sleep(self.BLOCK_TIME)
                    
                    latest_block = self.get_current_block()
                    
                    if latest_block > last_processed_block:
                        new_from = last_processed_block + 1
                        logger.info(f"🆕 发现新区块: {new_from} - {latest_block}")
                        
                        result = self.run_batch(new_from, latest_block)
                        
                        stats['total_logs'] += result['logs_found']
                        stats['total_trades_parsed'] += result['trades_parsed']
                        stats['total_trades_stored'] += result['trades_stored']
                        
                        if result['trades_stored'] > 0:
                            logger.info(f"   ✓ 新存储 {result['trades_stored']} 笔交易")
                        
                        self.store.update_sync_state(latest_block, stats['total_trades_stored'])
                        last_processed_block = latest_block
                
                except KeyboardInterrupt:
                    logger.info("⏹ 用户中断，停止索引器")
                    break
                except Exception as e:
                    logger.error(f"持续监听出错: {e}")
                    continue
            
            stats['status'] = 'stopped'
            stats['end_time'] = datetime.now().isoformat()
        
        return stats


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="Polymarket 区块链索引器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 扫描最近 1000 个区块
  python run.py
  
  # 从指定区块开始
  python run.py --from-block 50000000
  
  # 持续监听新区块
  python run.py --continuous
  
  # 只同步市场数据
  python run.py --sync-markets-only
"""
    )
    parser.add_argument(
        "--rpc-url",
        type=str,
        default=os.getenv("RPC_URL", "https://polygon-rpc.com"),
        help="Polygon RPC URL"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=os.getenv("DB_PATH", "data/polymarket.db"),
        help="SQLite 数据库路径"
    )
    parser.add_argument(
        "--from-block",
        type=int,
        default=None,
        help="起始区块（默认从同步状态读取）"
    )
    parser.add_argument(
        "--to-block",
        type=int,
        default=None,
        help="结束区块（默认为最新区块）"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="持续监听新区块"
    )
    parser.add_argument(
        "--no-sync-markets",
        action="store_true",
        help="跳过市场数据同步"
    )
    parser.add_argument(
        "--sync-markets-only",
        action="store_true",
        help="只同步市场数据，不扫描区块"
    )
    
    args = parser.parse_args()
    
    try:
        indexer = PolymarketIndexer(
            rpc_url=args.rpc_url,
            db_path=args.db
        )
        
        if args.sync_markets_only:
            # 只同步市场
            synced = indexer.sync_markets_from_gamma(limit=100)
            logger.info(f"同步完成: {synced} 个市场")
        else:
            # 运行索引器
            result = indexer.run_indexer(
                from_block=args.from_block,
                to_block=args.to_block,
                continuous=args.continuous,
                sync_markets=not args.no_sync_markets
            )
            
            logger.info(f"最终结果: {json.dumps(result, indent=2, default=str)}")
    
    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"索引器运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
