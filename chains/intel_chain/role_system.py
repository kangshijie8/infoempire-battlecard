"""
intel_chain - MetaGPT风格SOP角色系统
==========================================
核心思想：Code = SOP(Team)
把intel_chain的4个模块变成4个Role，通过SOP协作

Role架构：
  MonitorRole  → 观察数据源变化，写入共享上下文
  AnalyzerRole → 从上下文读取数据，AI分析，写入上下文
  AlerterRole → 从上下文读取分析结果，判断是否告警
  ReporterRole → 从上下文读取所有结果，生成报告

共享上下文（Blackboard）：
  所有Role读写同一个Context对象，实现松耦合
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import sys, os

logger = logging.getLogger(__name__)


class RoleState(Enum):
    IDLE = "idle"
    WORKING = "working"
    DONE = "done"
    ERROR = "error"


@dataclass
class Context:
    """
    共享黑板上下文
    所有Role读写同一个Context，通过key-value存储中间结果
    """
    # 原始数据
    raw_data: List[Any] = field(default_factory=list)

    # 各Role产出
    monitor_output: Dict = field(default_factory=dict)   # Monitor产出
    analysis: Dict = field(default_factory=dict)          # Analyzer产出（ai_analyzer结果）
    alerts: List[Dict] = field(default_factory=list)     # Alerter产出
    report: Dict = field(default_factory=dict)            # Reporter产出

    # 元数据
    timestamps: Dict[str, str] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)

    # 全局标记
    metadata: Dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any):
        setattr(self, key, value)
        self.timestamps[key] = datetime.now().isoformat()

    def get(self, key: str, default=None) -> Any:
        return getattr(self, key, default)

    def has(self, key: str) -> bool:
        return hasattr(self, key) and getattr(self, key) is not None


class Role:
    """
    角色基类（MetaGPT风格）

    每个Role有：
    - name: 角色名称
    - role_description: 角色描述（用于LLM理解职责）
    - actions: 可执行的动作列表
    - watch_events: 监听的事件类型
    """

    name: str = "BaseRole"
    role_description: str = "基础角色"

    def __init__(self, context: Context):
        self.context = context
        self.state = RoleState.IDLE
        self._llm_available = False

    async def think(self, prompt: str) -> str:
        """使用可用LLM思考（子类可覆盖）"""
        raise NotImplementedError

    async def act(self) -> bool:
        """执行角色主动作，返回是否成功"""
        raise NotImplementedError

    async def run(self) -> bool:
        """运行角色（think → act）"""
        self.state = RoleState.WORKING
        try:
            result = await self.act()
            self.state = RoleState.DONE if result else RoleState.ERROR
            return result
        except Exception as e:
            logger.error(f"[{self.name}] 执行异常: {e}")
            self.state = RoleState.ERROR
            self.context.errors[self.name] = str(e)
            return False


# ─── MiniMax LLM集成 ───────────────────────────────────────────────


class MiniMaxLLM:
    """MiniMax Anthropic兼容API调用器"""

    def __init__(self):
        self.api_key = os.getenv(
            "MINIMAX_API_KEY",
            "sk-cp-u41neK4opNpopBFRmhuHKAdQ2QpSj3dW5ziFrSJcyztEAGFQjm3RHRNaguRkLVo31oeBTT-DuxXF7AtIF4d2E65Pvyog1izC_i18dRSUrk013XSRC8K9sZY"
        )
        self.base_url = os.getenv(
            "MINIMAX_BASE_URL",
            "https://api.minimaxi.com/anthropic/v1"
        )
        self.model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")
        self._available = bool(self.api_key)

    async def chat(
        self,
        prompt: str,
        system: str = None,
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> Optional[str]:
        if not self._available:
            return None

        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            }
            messages = []
            if system:
                messages.append({"role": "assistant", "content": system})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=payload,
                )
            if resp.status_code == 200:
                data = resp.json()
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        return block["text"].strip()
        except Exception as e:
            logger.error(f"[MiniMax] 调用失败: {e}")
        return None


# ─── 具体Role实现 ────────────────────────────────────────────────


class MonitorRole(Role):
    """
    Monitor角色 - 观察数据源
    职责：采集数据源变化，检测异常，输出观察报告
    """
    name = "Monitor"
    role_description = "监控数据源，检测变化和异常"

    def __init__(self, context: Context, data_sources: List[Any]):
        super().__init__(context)
        self.data_sources = data_sources
        self.llm = MiniMaxLLM()

    async def think(self, prompt: str) -> str:
        result = await self.llm.chat(
            system="你是一个专业的监控分析师，用简洁的中文报告观察结果。",
            prompt=prompt,
            max_tokens=512,
        )
        return result or ""

    async def act(self) -> bool:
        logger.info("[Monitor] 开始监控...")
        observations = []

        for source in self.data_sources:
            # 调用数据源
            try:
                if hasattr(source, 'monitor_all'):
                    # 标准数据源（IntelTeam兼容）
                    data = source.monitor_all()
                    src_name = getattr(source, 'name', str(source))
                elif hasattr(source, 'crawl'):
                    # BaseCrawler 标准化爬虫
                    data = source.crawl()
                    src_name = getattr(source, 'name', 'unknown')
                elif callable(source):
                    result = source()
                    data = result if isinstance(result, list) else []
                    src_name = str(source)
                else:
                    continue

                observations.append({
                    "source": src_name,
                    "count": len(data),
                })
                self.context.raw_data.extend(data)
            except Exception as e:
                logger.warning(f"[Monitor] 数据源 {source} 异常: {e}")

        # 用LLM分析观察
        if observations and self.llm._available:
            summary_prompt = f"分析以下监控观察，给出1-2句总结：\n{observations}"
            summary = await self.think(summary_prompt)
        else:
            summary = f"监控到{len(observations)}个数据源，共{len(self.context.raw_data)}条数据"

        self.context.monitor_output = {
            "observations": observations,
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
        }
        logger.info(f"[Monitor] 完成：{summary}")
        return True


class AnalyzerRole(Role):
    """
    Analyzer角色 - 深度分析
    职责：读取Monitor的输出，进行深度AI分析
    复用了 ai_analyzer.py 的能力
    """
    name = "Analyzer"
    role_description = "深度AI分析，识别趋势/机会/风险"

    def __init__(self, context: Context):
        super().__init__(context)
        self._ai_analyzer = None

    def _get_ai_analyzer(self):
        """懒加载ai_analyzer"""
        if self._ai_analyzer is None:
            try:
                # 确保ai_analyzer所在路径在sys.path中
                _intel_path = os.path.dirname(os.path.abspath(__file__))
                if _intel_path not in sys.path:
                    sys.path.insert(0, _intel_path)
                from ai_analyzer import AIIntelAnalyzer
                self._ai_analyzer = AIIntelAnalyzer()
            except Exception as e:
                logger.warning(f"[Analyzer] ai_analyzer加载失败: {e}")
        return self._ai_analyzer

    async def act(self) -> bool:
        logger.info("[Analyzer] 开始分析...")
        raw = self.context.get("raw_data", [])
        if not raw:
            logger.info("[Analyzer] 无数据，跳过")
            return True

        ai = self._get_ai_analyzer()
        if ai and ai.use_ai:
            # 直接await异步方法（避免asyncio.run嵌套）
            try:
                self.context.analysis = await ai.analyze_async(raw)
                logger.info(f"[Analyzer] AI分析完成：{len(self.context.analysis.get('trends', []))}趋势")
            except Exception as e:
                logger.warning(f"[Analyzer] AI分析异常，fallback: {e}")
                self.context.analysis = ai._rule_analyze(raw)
        else:
            # Fallback：简单统计
            if ai:
                self.context.analysis = ai._rule_analyze(raw)
            else:
                self.context.analysis = {
                    "summary": f"规则分析：{len(raw)}条数据",
                    "ai_powered": False,
                }
        return True


class AlerterRole(Role):
    """
    Alerter角色 - 告警判断
    职责：读取分析结果，判断是否需要告警
    """
    name = "Alerter"
    role_description = "根据分析结果判断是否触发告警"

    def __init__(self, context: Context, threshold_high: int = 5):
        super().__init__(context)
        self.threshold_high = threshold_high
        self.llm = MiniMaxLLM()

    async def act(self) -> bool:
        logger.info("[Alerter] 判断告警...")
        analysis = self.context.get("analysis", {})
        alerts = []

        # 规则：热度超过阈值的趋势 → 告警
        trends = analysis.get("trends", [])
        for t in trends:
            severity = t.get("severity", "low")
            evidence = t.get("evidence_count", 0)
            if severity == "high" or evidence >= 3:
                alerts.append({
                    "level": "high" if severity == "high" else "medium",
                    "type": "trend",
                    "keyword": t.get("keyword", ""),
                    "description": t.get("description", ""),
                    "reasoning": t.get("reasoning", ""),
                })

        # AI增强：额外用LLM判断是否需要升级告警
        if alerts and self.llm._available:
            alert_summary = "\n".join([
                f"- [{a['level']}] {a['keyword']}: {a['description']}"
                for a in alerts[:5]
            ])
            prompt = f"""以下是当前告警列表，判断是否需要立即通知决策者：
{alert_summary}

