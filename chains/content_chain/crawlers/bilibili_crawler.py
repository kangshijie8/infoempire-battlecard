"""
B站热门视频数据采集器
标准化版本 - 继承 BaseCrawler
"""

import requests
import logging
from datetime import datetime
from typing import List, Dict

from .base_crawler import BaseCrawler, UnifiedItem

logger = logging.getLogger(__name__)


class BilibiliCrawler(BaseCrawler):
    """B站热门视频数据采集"""

    name = "bilibili"
    competitor = "B站"
    max_count = 20

    def __init__(self):
        super().__init__()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.bilibili.com',
        }

    def _fetch_raw(self) -> List[Dict]:
        """获取B站热门视频原始数据"""
        url = "https://api.bilibili.com/x/web-interface/popular"
        params = {'pn': 1, 'ps': self.max_count}

        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=15)
            data = response.json()
            if data.get('code') == 0:
                return data.get('data', {}).get('list', [])
        except Exception as e:
            self.logger.error(f"B站API请求失败: {e}")
        return []

    def _normalize(self, raw: Dict) -> UnifiedItem:
        """B站数据标准化"""
        stat = raw.get('stat', {})

        return UnifiedItem(
            source=self.name,
            competitor=raw.get('owner', {}).get('name', self.competitor),
            title=raw.get('title', ''),
            content=raw.get('desc', ''),
            url=f"https://www.bilibili.com/video/{raw.get('bvid', '')}",
            timestamp=datetime.fromtimestamp(raw.get('pubdate', 0)).isoformat() if raw.get('pubdate') else '',
            metrics={
                'view': int(stat.get('view', 0) or 0),
                'like': int(stat.get('like', 0) or 0),
                'comment': int(stat.get('reply', 0) or 0),
                'share': int(stat.get('share', 0) or 0),
            },
        )


def create_bilibili_crawler() -> BilibiliCrawler:
    return BilibiliCrawler()
