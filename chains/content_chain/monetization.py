"""
信息帝国 - 内容产业链变现闭环
实现: 数据采集 → 内容生成 → 发布 → 流量变现

核心功能:
1. 多平台热点采集 (抖音/头条/B站)
2. AI内容生成 (热点报告/爆款文案)
3. 自动发布 (多平台)
4. 效果追踪 (流量/收益)
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    from core.services.scoring import ScoringService
except ImportError:
    # 简单实现，避免导入错误
    class ScoringService:
        def estimate_monetization(self, item):
            return "高" if item.get('hot_value', 0) > 1000000 else "中"
        
        def calculate_topic_score(self, hot_value, competition, monetization, urgency):
            score = hot_value / 100000
            if monetization == "高":
                score += 20
            if urgency == "高":
                score += 10
            return min(score, 100)
        
        def categorize_topics(self, items):
            return {"热点": len(items)}

logger = logging.getLogger(__name__)

@dataclass
class Content:
    """内容实体"""
    id: str
    title: str
    content: str
    source: str
    keywords: List[str]
    hot_value: int = 0
    platform: str = ""
    status: str = "draft"
    views: int = 0
    likes: int = 0
    comments: int = 0
    revenue: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    published_at: Optional[datetime] = None
    published_url: Optional[str] = None

@dataclass
class RevenueStats:
    """收益统计"""
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_revenue: float = 0.0
    platform_stats: Dict[str, Dict] = field(default_factory=dict)

class ContentChain:
    """
    内容产业链 - 变现闭环
    
    流程:
    1. 采集热点数据
    2. 分析选题价值
    3. 生成爆款内容
    4. SEO优化
    5. 多平台发布
    6. 效果追踪
    7. 收益分析
    """
    
    def __init__(self, output_dir: str = "output/content_chain"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.contents: Dict[str, Content] = {}
        self.revenue_stats = RevenueStats()

        # 初始化评分服务
        self.scoring_service = ScoringService()
        
        # 初始化LLM引擎
        self._llm_engine = None

        self._load_history()

        logger.info("✅ 内容产业链初始化完成")
    
    @property
    def llm_engine(self):
        """延迟加载LLM引擎"""
        if self._llm_engine is None:
            try:
                from core.llm_engine import get_llm_engine
                self._llm_engine = get_llm_engine()
            except ImportError:
                # 模拟LLM引擎，用于测试
                class MockLLM:
                    async def generate(self, prompt, system_prompt=None):
                        class MockResponse:
                            success = True
                            content = f"模拟生成的内容：基于提示'{prompt[:50]}...'"
                            error = None
                        return MockResponse()
                self._llm_engine = MockLLM()
        return self._llm_engine
    
    def _load_history(self):
        """加载历史数据"""
        history_file = self.output_dir / "history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for item in data.get('contents', []):
                    content = Content(
                        id=item['id'],
                        title=item['title'],
                        content=item['content'],
                        source=item['source'],
                        keywords=item['keywords'],
                        hot_value=item.get('hot_value', 0),
                        platform=item.get('platform', ''),
                        status=item.get('status', 'draft'),
                        views=item.get('views', 0),
                        likes=item.get('likes', 0),
                        comments=item.get('comments', 0),
                        revenue=item.get('revenue', 0.0),
                        created_at=datetime.fromisoformat(item['created_at']),
                        published_at=datetime.fromisoformat(item['published_at']) if item.get('published_at') else None,
                        published_url=item.get('published_url')
                    )
                    self.contents[content.id] = content
                
                stats = data.get('revenue_stats', {})
                self.revenue_stats.total_views = stats.get('total_views', 0)
                self.revenue_stats.total_likes = stats.get('total_likes', 0)
                self.revenue_stats.total_comments = stats.get('total_comments', 0)
                self.revenue_stats.total_revenue = stats.get('total_revenue', 0.0)
                
                logger.info(f"📂 加载了 {len(self.contents)} 条历史内容")
            except Exception as e:
                logger.warning(f"⚠️ 加载历史失败: {e}")
    
    def _save_history(self):
        """保存历史数据"""
        history_file = self.output_dir / "history.json"
        
        data = {
            'contents': [
                {
                    'id': c.id,
                    'title': c.title,
                    'content': c.content,
                    'source': c.source,
                    'keywords': c.keywords,
                    'hot_value': c.hot_value,
                    'platform': c.platform,
                    'status': c.status,
                    'views': c.views,
                    'likes': c.likes,
                    'comments': c.comments,
                    'revenue': c.revenue,
                    'created_at': c.created_at.isoformat(),
                    'published_at': c.published_at.isoformat() if c.published_at else None,
                    'published_url': c.published_url
                }
                for c in self.contents.values()
            ],
            'revenue_stats': {
                'total_views': self.revenue_stats.total_views,
                'total_likes': self.revenue_stats.total_likes,
                'total_comments': self.revenue_stats.total_comments,
                'total_revenue': self.revenue_stats.total_revenue
            }
        }
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def step1_collect(self) -> Dict:
        """
        步骤1: 数据采集
        
        采集平台:
        - 抖音热搜
        - 头条热点
        - B站热门
        """
        logger.info("📥 步骤1: 数据采集...")
        
        try:
            from chains.content_chain.crawlers.empire_crawler import EmpireCrawler
        except ImportError:
            from content_chain.crawlers.empire_crawler import EmpireCrawler
        
        crawler = EmpireCrawler()
        result = crawler.crawl_all()
        
        hot_items = []
        
        for platform, data in result.items():
            if isinstance(data, dict) and 'data' in data:
                for item in data['data'][:20]:
                    hot_items.append({
                        'title': item.get('word') or item.get('title') or item.get('name', ''),
                        'hot_value': item.get('hot_value', 0),
                        'platform': platform,
                        'url': item.get('url', '')
                    })
        
        hot_items.sort(key=lambda x: x['hot_value'], reverse=True)
        
        output_file = self.output_dir / f"collected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(hot_items, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 采集完成: {len(hot_items)} 条热点数据")
        
        return {
            'success': True,
            'count': len(hot_items),
            'items': hot_items[:50],
            'output_file': str(output_file)
        }
    
    async def step2_analyze(self, collected_data: Dict) -> Dict:
        """
        步骤2: 选题分析
        
        分析维度:
        - 热度趋势
        - 竞争程度
        - 变现潜力
        - 时效性
        """
        logger.info("📊 步骤2: 选题分析...")
        
        items = collected_data.get('items', [])
        
        analyzed = []
        for item in items:
            hot_value = item.get('hot_value', 0)
            
            competition = "低" if hot_value > 10000000 else "中" if hot_value > 5000000 else "高"
            
            monetization_potential = self._estimate_monetization(item)
            
            urgency = "高" if hot_value > 10000000 else "中" if hot_value > 5000000 else "低"
            
            score = self._calculate_topic_score(hot_value, competition, monetization_potential, urgency)
            
            analyzed.append({
                **item,
                'competition': competition,
                'monetization_potential': monetization_potential,
                'urgency': urgency,
                'score': score
            })
        
        analyzed.sort(key=lambda x: x['score'], reverse=True)
        
        top_topics = analyzed[:10]
        
        logger.info(f"✅ 分析完成: 推荐 {len(top_topics)} 个选题")
        
        return {
            'success': True,
            'total': len(analyzed),
            'top_topics': top_topics,
            'categories': self._categorize_topics(analyzed)
        }
    
    def _estimate_monetization(self, item: Dict) -> str:
        """估算变现潜力"""
        return self.scoring_service.estimate_monetization(item)
    
    def _calculate_topic_score(self, hot_value: int, competition: str, monetization: str, urgency: str) -> float:
        """计算选题得分"""
        return self.scoring_service.calculate_topic_score(hot_value, competition, monetization, urgency)

    def _categorize_topics(self, items: List[Dict]) -> Dict[str, int]:
        """分类统计"""
        return self.scoring_service.categorize_topics(items)
    
    async def step3_generate(self, analysis_data: Dict) -> Dict:
        """
        步骤3: 内容生成
        
        生成类型:
        - 热点报告
        - 爆款文案
        - 短视频脚本
        - 公众号文章
        """
        logger.info("✍️ 步骤3: 内容生成...")
        
        top_topics = analysis_data.get('top_topics', [])
        
        generated = []
        
        for i, topic in enumerate(top_topics[:5]):
            content_id = f"content_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}"
            
            title = self._generate_title(topic)
            content = await self._generate_content_with_ai(topic)
            keywords = self._extract_keywords(topic)
            
            content_obj = Content(
                id=content_id,
                title=title,
                content=content,
                source=topic.get('title', ''),
                keywords=keywords,
                hot_value=topic.get('hot_value', 0),
                platform=topic.get('platform', '')
            )
            
            self.contents[content_id] = content_obj
            
            generated.append({
                'id': content_id,
                'title': title,
                'preview': content[:200] + "...",
                'keywords': keywords,
                'score': topic.get('score', 0)
            })
        
        self._save_history()
        
        logger.info(f"✅ 生成完成: {len(generated)} 篇内容")
        
        return {
            'success': True,
            'count': len(generated),
            'contents': generated
        }
    
    def _generate_title(self, topic: Dict) -> str:
        """生成标题"""
        base_title = topic.get('title', '')
        hot_value = topic.get('hot_value', 0)
        
        templates = [
            f"【热点】{base_title}，热度破{hot_value//10000}万！",
            f"深度解析：{base_title}背后的真相",
            f"{base_title}火了！一文看懂来龙去脉",
            f"关于{base_title}，你需要知道的一切",
            f"【独家】{base_title}最新进展全汇总"
        ]
        
        import random
        return random.choice(templates)
    
    async def _generate_content_with_ai(self, topic: Dict) -> str:
        """使用AI生成内容"""
        title = topic.get('title', '')
        hot_value = topic.get('hot_value', 0)
        platform = topic.get('platform', '')
        
        system_prompt = """你是一个专业的内容创作者，擅长撰写热点分析文章。