输出JSON：{{"should_alert": true/false, "priority": "high/medium/low", "reason": "原因"}}
直接输出JSON，不要其他文字。"""

            result = await self.llm.chat(
                prompt=prompt,
                system="你是告警分析专家，严格输出JSON。",
                max_tokens=256,
            )
            if result:
                import re, json
                m = re.search(r'\{.*\}', result, re.DOTALL)
                if m:
                    decision = json.loads(m.group())
                    if decision.get("should_alert", False):
                        for a in alerts:
                            a["ai_priority"] = decision.get("priority", "medium")
                    else:
                        alerts = []  # AI判断不需要告警，清空

        self.context.alerts = alerts
        logger.info(f"[Alerter] 完成：{len(alerts)}个告警")
        return True


class ReporterRole(Role):
    """
    Reporter角色 - 报告生成
    职责：汇总所有Role产出，生成最终报告
    """
    name = "Reporter"
    role_description = "汇总所有分析结果，生成结构化报告"

    def __init__(self, context: Context, output_path: str = "output"):
        super().__init__(context)
        self.output_path = output_path
        self.llm = MiniMaxLLM()
        os.makedirs(output_path, exist_ok=True)

    async def act(self) -> bool:
        logger.info("[Reporter] 生成报告...")

        report = {
            "report_id": f"intel_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "monitor_summary": self.context.get("monitor_output", {}).get("summary", ""),
            "analysis": self.context.get("analysis", {}),
            "alerts": self.context.get("alerts", []),
            "ai_powered": self.context.analysis.get("ai_powered", False) if hasattr(self.context, "analysis") else False,
        }

        # AI增强摘要
        if self.llm._available:
            trends = report["analysis"].get("trends", [])
            opps = report["analysis"].get("opportunities", [])
            if trends or opps:
                top_trend = trends[0].get("keyword", "无") if trends else "无"
                top_opp = opps[0].get("description", "无") if opps else "无"
                prompt = f"生成执行摘要：核心趋势={top_trend}，核心机会={top_opp}。直接输出文字。"
                summary = await self.llm.chat(prompt=prompt, max_tokens=128)
                if summary:
                    report["executive_summary"] = summary

        self.context.report = report

        # 保存JSON
        import json
        json_path = os.path.join(
            self.output_path,
            f"{report['report_id']}.json"
        )
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"[Reporter] 报告已生成：{json_path}")
        return True


# ─── SOP Team 编排器 ───────────────────────────────────────────────


class IntelTeam:
    """
    Intel Team - MetaGPT风格SOP编排

    4个Role按SOP顺序执行：
    Monitor → Analyzer → Alerter → Reporter

    每个Role只看Context，不直接调用其他Role（松耦合）
    """

    def __init__(self, data_sources: List[Any] = None, output_path: str = "output"):
        self.context = Context()
        self.data_sources = data_sources or []
        self.output_path = output_path

        # 实例化4个Role
        self.monitor = MonitorRole(self.context, self.data_sources)
        self.analyzer = AnalyzerRole(self.context)
        self.alerter = AlerterRole(self.context)
        self.reporter = ReporterRole(self.context, self.output_path)

        # SOP定义：角色执行顺序
        self._sop: List[Role] = [
            self.monitor,
            self.analyzer,
            self.alerter,
            self.reporter,
        ]

    async def run(self) -> Context:
        """按SOP顺序执行所有Role"""
        logger.info(f"=== IntelTeam SOP启动（{len(self._sop)}个Role）===")

        for role in self._sop:
            success = await role.run()
            if not success:
                logger.warning(f"[IntelTeam] {role.name} 执行失败，继续...")
                # 不中断，继续执行后续Role

        logger.info("=== IntelTeam SOP完成 ===")
        return self.context

    def run_sync(self) -> Context:
        """同步入口"""
        return asyncio.run(self.run())
