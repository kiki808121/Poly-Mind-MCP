"""
Gamma API集成

Gamma API 是 Polymarket 官方提供的 REST API，用于获取市场、事件等数据。
"""
import requests
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class GammaAPIClient:
    """Gamma API客户端"""
    
    def __init__(self, base_url: str = "https://gamma-api.polymarket.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PolyMind-MCP/1.0',
            'Accept': 'application/json'
        })
    
    def fetch_event(self, slug: str) -> Optional[Dict]:
        """获取事件信息"""
        try:
            url = f"{self.base_url}/events/{slug}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取事件失败: {e}")
            return None
    
    def fetch_market(self, slug: str) -> Optional[Dict]:
        """获取市场信息"""
        try:
            url = f"{self.base_url}/markets/{slug}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取市场失败: {e}")
            return None
    
    def fetch_event_markets(self, event_slug: str) -> List[Dict]:
        """获取事件下的所有市场"""
        try:
            url = f"{self.base_url}/events/{event_slug}/markets"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取事件市场列表失败: {e}")
            return []
    
    def fetch_active_markets(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        获取活跃市场列表
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            市场列表
        """
        try:
            url = f"{self.base_url}/markets"
            params = {
                'limit': limit,
                'offset': offset,
                'active': 'true',
                'closed': 'false'
            }
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取活跃市场失败: {e}")
            return []
    
    def search_markets(self, query: str, limit: int = 10) -> List[Dict]:
        """
        搜索市场
        
        Args:
            query: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            匹配的市场列表
        """
        try:
            url = f"{self.base_url}/markets"
            params = {
                'limit': limit,
                '_q': query
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"搜索市场失败: {e}")
            return []
    
    def fetch_market_by_condition_id(self, condition_id: str) -> Optional[Dict]:
        """
        通过 condition_id 获取市场
        
        Args:
            condition_id: 条件ID
            
        Returns:
            市场信息或 None
        """
        try:
            url = f"{self.base_url}/markets"
            params = {
                'conditionId': condition_id
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            markets = response.json()
            return markets[0] if markets else None
        except Exception as e:
            logger.error(f"通过 condition_id 获取市场失败: {e}")
            return None
    
    def fetch_events(self, limit: int = 50, active: bool = True) -> List[Dict]:
        """
        获取事件列表
        
        Args:
            limit: 返回数量限制
            active: 是否只返回活跃事件
            
        Returns:
            事件列表
        """
        try:
            url = f"{self.base_url}/events"
            params = {
                'limit': limit,
                'active': 'true' if active else 'false'
            }
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取事件列表失败: {e}")
            return []
