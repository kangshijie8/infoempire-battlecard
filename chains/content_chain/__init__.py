"""
信息帝国 - 内容产业链

整合:
- 采集器 (抖音/头条/B站)
- 分析器 (热点分析/趋势预测)
- 生成器 (AI内容生成)
- SEO优化器
- 发布器 (多平台发布)
- 追踪器 (效果追踪)
- 变现模块 (收益统计)
"""

from .crawlers.douyin_crawler import DouyinHotSearchCrawler
from .crawlers.toutiao_crawler import ToutiaoCrawler
from .crawlers.bilibili_crawler import BilibiliCrawler
from .analyzer import HotspotAnalyzer
from .generator import ContentGenerator
from .seo_optimizer import SEOOptimizer
from .publisher import ContentPublisher
from .tracker import PerformanceTracker as ContentTracker
from .monetization import ContentChain

# 别名
DouyinCrawler = DouyinHotSearchCrawler

__all__ = [
    "DouyinHotSearchCrawler",
    "DouyinCrawler",
    "ToutiaoCrawler",
    "BilibiliCrawler",
    "HotspotAnalyzer",
    "ContentGenerator",
    "SEOOptimizer",
    "ContentPublisher",
    "ContentTracker",
    "ContentChain",
]
