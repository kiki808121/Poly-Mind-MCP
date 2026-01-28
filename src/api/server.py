"""
PolyMind MCP - REST API 服务器
用于查询已索引的 Polymarket 交易数据
"""
import os
import sys
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, Query, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from db.schema import get_connection, init_db, check_db_health
from indexer.store import DataStore

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="PolyMind 交易查询 API",
    description="Polymarket 链上数据查询服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库路径
DB_PATH = os.getenv("DB_PATH", "data/polymarket.db")


# ========== 数据模型 ==========

class TradeResponse(BaseModel):
    """交易数据"""
    id: int
    market_id: Optional[int] = None
    tx_hash: str
    log_index: int
    block_number: Optional[int] = None
    maker: Optional[str] = None
    taker: Optional[str] = None
    side: Optional[str] = None
    outcome: Optional[str] = None
    price: Optional[float] = None
    size: Optional[float] = None
    token_id: Optional[str] = None
    exchange: Optional[str] = None
    timestamp: Optional[str] = None


class MarketResponse(BaseModel):
    """市场数据"""
    id: int
    slug: Optional[str] = None
    condition_id: str
    question_id: Optional[str] = None
    oracle: Optional[str] = None
    collateral_token: Optional[str] = None
    yes_token_id: str
    no_token_id: str
    enable_neg_risk: Optional[bool] = False
    status: Optional[str] = None
    title: Optional[str] = None
    created_at: Optional[str] = None


class TradeListResponse(BaseModel):
    """交易列表响应"""
    total: int
    limit: int
    offset: int
    trades: List[TradeResponse]


class MarketStatsResponse(BaseModel):
    """市场统计响应"""
    trade_count: int
    total_volume: float
    avg_price: float
    min_price: float
    max_price: float
    first_trade_at: Optional[str] = None
    last_trade_at: Optional[str] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str
    db_healthy: bool
    markets_count: int
    trades_count: int
    timestamp: str


# ========== 辅助函数 ==========

def get_store() -> DataStore:
    """获取 DataStore 实例"""
    return DataStore(DB_PATH)


# ========== API 端点 ==========

