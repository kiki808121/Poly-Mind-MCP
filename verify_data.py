"""
数据验证脚本 - 检查是否满足黑客松要求
运行: python verify_data.py
"""
import sqlite3
import sys
import os
from datetime import datetime


def verify_data(db_path: str = "data/polymarket.db"):
    """验证数据库中的数据是否满足黑客松要求"""
    
    print("=" * 60)
    print("📊 PolyMind MCP 数据验证报告")
    print("=" * 60)
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"数据库路径: {db_path}")
    print("-" * 60)
    
    # 检查数据库是否存在
    if not os.path.exists(db_path):
        print(f"\n❌ 数据库文件不存在: {db_path}")
        print("\n💡 解决方案:")
        print("   1. 运行索引器获取链上数据:")
        print("      python start.py index --from-block 66000000 --to-block 66001000")
        print("   2. 同步市场数据:")
        print("      python start.py sync-markets")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\n📋 数据库表: {', '.join(tables) if tables else '无'}")
        
        # 2. 检查交易数量
        trade_count = 0
        if 'trades' in tables:
            cursor.execute("SELECT COUNT(*) FROM trades")
            trade_count = cursor.fetchone()[0]
        
        # 3. 检查市场数量
        market_count = 0
        if 'markets' in tables:
            cursor.execute("SELECT COUNT(*) FROM markets")
            market_count = cursor.fetchone()[0]
        
        # 4. 检查事件数量
        event_count = 0
        if 'events' in tables:
            cursor.execute("SELECT COUNT(*) FROM events")
            event_count = cursor.fetchone()[0]
        
        # 输出统计
        print("\n📈 数据统计:")
        trade_status = "✅" if trade_count >= 100 else "❌ (需要 ≥100)"
        print(f"   交易记录: {trade_count:,} 条 {trade_status}")
        print(f"   市场数量: {market_count:,} 个")
        print(f"   事件数量: {event_count:,} 个")
        
        # 5. 显示示例交易
        if trade_count > 0 and 'trades' in tables:
            print("\n📝 最近交易示例:")
            cursor.execute("""
                SELECT tx_hash, side, price, maker, block_number, outcome
                FROM trades 
                ORDER BY id DESC 
                LIMIT 5
            """)
            for row in cursor.fetchall():
                tx_hash = row[0][:20] + "..." if row[0] and len(row[0]) > 20 else row[0] or "N/A"
                side = row[1] or "?"
                price = f"{float(row[2]):.4f}" if row[2] else "N/A"
                block = row[4] or "N/A"
                outcome = row[5] or "?"
                print(f"   {tx_hash} | {side} {outcome} @ {price} | 区块 {block}")
        
        # 6. 显示示例市场
        if market_count > 0 and 'markets' in tables:
            print("\n🏪 示例市场:")
            # 尝试获取市场的可用列
            cursor.execute("PRAGMA table_info(markets)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # 选择合适的列
            if 'slug' in columns:
                if 'question' in columns:
                    cursor.execute("SELECT slug, question FROM markets ORDER BY id DESC LIMIT 3")
                elif 'title' in columns:
                    cursor.execute("SELECT slug, title FROM markets ORDER BY id DESC LIMIT 3")
                else:
                    cursor.execute("SELECT slug, slug FROM markets ORDER BY id DESC LIMIT 3")
                
                for row in cursor.fetchall():
                    slug = row[0] or "N/A"
                    desc = row[1][:50] + "..." if row[1] and len(row[1]) > 50 else row[1] or "N/A"
                    print(f"   {slug}")
                    print(f"      {desc}")
        
        # 7. 检查唯一交易者数量
        if trade_count > 0 and 'trades' in tables:
            cursor.execute("SELECT COUNT(DISTINCT maker) FROM trades")
            unique_traders = cursor.fetchone()[0]
            print(f"\n👥 唯一交易者: {unique_traders:,} 个")
        
        conn.close()
        
        # 8. 最终验证结果
        print("\n" + "=" * 60)
        if trade_count >= 100:
            print("✅ 验证通过！满足黑客松最低要求（≥100 条交易）")
            print("=" * 60)
            print("\n🚀 下一步:")
            print("   1. 启动 API 服务: python run_mcp_server.py")
            print("   2. 打开前端看板: cd frontend && python -m http.server 3000")
            print("   3. 运行 MCP 测试: python test_mcp_stdio.py")
            return True
        else:
            print(f"❌ 验证未通过！还需要 {100 - trade_count} 条交易记录")
            print("=" * 60)
            print("\n💡 解决方案:")
            print("   运行索引器获取更多数据:")
            print("   python start.py index --from-block 66000000 --to-block 66010000")
            return False
            
    except sqlite3.Error as e:
        print(f"\n❌ 数据库错误: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_api():
    """验证 API 服务是否正常运行"""
    print("\n" + "=" * 60)
    print("🔌 API 服务验证")
    print("=" * 60)
    
    try:
        import requests
        
        endpoints = [
            ("健康检查", "http://127.0.0.1:8888/health"),
            ("热门市场", "http://127.0.0.1:8888/hot?limit=3"),
            ("聪明钱活动", "http://127.0.0.1:8888/smart-money?min_win_rate=50"),
        ]
        
        all_passed = True
        for name, url in endpoints:
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    print(f"   ✅ {name}: 正常")
                else:
                    print(f"   ❌ {name}: HTTP {r.status_code}")
                    all_passed = False
            except requests.exceptions.ConnectionError:
                print(f"   ❌ {name}: 连接失败")
                all_passed = False
            except Exception as e:
                print(f"   ❌ {name}: {e}")
                all_passed = False
        
        if all_passed:
            print("\n✅ API 服务运行正常！")
        else:
            print("\n⚠️ 部分 API 端点异常")
            print("   请确保服务器正在运行: python run_mcp_server.py")
        
        return all_passed
        
    except ImportError:
        print("   ⚠️ 跳过 API 验证（需要 requests 库）")
        return None


def main():
    """主入口"""
    # 确定数据库路径
    db_path = "data/polymarket.db"
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    # 验证数据
    data_ok = verify_data(db_path)
    
    # 可选：验证 API
    if "--api" in sys.argv:
        verify_api()
    
    # 返回退出码
    sys.exit(0 if data_ok else 1)


if __name__ == "__main__":
    main()
