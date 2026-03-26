"""
intel_chain - AI智能分析模块
集成大模型分析（MiniMax优先 → Bailian备用 → 规则fallback）
替换rule-based关键词统计
"""

import sys
import os
import json
import re
import asyncio
import logging
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

try:
    from .monitor import CompetitorData
except ImportError:
    # 兼容直接运行或跨路径导入
    import sys
    from pathlib import Path
    _p = Path(__file__).parent
    sys.path.insert(0, str(_p))
    from monitor import CompetitorData

logger = logging.getLogger(__name__)


def _parse_json_response(text: str) -> Optional[Dict]:
    """从LLM输出中提取JSON"""
    if not text:
        return None
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except json.JSONDecodeError:
        pass
    return None


# ─── MiniMax (Anthropic兼容) 直接调用 ───────────────────────────────


async def _minimax_chat(
    prompt: str,
    system: str = None,
    api_key: str = None,
    base_url: str = "https://api.minimaxi.com/anthropic/v1",  # /v1/messages endpoint
    model: str = "MiniMax-M2.7",
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> Optional[str]:
    """
    直接调用MiniMax Anthropic兼容API
    """
    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }

    messages = []
    if system:
        messages.append({"role": "assistant", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/messages",
                headers=headers,
                json=payload,
            )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", [])
            if content and isinstance(content, list):
                for block in content:
                    if block.get("type") == "text":
                        return block["text"].strip()
        else:
            logger.error(f"MiniMax API错误: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        logger.error(f"MiniMax调用失败: {e}")

    return None


# ─── Bailian 回退调用 ───────────────────────────────────────────────


async def _bailian_chat(engine, prompt: str, system: str = None) -> Optional[str]:
    """通过llm_engine调用Bailian"""
    try:
        resp = await engine.generate(prompt, system_prompt=system)
        if resp.success and resp.content:
            return resp.content.strip()
    except Exception as e:
        logger.error(f"Bailian调用失败: {e}")
    return None


# ─── AI分析器 ───────────────────────────────────────────────────────


class AIIntelAnalyzer:
    """
    AI驱动的智能分析器
    使用大模型分析竞品数据，识别趋势/机会/风险
    保留规则fallback，无API时也能工作
    """

    SYSTEM_PROMPT = (
        "你是一个专业的AI行业情报分析师，擅长从数据中提取关键洞察。"
        "严格按要求的JSON格式输出，不要额外文字。"
    )

    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai
        self.llm_engine = None
        self._init_llm()

    def _init_llm(self):
        """初始化AI引擎：MiniMax优先 → Bailian备用"""
        if not self.use_ai:
            logger.info("AI分析已禁用，使用规则分析")
            return

        # 1. 尝试 MiniMax（直接从环境变量读）
        self._mini_api_key = os.getenv("MINIMAX_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
        # MiniMax Anthropic兼容端点，需要 /v1 前缀
        self._mini_base_url = os.getenv("MINIMAX_BASE_URL") or "https://api.minimaxi.com/anthropic/v1"
        self._mini_model = os.getenv("MINIMAX_MODEL") or "MiniMax-M2.7"
        self._mini_available = bool(self._mini_api_key)

        if self._mini_available:
            logger.info(f"✅ MiniMax AI分析器就绪（{self._mini_model}）")
            return  # 优先用MiniMax

        logger.warning("⚠️ 未找到MINIMAX_API_KEY，尝试Bailian...")

        # 2. 回退 Bailian（通过llm_engine）
        try:
            core_path = str(Path(__file__).parent.parent.parent / "core")
            if core_path not in sys.path:
                sys.path.insert(0, core_path)

            from llm_engine import LLMEngine, LLMProvider, LLMConfig
            from dotenv import load_dotenv

            env_path = Path(__file__).parent.parent.parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)

            config = LLMConfig(
                provider=LLMProvider.BAILIAN,
                model=os.getenv("EMPIRE_LLM_DEFAULT_MODEL", "qwen3.5-plus"),
                api_key=os.getenv("BAILIAN_API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                temperature=0.3,
                max_tokens=2048,
            )
            self.llm_engine = LLMEngine(config)
            self._bailian_available = bool(config.api_key)
            logger.info("✅ Bailian AI分析器就绪")
            return
        except Exception as e:
            logger.warning(f"⚠️ Bailian初始化失败: {e}")

        logger.warning("⚠️ 所有AI引擎初始化失败，降级到规则分析")
        self.use_ai = False

    def analyze(self, data: List[CompetitorData]) -> Dict[str, Any]:
        """分析竞品数据（同步入口，asyncio.run包装）"""
        if not data:
            return self._empty_analysis()

        has_ai_engine = (
            getattr(self, "_mini_available", False) or
            getattr(self, "llm_engine", None) is not None
        )
        if self.use_ai and has_ai_engine:
            try:
                # 同步调用：用asyncio.run启动event loop
                result = asyncio.run(self._ai_analyze(data))
                if not result.get("ai_powered", False):
                    logger.info("AI分析返回空，fallback到规则分析")
                    return self._rule_analyze(data)
                return result
            except Exception as e:
                logger.warning(f"AI分析失败，fallback到规则分析: {e}")
                return self._rule_analyze(data)
        else:
            return self._rule_analyze(data)

    def _empty_analysis(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now().isoformat(),
            "total_items": 0,
            "by_source": {},
            "trends": [],
            "opportunities": [],
            "risks": [],
            "insights": [],
            "summary": "无数据",
            "ai_powered": False,
        }

    # ─── AI分析核心 ──────────────────────────────────────────────

    def _build_data_summary(self, data: List[CompetitorData], max_items: int = 50) -> str:
        lines = []
        for item in data[:max_items]:
            m = item.metrics or {}
            metrics_str = ", ".join(f"{k}={v}" for k, v in m.items() if v)
            content_preview = (item.content or "")[:80].replace("\n", " ")
            lines.append(
                f"[{item.source}] {item.competitor} | {item.title} | "
                f"{content_preview}... | {metrics_str}"
            )
        return "\n".join(lines)

    async def _ai_analyze(self, data: List[CompetitorData]) -> Dict[str, Any]:
        """使用大模型进行深度分析（所有LLM调用共享一个event loop）"""
        logger.info(f"🤖 AI分析中：{len(data)}条数据")
        data_summary = self._build_data_summary(data)

        # 在一个event loop中并行执行所有LLM调用
        async def _run_all():
            trends_task = self._afind_trends(data_summary)
            opps_task = self._afind_opportunities(data_summary)
            risks_task = self._afind_risks(data_summary)

            results = await asyncio.gather(
                trends_task, opps_task, risks_task, return_exceptions=True
            )

            # handle exceptions & count successful calls
            successful = 0
            trends = results[0] if not isinstance(results[0], Exception) else []
            opps = results[1] if not isinstance(results[1], Exception) else []
            risks = results[2] if not isinstance(results[2], Exception) else []

            # 真正成功的标准：返回了非空列表（API call成功 + 有内容）
            if not isinstance(results[0], Exception) and len(trends) > 0:
                successful += 1
            if not isinstance(results[1], Exception) and len(opps) > 0:
                successful += 1
            if not isinstance(results[2], Exception) and len(risks) > 0:
                successful += 1

            insights = []
            summary = ""
            if successful >= 2:  # 至少2/3成功才继续
                insights = await self._agenerate_insights(data_summary, trends, opps)
                summary = await self._agenerate_summary(data_summary, trends, opps, risks)
            else:
                summary = f"AI分析：{len(trends)}个趋势、{len(opps)}个机会、{len(risks)}个风险（API调用失败）"

            return trends, opps, risks, insights, summary, successful >= 2

        trends, opps, risks, insights, summary, ai_ok = await _run_all()

        analysis = {
            "timestamp": datetime.now().isoformat(),
            "total_items": len(data),
            "by_source": self._stats_by_source(data),
            "trends": trends,
            "opportunities": opps,
            "risks": risks,
            "insights": insights,
            "summary": summary,
            "ai_powered": ai_ok,
        }
        if not ai_ok:
            logger.warning("⚠️ AI分析部分/全部失败，已使用规则fallback补充")
        logger.info(f"✅ AI分析完成：{len(trends)}趋势/{len(opps)}机会/{len(risks)}风险")
        return analysis

    async def _afind_trends(self, data_summary: str) -> List[Dict]:
        prompt = f"""从以下竞品情报数据中识别正在兴起的技术/产品/市场趋势。

数据：
{data_summary}

输出严格JSON（不要有任何其他文字）：
{{
  "trends": [
    {{
      "keyword": "趋势关键词（1-2字）",
      "description": "趋势具体描述",
      "evidence_count": 支持此趋势的数据条目数,
      "severity": "high/medium/low",
      "reasoning": "为什么这是一个趋势"
    }}
  ]
}}"""
        text = await self._llm_call(prompt)
        if text:
            result = _parse_json_response(text)
            if result:
                return result.get("trends", [])
        return []

    async def _afind_opportunities(self, data_summary: str) -> List[Dict]:
        prompt = f"""从以下竞品情报数据中识别3-5个商业机会（蓝海市场/细分赛道/差异化方向/技术空白）。

数据：
{data_summary}

输出严格JSON（不要有任何其他文字）：
{{
  "opportunities": [
    {{
      "type": "market_gap/tech_gap/content_gap",
      "description": "机会具体描述",
      "target_audience": "目标用户群体",
      "difficulty": "high/medium/low",
      "potential": "large/medium/small",
      "action": "具体可行行动"
    }}
  ]
}}"""
        text = await self._llm_call(prompt)
        if text:
            result = _parse_json_response(text)
            if result:
                return result.get("opportunities", [])
        return []

    async def _afind_risks(self, data_summary: str) -> List[Dict]:
        prompt = f"""从以下竞品情报数据中识别3-5个威胁/风险（竞争加剧/技术替代/政策风险/市场饱和）。

数据：
{data_summary}

输出严格JSON（不要有任何其他文字）：
{{
  "risks": [
    {{
      "type": "competition/technology/policy/market",
      "description": "风险具体描述",
      "likelihood": "high/medium/low",
      "impact": "high/medium/low",
      "mitigation": "应对策略"
    }}
  ]
}}"""
        text = await self._llm_call(prompt)
        if text:
            result = _parse_json_response(text)
            if result:
                return result.get("risks", [])
        return []

    async def _agenerate_insights(
        self, data_summary: str, trends: List, opportunities: List
    ) -> List[str]:
        if not trends and not opportunities:
            return []
        prompt = f"""基于以下AI行业情报，给出3条深度洞察。

趋势：{json.dumps(trends, ensure_ascii=False)[:300]}
机会：{json.dumps(opportunities, ensure_ascii=False)[:300]}
数据：{data_summary[:300]}

输出严格JSON：{{"insights": ["洞察1", "洞察2", "洞察3"]}}"""
        text = await self._llm_call(prompt)
        if text:
            result = _parse_json_response(text)
            if result:
                return result.get("insights", [])
        return []

    async def _agenerate_summary(
        self, data_summary: str, trends: List, opportunities: List, risks: List
    ) -> str:
        top_trend = (trends[0]["keyword"] if trends else "无")
        top_opp = (opportunities[0]["description"] if opportunities else "无")
        top_risk = (risks[0]["description"] if risks else "无")
        prompt = f"""用2-3句话生成执行摘要：核心趋势={top_trend}，核心机会={top_opp}，核心风险={top_risk}。直接输出文字，不要前缀。"""
        text = await self._llm_call(prompt)
        return text or f"AI分析：{len(trends)}个趋势、{len(opportunities)}个机会、{len(risks)}个风险"

    # ─── 统一LLM调用入口 ─────────────────────────────────────

    async def _llm_call(self, prompt: str, system: str = None) -> Optional[str]:
        """根据可用引擎调用LLM（MiniMax优先）"""
        # MiniMax
        if getattr(self, "_mini_available", False):
            return await _minimax_chat(
                prompt=prompt,
                system=system or self.SYSTEM_PROMPT,
                api_key=self._mini_api_key,
                base_url=self._mini_base_url,
                model=self._mini_model,
            )
        # Bailian fallback
        if getattr(self, "llm_engine", None):
            return await _bailian_chat(self.llm_engine, prompt, system=system)
        return None

    async def analyze_async(self, data: List[CompetitorData]) -> Dict[str, Any]:
        """异步分析入口（供 AnalyzerRole 调用，避免 asyncio.run 嵌套）"""
        if not data:
            return self._empty_analysis()

        has_ai = (
            getattr(self, "_mini_available", False) or
            getattr(self, "llm_engine", None) is not None
        )
        if self.use_ai and has_ai:
            try:
                result = await self._ai_analyze(data)
                if not result.get("ai_powered", False):
                    logger.info("AI分析返回空，使用规则分析")
                    return self._rule_analyze(data)
                return result
            except Exception as e:
                logger.warning(f"AI分析失败，fallback到规则分析: {e}")
                return self._rule_analyze(data)
        else:
            return self._rule_analyze(data)

    # ─── 规则分析fallback ───────────────────────────────────────

    def _rule_analyze(self, data: List[CompetitorData]) -> Dict[str, Any]:
        keywords = {
            "AI大模型": ["AI", "大模型", "LLM", "Agent", "智能", "GPT", "Claude"],
            "自动化": ["自动化", "工作流", "RPA", "流程", "workflow"],
            "数据采集": ["爬虫", "采集", "数据", "抓取", "scrape"],
            "视频AI": ["视频", "剪辑", "字幕", "语音", "TTS", "ASR"],
            "内容创作": ["内容创作", "文案", "SEO", "分发", "创作"],
        }
        all_text = " ".join(item.title + " " + item.content for item in data)
        trends = []
        for kw_name, kw_list in keywords.items():
            count = sum(all_text.count(kw) for kw in kw_list)
            if count >= 2:
                trends.append(
                    {
                        "keyword": kw_name,
                        "description": f"涉及{kw_name}相关",
                        "evidence_count": count,
                        "severity": "high" if count > 5 else "medium",
                        "reasoning": f"出现{kw_name}共{count}次",
                    }
                )
        trends.sort(key=lambda x: x["evidence_count"], reverse=True)

        return {
            "timestamp": datetime.now().isoformat(),
            "total_items": len(data),
            "by_source": self._stats_by_source(data),
            "trends": trends[:5],
            "opportunities": [
                {"type": "content_gap", "description": "AI自动化内容创作",
                 "target_audience": "内容创作者", "difficulty": "medium",
                 "potential": "large", "action": "开发内容自动生成工作流"}
            ],
            "risks": [
                {"type": "competition", "description": "AI工具领域竞争激烈",
                 "likelihood": "high", "impact": "medium", "mitigation": "专注细分赛道"}
            ],
            "insights": [],
            "summary": f"规则分析：{len(trends)}个趋势，{len(data)}条数据",
            "ai_powered": False,
        }

    def _stats_by_source(self, data: List[CompetitorData]) -> Dict:
        stats = defaultdict(lambda: {"count": 0, "total_hot": 0})
        for item in data:
            stats[item.source]["count"] += 1
            m = item.metrics or {}
            stats[item.source]["total_hot"] += m.get("hot", 0) or m.get("view", 0) or 0
        return dict(stats)


def create_ai_analyzer(use_ai: bool = True) -> AIIntelAnalyzer:
    return AIIntelAnalyzer(use_ai=use_ai)