@app.get("/", tags=["基础"])
async def root() -> Dict[str, str]:
    """API 根端点"""
    return {
        "name": "PolyMind 交易查询 API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["基础"])
async def health_check() -> HealthResponse:
    """
    健康检查端点
    
    返回系统状态和统计信息
    """
    try:
        health = check_db_health(DB_PATH)
        
        if health.get("healthy"):
            counts = health.get("table_counts", {})
            return HealthResponse(
                status="ok",
                service="PolyMind API",
                db_healthy=True,
                markets_count=counts.get("markets", 0),
                trades_count=counts.get("trades", 0),
                timestamp=datetime.now().isoformat()
            )
        else:
            return HealthResponse(
                status="degraded",
                service="PolyMind API",
                db_healthy=False,
                markets_count=0,
                trades_count=0,
                timestamp=datetime.now().isoformat()
            )
            
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return HealthResponse(
            status="error",
            service="PolyMind API",
            db_healthy=False,
            markets_count=0,
            trades_count=0,
            timestamp=datetime.now().isoformat()
        )


@app.get("/status", tags=["基础"])
async def get_status() -> Dict[str, Any]:
    """获取索引器状态"""
    try:
        store = get_store()
        sync_state = store.get_sync_state()
        overall = store.get_overall_stats()
        
        return {
            "last_block": sync_state.get("last_block", 0),
            "total_trades": sync_state.get("total_trades", 0),
            "updated_at": sync_state.get("updated_at"),
            "stats": overall
        }
        
    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ========== 事件端点 ==========

@app.get("/events/{slug}", tags=["事件"])
async def get_event(
    slug: str = Path(..., description="事件 slug")
) -> Dict[str, Any]:
    """获取事件详情"""
    store = get_store()
    event = store.fetch_event_by_slug(slug)
    
    if not event:
        raise HTTPException(status_code=404, detail=f"事件未找到: {slug}")
    
    return {"event": event}


@app.get("/events/{slug}/markets", tags=["事件"])
async def get_event_markets(
    slug: str = Path(..., description="事件 slug"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """获取事件下的所有市场"""
    store = get_store()
    event = store.fetch_event_by_slug(slug)
    
    if not event:
        raise HTTPException(status_code=404, detail=f"事件未找到: {slug}")
    
    # 获取该事件下的市场
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM markets 
            WHERE event_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (event['id'], limit, offset))
        
        rows = cursor.fetchall()
        markets = [dict(row) for row in rows]
        
        cursor.execute("SELECT COUNT(*) FROM markets WHERE event_id = ?", (event['id'],))
        total = cursor.fetchone()[0]
        
        return {
            "event": event,
            "markets": markets,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    finally:
        conn.close()


# ========== 市场端点 ==========

@app.get("/markets", tags=["市场"])
async def list_markets(
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
) -> Dict[str, Any]:
    """获取市场列表"""
    store = get_store()
    markets = store.fetch_all_markets(limit=limit, offset=offset)
    
    return {
        "markets": markets,
        "limit": limit,
        "offset": offset
    }


@app.get("/markets/{slug}", tags=["市场"])
async def get_market(
    slug: str = Path(..., description="市场 slug")
) -> Dict[str, Any]:
    """
    获取市场详情和统计数据
    
    Args:
        slug: 市场 slug
        
    Returns:
        市场信息和统计数据
    """
    logger.info(f"查询市场: {slug}")
    
    store = get_store()
    market = store.fetch_market_by_slug(slug)
    
    if not market:
        raise HTTPException(status_code=404, detail=f"市场未找到: {slug}")
    
    stats = store.get_market_stats(market_id=market['id'])
    
    return {
        "market": market,
        "stats": stats
    }


@app.get("/markets/{slug}/trades", response_model=TradeListResponse, tags=["市场"])
async def get_market_trades(
    slug: str = Path(..., description="市场 slug"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    cursor: int = Query(0, ge=0, alias="offset", description="偏移量"),
    from_block: Optional[int] = Query(None, alias="fromBlock", description="起始区块"),
    to_block: Optional[int] = Query(None, alias="toBlock", description="结束区块")
) -> TradeListResponse:
    """
    获取市场交易记录
    
    Args:
        slug: 市场 slug
        limit: 返回数量 (1-1000)
        cursor: 分页偏移量
        from_block: 起始区块过滤
        to_block: 结束区块过滤
        
    Returns:
        交易列表
    """
    logger.info(f"查询市场交易: {slug}, limit={limit}, offset={cursor}")
    
    store = get_store()
    market = store.fetch_market_by_slug(slug)
    
    if not market:
        raise HTTPException(status_code=404, detail=f"市场未找到: {slug}")
    
    trades, total = store.fetch_trades_for_market(
        market_id=market['id'],
        limit=limit,
        offset=cursor,
        from_block=from_block,
        to_block=to_block
    )
    
    # 转换为响应模型
    trade_responses = []
    for t in trades:
        trade_responses.append(TradeResponse(
            id=t.get('id', 0),
            market_id=t.get('market_id'),
            tx_hash=t.get('tx_hash', ''),
            log_index=t.get('log_index', 0),
            block_number=t.get('block_number'),
            maker=t.get('maker'),
            taker=t.get('taker'),
            side=t.get('side'),
            outcome=t.get('outcome'),
            price=float(t.get('price', 0)) if t.get('price') else None,
            size=float(t.get('size', 0)) if t.get('size') else None,
            token_id=t.get('token_id'),
            exchange=t.get('exchange'),
            timestamp=t.get('timestamp')
        ))
    
    return TradeListResponse(
        total=total,
        limit=limit,
        offset=cursor,
        trades=trade_responses
    )


# ========== Token 端点 ==========

@app.get("/tokens/{token_id}/trades", response_model=TradeListResponse, tags=["Token"])
async def get_token_trades(
    token_id: str = Path(..., description="ERC-1155 Token ID"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    cursor: int = Query(0, ge=0, alias="offset", description="偏移量")
) -> TradeListResponse:
    """
    通过 TokenId 获取交易记录
    
    Args:
        token_id: ERC-1155 Token ID (十六进制或十进制)
        limit: 返回数量 (1-1000)
        cursor: 分页偏移量
        
    Returns:
        交易列表
    """
    logger.info(f"查询 TokenId 交易: {token_id[:20]}..., limit={limit}, offset={cursor}")
    
    store = get_store()
    trades, total = store.fetch_trades_by_token(
        token_id=token_id,
        limit=limit,
        offset=cursor
    )
    
    if total == 0:
        raise HTTPException(status_code=404, detail=f"TokenId 未找到交易: {token_id}")
    
    # 转换为响应模型
    trade_responses = []
    for t in trades:
        trade_responses.append(TradeResponse(
            id=t.get('id', 0),
            market_id=t.get('market_id'),
            tx_hash=t.get('tx_hash', ''),
            log_index=t.get('log_index', 0),
            block_number=t.get('block_number'),
            maker=t.get('maker'),
            taker=t.get('taker'),
            side=t.get('side'),
            outcome=t.get('outcome'),
            price=float(t.get('price', 0)) if t.get('price') else None,
            size=float(t.get('size', 0)) if t.get('size') else None,
            token_id=t.get('token_id'),
            exchange=t.get('exchange'),
            timestamp=t.get('timestamp')
        ))
    
    return TradeListResponse(
        total=total,
        limit=limit,
        offset=cursor,
        trades=trade_responses
    )


# ========== 交易者端点 ==========

@app.get("/traders/{address}/trades", response_model=TradeListResponse, tags=["交易者"])
async def get_trader_trades(
    address: str = Path(..., description="交易者地址"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    cursor: int = Query(0, ge=0, alias="offset", description="偏移量")
) -> TradeListResponse:
    """
    获取交易者的交易记录
    
    Args:
        address: 交易者钱包地址
        limit: 返回数量 (1-1000)
        cursor: 分页偏移量
        
    Returns:
        交易列表
    """
    logger.info(f"查询交易者: {address[:10]}..., limit={limit}, offset={cursor}")
    
    store = get_store()
    trades, total = store.fetch_trades_by_address(
        address=address,
        limit=limit,
        offset=cursor
    )
    
    if total == 0:
        raise HTTPException(status_code=404, detail=f"未找到该地址的交易: {address}")
    
    # 转换为响应模型
    trade_responses = []
    for t in trades:
        trade_responses.append(TradeResponse(
            id=t.get('id', 0),
            market_id=t.get('market_id'),
            tx_hash=t.get('tx_hash', ''),
            log_index=t.get('log_index', 0),
            block_number=t.get('block_number'),
            maker=t.get('maker'),
            taker=t.get('taker'),
            side=t.get('side'),
            outcome=t.get('outcome'),
            price=float(t.get('price', 0)) if t.get('price') else None,
            size=float(t.get('size', 0)) if t.get('size') else None,
            token_id=t.get('token_id'),
            exchange=t.get('exchange'),
            timestamp=t.get('timestamp')
        ))
    
    return TradeListResponse(
        total=total,
        limit=limit,
        offset=cursor,
        trades=trade_responses
    )


# ========== 启动函数 ==========

def main():
    """启动 API 服务器"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PolyMind REST API 服务器")
    parser.add_argument("--port", type=int, default=8000, help="服务端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="绑定地址")
    parser.add_argument("--db", type=str, default=None, help="数据库路径")
    args = parser.parse_args()
    
    global DB_PATH
    if args.db:
        DB_PATH = args.db
    
    logger.info(f"启动 API 服务器: {args.host}:{args.port}")
    logger.info(f"数据库路径: {DB_PATH}")
    logger.info(f"API 文档: http://localhost:{args.port}/docs")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
