"""
内容生成模块 - 文案生成
基于分析结果生成高质量内容
AI驱动的内容创作
"""

from typing import Dict, List
import logging
import asyncio

logger = logging.getLogger(__name__)

class ChainContentGenerator:
    """
    产业链内容生成器 - AI驱动
    （注意：这是产业链特定实现，与 core.content_pipeline.ContentGenerator 区分）
    """
    
    def __init__(self, llm_engine=None):
        self._llm_engine = llm_engine
        self.templates = self._load_templates()
    
    @property
    def llm_engine(self):
        if self._llm_engine is None:
            from core.llm_engine import get_llm_engine
            self._llm_engine = get_llm_engine()
        return self._llm_engine
    
    def _load_templates(self) -> Dict:
        """
        加载内容模板
        """
        return {
            "hotspot_report": self._hotspot_report_template,
            "topic_analysis": self._topic_analysis_template,
            "seo_article": self._seo_article_template
        }
    
    async def generate_hotspot_report_async(self, hotspots: List[Dict]) -> str:
        """
        AI生成热点报告
        """
        content = []
        
        content.append("# 🔥 今日热点报告\n")
        content.append(f"生成时间: {self._get_current_time()}\n")
        content.append("---\n")
        
        content.append("## 📊 TOP 5 热点\n")
        for i, hotspot in enumerate(hotspots[:5], 1):
            content.append(f"### {i}. {hotspot['word']}\n")
            content.append(f"- 热度值: {hotspot['hot_value']:,}\n")
            content.append(f"- 来源: {hotspot['platform']}\n")
        
        content.append("\n---\n")
        content.append("## 💡 AI选题建议\n")
        
        ai_suggestions = await self._generate_ai_suggestions(hotspots[:3])
        for i, suggestion in enumerate(ai_suggestions, 1):
            content.append(f"{i}. **{suggestion.get('topic', hotspots[i-1]['word'])}**\n")
            content.append(f"   - 角度: {suggestion.get('angle', '深度解析')}\n")
            content.append(f"   - 理由: {suggestion.get('reason', '热度高，用户关注')}\n")
        
        return "\n".join(content)
    
    async def _generate_ai_suggestions(self, hotspots: List[Dict]) -> List[Dict]:
        """AI生成选题建议"""
        prompt = f"""基于以下热点话题，生成3个内容创作建议：

热点话题：
{chr(10).join([f"- {h['word']} (热度: {h['hot_value']})" for h in hotspots])}

请返回JSON格式：
{{
    "suggestions": [
        {{"topic": "话题", "angle": "创作角度", "reason": "推荐理由"}}
    ]
}}"""
        
        try:
            response = await self.llm_engine.generate(prompt)
            if response.success:
                import json
                content = response.content
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    data = json.loads(content[json_start:json_end])
                    return data.get("suggestions", [])
        except Exception as e:
            logger.warning(f"AI建议生成失败: {e}")
        
        return [{"topic": h['word'], "angle": "深度解析", "reason": "热度高"} for h in hotspots]
    
    def generate_hotspot_report(self, hotspots: List[Dict]) -> str:
        """
        生成热点报告 (同步兼容)
        """
        content = []
        
        content.append("# 🔥 今日热点报告\n")
        content.append(f"生成时间: {self._get_current_time()}\n")
        content.append("---\n")
        
        content.append("## 📊 TOP 5 热点\n")
        for i, hotspot in enumerate(hotspots[:5], 1):
            content.append(f"### {i}. {hotspot['word']}\n")
            content.append(f"- 热度值: {hotspot['hot_value']:,}\n")
            content.append(f"- 来源: {hotspot['platform']}\n")
        
        content.append("\n---\n")
        content.append("## 💡 选题建议\n")
        
        for i, hotspot in enumerate(hotspots[:3], 1):
            content.append(f"{i}. **{hotspot['word']}**\n")
            content.append(f"   - 角度: 深度解析 + 用户洞察\n")
        
        return "\n".join(content)
    
    async def generate_topic_article_async(self, topic: str, analysis: Dict) -> str:
        """
        AI生成话题文章
        """
        prompt = f"""请为话题「{topic}」撰写一篇深度分析文章。

背景信息：
{analysis.get('summary', '暂无背景信息')}

请按照以下结构撰写：
1. 背景介绍
2. 热点洞察
3. 多方观点
4. 未来展望

要求：
- 内容客观、有深度
- 语言流畅、易读
- 字数控制在500-800字"""
        
        try:
            response = await self.llm_engine.generate(prompt)
            if response.success:
                return response.content
        except Exception as e:
            logger.warning(f"AI文章生成失败: {e}")
        
        return self.generate_topic_article(topic, analysis)
    
    def generate_topic_article(self, topic: str, analysis: Dict) -> str:
        """
        生成话题文章 (同步兼容)
        """
        content = []
        
        content.append(f"# {topic}\n")
        content.append("\n## 一、背景介绍\n")
        content.append(f"这是关于「{topic}」的深度分析。\n")
        
        content.append("\n## 二、热点洞察\n")
        content.append("- 热度持续上升\n")
        content.append("- 用户关注度高\n")
        
        content.append("\n## 三、观点汇总\n")
        content.append("多方观点正在激烈讨论中...\n")
        
        content.append("\n## 四、未来展望\n")
        content.append("让我们持续关注事态发展...\n")
        
        return "\n".join(content)
    
    async def generate_seo_content_async(self, keyword: str, style: str = "informative") -> str:
        """
        AI生成SEO优化内容
        """
        prompt = f"""请为关键词「{keyword}」生成一篇SEO优化的文章。

风格：{style}

要求：
1. 标题包含关键词
2. 自然融入关键词3-5次
3. 结构清晰，有小标题
4. 内容有价值，能解决用户问题
5. 字数300-500字"""
        
        try:
            response = await self.llm_engine.generate(prompt)
            if response.success:
                return response.content
        except Exception as e:
            logger.warning(f"SEO内容生成失败: {e}")
        
        return f"# {keyword} - 深度解析\n\n关于{keyword}的详细内容..."
    
    def _hotspot_report_template(self, data: Dict) -> str:
        return self.generate_hotspot_report(data.get("hotspots", []))
    
    def _topic_analysis_template(self, data: Dict) -> str:
        return self.generate_topic_article(
            data.get("topic", ""), 
            data.get("analysis", {})
        )
    
    def _seo_article_template(self, data: Dict) -> str:
        return self.generate_topic_article(
            data.get("topic", ""), 
            data.get("analysis", {})
        )
    
    def _get_current_time(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 为了向后兼容，保留别名
ContentGenerator = ChainContentGenerator


# 测试
if __name__ == "__main__":
    generator = ChainContentGenerator()
    
    test_hotspots = [
        {"word": "全国两会", "hot_value": 1870000, "platform": "抖音"},
        {"word": "AI大模型", "hot_value": 560000, "platform": "抖音"},
        {"word": "山河向未来", "hot_value": 420000, "platform": "抖音"}
    ]
    
    report = generator.generate_hotspot_report(test_hotspots)
    print(report)
