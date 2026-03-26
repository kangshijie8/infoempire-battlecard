"""
信息帝国 - 爬虫模块（标准化版）

所有爬虫继承 BaseCrawler，统一输出 UnifiedItem 格式。
用法：
    from chains.content_chain.crawlers import ToutiaoCrawler, BilibiliCrawler
    items = crawler.crawl()  # List[UnifiedItem]
    competitor_data = crawler.to_competitor_data()  # List[CompetitorData]
"""

from .douyin_crawler import DouyinHotSearchCrawler
from .toutiao_crawler import ToutiaoCrawler
from .bilibili_crawler import BilibiliCrawler
from .base_crawler import BaseCrawler, UnifiedItem, CompetitorData

# 别名，方便导入
DouyinCrawler = DouyinHotSearchCrawler

__all__ = [
    # 基类
    "BaseCrawler",
    "UnifiedItem",
    "CompetitorData",
    # 爬虫
    "DouyinHotSearchCrawler",
    "DouyinCrawler",
    "ToutiaoCrawler",
    "BilibiliCrawler",
]
