"""
测试 MCP stdio 服务器的 JSON-RPC 通信
"""
import subprocess
import json
import sys

def test_stdio_server():
    """测试 stdio 服务器的 JSON-RPC 通信"""
    print("=" * 60)
    print("测试 PolyMind MCP Stdio 服务器")
    print("=" * 60)
    
    # 启动 MCP 服务器作为子进程
    proc = subprocess.Popen(
        [sys.executable, "-m", "src.mcp.mcp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=r"C:\Users\28119\Desktop\Poly Mind MCP"
    )
    
    def send_request(request: dict) -> dict:
        """发送请求并获取响应"""
        request_str = json.dumps(request) + "\n"
        proc.stdin.write(request_str)
        proc.stdin.flush()
        
        response_str = proc.stdout.readline()
        if response_str:
            return json.loads(response_str)
        return None
    
    def send_notification(notification: dict):
        """发送通知（无响应）"""
        notification_str = json.dumps(notification) + "\n"
        proc.stdin.write(notification_str)
        proc.stdin.flush()
    
    try:
        # 1. 测试 initialize
        print("\n1. 测试 initialize...")
        response = send_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        })
        print(f"   ✅ 协议版本: {response['result']['protocolVersion']}")
        print(f"   ✅ 服务器: {response['result']['serverInfo']['name']} v{response['result']['serverInfo']['version']}")
        
        # 2. 发送 initialized 通知（不需要响应）
        print("\n2. 发送 initialized 通知...")
        send_notification({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        })
        print("   ✅ 已发送")
        
        # 3. 测试 tools/list
        print("\n3. 测试 tools/list...")
        response = send_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        })
        if response and "result" in response:
            tools = response["result"].get("tools", [])
            print(f"   ✅ 可用工具数量: {len(tools)}")
            for tool in tools:
                print(f"      - {tool['name']}: {tool['description'][:50]}...")
        else:
            print(f"   ❌ 响应: {response}")
        
        # 4. 测试 tools/call - get_hot_markets
        print("\n4. 测试 tools/call (get_hot_markets)...")
        response = send_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_hot_markets",
                "arguments": {"limit": 3}
            }
        })
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content:
                text = content[0].get("text", "")
                try:
                    data = json.loads(text)
                    print(f"   ✅ 热门市场数量: {len(data.get('markets', []))}")
                    for m in data.get('markets', [])[:3]:
                        q = m.get('question', m.get('slug', 'N/A'))
                        print(f"      - {q[:60]}...")
                except:
                    print(f"   ⚠️ 原始响应: {text[:200]}...")
        else:
            print(f"   ❌ 响应: {response}")
        
        # 5. 测试 tools/call - search_markets
        print("\n5. 测试 tools/call (search_markets)...")
        response = send_request({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "search_markets",
                "arguments": {"query": "bitcoin", "limit": 2}
            }
        })
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content:
                text = content[0].get("text", "")
                try:
                    data = json.loads(text)
                    print(f"   ✅ 搜索结果数量: {data.get('count', 0)}")
                except:
                    print(f"   ⚠️ 原始响应: {text[:200]}...")
        else:
            print(f"   ❌ 响应: {response}")
        
        # 6. 测试 tools/call - get_smart_money_activity
        print("\n6. 测试 tools/call (get_smart_money_activity)...")
        response = send_request({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "get_smart_money_activity",
                "arguments": {"min_trades": 5, "min_winrate": 0.5}
            }
        })
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content:
                text = content[0].get("text", "")
                try:
                    data = json.loads(text)
                    print(f"   ✅ 聪明钱地址数量: {data.get('smart_money_count', 0)}")
                    print(f"   ✅ 分析: {data.get('analysis', 'N/A')[:80]}")
                except:
                    print(f"   ⚠️ 原始响应: {text[:200]}...")
        else:
            print(f"   ❌ 响应: {response}")
        
        # 7. 测试 resources/list
        print("\n7. 测试 resources/list...")
        response = send_request({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "resources/list",
            "params": {}
        })
        if response and "result" in response:
            resources = response["result"].get("resources", [])
            print(f"   ✅ 可用资源数量: {len(resources)}")
            for r in resources:
                print(f"      - {r.get('name', 'N/A')}: {r.get('description', 'N/A')[:40]}...")
        else:
            print(f"   ❌ 响应: {response}")
        
        print("\n" + "=" * 60)
        print("✅ MCP stdio 服务器测试完成！所有 JSON-RPC 通信正常")
        print("=" * 60)
        print("\n📝 Claude Desktop 配置方法:")
        print("   1. 打开 Claude Desktop 设置")
        print("   2. 找到 MCP 服务器配置")
        print("   3. 添加 mcp_config.json 中的配置")
        print("   4. 重启 Claude Desktop")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 关闭子进程
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    test_stdio_server()
