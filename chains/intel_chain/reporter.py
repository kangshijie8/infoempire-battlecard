"""
竞品情报 - 报告模块
生成竞品情报报告
支持新旧两种分析格式（新格式：ai_analyzer的rich结构 + 老格式：rule-based的简化结构）
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging

from .monitor import CompetitorData
from .analyzer import IntelAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntelReporter:
    """竞品情报报告生成器"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_report(
        self, analysis: Dict, data: List[CompetitorData]
    ) -> Dict:
        """生成完整报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        report = {
            "report_id": f"intel_{timestamp}",
            "generated_at": datetime.now().isoformat(),
            "analysis": analysis,
            "raw_data_count": len(data),
            "ai_powered": analysis.get("ai_powered", False),
            "recommendations": self._generate_recommendations(analysis),
        }

        # 保存报告
        self._save_json(report, f"intel_report_{timestamp}.json")
        self._save_markdown(report, f"intel_report_{timestamp}.md")

        logger.info(f"✅ 报告已生成: intel_report_{timestamp}")
        return report

    def _generate_recommendations(self, analysis: Dict) -> List[Dict]:
        """从分析结果中提取行动建议（兼容新旧格式）"""
        recommendations = []

        # ── 趋势 ──────────────────────────────────────────────
        for trend in analysis.get("trends", [])[:3]:
            # 新格式: {keyword, description, evidence_count, severity, reasoning}
            # 老格式: {keyword, mentions, type}
            evidence = trend.get("evidence_count") or trend.get("mentions", 0)
            severity = trend.get("severity", "medium")
            keyword = trend.get("keyword", "未知")
            desc = trend.get("description", trend.get("reasoning", ""))
            recommendations.append({
                "type": "trend_follow",
                "priority": severity,
                "action": f"关注【{keyword}】趋势",
                "details": f"{desc}（证据:{evidence}条）",
            })

        # ── 机会 ──────────────────────────────────────────────
        for opp in analysis.get("opportunities", [])[:2]:
            # 新格式: {type, description, target_audience, difficulty, potential, action}
            # 老格式: {type, description, priority, reason}
            desc = opp.get("description", "未知机会")
            diff = opp.get("difficulty", opp.get("priority", "medium"))
            potential = opp.get("potential", "")
            action = opp.get("action", "")
            recommendations.append({
                "type": "opportunity",
                "priority": diff,
                "action": f"探索【{desc}】",
                "details": f"{'难度:'+diff} | {'潜力:'+potential if potential else ''} {action}",
            })

        # ── 风险 ──────────────────────────────────────────────
        for risk in analysis.get("risks", [])[:2]:
            # 新格式: {type, description, likelihood, impact, mitigation}
            # 老格式: {type, description, severity}
            desc = risk.get("description", "未知风险")
            severity = risk.get("impact") or risk.get("severity", "medium")
            mitigation = risk.get("mitigation", "提前准备预案")
            likelihood = risk.get("likelihood", "")
            recommendations.append({
                "type": "risk_mitigation",
                "priority": severity,
                "action": f"应对【{desc}】",
                "details": f"{'概率:'+likelihood if likelihood else ''} | 应对:{mitigation}",
            })

        # ── 深度洞察（仅新格式有） ─────────────────────────────
        for insight in analysis.get("insights", [])[:3]:
            recommendations.append({
                "type": "insight",
                "priority": "high",
                "action": f"深度洞察: {insight[:50]}...",
                "details": insight,
            })

        return recommendations

    def _save_json(self, data: Dict, filename: str):
        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_markdown(self, report: Dict, filename: str):
        filepath = self.output_dir / filename
        analysis = report["analysis"]
        ai_tag = "🤖 AI驱动" if report.get("ai_powered") else "📊 规则驱动"

        md_lines = [
            "# 📊 竞品情报报告\n",
            f"**生成时间**: {report['generated_at']}  {ai_tag}\n",
            f"**数据量**: {report['raw_data_count']} 条\n",
            "\n## 📈 分析摘要\n",
            f"{analysis.get('summary', 'N/A')}\n",
            "\n## 🎯 热门趋势\n",
        ]

        # 趋势
        for trend in analysis.get("trends", [])[:5]:
            kw = trend.get("keyword", "未知")
            ev = trend.get("evidence_count") or trend.get("mentions", 0)
            sev = trend.get("severity", "medium")
            reason = trend.get("reasoning", trend.get("description", ""))
            md_lines.append(f"- **{kw}** [{sev}] 证据:{ev}条\n")
            if reason:
                md_lines.append(f"  - {reason}\n")

        # 机会
        md_lines.extend(["\n## 💡 机会发现\n"])
        for opp in analysis.get("opportunities", []):
            desc = opp.get("description", "未知")
            diff = opp.get("difficulty") or opp.get("priority", "medium")
            potential = opp.get("potential", "")
            action = opp.get("action", "")
            md_lines.append(f"- **{desc}** [难度:{diff}]\n")
            if potential:
                md_lines.append(f"  - 潜力:{potential}\n")
            if action:
                md_lines.append(f"  - 行动:{action}\n")

        # 风险
        md_lines.extend(["\n## ⚠️ 风险提示\n"])
        for risk in analysis.get("risks", []):
            desc = risk.get("description", "未知")
            impact = risk.get("impact") or risk.get("severity", "medium")
            mitigation = risk.get("mitigation", "提前准备预案")
            likelihood = risk.get("likelihood", "")
            md_lines.append(f"- **{desc}** [影响:{impact}]\n")
            if likelihood:
                md_lines.append(f"  - 发生概率:{likelihood}\n")
            md_lines.append(f"  - 应对:{mitigation}\n")

        # 洞察
        insights = analysis.get("insights", [])
        if insights:
            md_lines.extend(["\n## 🔍 深度洞察\n"])
            for i, insight in enumerate(insights[:3], 1):
                md_lines.append(f"{i}. {insight}\n")

        # 行动建议
        md_lines.extend(["\n## 🚀 行动建议\n"])
        for i, rec in enumerate(report.get("recommendations", [])[:8], 1):
            priority = rec.get("priority", "medium")
            action = rec.get("action", "")
            details = rec.get("details", "")
            md_lines.append(f"{i}. **{action}** [{priority}]\n")
            if details:
                md_lines.append(f"   {details}\n")

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(md_lines)
