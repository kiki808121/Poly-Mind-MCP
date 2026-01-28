"""启动 MCP HTTP 服务器的简易脚本"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.mcp.server import create_app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("MCP_PORT", 8888))
    host = os.getenv("MCP_HOST", "0.0.0.0")
    print(f"🚀 PolyMind MCP Server starting on http://{host}:{port}")
    print(f"📌 可访问地址: http://localhost:{port}")
    print(f"📌 API 文档: http://localhost:{port}/")
    print("=" * 50)
    try:
        app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
    except Exception as e:
        print(f"❌ 服务器错误: {e}")
