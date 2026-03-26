"""
数据分析模块 - 热点识别、趋势分析
基于采集的数据进行AI分析
"""

from typing import List, Dict
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)

class HotspotAnalyzer:
    """
    热点分析器 - AI驱动
    """
    
    def __init__(self, llm_engine=None):
        self.heat_threshold = 100000
        self._llm_engine = llm_engine
    
    @property
    def llm_engine(self):
        if self._llm_engine is None:
            from core.llm_engine import get_llm_engine
            self._llm_engine = get_llm_engine()
        return self._llm_engine
    
    async def analyze_hotspots_async(self, data: Dict) -> Dict:
        """
        AI异步分析热点数据
        """
        results = {
            "top_hotspots": [],
            "trending_up": [],
            "trending_down": [],
            "categories": {},
            "ai_insights": []
        }
        
        for platform, platform_data in data.items():
            if not platform_data.get("success"):
                continue
            
            items = platform_data.get("data", [])
            
            for item in items:
                hot_value = item.get("hot_value", 0)
                word = item.get("word", "")
                
                if hot_value > self.heat_threshold:
                    results["top_hotspots"].append({
                        "word": word,
                        "hot_value": hot_value,
                        "platform": platform
                    })
                
                category = self._classify_topic(word)
                if category not in results["categories"]:
                    results["categories"][category] = 0
                results["categories"][category] += 1
        
        results["top_hotspots"].sort(
            key=lambda x: x["hot_value"], 
            reverse=True
        )
        
        if results["top_hotspots"]:
            try:
                ai_insights = await self._generate_ai_insights(results["top_hotspots"][:5])
                results["ai_insights"] = ai_insights
            except Exception as e:
                logger.warning(f"AI洞察生成失败: {e}")
                results["ai_insights"] = []
        
        return results
    
    def analyze_hotspots(self, data: Dict) -> Dict:
        """
        同步分析热点数据 (兼容旧接口)
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, 
                        self.analyze_hotspots_async(data)
                    )
                    return future.result(timeout=60)
            else:
                return asyncio.run(self.analyze_hotspots_async(data))
        except Exception as e:
            logger.warning(f"异步分析失败，使用同步模式: {e}")
            return self._analyze_hotspots_sync(data)
    
    def _analyze_hotspots_sync(self, data: Dict) -> Dict:
        """同步分析热点数据"""
        results = {
            "top_hotspots": [],
            "trending_up": [],
            "trending_down": [],
            "categories": {}
        }
        
        for platform, platform_data in data.items():
            if not platform_data.get("success"):
                continue
            
            items = platform_data.get("data", [])
            
            for item in items:
                hot_value = item.get("hot_value", 0)
                word = item.get("word", "")
                
                if hot_value > self.heat_threshold:
                    results["top_hotspots"].append({
                        "word": word,
                        "hot_value": hot_value,
                        "platform": platform
                    })
                
                category = self._classify_topic(word)
                if category not in results["categories"]:
                    results["categories"][category] = 0
                results["categories"][category] += 1
        
        results["top_hotspots"].sort(
            key=lambda x: x["hot_value"], 
            reverse=True
        )
        
        return results
    
    async def _generate_ai_insights(self, hotspots: List[Dict]) -> List[Dict]:
        """使用AI生成洞察"""
        if not hotspots:
            return []
        
        prompt = f"""分析以下热点话题，给出3个关键洞察：

热点列表：
{chr(10).join([f"- {h['word']} (热度: {h['hot_value']:,})" for h in hotspots])}

请返回JSON格式：
{{
    "insights": [
        {{"topic": "话题", "insight": "洞察内容", "recommendation": "建议"}}
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
                    return data.get("insights", [])
        except Exception as e:
            logger.warning(f"AI洞察解析失败: {e}")
        
        return []
    
    def _classify_topic(self, word: str) -> str:
        """
        简单话题分类
        """
        categories = {
            "娱乐": ["明星", "综艺", "电视剧", "电影", "音乐"],
            "科技": ["AI", "人工智能", "ChatGPT", "手机", "电脑"],
            "社会": ["两会", "政策", "新闻", "事件"],
            "生活": ["美食", "旅游", "穿搭", "健身"],
            "财经": ["股票", "基金", "经济", "投资"]
        }
        
        for category, keywords in categories.items():
            if any(k in word for k in keywords):
                return category
        
        return "其他"
    
    async def generate_topic_suggestions_async(self, analysis: Dict) -> List[Dict]:
        """
        AI生成选题建议
        """
        suggestions = []
        
        for hotspot in analysis["top_hotspots"][:5]:
            suggestions.append({
                "topic": hotspot["word"],
                "hot_value": hotspot["hot_value"],
                "platform": hotspot["platform"],
                "priority": "high" if hotspot["hot_value"] > 500000 else "medium",
                "angle": await self._generate_angle_async(hotspot["word"])
            })
        
        return suggestions
    
    def generate_topic_suggestions(self, analysis: Dict) -> List[Dict]:
        """
        生成选题建议 (同步兼容)
        """
        suggestions = []
        
        for hotspot in analysis["top_hotspots"][:5]:
            suggestions.append({
                "topic": hotspot["word"],
                "hot_value": hotspot["hot_value"],
                "platform": hotspot["platform"],
                "priority": "high" if hotspot["hot_value"] > 500000 else "medium",
                "angle": self._generate_angle(hotspot["word"])
            })
        
        return suggestions
    
    async def _generate_angle_async(self, topic: str) -> str:
        """AI生成角度建议"""
        prompt = f"""为话题「{topic}」生成一个最佳内容创作角度。
        
请从以下角度中选择一个最合适的：
- 深度解析
- 背景介绍
- 用户看法
- 历史回顾
- 未来展望

只返回角度名称，不要其他内容。"""
        
        try:
            response = await self.llm_engine.generate(prompt)
            if response.success:
                angle = response.content.strip()
                valid_angles = ["深度解析", "背景介绍", "用户看法", "历史回顾", "未来展望"]
                if angle in valid_angles:
                    return angle
        except Exception as e:
            logger.warning(f"AI角度生成失败: {e}")
        
        return self._generate_angle(topic)
    
    def _generate_angle(self, topic: str) -> str:
        """
        生成角度建议
        """
        angles = [
            "深度解析",
            "背景介绍",
            "用户看法",
            "历史回顾",
            "未来展望"
        ]
        
        return angles[hash(topic) % len(angles)]

# 测试
if __name__ == "__main__":
    analyzer = HotspotAnalyzer()
    
    # 测试数据
    test_data = {
        "douyin": {
            "success": True,
            "data": [
                {"word": "全国两会", "hot_value": 1870000},
                {"word": "AI大模型", "hot_value": 560000}
            ]
        }
    }
    
    analysis = analyzer.analyze_hotspots(test_data)
    suggestions = analyzer.generate_topic_suggestions(analysis)
    
    print("="*60)
    print("📊 热点分析")
    print("="*60)
    print(f"🔥 热门话题数: {len(analysis['top_hotspots'])}")
    print(f"📂 分类: {analysis['categories']}")
    
    print("\n💡 选题建议:")
    for s in suggestions:
        print(f"  - {s['topic']} ({s['hot_value']}) - {s['angle']}")
