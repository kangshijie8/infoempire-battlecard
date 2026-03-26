"""
SEO优化模块
基于seo-audit SKILL最佳实践
"""

from typing import Dict, List

class SEOOptimizer:
    """
    SEO优化器
    """
    
    def __init__(self):
        self.principles = self._load_principles()
    
    def _load_principles(self) -> Dict:
        """
        加载SEO原则
        """
        return {
            "title_length": (50, 60),
            "description_length": (150, 160),
            "keyword_density": (1, 3)
        }
    
    def optimize_title(self, title: str, keyword: str = "") -> str:
        """
        优化标题
        """
        # 确保关键词在前
        if keyword and keyword not in title:
            title = f"{keyword} | {title}"
        
        # 长度控制
        if len(title) > 60:
            title = title[:57] + "..."
        
        return title
    
    def optimize_description(self, content: str, keyword: str = "") -> str:
        """
        优化描述
        """
        # 提取前150-160字符
        desc = content[:155]
        
        if len(content) > 155:
            desc = desc[:152] + "..."
        
        # 确保包含关键词
        if keyword and keyword not in desc:
            desc = f"{keyword} - {desc}"
        
        return desc
    
    def analyze_seo_health(self, content: str, title: str = "") -> Dict:
        """
        分析SEO健康度
        """
        score = 100
        issues = []
        
        # 标题检查
        if title:
            if len(title) < 10:
                score -= 10
                issues.append("标题太短")
            elif len(title) > 60:
                score -= 5
                issues.append("标题过长")
        
        # 内容长度检查
        if len(content) < 300:
            score -= 20
            issues.append("内容太短")
        
        # 关键词密度（简单检查）
        word_count = len(content.split())
        if word_count > 0:
            # 这里可以扩展真正的关键词检查
            pass
        
        return {
            "score": max(0, score),
            "issues": issues,
            "recommendations": self._generate_recommendations(issues)
        }
    
    def _generate_recommendations(self, issues: List[str]) -> List[str]:
        """
        生成优化建议
        """
        recommendations = []
        
        for issue in issues:
            if "太短" in issue:
                recommendations.append("增加内容长度，提供更多价值")
            elif "过长" in issue:
                recommendations.append("精简标题，保持在60字符以内")
        
        if not recommendations:
            recommendations.append("继续保持当前SEO策略")
        
        return recommendations
    
    def generate_meta_tags(self, title: str, description: str, keywords: List[str] = None) -> Dict:
        """
        生成Meta标签
        """
        return {
            "title": self.optimize_title(title),
            "description": self.optimize_description(description),
            "keywords": ", ".join(keywords) if keywords else ""
        }

# 测试
if __name__ == "__main__":
    optimizer = SEOOptimizer()
    
    test_title = "全国两会最新消息"
    test_content = "这是关于全国两会的详细报道内容..."
    
    health = optimizer.analyze_seo_health(test_content, test_title)
    
    print("="*60)
    print("🔍 SEO分析")
    print("="*60)
    print(f"健康度: {health['score']}/100")
    print(f"问题: {health['issues']}")
    print(f"建议: {health['recommendations']}")
