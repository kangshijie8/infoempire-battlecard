"""
信息帝国爬虫 - 集成你的超级爬虫
抖音+头条+B站，无需登录，完全自动化
同时实现项目信息收集功能
"""

from typing import Dict, List
from datetime import datetime
from pathlib import Path
import json
import logging

try:
    from .douyin_crawler import DouyinHotSearchCrawler
    from .bilibili_crawler import BilibiliCrawler
    from .toutiao_crawler import ToutiaoCrawler
except ImportError:
    from douyin_crawler import DouyinHotSearchCrawler
    from bilibili_crawler import BilibiliCrawler
    from toutiao_crawler import ToutiaoCrawler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmpireCrawler:
    """
    帝国爬虫 - 多平台统一接口
    整合你的抖音+头条+B站爬虫
    """
    
    def __init__(self, db_path="data/empire.db", output_dir="output"):
        self.douyin_crawler = DouyinHotSearchCrawler()
        self.bilibili_crawler = BilibiliCrawler()
        self.toutiao_crawler = ToutiaoCrawler()
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def crawl_all(self):
        """
        采集所有平台数据
        """
        results = {}
        
        platforms = [
            ("douyin", self._douyin_crawler),
            ("toutiao", self._toutiao_crawler),
            ("bilibili", self._bilibili_crawler)
        ]
        
        for platform, crawler_func in platforms:
            try:
                data = crawler_func()
                results[platform] = {
                    "success": True,
                    "data": data,
                    "count": len(data) if data else 0
                }
                
                self._save_data(platform, data)
                print(f"✅ {platform}: 采集 {len(data)} 条")
                
            except Exception as e:
                results[platform] = {
                    "success": False,
                    "error": str(e),
                    "data": []
                }
                print(f"❌ {platform}: 失败 - {e}")
        
        return results
    
    def _douyin_crawler(self) -> List[Dict]:
        """抖音爬虫"""
        return self.douyin_crawler.get_hot_search()
    
    def _toutiao_crawler(self) -> List[Dict]:
        """头条爬虫"""
        return self.toutiao_crawler.get_hot_news()
    
    def _bilibili_crawler(self) -> List[Dict]:
        """B站爬虫"""
        return self.bilibili_crawler.get_popular_videos()
    
    def _save_data(self, platform, data):
        """保存数据"""
        if not data:
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.output_dir / f"{platform}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
            'platform': platform,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存: {filename}")
    
    def analyze(self, data):
        """
        分析采集的数据
        """
        return {"status": "analyzed", "data": data}

