"""启动 MCP HTTP 服务器的简易脚本"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.mcp.server import create_app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("MCP_PORT", 8888))
    print(f"🚀 PolyMind MCP Server starting on http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False, threaded=True)
