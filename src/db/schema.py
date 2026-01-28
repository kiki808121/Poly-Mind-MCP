"""
数据库Schema定义 - PolyMind MCP
支持 Polymarket 市场和交易数据存储
"""
import sqlite3
from typing import Optional, Dict, List, Any
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


# SQL Schema 定义
SCHEMA_SQL = """
-- 事件表：存储 Polymarket 事件信息
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug VARCHAR UNIQUE NOT NULL,
    title VARCHAR,
    description TEXT,
    neg_risk BOOLEAN DEFAULT 0,
    status VARCHAR DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 市场表：存储市场参数和 TokenId
CREATE TABLE IF NOT EXISTS markets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER,
    slug VARCHAR UNIQUE,
    condition_id VARCHAR UNIQUE NOT NULL,
    question_id VARCHAR,
    oracle VARCHAR,
    collateral_token VARCHAR DEFAULT '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
    yes_token_id VARCHAR NOT NULL,
    no_token_id VARCHAR NOT NULL,
    enable_neg_risk BOOLEAN DEFAULT 0,
    outcome_slot_count INTEGER DEFAULT 2,
    status VARCHAR DEFAULT 'active',
    title VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(event_id) REFERENCES events(id)
);

-- 交易表：存储链上 OrderFilled 事件解析结果
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id INTEGER,
    tx_hash VARCHAR NOT NULL,
    log_index INTEGER NOT NULL,
    block_number INTEGER,
    maker VARCHAR,
    taker VARCHAR,
    maker_asset_id VARCHAR,
    taker_asset_id VARCHAR,
    maker_amount VARCHAR,
    taker_amount VARCHAR,
    fee VARCHAR,
    side VARCHAR,
    outcome VARCHAR,
    price DECIMAL(20,8),
    size DECIMAL(20,8),
    token_id VARCHAR,
    exchange VARCHAR,
    order_hash VARCHAR,
    timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tx_hash, log_index),
    FOREIGN KEY(market_id) REFERENCES markets(id)
);

-- 同步状态表：记录索引器进度
CREATE TABLE IF NOT EXISTS sync_state (
    key VARCHAR PRIMARY KEY,
    last_block INTEGER DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 交易者画像表：存储分析结果
CREATE TABLE IF NOT EXISTS trader_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address VARCHAR UNIQUE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    total_volume DECIMAL(20,8) DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    loss_count INTEGER DEFAULT 0,
    win_rate DECIMAL(5,4) DEFAULT 0,
    labels TEXT,
    trading_style VARCHAR,
    last_trade_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_trades_market_id ON trades(market_id);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_block_number ON trades(block_number);
CREATE INDEX IF NOT EXISTS idx_trades_maker ON trades(maker);
CREATE INDEX IF NOT EXISTS idx_trades_taker ON trades(taker);
CREATE INDEX IF NOT EXISTS idx_trades_token_id ON trades(token_id);
CREATE INDEX IF NOT EXISTS idx_markets_condition_id ON markets(condition_id);
CREATE INDEX IF NOT EXISTS idx_markets_yes_token ON markets(yes_token_id);
CREATE INDEX IF NOT EXISTS idx_markets_no_token ON markets(no_token_id);
CREATE INDEX IF NOT EXISTS idx_trader_profiles_address ON trader_profiles(address);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    """
    初始化数据库
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        数据库连接
    """
    try:
        # 确保目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"创建数据库目录: {db_dir}")
        
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # 返回字典形式的行
        cursor = conn.cursor()
        
        # 启用外键约束
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # 创建表和索引
        cursor.executescript(SCHEMA_SQL)
        
        # 初始化同步状态
        cursor.execute("""
            INSERT OR IGNORE INTO sync_state (key, last_block, total_trades, updated_at)
            VALUES ('indexer', 0, 0, ?)
        """, (datetime.now().isoformat(),))
        
        conn.commit()
        logger.info(f"✓ 数据库初始化成功: {db_path}")
        return conn
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    获取数据库连接
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        数据库连接
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def dict_from_row(row: sqlite3.Row) -> Dict[str, Any]:
    """将 sqlite3.Row 转换为字典"""
    if row is None:
        return None
    return dict(row)


def check_db_health(db_path: str) -> Dict[str, Any]:
    """
    检查数据库健康状态
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        健康状态信息
    """
    try:
        if not os.path.exists(db_path):
            return {
                "healthy": False,
                "error": "数据库文件不存在",
                "db_path": db_path
            }
        
        conn = get_connection(db_path)
        cursor = conn.cursor()
        
        # 统计各表数据量
        tables = ["events", "markets", "trades", "sync_state", "trader_profiles"]
        counts = {}
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            except:
                counts[table] = 0
        
        # 获取同步状态
        cursor.execute("SELECT * FROM sync_state WHERE key = 'indexer'")
        sync_row = cursor.fetchone()
        sync_state = dict_from_row(sync_row) if sync_row else {}
        
        conn.close()
        
        return {
            "healthy": True,
            "db_path": db_path,
            "table_counts": counts,
            "sync_state": sync_state,
            "file_size_mb": round(os.path.getsize(db_path) / 1024 / 1024, 2)
        }
        
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "db_path": db_path
        }
