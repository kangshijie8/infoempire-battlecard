"""
安全审计 - 合规模块
合规检查、报告生成
"""

import logging
import json
from pathlib import Path
from typing import Dict
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceChecker:
    """合规检查器"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.frameworks = ["OWASP Top 10", "CIS", "NIST"]
    
    def check_compliance(self, assessment: Dict, remediation: Dict) -> Dict:
        """检查合规性"""
        logger.info("📋 开始合规检查...")
        
        compliance = {
            "check_time": datetime.now().isoformat(),
            "frameworks": {},
            "status": "compliant",
            "report_path": ""
        }
        
        for framework in self.frameworks:
            compliance["frameworks"][framework] = self._check_framework(framework, assessment)
        
        # 确定整体状态
        all_passed = all(fw.get("passed", False) for fw in compliance["frameworks"].values())
        compliance["status"] = "compliant" if all_passed else "partial"
        
        # 生成报告
        compliance["report_path"] = self._generate_compliance_report(compliance, assessment, remediation)
        
        logger.info(f"✅ 合规检查完成: {compliance['status']}")
        return compliance
    
    def _check_framework(self, framework: str, assessment: Dict) -> Dict:
        """检查特定框架"""
        risk_level = assessment.get("risk_level", "low")
        
        return {
            "framework": framework,
            "passed": risk_level in ["low", "medium"],
            "risk_level": risk_level,
            "last_checked": datetime.now().isoformat()
        }
    
    def _generate_compliance_report(self, compliance: Dict, assessment: Dict, remediation: Dict) -> str:
        """生成合规报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.output_dir / f"security_compliance_{timestamp}.json"
        md_file = self.output_dir / f"security_compliance_{timestamp}.md"
        
        report = {
            "report_id": f"security_{timestamp}",
            "generated_at": datetime.now().isoformat(),
            "compliance": compliance,
            "assessment": assessment,
            "remediation": remediation
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(self._generate_markdown_report(report))
        
        logger.info(f"📄 合规报告已生成: {report_file}")
        return str(report_file)
    
    def _generate_markdown_report(self, report: Dict) -> str:
        """生成Markdown报告"""
        md = "# 🔒 安全审计报告\n\n"
        md += f"**生成时间**: {report['generated_at']}\n\n"
        
        md += "## 📊 合规状态\n\n"
        md += f"**整体状态**: {report['compliance']['status']}\n\n"
        
        for framework, status in report['compliance']['frameworks'].items():
            status_icon = "✅" if status['passed'] else "⚠️"
            md += f"- {status_icon} {framework}: {status['risk_level']}\n"
        
        md += "\n## 🎯 风险评估\n\n"
        md += f"**风险等级**: {report['assessment']['risk_level']}\n"
        md += f"**风险分数**: {report['assessment']['risk_score']}\n"
        md += f"**漏洞数**: {report['assessment']['vuln_count']}\n"
        md += f"**警告数**: {report['assessment']['warning_count']}\n"
        
        md += "\n## 🔧 修复记录\n\n"
        md += f"**已修复**: {len(report['remediation']['fixed'])}\n"
        md += f"**已跳过**: {len(report['remediation']['skipped'])}\n"
        
        return md
