"""
数据存储层 - PolyMind MCP
提供市场和交易数据的 CRUD 操作
"""
import sqlite3
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataStore:
    """数据存储管理器"""
    
    def __init__(self, db_path: str):
        """
        初始化存储管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ========== 事件操作 ==========
    
    def upsert_event(self, event: Dict[str, Any]) -> int:
        """
        插入或更新事件
        
        Args:
            event: 事件数据 {slug, title, description, neg_risk, status}
            
        Returns:
            事件 ID
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO events (slug, title, description, neg_risk, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    neg_risk = excluded.neg_risk,
                    status = excluded.status,
                    updated_at = excluded.updated_at
            """, (
                event.get('slug'),
                event.get('title'),
                event.get('description'),
                event.get('neg_risk', False),
                event.get('status', 'active'),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            
            # 获取事件 ID
            cursor.execute("SELECT id FROM events WHERE slug = ?", (event.get('slug'),))
            row = cursor.fetchone()
            event_id = row[0] if row else 0
            
            logger.debug(f"✓ 事件已保存: {event.get('slug')} (ID: {event_id})")
            return event_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"保存事件失败: {e}")
            raise
        finally:
            conn.close()
    
    def fetch_event_by_slug(self, slug: str) -> Optional[Dict]:
        """根据 slug 获取事件"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM events WHERE slug = ?", (slug,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    # ========== 市场操作 ==========
    
    def upsert_market(self, market: Dict[str, Any]) -> int:
        """
        插入或更新市场
        
        Args:
            market: 市场数据
            
        Returns:
            市场 ID
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO markets (
                    event_id, slug, condition_id, question_id, oracle,
                    collateral_token, yes_token_id, no_token_id,
                    enable_neg_risk, outcome_slot_count, status, title, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(condition_id) DO UPDATE SET
                    slug = excluded.slug,
                    question_id = excluded.question_id,
                    oracle = excluded.oracle,
                    collateral_token = excluded.collateral_token,
                    yes_token_id = excluded.yes_token_id,
                    no_token_id = excluded.no_token_id,
                    enable_neg_risk = excluded.enable_neg_risk,
                    outcome_slot_count = excluded.outcome_slot_count,
                    status = excluded.status,
                    title = excluded.title,
                    updated_at = excluded.updated_at
            """, (
                market.get('event_id'),
                market.get('slug'),
                market.get('condition_id'),
                market.get('question_id'),
                market.get('oracle'),
                market.get('collateral_token', '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'),
                market.get('yes_token_id'),
                market.get('no_token_id'),
                market.get('enable_neg_risk', False),
                market.get('outcome_slot_count', 2),
                market.get('status', 'active'),
                market.get('title'),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            
            # 获取市场 ID
            cursor.execute("SELECT id FROM markets WHERE condition_id = ?", 
                          (market.get('condition_id'),))
            row = cursor.fetchone()
            market_id = row[0] if row else 0
            
            logger.debug(f"✓ 市场已保存: {market.get('slug')} (ID: {market_id})")
            return market_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"保存市场失败: {e}")
            raise
        finally:
            conn.close()
    
    def fetch_market_by_slug(self, slug: str) -> Optional[Dict]:
        """根据 slug 获取市场"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM markets WHERE slug = ?", (slug,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def fetch_market_by_condition_id(self, condition_id: str) -> Optional[Dict]:
        """根据 condition_id 获取市场"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM markets WHERE condition_id = ?", (condition_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def fetch_market_by_token_id(self, token_id: str) -> Optional[Dict]:
        """根据 TokenId 获取市场（匹配 YES 或 NO）"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM markets 
                WHERE yes_token_id = ? OR no_token_id = ?
            """, (token_id, token_id))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def fetch_all_markets(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取所有市场"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM markets 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    # ========== 交易操作 ==========
    
    def insert_trade(self, trade: Dict[str, Any]) -> bool:
        """
        插入单条交易（幂等，重复插入会被忽略）
        
        Args:
            trade: 交易数据
            
        Returns:
            是否成功插入
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO trades (
                    market_id, tx_hash, log_index, block_number,
                    maker, taker, maker_asset_id, taker_asset_id,
                    maker_amount, taker_amount, fee,
                    side, outcome, price, size, token_id,
                    exchange, order_hash, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.get('market_id'),
                trade.get('tx_hash'),
                trade.get('log_index'),
                trade.get('block_number'),
                trade.get('maker'),
                trade.get('taker'),
                trade.get('maker_asset_id'),
                trade.get('taker_asset_id'),
                trade.get('maker_amount'),
                trade.get('taker_amount'),
                trade.get('fee'),
                trade.get('side'),
                trade.get('outcome'),
                trade.get('price'),
                trade.get('size'),
                trade.get('token_id'),
                trade.get('exchange'),
                trade.get('order_hash'),
                trade.get('timestamp', datetime.now().isoformat())
            ))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            conn.rollback()
            logger.error(f"插入交易失败: {e}")
            return False
        finally:
            conn.close()
    
    def insert_trades(self, trades: List[Dict[str, Any]]) -> int:
        """
        批量插入交易（幂等）
        
        Args:
            trades: 交易列表
            
        Returns:
            成功插入的数量
        """
        if not trades:
            return 0
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        inserted = 0
        
        try:
            for trade in trades:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO trades (
                            market_id, tx_hash, log_index, block_number,
                            maker, taker, maker_asset_id, taker_asset_id,
                            maker_amount, taker_amount, fee,
                            side, outcome, price, size, token_id,
                            exchange, order_hash, timestamp
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade.get('market_id'),
                        trade.get('tx_hash'),
                        trade.get('log_index'),
                        trade.get('block_number'),
                        trade.get('maker'),
                        trade.get('taker'),
                        trade.get('maker_asset_id'),
                        trade.get('taker_asset_id'),
                        trade.get('maker_amount'),
                        trade.get('taker_amount'),
                        trade.get('fee'),
                        trade.get('side'),
                        trade.get('outcome'),
                        trade.get('price'),
                        trade.get('size'),
                        trade.get('token_id'),
                        trade.get('exchange'),
                        trade.get('order_hash'),
                        trade.get('timestamp', datetime.now().isoformat())
                    ))
                    
                    if cursor.rowcount > 0:
                        inserted += 1
                        
                except sqlite3.IntegrityError:
                    # 重复数据，跳过
                    continue
                except Exception as e:
                    logger.warning(f"插入交易出错: {e}")
                    continue
            
            conn.commit()
            logger.info(f"✓ 批量插入完成: {inserted}/{len(trades)} 条交易")
            return inserted
            
        except Exception as e:
            conn.rollback()
            logger.error(f"批量插入交易失败: {e}")
            return 0
        finally:
            conn.close()
    
    def fetch_trades_for_market(
        self,
        market_id: int = None,
        market_slug: str = None,
        limit: int = 100,
        offset: int = 0,
        from_block: int = None,
        to_block: int = None
    ) -> Tuple[List[Dict], int]:
        """
        获取市场的交易记录
        
        Args:
            market_id: 市场 ID
            market_slug: 市场 slug（二选一）
            limit: 返回数量限制
            offset: 偏移量
            from_block: 起始区块
            to_block: 结束区块
            
        Returns:
            (交易列表, 总数)
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 如果传入 slug，先获取 market_id
            if market_slug and not market_id:
                cursor.execute("SELECT id FROM markets WHERE slug = ?", (market_slug,))
                row = cursor.fetchone()
                if row:
                    market_id = row[0]
                else:
                    return [], 0
            
            # 构建查询条件
            conditions = ["market_id = ?"]
            params = [market_id]
            
            if from_block:
                conditions.append("block_number >= ?")
                params.append(from_block)
            
            if to_block:
                conditions.append("block_number <= ?")
                params.append(to_block)
            
            where_clause = " AND ".join(conditions)
            
            # 获取总数
            cursor.execute(f"SELECT COUNT(*) FROM trades WHERE {where_clause}", params)
            total = cursor.fetchone()[0]
            
            # 获取交易
            cursor.execute(f"""
                SELECT * FROM trades 
                WHERE {where_clause}
                ORDER BY block_number DESC, log_index DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])
            
            rows = cursor.fetchall()
            trades = [dict(row) for row in rows]
            
            return trades, total
            
        finally:
            conn.close()
    
    def fetch_trades_by_token(
        self,
        token_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """根据 TokenId 获取交易"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 获取总数
            cursor.execute(
                "SELECT COUNT(*) FROM trades WHERE token_id = ?",
                (token_id,)
            )
            total = cursor.fetchone()[0]
            
            # 获取交易
            cursor.execute("""
                SELECT * FROM trades 
                WHERE token_id = ?
                ORDER BY block_number DESC, log_index DESC
                LIMIT ? OFFSET ?
            """, (token_id, limit, offset))
            
            rows = cursor.fetchall()
            trades = [dict(row) for row in rows]
            
            return trades, total
            
        finally:
            conn.close()
    
    def fetch_trades_by_address(
        self,
        address: str,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """根据交易者地址获取交易"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 获取总数
            cursor.execute("""
                SELECT COUNT(*) FROM trades 
                WHERE maker = ? OR taker = ?
            """, (address, address))
            total = cursor.fetchone()[0]
            
            # 获取交易
            cursor.execute("""
                SELECT * FROM trades 
                WHERE maker = ? OR taker = ?
                ORDER BY block_number DESC, log_index DESC
                LIMIT ? OFFSET ?
            """, (address, address, limit, offset))
            
            rows = cursor.fetchall()
            trades = [dict(row) for row in rows]
            
            return trades, total
            
        finally:
            conn.close()
    
    # ========== 同步状态操作 ==========
    
    def get_sync_state(self, key: str = 'indexer') -> Dict:
        """获取同步状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM sync_state WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {'key': key, 'last_block': 0, 'total_trades': 0}
        finally:
            conn.close()
    
    def update_sync_state(
        self,
        last_block: int,
        total_trades: int = None,
        key: str = 'indexer'
    ) -> None:
        """更新同步状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            if total_trades is not None:
                cursor.execute("""
                    INSERT INTO sync_state (key, last_block, total_trades, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        last_block = excluded.last_block,
                        total_trades = excluded.total_trades,
                        updated_at = excluded.updated_at
                """, (key, last_block, total_trades, datetime.now().isoformat()))
            else:
                cursor.execute("""
                    INSERT INTO sync_state (key, last_block, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        last_block = excluded.last_block,
                        updated_at = excluded.updated_at
                """, (key, last_block, datetime.now().isoformat()))
            
            conn.commit()
            logger.debug(f"✓ 同步状态已更新: block={last_block}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"更新同步状态失败: {e}")
        finally:
            conn.close()
    
    # ========== 统计操作 ==========
    
    def get_market_stats(self, market_id: int = None, market_slug: str = None) -> Dict:
        """获取市场统计信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 获取 market_id
            if market_slug and not market_id:
                cursor.execute("SELECT id FROM markets WHERE slug = ?", (market_slug,))
                row = cursor.fetchone()
                if row:
                    market_id = row[0]
                else:
                    return {}
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as trade_count,
                    COALESCE(SUM(size), 0) as total_volume,
                    COALESCE(AVG(price), 0) as avg_price,
                    COALESCE(MIN(price), 0) as min_price,
                    COALESCE(MAX(price), 0) as max_price,
                    MIN(timestamp) as first_trade_at,
                    MAX(timestamp) as last_trade_at
                FROM trades
                WHERE market_id = ?
            """, (market_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'trade_count': row[0],
                    'total_volume': float(row[1]),
                    'avg_price': float(row[2]),
                    'min_price': float(row[3]),
                    'max_price': float(row[4]),
                    'first_trade_at': row[5],
                    'last_trade_at': row[6]
                }
            return {}
            
        finally:
            conn.close()
    
    def get_overall_stats(self) -> Dict:
        """获取整体统计信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM events")
            event_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM markets")
            market_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM trades")
            trade_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COALESCE(SUM(size), 0) FROM trades")
            total_volume = cursor.fetchone()[0]
            
            return {
                'event_count': event_count,
                'market_count': market_count,
                'trade_count': trade_count,
                'total_volume': float(total_volume)
            }
            
        finally:
            conn.close()
    
    def get_token_to_market_mapping(self) -> Dict[str, Dict]:
        """
        获取 token_id 到市场的映射
        
        Returns:
            {token_id: {'slug': ..., 'condition_id': ..., 'outcome': 'YES'/'NO'}}
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT slug, condition_id, yes_token_id, no_token_id 
                FROM markets 
                WHERE yes_token_id IS NOT NULL OR no_token_id IS NOT NULL
            """)
            rows = cursor.fetchall()
            
            mapping = {}
            for row in rows:
                slug, condition_id, yes_token, no_token = row
                if yes_token:
                    mapping[yes_token] = {
                        'slug': slug,
                        'condition_id': condition_id,
                        'outcome': 'YES'
                    }
                if no_token:
                    mapping[no_token] = {
                        'slug': slug,
                        'condition_id': condition_id,
                        'outcome': 'NO'
                    }
            
            return mapping
            
        finally:
            conn.close()


# 便捷函数，兼容旧代码

def upsert_market(conn_or_path, market: Dict) -> int:
    """兼容函数：插入或更新市场"""
    if isinstance(conn_or_path, str):
        store = DataStore(conn_or_path)
    else:
        store = DataStore(conn_or_path)
    return store.upsert_market(market)


def insert_trades(conn_or_path, trades: List[Dict]) -> int:
    """兼容函数：批量插入交易"""
    if isinstance(conn_or_path, str):
        store = DataStore(conn_or_path)
    else:
        store = DataStore(conn_or_path)
    return store.insert_trades(trades)


def fetch_market_by_slug(conn_or_path, slug: str) -> Optional[Dict]:
    """兼容函数：根据 slug 获取市场"""
    if isinstance(conn_or_path, str):
        store = DataStore(conn_or_path)
    else:
        store = DataStore(conn_or_path)
    return store.fetch_market_by_slug(slug)


def fetch_trades_for_market(
    conn_or_path,
    market_id: int,
    limit: int = 100,
    offset: int = 0
) -> Tuple[List[Dict], int]:
    """兼容函数：获取市场交易"""
    if isinstance(conn_or_path, str):
        store = DataStore(conn_or_path)
    else:
        store = DataStore(conn_or_path)
    return store.fetch_trades_for_market(market_id=market_id, limit=limit, offset=offset)
