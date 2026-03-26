"""
安全审计 - 评估模块
风险评估、影响分析
"""

import logging
from typing import List, Dict
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityAssessor:
    """安全评估器"""
    
    def __init__(self):
        self.risk_matrix = {
            "critical": {"impact": 4, "likelihood": 4},
            "high": {"impact": 3, "likelihood": 3},
            "medium": {"impact": 2, "likelihood": 2},
            "low": {"impact": 1, "likelihood": 1}
        }
    
    def assess(self, scan_results: Dict) -> Dict:
        """评估扫描结果"""
        logger.info("📊 开始安全评估...")
        
        vulnerabilities = scan_results.get("vulnerabilities", [])
        warnings = scan_results.get("warnings", [])
        
        assessment = {
            "assessment_time": datetime.now().isoformat(),
            "risk_level": "low",
            "risk_score": 0,
            "vuln_count": len(vulnerabilities),
            "warning_count": len(warnings),
            "findings": self._categorize_findings(vulnerabilities + warnings),
            "recommendations": []
        }
        
        # 计算风险分数
        assessment["risk_score"] = self._calculate_risk_score(assessment["findings"])
        assessment["risk_level"] = self._determine_risk_level(assessment["risk_score"])
        
        # 生成建议
        assessment["recommendations"] = self._generate_recommendations(assessment)
        
        logger.info(f"✅ 评估完成: 风险等级 {assessment['risk_level']}")
        return assessment
    
    def _categorize_findings(self, findings: List[Dict]) -> Dict:
        """分类发现的问题"""
        categorized = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        for finding in findings:
            severity = finding.get("severity", "low")
            if severity in categorized:
                categorized[severity].append(finding)
        
        return categorized
    
    def _calculate_risk_score(self, findings: Dict) -> int:
        """计算风险分数"""
        score = 0
        weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
        
        for severity, items in findings.items():
            score += len(items) * weights.get(severity, 0)
        
        return score
    
    def _determine_risk_level(self, score: int) -> str:
        """确定风险等级"""
        if score >= 20:
            return "critical"
        elif score >= 10:
            return "high"
        elif score >= 5:
            return "medium"
        else:
            return "low"
    
    def _generate_recommendations(self, assessment: Dict) -> List[Dict]:
        """生成修复建议"""
        recommendations = []
        
        findings = assessment["findings"]
        
        if findings["critical"]:
            recommendations.append({
                "priority": "critical",
                "action": "立即修复关键漏洞",
                "details": f"发现 {len(findings['critical'])} 个关键漏洞"
            })
        
        if findings["high"]:
            recommendations.append({
                "priority": "high",
                "action": "尽快修复高危问题",
                "details": f"发现 {len(findings['high'])} 个高危问题"
            })
        
        recommendations.append({
            "priority": "medium",
            "action": "建立定期安全审计",
            "details": "建议每月执行一次完整安全扫描"
        })
        
        return recommendations