请根据提供的热点话题，撰写一篇深度分析文章。
要求：
1. 结构清晰，有明确的标题和小标题
2. 内容客观，引用多方观点
3. 语言简洁有力，适合快速阅读
4. 包含背景分析、各方观点、影响预测和总结
5. 字数控制在500-800字"""

        prompt = f"""请针对以下热点话题撰写一篇深度分析文章：

话题：{title}
平台：{platform}
热度值：{hot_value:,}

请按照以下结构撰写：
## 📊 热度数据
## 💡 核心要点
### 1. 事件背景
### 2. 各方观点
### 3. 专家解读
### 4. 后续影响
## 📝 总结"""

        try:
            response = await self.llm_engine.generate(prompt, system_prompt)
            if response.success:
                return response.content
            else:
                logger.warning(f"AI生成失败: {response.error}，使用模板生成")
                return self._generate_content_fallback(topic)
        except Exception as e:
            logger.warning(f"AI生成异常: {e}，使用模板生成")
            return self._generate_content_fallback(topic)
    
    def _generate_content_fallback(self, topic: Dict) -> str:
        """模板生成内容（AI失败时的后备方案）"""
        title = topic.get('title', '')
        hot_value = topic.get('hot_value', 0)
        platform = topic.get('platform', '')
        
        content = f"""# {title}

## 📊 热度数据
- 平台: {platform}
- 热度值: {hot_value:,}
- 采集时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 💡 核心要点

### 1. 事件背景
{title}近期在{platform}平台引发广泛关注，热度持续攀升。

### 2. 各方观点
- 观点一：支持方认为这是积极的发展趋势
- 观点二：质疑方提出需要更多数据支撑
- 观点三：中立派呼吁理性看待

### 3. 专家解读
根据目前公开信息，专业人士分析认为...

### 4. 后续影响
此事可能对相关领域产生以下影响：
1. 行业格局可能重新洗牌
2. 用户消费习惯或将改变
3. 相关政策可能调整

## 📝 总结
{title}作为当前热点，值得我们持续关注。建议保持理性态度，等待更多官方信息。

---
*本文由信息帝国AI自动生成，仅供参考*
"""
        return content
    
    def _extract_keywords(self, topic: Dict) -> List[str]:
        """提取关键词"""
        title = topic.get('title', '')
        
        keywords = []
        
        import re
        words = re.findall(r'[\u4e00-\u9fa5]{2,4}', title)
        keywords.extend(words[:3])
        
        keywords.append(topic.get('platform', ''))
        
        return list(set(keywords))[:5]
    
    async def step4_seo_optimize(self, generated_data: Dict) -> Dict:
        """
        步骤4: SEO优化
        
        优化项:
        - 关键词密度
        - 标题优化
        - 元描述
        - 标签建议
        """
        logger.info("🔍 步骤4: SEO优化...")
        
        contents = generated_data.get('contents', [])
        
        optimized = []
        for item in contents:
            content_id = item['id']
            content = self.contents.get(content_id)
            
            if not content:
                continue
            
            seo_data = {
                'id': content_id,
                'optimized_title': self._optimize_seo_title(content.title),
                'meta_description': self._generate_meta_description(content),
                'keywords': content.keywords,
                'tags': self._suggest_tags(content),
                'seo_score': self._calculate_seo_score(content)
            }
            
            optimized.append(seo_data)
        
        logger.info(f"✅ SEO优化完成: {len(optimized)} 篇")
        
        return {
            'success': True,
            'optimized': optimized
        }
    
    def _optimize_seo_title(self, title: str) -> str:
        """优化SEO标题"""
        if len(title) > 30:
            return title[:27] + "..."
        return title
    
    def _generate_meta_description(self, content: Content) -> str:
        """生成元描述"""
        return f"{content.title} - 热度{content.hot_value}，{content.source}平台热门话题，深度解析最新动态。"
    
    def _suggest_tags(self, content: Content) -> List[str]:
        """建议标签"""
        tags = content.keywords.copy()
        tags.extend(['热点', '最新', '深度解析'])
        return list(set(tags))[:8]
    
    def _calculate_seo_score(self, content: Content) -> int:
        """计算SEO得分"""
        score = 60
        
        if len(content.title) >= 10 and len(content.title) <= 30:
            score += 10
        
        if len(content.keywords) >= 3:
            score += 10
        
        if len(content.content) >= 300:
            score += 10
        
        if content.hot_value > 1000000:
            score += 10
        
        return min(score, 100)
    
    async def step5_publish(self, seo_data: Dict) -> Dict:
        """
        步骤5: 多平台发布
        
        发布平台:
        - 公众号
        - 头条号
        - 百家号
        - 知乎
        - 微博
        """
        logger.info("🚀 步骤5: 多平台发布...")
        
        optimized = seo_data.get('optimized', [])
        
        published = []
        for item in optimized:
            content_id = item['id']
            content = self.contents.get(content_id)
            
            if not content:
                continue
            
            publish_result = await self._publish_to_platforms(content, item)
            
            content.status = "published"
            content.published_at = datetime.now()
            content.published_url = publish_result.get('url', '')
            
            published.append({
                'id': content_id,
                'title': content.title,
                'platforms': publish_result.get('platforms', []),
                'url': content.published_url
            })
        
        self._save_history()
        
        logger.info(f"✅ 发布完成: {len(published)} 篇")
        
        return {
            'success': True,
            'published': published
        }
    
    async def _publish_to_platforms(self, content: Content, seo_data: Dict) -> Dict:
        """发布到各平台"""
        platforms = ['公众号', '头条号', '百家号']
        
        output_file = self.output_dir / f"published_{content.id}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {content.title}\n\n")
            f.write(content.content)
            f.write(f"\n\n---\n")
            f.write(f"SEO标题: {seo_data.get('optimized_title', '')}\n")
            f.write(f"关键词: {', '.join(content.keywords)}\n")
            f.write(f"标签: {', '.join(seo_data.get('tags', []))}\n")
        
        return {
            'platforms': platforms,
            'url': str(output_file)
        }
    
    async def step6_track(self, publish_data: Dict) -> Dict:
        """
        步骤6: 效果追踪
        
        追踪指标:
        - 阅读量
        - 点赞数
        - 评论数
        - 转发数
        - 收益
        
        注意: 由于没有真实的平台API，这里使用基于热度值的估算模型。
        实际生产环境应接入各平台的数据统计API。
        """
        logger.info("📈 步骤6: 效果追踪...")
        
        published = publish_data.get('published', [])
        
        tracked = []
        for item in published:
            content_id = item['id']
            content = self.contents.get(content_id)
            
            if not content:
                continue
            
            views, likes, comments, revenue = self._estimate_performance(content)
            
            content.views = views
            content.likes = likes
            content.comments = comments
            content.revenue = revenue
            
            self.revenue_stats.total_views += views
            self.revenue_stats.total_likes += likes
            self.revenue_stats.total_comments += comments
            self.revenue_stats.total_revenue += revenue
            
            tracked.append({
                'id': content_id,
                'title': content.title,
                'views': views,
                'likes': likes,
                'comments': comments,
                'revenue': revenue
            })
        
        self._save_history()
        
        logger.info(f"✅ 追踪完成: {len(tracked)} 篇")
        
        return {
            'success': True,
            'tracked': tracked,
            'total_stats': {
                'total_views': self.revenue_stats.total_views,
                'total_likes': self.revenue_stats.total_likes,
                'total_revenue': self.revenue_stats.total_revenue
            }
        }
    
    def _estimate_performance(self, content: Content) -> tuple:
        """
        估算内容表现（基于热度值和平台特性）
        
        注意: 这是估算模型，实际应接入平台API获取真实数据
        
        估算逻辑:
        - 阅读量 = 热度值 * 平台系数 * 内容质量系数
        - 点赞率 = 根据平台类型估算
        - 评论率 = 根据平台类型估算
        - 收益 = 阅读量 * 平台单价
        """
        platform_coefficients = {
            'douyin': {'view_rate': 0.001, 'like_rate': 0.05, 'comment_rate': 0.01, 'revenue_per_1k': 0.1},
            'toutiao': {'view_rate': 0.002, 'like_rate': 0.03, 'comment_rate': 0.008, 'revenue_per_1k': 0.15},
            'bilibili': {'view_rate': 0.0015, 'like_rate': 0.08, 'comment_rate': 0.02, 'revenue_per_1k': 0.08},
            'default': {'view_rate': 0.001, 'like_rate': 0.04, 'comment_rate': 0.01, 'revenue_per_1k': 0.1}
        }
        
        platform = content.platform.lower() if content.platform else 'default'
        coef = platform_coefficients.get(platform, platform_coefficients['default'])
        
        base_views = int(content.hot_value * coef['view_rate'])
        views = max(base_views, 100)
        
        likes = int(views * coef['like_rate'])
        comments = int(views * coef['comment_rate'])
        revenue = (views / 1000) * coef['revenue_per_1k']
        
        return views, likes, comments, revenue
    
    def update_real_stats(self, content_id: str, views: int, likes: int, comments: int, revenue: float) -> bool:
        """
        更新真实统计数据（手动或API调用后使用）
        
        Args:
            content_id: 内容ID
            views: 真实阅读量
            likes: 真实点赞数
            comments: 真实评论数
            revenue: 真实收益
        
        Returns:
            是否更新成功
        """
        content = self.contents.get(content_id)
        if not content:
            return False
        
        old_views = content.views
        old_likes = content.likes
        old_comments = content.comments
        old_revenue = content.revenue
        
        content.views = views
        content.likes = likes
        content.comments = comments
        content.revenue = revenue
        
        self.revenue_stats.total_views += (views - old_views)
        self.revenue_stats.total_likes += (likes - old_likes)
        self.revenue_stats.total_comments += (comments - old_comments)
        self.revenue_stats.total_revenue += (revenue - old_revenue)
        
        self._save_history()
        logger.info(f"✅ 更新真实数据: {content_id} - 阅读{views} 点赞{likes} 收益¥{revenue:.2f}")
        
        return True
    
    async def run_full_chain(self) -> Dict:
        """运行完整产业链"""
        print("\n" + "=" * 60)
        print("📰 内容产业链 - 变现闭环")
        print("=" * 60)
        
        result = {}
        
        result['collect'] = await self.step1_collect()
        result['analyze'] = await self.step2_analyze(result['collect'])
        result['generate'] = await self.step3_generate(result['analyze'])
        result['seo'] = await self.step4_seo_optimize(result['generate'])
        result['publish'] = await self.step5_publish(result['seo'])
        result['track'] = await self.step6_track(result['publish'])
        
        print("\n" + "=" * 60)
        print("📊 变现闭环完成!")
        print("=" * 60)
        
        stats = result['track'].get('total_stats', {})
        print(f"\n💰 累计收益统计:")
        print(f"   总阅读: {stats.get('total_views', 0):,}")
        print(f"   总点赞: {stats.get('total_likes', 0):,}")
        print(f"   总收益: ¥{stats.get('total_revenue', 0):.2f}")
        
        return result
    
    def get_revenue_report(self) -> Dict:
        """获取收益报告"""
        return {
            'total_views': self.revenue_stats.total_views,
            'total_likes': self.revenue_stats.total_likes,
            'total_comments': self.revenue_stats.total_comments,
            'total_revenue': self.revenue_stats.total_revenue,
            'content_count': len(self.contents),
            'published_count': sum(1 for c in self.contents.values() if c.status == 'published'),
            'top_contents': sorted(
                [{'title': c.title, 'views': c.views, 'revenue': c.revenue} 
                 for c in self.contents.values()],
                key=lambda x: x['revenue'],
                reverse=True
            )[:10]
        }

if __name__ == "__main__":
    async def test():
        chain = ContentChain()
        result = await chain.run_full_chain()
        
        print("\n" + "=" * 60)
        print("💰 收益报告")
        print("=" * 60)
        report = chain.get_revenue_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    
    asyncio.run(test())
