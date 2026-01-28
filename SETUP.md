# PolyMind MCP 快速安装指南

本指南帮助你在 **5 分钟内** 完成项目配置和运行。

## 📋 前置要求

- Python 3.10+
- Git
- 免费的 Polygon RPC 账户（[Alchemy](https://www.alchemy.com/) 或 [Infura](https://www.infura.io/)）

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/poly-mind-mcp.git
cd poly-mind-mcp
```

### 2. 创建虚拟环境

**Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件，填入你的配置
```

**必需配置：**
```env
# Polygon RPC URL（从 Alchemy/Infura 获取）
RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY
```

**可选配置：**
```env
# OpenAI API Key（启用 AI 分析功能）
OPENAI_API_KEY=sk-xxx

# 数据库路径
DB_PATH=./data/polymarket.db
```

### 5. 初始化数据库

```bash
# 创建数据目录
mkdir -p data

# 同步市场数据（从 Gamma API）
python start.py --demo
```

### 6. 启动服务

**方式一：启动 HTTP API**
```bash
python run_mcp_server.py
```

访问 http://localhost:8888 查看 API 文档

**方式二：启动完整服务（API + 前端）**
```bash
python start.py
```

- API: http://localhost:8888
- 前端看板: http://localhost:3000

### 7. 验证安装

```bash
# 验证数据
python verify_data.py

# 测试 MCP stdio 协议
python test_mcp_stdio.py
```

## 🔧 Claude Desktop 配置

将以下配置添加到 Claude Desktop 配置文件：

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "polymind": {
      "command": "python",
      "args": ["-m", "src.mcp.mcp_server"],
      "cwd": "你的项目完整路径",
      "env": {
        "PYTHONPATH": "你的项目完整路径"
      }
    }
  }
}
```

重启 Claude Desktop 后，即可在对话中使用 PolyMind MCP 工具。

## 📊 索引链上数据（可选）

如需索引更多链上交易数据：

```bash
# 索引最近 1000 个区块
python start.py --indexer --from-block 82230000 --to-block 82231000

# 持续索引（后台运行）
python start.py --indexer
```

## 🛠️ 常见问题

### Q: RPC 请求失败？
A: 检查 RPC URL 是否正确，确保有足够的请求配额。免费 RPC 推荐使用 Alchemy 或 Infura。

### Q: OpenAI API 错误？
A: `OPENAI_API_KEY` 是可选的。不配置时，系统会使用规则引擎替代 LLM 分析。

### Q: 前端无法连接后端？
A: 确保 API 服务器在端口 8888 运行，检查防火墙设置。

### Q: 如何重置数据库？
```bash
rm data/polymarket.db
python start.py --demo
```

## 📚 更多文档

- [README.md](README.md) - 完整项目文档
- [DEMO.md](DEMO.md) - 演示流程
- [mcp_config.json](mcp_config.json) - Claude Desktop 配置示例

## 🆘 获取帮助

如有问题，请提交 GitHub Issue 或联系项目维护者。

---

**Happy Trading! 🎯**
