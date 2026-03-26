"""
效果追踪模块
监控发布后的表现数据
"""

from typing import Dict, List
from datetime import datetime, timedelta
from pathlib import Path
import json

class PerformanceTracker:
    """
    效果追踪器
    """
    
    def __init__(self, db_path: str = "data/tracking.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.tracking_data = self._load_data()
    
    def _load_data(self) -> Dict:
        """
        加载追踪数据
        """
        if self.db_path.exists():
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"records": []}
    
    def _save_data(self):
        """
        保存追踪数据
        """
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.tracking_data, f, ensure_ascii=False, indent=2)
    
    def track_content(self, content_id: str, metrics: Dict) -> Dict:
        """
        追踪内容表现
        """
        record = {
            "content_id": content_id,
            "tracked_at": datetime.now().isoformat(),
            "metrics": metrics
        }
        
        self.tracking_data["records"].append(record)
        self._save_data()
        
        return record
    
    def get_performance_report(self, content_id: str = None, days: int = 7) -> Dict:
        """
        获取表现报告
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        filtered_records = []
        for record in self.tracking_data["records"]:
            record_date = datetime.fromisoformat(record["tracked_at"])
            if record_date >= cutoff_date:
                if content_id is None or record["content_id"] == content_id:
                    filtered_records.append(record)
        
        # 计算汇总指标
        total_views = sum(r["metrics"].get("views", 0) for r in filtered_records)
        total_likes = sum(r["metrics"].get("likes", 0) for r in filtered_records)
        total_comments = sum(r["metrics"].get("comments", 0) for r in filtered_records)
        
        return {
            "period_days": days,
            "record_count": len(filtered_records),
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "top_performers": self._get_top_performers(filtered_records),
            "trends": self._calculate_trends(filtered_records)
        }
    
    def _get_top_performers(self, records: List[Dict], limit: int = 5) -> List[Dict]:
        """
        获取表现最好的内容
        """
        sorted_records = sorted(
            records,
            key=lambda x: x["metrics"].get("views", 0),
            reverse=True
        )
        
        return sorted_records[:limit]
    
    def _calculate_trends(self, records: List[Dict]) -> Dict:
        """
        计算趋势
        """
        if len(records) < 2:
            return {"direction": "insufficient_data"}
        
        first_half = records[:len(records)//2]
        second_half = records[len(records)//2:]
        
        first_avg = sum(r["metrics"].get("views", 0) for r in first_half) / len(first_half)
        second_avg = sum(r["metrics"].get("views", 0) for r in second_half) / len(second_half)
        
        if second_avg > first_avg * 1.1:
            direction = "up"
        elif second_avg < first_avg * 0.9:
            direction = "down"
        else:
            direction = "stable"
        
        return {
            "direction": direction,
            "first_half_avg": first_avg,
            "second_half_avg": second_avg
        }

# 测试
if __name__ == "__main__":
    tracker = PerformanceTracker()
    
    # 测试追踪
    tracker.track_content("test_001", {
        "views": 1000,
        "likes": 50,
        "comments": 10
    })
    
    tracker.track_content("test_002", {
        "views": 2000,
        "likes": 100,
        "comments": 20
    })
    
    report = tracker.get_performance_report(days=7)
    
    print("="*60)
    print("📈 表现报告")
    print("="*60)
    print(f"记录数: {report['record_count']}")
    print(f"总播放: {report['total_views']}")
    print(f"总点赞: {report['total_likes']}")
    print(f"趋势: {report['trends']['direction']}")
