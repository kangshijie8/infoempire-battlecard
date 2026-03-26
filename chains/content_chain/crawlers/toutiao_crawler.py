"""
今日头条热点数据采集器
标准化版本 - 继承 BaseCrawler
"""

import requests
import logging
from datetime import datetime
from typing import List, Dict

from .base_crawler import BaseCrawler, UnifiedItem, CompetitorData

logger = logging.getLogger(__name__)


class ToutiaoCrawler(BaseCrawler):
    """今日头条热点数据采集"""

    name = "toutiao"
    competitor = "今日头条"
    max_count = 20

    def __init__(self, category: str = 'news_hot'):
        super().__init__()
        self.category = category
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.toutiao.com',
        }

    def _fetch_raw(self) -> List[Dict]:
        """获取头条热点原始数据"""
        url = "https://www.toutiao.com/api/pc/feed/"
        params = {
            'category': self.category,
            'utm_source': 'toutiao',
            'widen': 1,
        }

        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=15)
            data = response.json()
            return data.get('data', [])[:self.max_count]
        except Exception as e:
            self.logger.error(f"头条API请求失败: {e}")
            return []

    def _normalize(self, raw: Dict) -> UnifiedItem:
        """头条数据标准化"""
        # 头条特有字段映射
        title = raw.get('title', '')
        abstract = raw.get('abstract', '')
        source = raw.get('source', '')

        # 时间戳可能是unix时间
        publish_time = raw.get('publish_time') or raw.get('ctime', '')
        if isinstance(publish_time, (int, float)):
            try:
                publish_time = datetime.fromtimestamp(publish_time).isoformat()
            except Exception:
                publish_time = str(publish_time)

        return UnifiedItem(
            source=self.name,
            competitor=source or self.competitor,
            title=title,
            content=abstract,
            url=raw.get('article_url', ''),
            timestamp=publish_time,
            metrics={
                'view': int(raw.get('read_count', 0) or 0),
                'comment': int(raw.get('comments_count', 0) or 0),
            },
        )


def create_toutiao_crawler() -> ToutiaoCrawler:
    return ToutiaoCrawler()
