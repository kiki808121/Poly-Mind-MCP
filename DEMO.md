# PolyMind MCP 演示说明

## 演示步骤

### 1. 环境准备

```bash
# 克隆/解压项目
cd "Poly Mind MCP"

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 POLYGON_RPC_URL
```

### 2. 运行索引器获取链上数据

```bash
# 索引 1000 个区块的交易数据（约 100-500 条交易）
python start.py index --from-block 66000000 --to-block 66001000

# 同步市场元数据
python start.py sync-markets
```

### 3. 验证数据

```bash
python verify_data.py
```

预期输出：
```
==================================================
📊 PolyMind MCP 数据验证报告
==================================================
交易记录: 4,592 条 ✅
市场数量: 101 个
事件数量: 0 个

📝 最近交易示例:
   0x916cad96dd5c219... | BUY @ 0.52 | 区块 66000123

✅ 满足黑客松最低要求（≥100 条交易）
```

### 4. 启动 MCP 服务

```bash
# 方式一：启动 HTTP API 服务器
python run_mcp_server.py
# 服务地址: http://localhost:8888

# 方式二：启动 MCP stdio 服务器（用于 Claude Desktop）
python -m src.mcp.mcp_server
```

### 5. 测试 API 端点

```bash
# 健康检查
curl http://localhost:8888/health

# 搜索市场
curl "http://localhost:8888/markets/search?q=trump"

# 获取热门市场
curl "http://localhost:8888/hot?limit=5"

# 获取聪明钱活动
curl "http://localhost:8888/smart-money?min_win_rate=55"

# 分析交易者
curl "http://localhost:8888/trader/0x1234567890abcdef1234567890abcdef12345678"

# 查找套利机会
curl "http://localhost:8888/arbitrage?limit=10"
```

### 6. 打开前端看板

```bash
cd frontend
python -m http.server 3000
```

访问 http://localhost:3000

---

## 预期输出

### 索引器输出

```
📡 启动 Polymarket 索引器...
✓ RPC 连接成功，链ID: 137
✓ 从 Gamma API 同步市场数据: 101 个市场
📊 开始索引区块范围: 66,000,000 - 66,001,000
  处理区块 66000000-66000050... 找到 23 个事件
  处理区块 66000050-66000100... 找到 45 个事件
  ...
✅ 索引完成! 
   总日志: 4,592
   解析交易: 4,592
   存储交易: 4,592
```

### API 响应示例

**GET /hot?limit=3**
```json
{
  "markets": [
    {
      "slug": "will-trump-win-2024",
      "question": "Will Trump win the 2024 presidential election?",
      "yes_price": 0.52,
      "no_price": 0.48,
      "volume": 15234567.89
    },
    {
      "slug": "will-bitcoin-reach-100k",
      "question": "Will Bitcoin reach $100,000 in 2024?",
      "yes_price": 0.35,
      "no_price": 0.65,
      "volume": 8901234.56
    }
  ],
  "count": 3,
  "sort_by": "volume",
  "timestamp": "2024-01-28T12:00:00.000000"
}
```

**GET /smart-money?min_win_rate=55**
```json
{
  "smart_money_addresses": [
    {
      "address": "0x1234...abcd",
      "full_address": "0x1234567890abcdef1234567890abcdef12345678",
      "trade_count": 156,
      "win_rate": 72.5,
      "total_volume": 45600.00,
      "recent_action": "BUY YES",
      "last_active": "2024-01-28T11:30:00"
    }
  ],
  "total_found": 20,
  "summary": "聪明钱整体偏向买入 (15买/5卖)",
  "timestamp": "2024-01-28T12:00:00.000000"
}
```

### MCP stdio 测试输出

```
============================================================
测试 PolyMind MCP Stdio 服务器
============================================================

1. 测试 initialize...
   ✅ 协议版本: 2024-11-05
   ✅ 服务器: polymind-mcp v1.0.0

2. 发送 initialized 通知...
   ✅ 已发送

3. 测试 tools/list...
   ✅ 可用工具数量: 9
      - get_market_info: 获取 Polymarket 市场详细信息...
      - search_markets: 搜索 Polymarket 市场...
      - analyze_trader: 分析交易者地址的行为模式...
      - get_trading_advice: 获取特定市场的交易建议...
      - find_arbitrage: 扫描所有市场，发现套利机会...
      - get_smart_money_activity: 获取聪明钱活动...
      - get_hot_markets: 获取当前热门市场...
      - analyze_market_relationship: 分析两个市场关系...
      - natural_language_query: 自然语言查询...

4. 测试 tools/call (get_hot_markets)...
   ✅ 热门市场数量: 3

============================================================
✅ MCP stdio 服务器测试完成！所有 JSON-RPC 通信正常
============================================================
```

---

## 截图

### 前端看板

![前端看板](screenshots/dashboard.png)

### API 测试

![API 测试](screenshots/api_test.png)

### MCP stdio 测试

![MCP stdio 测试](screenshots/mcp_stdio_test.png)

---

## 演示数据

### 示例交易哈希

```
0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946
```

可在 Polygonscan 验证: https://polygonscan.com/tx/0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946

### 示例市场

```
will-there-be-another-us-government-shutdown-by-january-31
```

Polymarket 链接: https://polymarket.com/event/will-there-be-another-us-government-shutdown-by-january-31

### 示例交易者地址

```
0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E
```

---

## Claude Desktop 集成演示

### 1. 配置 Claude Desktop

将以下内容添加到 Claude Desktop 配置文件：

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "polymind": {
      "command": "python",
      "args": ["-m", "src.mcp.mcp_server"],
      "cwd": "C:\\path\\to\\Poly Mind MCP",
      "env": {
        "PYTHONPATH": "C:\\path\\to\\Poly Mind MCP"
      }
    }
  }
}
```

### 2. 重启 Claude Desktop

### 3. 测试 MCP 工具

在 Claude Desktop 对话中输入：

- "搜索关于 Trump 的 Polymarket 市场"
- "分析地址 0x1234... 的交易风格"
- "查找当前的套利机会"
- "获取最热门的 5 个市场"
- "查看聪明钱最近的交易活动"

Claude 将自动调用 PolyMind MCP 工具并返回分析结果。

---

## 常见问题

### Q: 索引器运行很慢怎么办？

A: 减少区块范围，例如只索引 500 个区块：
```bash
python start.py index --from-block 66000000 --to-block 66000500
```

### Q: API 返回空数据？

A: 确保先运行索引器和市场同步：
```bash
python start.py index --from-block 66000000
python start.py sync-markets
```

### Q: 前端显示"离线"？

A: 确保 MCP 服务器正在运行：
```bash
python run_mcp_server.py
```