class ProjectInfoCollector:
    """
    项目信息收集器 - 收集项目不足之处，提供知识与技术
    """
    
    def __init__(self, project_root: Path, output_dir: Path = None):
        self.project_root = Path(project_root)
        self.output_dir = Path(output_dir) if output_dir else self.project_root / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        self.known_patterns = [
            "TODO:", "FIXME:", "HACK:", "XXX:",
            "TODO ", "FIXME ", "HACK ", "XXX ",
            "BUG:", "ISSUE:",
            "待实现:", "待完善:", "待优化:",
            "# TODO", "# FIXME", "# HACK", "# XXX"
        ]
    
    def scan_codebase(self) -> Dict:
        """
        扫描代码库，收集项目信息
        
        Returns:
            项目分析报告
        """
        print("🔍 开始扫描代码库...")
        
        report = {
            'scan_time': datetime.now().isoformat(),
            'todo_items': [],
            'file_statistics': {},
            'suggestions': [],
            'skills_coverage': {}
        }
        
        # 扫描文件统计
        report['file_statistics'] = self._scan_file_statistics()
        
        # 扫描TODO项
        report['todo_items'] = self._scan_todo_items()
        
        # 生成改进建议
        report['suggestions'] = self._generate_suggestions(report)
        
        # 保存报告
        self._save_report(report)
        
        print(f"✅ 扫描完成: 发现 {len(report['todo_items'])} 个待办项")
        return report
    
    def _scan_file_statistics(self) -> Dict:
        """扫描文件统计"""
        stats = {
            'total_files': 0,
            'by_extension': {},
            'total_lines': 0
        }
        
        for ext in ['*.py', '*.md', '*.json', '*.js', '*.ts']:
            files = list(self.project_root.rglob(ext))
            count = len(list(files))
            stats['by_extension'][ext] = count
            stats['total_files'] += count
        
        return stats
    
    def _scan_todo_items(self) -> List[Dict]:
        """扫描TODO项"""
        todos = []
        
        # 扫描Python文件
        for py_file in self.project_root.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line_num, line in enumerate(lines, 1):
                    line_lower = line.lower()
                    for pattern in self.known_patterns:
                        if pattern.lower() in line_lower:
                            todos.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': line_num,
                                'content': line.strip(),
                                'pattern': pattern
                            })
                            break
            except Exception as e:
                continue
        
        return todos
    
    def _generate_suggestions(self, report: Dict) -> List[Dict]:
        """生成改进建议"""
        suggestions = []
        
        # 基于扫描结果生成建议
        if len(report['todo_items']) > 10:
            suggestions.append({
                'priority': 'high',
                'category': '代码质量',
                'title': '清理技术债务过多',
                'description': f'发现 {len(report["todo_items"])} 个待办项，建议优先处理高优先级的'
            })
        
        # 检查测试覆盖
        suggestions.append({
            'priority': 'medium',
            'category': '测试',
            'title': '完善测试套件',
            'description': '建议增加单元测试和集成测试，确保代码质量'
        })
        
        # 检查文档
        suggestions.append({
            'priority': 'medium',
            'category': '文档',
            'title': '完善文档完善',
            'description': '建议完善API文档和使用指南'
        })
        
        return suggestions
    
    def _save_report(self, report: Dict):
        """保存报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.output_dir / f"project_analysis_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 同时保存Markdown版本
        md_file = self.output_dir / f"project_analysis_{timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(self._generate_markdown_report(report))
        
        logger.info(f"项目分析报告已保存: {report_file}")
        logger.info(f"Markdown版本: {md_file}")
    
    def _generate_markdown_report(self, report: Dict) -> str:
        """生成Markdown报告"""
        md = "# 信息帝国 - 项目分析报告\n\n"
        md += f"**扫描时间**: {report['scan_time']}\n\n"
        
        md += "## 📊 文件统计\n\n"
        for ext, count in report['file_statistics']['by_extension'].items():
            md += f"- {ext}: {count} 个\n"
        
        md += f"\n## ✅ 待办项 ({len(report['todo_items'])}个)\n\n"
        
        if report['todo_items']:
            for todo in report['todo_items'][:20]:
                md += f"- [{todo['file']}:{todo['line']}] - {todo['content']}\n"
        
        md += "\n## 💡 改进建议\n\n"
        for sug in report['suggestions']:
            md += f"### {sug['title']} ({sug['priority']})\n\n"
            md += f"{sug['description']}\n\n"
        
        return md

# 测试
if __name__ == "__main__":
    print("="*60)
    print("📊 帝国爬虫 - 测试")
    print("="*60)
    
    # 测试爬虫
    crawler = EmpireCrawler()
    results = crawler.crawl_all()
    
    print("\n" + "="*60)
    print("📊 采集结果汇总")
    print("="*60)
    
    for platform, result in results.items():
        status = "✅" if result["success"] else "❌"
        count = result.get("count", 0)
        print(f"{status} {platform}: {count} 条")
    
    # 测试项目信息收集
    print("\n" + "="*60)
    print("🔍 项目信息收集测试")
    print("="*60)
    
    collector = ProjectInfoCollector(Path(__file__).parent.parent.parent.parent)
    report = collector.scan_codebase()
