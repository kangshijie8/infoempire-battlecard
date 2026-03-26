"""
竞品情报 - 预警模块
实时监控、异常预警、推送通知
"""

import logging
from typing import List, Dict
from datetime import datetime
from collections import deque

from .monitor import CompetitorData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntelAlerter:
    """竞品情报预警器"""
    
    def __init__(self, threshold_hot: int = 1000000):
        self.threshold_hot = threshold_hot
        self.alert_history = deque(maxlen=100)
        self.keywords_to_watch = ["AI", "爬虫", "MCP", "Agent", "大模型"]
    
    def check_alerts(self, data: List[CompetitorData]) -> List[Dict]:
        """检查预警"""
        alerts = []
        
        for item in data:
            # 高热度预警
            hot_value = item.metrics.get("hot", 0) or item.metrics.get("view", 0)
            if hot_value > self.threshold_hot:
                alerts.append({
                    "type": "high_hot",
                    "severity": "high",
                    "item": item,
                    "message": f"高热度: {item.title} ({hot_value:,})",
                    "timestamp": datetime.now().isoformat()
                })
            
            # 关键词预警
            for keyword in self.keywords_to_watch:
                if keyword in item.title or keyword in item.content:
                    alerts.append({
                        "type": "keyword_match",
                        "severity": "medium",
                        "item": item,
                        "keyword": keyword,
                        "message": f"关键词触发: {keyword} - {item.title}",
                        "timestamp": datetime.now().isoformat()
                    })
                    break
        
        # 记录历史
        for alert in alerts:
            self.alert_history.append(alert)
        
        logger.info(f"🔔 发现 {len(alerts)} 条预警")
        return alerts
    
    def get_alert_summary(self) -> Dict:
        """获取预警摘要"""
        summary = {
            "total_alerts": len(self.alert_history),
            "by_type": {},
            "by_severity": {},
            "recent": list(self.alert_history)[-10:]
        }
        
        for alert in self.alert_history:
            alert_type = alert["type"]
            severity = alert["severity"]
            
            summary["by_type"][alert_type] = summary["by_type"].get(alert_type, 0) + 1
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
        
        return summary
