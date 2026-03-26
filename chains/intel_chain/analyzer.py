"""
竞品情报 - 分析模块
分析竞品数据、识别趋势、发现机会
原rule-based逻辑已废弃，改用AI分析（ai_analyzer.py）
"""

import logging
from typing import List, Dict
from datetime import datetime

from .monitor import CompetitorData
from . import ai_analyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntelAnalyzer:
    """
    竞品情报分析器

    优先使用AI分析（依赖Bailian API）。
    API key无效时自动降级到规则分析。
    """

    def __init__(self):
        self._ai: ai_analyzer.AIIntelAnalyzer = ai_analyzer.AIIntelAnalyzer()

    def analyze(self, data: List[CompetitorData]) -> Dict:
        """
        分析竞品数据

        内部委托给 ai_analyzer.AIIntelAnalyzer，
        返回格式兼容原有字段（ai_analyzer会补全所有字段）。
        """
        logger.info(f"📊 开始分析 {len(data)} 条竞品数据（AI模式={self._ai.use_ai}）")

        result = self._ai.analyze(data)

        logger.info("✅ 分析完成")
        return result
