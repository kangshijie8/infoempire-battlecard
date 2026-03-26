"""
内容采集层 - 标准化爬虫基类
================================
目标：统一所有爬虫的输出格式，适配 intel_chain CompetitorData

标准输出格式（UnifiedItem）：
{
    "source": str,        # 平台标识：toutiao/bilibili/douyin/aibase等
    "competitor": str,     # 竞品/作者/账号名称
    "title": str,        # 内容标题
    "content": str,      # 内容正文/摘要
    "url": str,          # 原文链接
    "timestamp": str,     # 发布时间（ISO格式）
    "metrics": {          # 量化指标（统一命名）
        "hot": int,       # 热度值（如抖音热搜值）
        "view": int,      # 阅读/播放量
        "like": int,      # 点赞数
        "comment": int,    # 评论数
        "share": int,     # 转发/分享数
        "rank": int,       # 排名（如热搜榜排名）
    }
}

使用说明：
    class MyCrawler(BaseCrawler):
        name = "myplatform"     # 平台标识
        competitor = "账号名"    # 竞品名称

        def _fetch_raw(self) -> List[Dict]:
            # 返回原始数据（平台特有字段）
            pass

        def _normalize(self, raw: Dict) -> UnifiedItem:
            # 将原始字段映射到标准格式
            pass
"""

import abc
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class UnifiedItem:
    """
    标准化采集项
    所有爬虫输出必须符合此格式
    """
    source: str = ""           # 平台标识
    competitor: str = ""         # 竞品/作者/账号
    title: str = ""              # 内容标题
    content: str = ""            # 内容摘要/正文
    url: str = ""                # 原文链接
    timestamp: str = ""           # 发布时间（ISO格式）
    metrics: Dict[str, Any] = field(default_factory=dict)  # 量化指标

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_raw(cls, source: str, raw: Dict) -> "UnifiedItem":
        """从原始数据创建标准化项（子类覆盖）"""
        return cls(source=source, title=raw.get("title", ""))


@dataclass
class CompetitorData:
    """
    intel_chain兼容格式
    用于对接 intel_chain.monitor.CompetitorData
    """
    source: str
    competitor: str
    title: str
    content: str
    url: str
    timestamp: str
    metrics: Dict

    @classmethod
    def from_unified(cls, item: UnifiedItem) -> "CompetitorData":
        return cls(
            source=item.source,
            competitor=item.competitor,
            title=item.title,
            content=item.content,
            url=item.url,
            timestamp=item.timestamp,
            metrics=item.metrics,
        )


class BaseCrawler(abc.ABC):
    """
    爬虫基类

    子类只需实现：
    - name: 平台标识
    - competitor: 默认竞品名称
    - _fetch_raw(): 返回原始数据列表
    - _normalize(): 单条数据标准化
    """

    name: str = "unknown"
    competitor: str = "未知"
    max_count: int = 20

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    @abc.abstractmethod
    def _fetch_raw(self) -> List[Dict]:
        """获取原始数据（子类实现）"""
        pass

    def _normalize(self, raw: Dict) -> UnifiedItem:
        """
        默认标准化映射（子类可覆盖）
        自动把常用字段名映射到标准格式
        """
        # 自动字段映射
        title = (
            raw.get("title") or
            raw.get("text") or
            raw.get("word") or
            raw.get("name") or
            ""
        )
        content = (
            raw.get("content") or
            raw.get("abstract") or
            raw.get("description") or
            raw.get("desc") or
            raw.get("summary") or
            raw.get("intro") or
            ""
        )
        url = (
            raw.get("url") or
            raw.get("link") or
            raw.get("share_url") or
            raw.get("item_url") or
            raw.get("article_url") or
            ""
        )

        # 时间戳标准化
        raw_time = (
            raw.get("timestamp") or
            raw.get("publish_time") or
            raw.get("ctime") or
            raw.get("mtime") or
            raw.get("create_time") or
            raw.get("crawl_time") or
            ""
        )
        if isinstance(raw_time, (int, float)):
            try:
                raw_time = datetime.fromtimestamp(raw_time).isoformat()
            except Exception:
                raw_time = str(raw_time)

        # 指标标准化
        metrics = {}
        for std_key, raw_keys in [
            ("hot",     ["hot", "hot_value", "hot_num"]),
            ("view",    ["view", "view_count", "views", "read_count", "play_count"]),
            ("like",    ["like", "like_count", "likes", "digg_count"]),
            ("comment", ["comment", "comment_count", "comments", "reply"]),
            ("share",   ["share", "share_count", "share_num", "repost"]),
            ("rank",    ["rank", "index", "position", "order"]),
        ]:
            for k in raw_keys:
                if k in raw and raw[k] is not None:
                    metrics[std_key] = int(raw[k])
                    break

        return UnifiedItem(
            source=self.name,
            competitor=self.competitor,
            title=title,
            content=content,
            url=url,
            timestamp=raw_time,
            metrics=metrics,
        )

    def crawl(self) -> List[UnifiedItem]:
        """执行采集"""
        self.logger.info(f"[{self.name}] 开始采集...")
        try:
            raw_list = self._fetch_raw()
            items = [self._normalize(raw) for raw in raw_list]
            items = [i for i in items if i.title]  # 过滤空标题
            self.logger.info(f"[{self.name}] 采集完成：{len(items)} 条")
            return items
        except Exception as e:
            self.logger.error(f"[{self.name}] 采集失败: {e}")
            return []

    def to_competitor_data(self) -> List[CompetitorData]:
        """转换为intel_chain格式"""
        return [CompetitorData.from_unified(item) for item in self.crawl()]

    def monitor_all(self) -> List[CompetitorData]:
        """兼容IntelTeam数据源接口（MonitorRole使用）"""
        return self.to_competitor_data()
