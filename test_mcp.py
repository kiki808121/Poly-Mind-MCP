"""测试 MCP 工具和 API 功能"""
import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.mcp.tools import PolymarketTools

def main():
    print("=" * 60)
    print("  🧪 PolyMind MCP 工具测试")
    print("=" * 60)
    print()
    
    tools = PolymarketTools()
    
    # 1. 测试热门市场
    print("📊 测试 get_hot_markets:")
    result = tools.execute_tool('get_hot_markets', {'limit': 3, 'sort_by': 'volume'})
    if 'error' not in result:
        print(f"   ✅ 获取到 {result.get('count', 0)} 个热门市场")
        for m in result.get('markets', [])[:3]:
            title = m.get('title', 'Unknown')[:50]
            price = m.get('yes_price', 0)
            print(f"      - {title}... (YES: {price:.2f})")
    else:
        print(f"   ❌ 错误: {result.get('error')}")
    print()
    
    # 2. 测试搜索市场
    print("🔍 测试 search_markets:")
    result = tools.execute_tool('search_markets', {'query': 'bitcoin', 'limit': 3})
    if 'error' not in result:
        print(f"   ✅ 找到 {result.get('count', 0)} 个匹配市场")
        for m in result.get('results', [])[:3]:
            title = m.get('title', 'Unknown')[:50]
            print(f"      - {title}...")
    else:
        print(f"   ❌ 错误: {result.get('error')}")
    print()
    
    # 3. 测试聪明钱活动
    print("💰 测试 get_smart_money_activity:")
    result = tools.execute_tool('get_smart_money_activity', {'min_win_rate': 50})
    if 'error' not in result:
        print(f"   ✅ 找到 {result.get('total_found', 0)} 个高胜率地址")
        print(f"   摘要: {result.get('summary', 'N/A')}")
        for addr in result.get('smart_money_addresses', [])[:3]:
            print(f"      - {addr.get('address')} (胜率: {addr.get('win_rate')}%)")
    else:
        print(f"   ❌ 错误: {result.get('error')}")
    print()
    
    # 4. 测试套利扫描
    print("📈 测试 find_arbitrage:")
    result = tools.execute_tool('find_arbitrage', {'limit': 5})
    if 'error' not in result:
        print(f"   ✅ 找到 {result.get('count', 0)} 个套利机会")
        for opp in result.get('opportunities', [])[:3]:
            print(f"      - {opp.get('market_a_title', 'Unknown')[:30]}...")
            print(f"        潜在收益: {opp.get('potential_profit', 0):.2f}%")
    else:
        print(f"   ❌ 错误: {result.get('error')}")
    print()
    
    # 5. 测试工具定义
    print("🛠️ 可用工具列表:")
    for tool in tools.get_tool_definitions():
        name = tool['function']['name']
        desc = tool['function']['description'][:50]
        print(f"   - {name}: {desc}...")
    print()
    
    print("=" * 60)
    print("  ✅ MCP 工具测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
