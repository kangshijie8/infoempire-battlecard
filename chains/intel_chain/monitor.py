"""
竞品情报 - 监控模块
采集竞品数据、社交媒体、新闻动态
"""

import requests
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CompetitorData:
    """竞品数据"""
    source: str
    competitor: str
    title: str
    content: str
    url: str
    timestamp: str
    metrics: Dict

class CompetitorMonitor:
    """竞品监控器"""
    
    def __init__(self, competitors: List[str] = None):
        self.competitors = competitors or []
        self.sources = {
            "news": self._monitor_news,
            "social": self._monitor_social,
            "tech": self._monitor_tech
        }
    
    def monitor_all(self) -> List[CompetitorData]:
        """监控所有来源"""
        all_data = []
        
        for source_name, monitor_func in self.sources.items():
            try:
                data = monitor_func()
                all_data.extend(data)
                logger.info(f"✅ {source_name}: 获取 {len(data)} 条")
            except Exception as e:
                logger.error(f"❌ {source_name}: 失败 - {e}")
        
        return all_data
    
    def _monitor_news(self) -> List[CompetitorData]:
        """监控新闻"""
        data = []
        
        # 示例：使用头条爬虫监控新闻
        try:
            from ..content_chain.crawlers.toutiao_crawler import ToutiaoCrawler
            crawler = ToutiaoCrawler()
            news = crawler.get_hot_news()
            
            for item in news:
                data.append(CompetitorData(
                    source="toutiao",
                    competitor="热点",
                    title=item.get("title", ""),
                    content=item.get("abstract", ""),
                    url="",
                    timestamp=item.get("crawl_time", ""),
                    metrics={
                        "comments": item.get("comments_count", 0),
                        "read": item.get("read_count", 0)
                    }
                ))
        except Exception as e:
            logger.warning(f"新闻监控失败: {e}")
        
        return data
    
    def _monitor_social(self) -> List[CompetitorData]:
        """监控社交媒体"""
        data = []
        
        # 示例：使用抖音爬虫监控热搜
        try:
            from ..content_chain.crawlers.douyin_crawler import DouyinHotSearchCrawler
            crawler = DouyinHotSearchCrawler()
            hotsearch = crawler.get_hot_search()
            
            for item in hotsearch:
                data.append(CompetitorData(
                    source="douyin",
                    competitor="热搜",
                    title=item.get("word", ""),
                    content="",
                    url="",
                    timestamp=item.get("event_time", ""),
                    metrics={
                        "hot": item.get("hot_value", 0),
                        "view": item.get("view_count", 0)
                    }
                ))
        except Exception as e:
            logger.warning(f"社交媒体监控失败: {e}")
        
        return data
    
    def _monitor_tech(self) -> List[CompetitorData]:
        """监控技术动态"""
        data = []
        
        # 示例：使用B站爬虫监控技术视频
        try:
            from ..content_chain.crawlers.bilibili_crawler import BilibiliCrawler
            crawler = BilibiliCrawler()
            videos = crawler.get_popular_videos()
            
            for item in videos:
                data.append(CompetitorData(
                    source="bilibili",
                    competitor=item.get("author", ""),
                    title=item.get("title", ""),
                    content=item.get("description", ""),
                    url="",
                    timestamp=item.get("crawl_time", ""),
                    metrics={
                        "view": item.get("view_count", 0),
                        "like": item.get("like_count", 0)
                    }
                ))
        except Exception as e:
            logger.warning(f"技术动态监控失败: {e}")
        
        return data
