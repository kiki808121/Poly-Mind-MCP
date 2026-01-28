"""
PolyMind MCP - 统一启动脚本
启动 MCP API 服务器和前端看板
支持环境检查、索引器运行、Demo 演示等功能
"""
import os
import sys
import time
import argparse
import threading
import webbrowser
import http.server
import socketserver
import subprocess
import json
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DATA_DIR = PROJECT_ROOT / "data"

# 默认配置
DEFAULT_DB_PATH = DATA_DIR / "polymarket.db"
DEFAULT_MCP_PORT = 8888
DEFAULT_API_PORT = 8000
DEFAULT_FRONTEND_PORT = 3000

# 示例数据
SAMPLE_TX_HASH = "0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946"
SAMPLE_EVENT_SLUG = "will-there-be-another-us-government-shutdown-by-january-31"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """静默 HTTP 处理器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)
    
    def log_message(self, format, *args):
        pass  # 禁用请求日志
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()


def print_banner():
    """打印启动横幅"""
    print()
    print("=" * 60)
    print("  🧠 PolyMind MCP - AI 预测市场分析平台")
    print("=" * 60)
    print()


def check_environment() -> dict:
    """
    检查运行环境
    
    Returns:
        检查结果字典
    """
    results = {
        "python_version": sys.version,
        "rpc_url": None,
        "db_path": None,
        "dependencies": {},
        "errors": []
    }
    
    print("🔍 检查运行环境...\n")
    
    # 检查 Python 版本
    if sys.version_info < (3, 8):
        results["errors"].append("Python 版本需要 >= 3.8")
        print("❌ Python 版本过低，需要 >= 3.8")
    else:
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # 检查 RPC_URL
    rpc_url = os.getenv("RPC_URL")
    if rpc_url:
        results["rpc_url"] = rpc_url[:50] + "..." if len(rpc_url) > 50 else rpc_url
        print(f"✅ RPC_URL: {results['rpc_url']}")
    else:
        results["errors"].append("RPC_URL 未配置")
        print("❌ RPC_URL 未配置（请在 .env 文件中设置）")
    
    # 检查数据目录
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建数据目录: {DATA_DIR}")
    else:
        print(f"✅ 数据目录: {DATA_DIR}")
    
    # 检查关键依赖
    dependencies = ["web3", "flask", "fastapi", "requests", "dotenv"]
    for dep in dependencies:
        try:
            if dep == "dotenv":
                __import__("dotenv")
            else:
                __import__(dep)
            results["dependencies"][dep] = "✅"
            print(f"✅ {dep}")
        except ImportError:
            results["dependencies"][dep] = "❌"
            results["errors"].append(f"缺少依赖: {dep}")
            print(f"❌ {dep} (未安装)")
    
    # 检查数据库
    db_path = os.getenv("DB_PATH", str(DEFAULT_DB_PATH))
    results["db_path"] = db_path
    if Path(db_path).exists():
        # 检查数据库健康状态
        try:
            from src.db.schema import check_db_health
            health = check_db_health(db_path)
            if health.get("healthy"):
                counts = health.get("table_counts", {})
                print(f"✅ 数据库: {db_path}")
                print(f"   - 事件: {counts.get('events', 0)}")
                print(f"   - 市场: {counts.get('markets', 0)}")
                print(f"   - 交易: {counts.get('trades', 0)}")
            else:
                print(f"⚠️  数据库存在但可能损坏: {health.get('error')}")
        except Exception as e:
            print(f"⚠️  无法检查数据库: {e}")
    else:
        print(f"ℹ️  数据库尚未创建: {db_path}")
    
    print()
    
    if results["errors"]:
        print("⚠️  发现以下问题:")
        for error in results["errors"]:
            print(f"   - {error}")
        print()
    else:
        print("✅ 环境检查通过！\n")
    
    return results


def run_demo(tx_hash: str = None, event_slug: str = None, output_path: str = None):
    """
    运行演示：解码交易 + 解码市场
    
    Args:
        tx_hash: 交易哈希（默认使用示例）
        event_slug: 事件 slug（默认使用示例）
        output_path: 输出文件路径
    """
    tx_hash = tx_hash or SAMPLE_TX_HASH
    event_slug = event_slug or SAMPLE_EVENT_SLUG
    
    print("🎯 运行 Demo 演示...\n")
    
    rpc_url = os.getenv("RPC_URL")
    if not rpc_url:
        print("❌ 错误: RPC_URL 未配置")
        print("   请在 .env 文件中设置 RPC_URL")
        return
    
    results = {
        "demo": {
            "tx_hash": tx_hash,
            "event_slug": event_slug,
            "trades": [],
            "market": None,
            "errors": []
        }
    }
    
    # 1. 交易解码
    print(f"📊 解码交易: {tx_hash[:20]}...")
    try:
        from src.trade_decoder import TradeDecoder
        from dataclasses import asdict
        
        decoder = TradeDecoder(rpc_url)
        trades = decoder.decode_tx_logs(tx_hash)
        
        if trades:
            results["demo"]["trades"] = [asdict(t) for t in trades]
            print(f"   ✅ 解码到 {len(trades)} 笔交易")
            for t in trades:
                print(f"      - {t.side} @ {t.price} USDC")
        else:
            print("   ⚠️  未找到 OrderFilled 事件")
            
    except Exception as e:
        error = f"交易解码失败: {e}"
        results["demo"]["errors"].append(error)
        print(f"   ❌ {error}")
    
    print()
    
    # 2. 市场解码
    print(f"🏪 解码市场: {event_slug[:40]}...")
    try:
        from src.market_decoder import MarketDecoder
        from dataclasses import asdict
        
        decoder = MarketDecoder()
        market_params = decoder.decode_market_from_gamma_slug(event_slug)
        
        if market_params:
            results["demo"]["market"] = asdict(market_params)
            print(f"   ✅ Condition ID: {market_params.condition_id[:20]}...")
            print(f"   ✅ YES Token: {market_params.yes_token_id[:20]}...")
            print(f"   ✅ NO Token:  {market_params.no_token_id[:20]}...")
        else:
            print("   ⚠️  未找到市场信息")
            
    except Exception as e:
        error = f"市场解码失败: {e}"
        results["demo"]["errors"].append(error)
        print(f"   ❌ {error}")
    
    print()
    
    # 3. 验证交易归属
    if results["demo"]["trades"] and results["demo"]["market"]:
        print("🔗 验证交易归属...")
        market = results["demo"]["market"]
        for trade in results["demo"]["trades"]:
            token_id = trade.get("token_id", "")
            if token_id == market.get("yes_token_id"):
                trade["outcome"] = "YES"
                print(f"   ✅ 交易属于 YES 头寸")
            elif token_id == market.get("no_token_id"):
                trade["outcome"] = "NO"
                print(f"   ✅ 交易属于 NO 头寸")
            else:
                print(f"   ⚠️  Token ID 不匹配")
    
    print()
    
    # 4. 保存结果
    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"💾 结果已保存到: {output_path}")
        except Exception as e:
            print(f"❌ 保存失败: {e}")
    else:
        print("📝 Demo 结果:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
    
    print()
    print("✅ Demo 完成！")


def run_indexer(
    from_block: int = None,
    to_block: int = None,
    event_slug: str = None,
    reset_db: bool = False
):
    """
    运行索引器
    
    Args:
        from_block: 起始区块
        to_block: 结束区块
        event_slug: 事件 slug（用于市场发现）
        reset_db: 是否重置数据库
    """
    print("📡 启动索引器...\n")
    
    rpc_url = os.getenv("RPC_URL")
    db_path = os.getenv("DB_PATH", str(DEFAULT_DB_PATH))
    
    if not rpc_url:
        print("❌ 错误: RPC_URL 未配置")
        return
    
    # 初始化数据库
    from src.db.schema import init_db
    
    if reset_db and Path(db_path).exists():
        print(f"🗑️  重置数据库: {db_path}")
        Path(db_path).unlink()
    
    print(f"💾 数据库路径: {db_path}")
    conn = init_db(db_path)
    
    # 初始化索引器
    from src.indexer.run import PolymarketIndexer
    
    try:
        indexer = PolymarketIndexer(rpc_url, db_path)
        
        # 如果提供了 event_slug，先进行市场发现
        if event_slug:
            print(f"\n🔍 市场发现: {event_slug}")
            from src.market_decoder import MarketDecoder
            from src.indexer.store import DataStore
            
            decoder = MarketDecoder()
            store = DataStore(db_path)
            
            market_params = decoder.decode_market_from_gamma_slug(event_slug)
            if market_params:
                from dataclasses import asdict
                market_dict = asdict(market_params)
                market_dict['slug'] = event_slug
                store.upsert_market(market_dict)
                print(f"   ✅ 市场已保存")
        
        # 确定区块范围
        if from_block is None:
            # 从同步状态获取
            from src.indexer.store import DataStore
            store = DataStore(db_path)
            sync_state = store.get_sync_state()
            from_block = sync_state.get('last_block', 0)
            if from_block == 0:
                # 首次运行，从最近的区块开始
                from_block = indexer.web3.eth.block_number - 1000
        
        if to_block is None:
            to_block = indexer.web3.eth.block_number
        
        print(f"\n📦 区块范围: {from_block:,} - {to_block:,}")
        
        # 运行索引
        result = indexer.run_indexer(
            from_block=from_block,
            to_block=to_block,
            continuous=False,
            sync_markets=True
        )
        
        print(f"\n📊 索引结果:")
        print(f"   总日志: {result.get('total_logs', 0):,}")
        print(f"   解析交易: {result.get('total_trades_parsed', 0):,}")
        print(f"   存储交易: {result.get('total_trades_stored', 0):,}")
        
    except Exception as e:
        print(f"❌ 索引器错误: {e}")
        import traceback
        traceback.print_exc()


def start_frontend(port: int = DEFAULT_FRONTEND_PORT):
    """启动前端静态服务器"""
    try:
        with socketserver.TCPServer(("", port), QuietHandler) as httpd:
            httpd.serve_forever()
    except OSError as e:
        print(f"⚠️  前端端口 {port} 已被占用: {e}")


def start_mcp_server(port: int = DEFAULT_MCP_PORT):
    """启动 MCP API 服务器"""
    subprocess.run([
        sys.executable, "-m", "src.mcp.server",
        "--port", str(port)
    ], cwd=str(PROJECT_ROOT))


def start_api_server(port: int = DEFAULT_API_PORT):
    """启动 REST API 服务器"""
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "src.api.server:app",
        "--host", "0.0.0.0",
        "--port", str(port)
    ], cwd=str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(
        description="PolyMind MCP 启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python start.py --check              # 检查环境配置
  python start.py --demo               # 运行演示
  python start.py --mcp-only           # 仅启动 MCP 服务器
  python start.py                      # 启动完整服务

更多信息请参考 README.md
        """
    )
    
    # 模式选择
    parser.add_argument("--check", action="store_true", 
                       help="检查运行环境")
    parser.add_argument("--demo", action="store_true",
                       help="运行演示（解码交易和市场）")
    parser.add_argument("--indexer", action="store_true",
                       help="启动索引器")
    parser.add_argument("--mcp-only", action="store_true",
                       help="仅启动 MCP 服务器")
    parser.add_argument("--api-only", action="store_true",
                       help="仅启动 REST API 服务器")
    
    # 端口配置
    parser.add_argument("--frontend-port", type=int, default=DEFAULT_FRONTEND_PORT,
                       help=f"前端端口 (默认: {DEFAULT_FRONTEND_PORT})")
    parser.add_argument("--mcp-port", type=int, default=DEFAULT_MCP_PORT,
                       help=f"MCP 服务端口 (默认: {DEFAULT_MCP_PORT})")
    parser.add_argument("--api-port", type=int, default=DEFAULT_API_PORT,
                       help=f"REST API 端口 (默认: {DEFAULT_API_PORT})")
    
    # Demo 参数
    parser.add_argument("--tx-hash", type=str, default=SAMPLE_TX_HASH,
                       help="交易哈希（用于 demo）")
    parser.add_argument("--event-slug", type=str, default=SAMPLE_EVENT_SLUG,
                       help="事件 slug（用于 demo 和 indexer）")
    parser.add_argument("--output", type=str, default=None,
                       help="输出文件路径")
    
    # 索引器参数
    parser.add_argument("--from-block", type=int, default=None,
                       help="起始区块")
    parser.add_argument("--to-block", type=int, default=None,
                       help="结束区块")
    parser.add_argument("--reset-db", action="store_true",
                       help="重置数据库")
    
    # 其他
    parser.add_argument("--no-browser", action="store_true",
                       help="不自动打开浏览器")
    
    args = parser.parse_args()
    
    print_banner()
    
    # 环境检查模式
    if args.check:
        check_environment()
        return
    
    # Demo 模式
    if args.demo:
        run_demo(
            tx_hash=args.tx_hash,
            event_slug=args.event_slug,
            output_path=args.output
        )
        return
    
    # 索引器模式
    if args.indexer:
        run_indexer(
            from_block=args.from_block,
            to_block=args.to_block,
            event_slug=args.event_slug,
            reset_db=args.reset_db
        )
        return
    
    # 仅 MCP 服务器
    if args.mcp_only:
        print(f"🚀 MCP 服务器: http://localhost:{args.mcp_port}")
        start_mcp_server(args.mcp_port)
        return
    
    # 仅 REST API 服务器
    if args.api_only:
        print(f"🚀 REST API: http://localhost:{args.api_port}")
        start_api_server(args.api_port)
        return
    
    # 完整启动模式
    # 启动前端（后台线程）
    frontend_thread = threading.Thread(
        target=start_frontend,
        args=(args.frontend_port,),
        daemon=True
    )
    frontend_thread.start()
    print(f"✅ 前端看板: http://localhost:{args.frontend_port}")
    
    time.sleep(0.5)
    
    # 打开浏览器
    if not args.no_browser:
        webbrowser.open(f"http://localhost:{args.frontend_port}")
    
    print(f"🚀 MCP 服务器: http://localhost:{args.mcp_port}")
    print()
    print("按 Ctrl+C 停止服务")
    print("-" * 60)
    print()
    
    # 启动 MCP 服务器（主线程）
    try:
        start_mcp_server(args.mcp_port)
    except KeyboardInterrupt:
        print("\n✅ 服务已停止")


if __name__ == "__main__":
    main()
