#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
情报报告生成工具
================
信息帝国变现核心产品：AI竞争情报报告API

使用方法：
    # 生成单次报告
    python tools/generate_intel_report.py --industry AI工具 --sources toutiao,bilibili

    # 启动本地API服务
    python tools/generate_intel_report.py --serve --port 8081

    # 带API密钥验证
    python tools/generate_intel_report.py --serve --api-key YOUR_KEY --port 8081

商业定价：
    - 单次报告：¥500（10家竞品）
    - 月度订阅：¥2000/月（每日自动生成）
    - 企业定制：¥5000/月（多行业+实时告警）
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 路径设置
_SYS_PATH = str(Path(__file__).parent.parent)
if _SYS_PATH not in sys.path:
    sys.path.insert(0, _SYS_PATH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("intel_report")


# ─── MiniMax LLM（内嵌，避免依赖问题）───────────────────────────────


def _get_minimax_config() -> dict:
    """从.env加载MiniMax配置"""
    env_path = Path(_SYS_PATH) / ".env"
    config = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
    return {
        "api_key": os.environ.get(
            "MINIMAX_API_KEY",
            config.get("MINIMAX_API_KEY", ""),
        ),
        "base_url": os.environ.get(
            "MINIMAX_BASE_URL",
            config.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic/v1"),
        ),
        "model": os.environ.get(
            "MINIMAX_MODEL",
            config.get("MINIMAX_MODEL", "MiniMax-M2.7"),
        ),
    }


async def _minimax_chat(
    prompt: str,
    system: str = None,
    api_key: str = "",
    base_url: str = "https://api.minimaxi.com/anthropic/v1",
    model: str = "MiniMax-M2.7",
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> Optional[str]:
    """直接调用MiniMax API"""
    if not api_key:
        return None
    try:
        import httpx

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        messages = []
        if system:
            messages.append({"role": "assistant", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/messages",
                headers=headers,
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": messages,
                },
            )
        if resp.status_code == 200:
            for block in resp.json().get("content", []):
                if block.get("type") == "text":
                    return block["text"].strip()
    except Exception as e:
        logger.error(f"MiniMax调用失败: {e}")
    return None


# ─── 核心报告生成器 ────────────────────────────────────────────────


class IntelReportGenerator:
    """
    竞争情报报告生成器

    支持的数据源：
    - toutiao: 头条热点
    - bilibili: B站热门
    - douyin: 抖音热搜
    - github: GitHub趋势（通过爬虫）

    输出格式：
    - JSON: 完整结构化报告
    - Markdown: 可读报告
    - HTML: 网页版报告
    """

    SYSTEM_PROMPT = (
        "你是一个专业的AI竞争情报分析师，擅长从海量数据中提取关键洞察。"
        "你的分析必须基于数据，给出有价值的商业建议。"
        "严格按要求的JSON格式输出，不要额外文字。"
    )

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        cfg = _get_minimax_config()
        self.api_key = api_key or cfg["api_key"]
        self.base_url = base_url or cfg["base_url"]
        self.model = model or cfg["model"]

    async def generate(
        self,
        sources: List[str] = None,
        industry: str = "AI工具",
        depth: str = "full",  # quick / standard / full
        output_format: str = "json",  # json / markdown / html
        output_dir: str = None,
    ) -> dict:
        """
        生成竞争情报报告

        Args:
            sources: 数据源列表，默认["toutiao", "bilibili"]
            industry: 行业/竞品领域
            depth: 报告深度
            output_format: 输出格式
            output_dir: 输出目录

        Returns:
            {
                "report_id": str,
                "generated_at": str,
                "industry": str,
                "sources": List[str],
                "data_count": int,
                "trends": List[dict],
                "opportunities": List[dict],
                "risks": List[dict],
                "insights": List[str],
                "executive_summary": str,
                "recommendations": List[dict],
                "report_file": str,  # 报告文件路径
            }
        """
        sources = sources or ["toutiao", "bilibili"]
        output_dir = output_dir or os.path.join(_SYS_PATH, "output")
        os.makedirs(output_dir, exist_ok=True)

        report_id = f"intel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"[{report_id}] 开始生成报告: industry={industry}, sources={sources}")

        t0 = time.time()

        # Step 1: 采集数据
        logger.info(f"[{report_id}] Step 1: 采集数据...")
        raw_data = await self._collect_data(sources)
        logger.info(f"[{report_id}] 采集完成: {len(raw_data)}条数据")

        if not raw_data:
            return {"error": "数据采集失败", "report_id": report_id}

        # Step 2: AI分析
        logger.info(f"[{report_id}] Step 2: AI分析...")
        analysis = await self._analyze(raw_data, industry)
        logger.info(f"[{report_id}] 分析完成: {len(analysis.get('trends', []))}趋势")

        # Step 3: 生成报告
        logger.info(f"[{report_id}] Step 3: 生成报告...")
        report = {
            "report_id": report_id,
            "generated_at": datetime.now().isoformat(),
            "industry": industry,
            "sources": sources,
            "depth": depth,
            "data_count": len(raw_data),
            **analysis,
        }

        # Step 4: 保存
        report_file = self._save_report(report, output_format, output_dir)
        report["report_file"] = report_file
        report["generation_time_seconds"] = round(time.time() - t0, 1)

        logger.info(f"[{report_id}] 完成！耗时{report['generation_time_seconds']}秒")
        return report

    async def _collect_data(self, sources: List[str]) -> List[dict]:
        """采集各数据源数据"""
        all_data = []

        # 并行采集
        tasks = []
        for src in sources:
            if src == "toutiao":
                tasks.append(self._collect_toutiao())
            elif src == "bilibili":
                tasks.append(self._collect_bilibili())
            elif src == "douyin":
                tasks.append(self._collect_douyin())

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                all_data.extend(result)

        return all_data

    async def _collect_toutiao(self) -> List[dict]:
        """采集头条数据"""
        try:
            import requests

            url = "https://www.toutiao.com/api/pc/feed/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Referer": "https://www.toutiao.com",
            }
            resp = requests.get(url, params={"category": "news_hot", "widen": 1}, headers=headers, timeout=10)
            items = resp.json().get("data", [])[:15]
            return [
                {
                    "source": "toutiao",
                    "competitor": i.get("source", "头条"),
                    "title": i.get("title", ""),
                    "content": i.get("abstract", ""),
                    "url": i.get("article_url", ""),
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {
                        "view": i.get("read_count", 0) or 0,
                        "comment": i.get("comments_count", 0) or 0,
                    },
                }
                for i in items
                if i.get("title") and not i.get("is_ad")
            ]
        except Exception as e:
            logger.warning(f"头条采集失败: {e}")
            return []

    async def _collect_bilibili(self) -> List[dict]:
        """采集B站数据"""
        try:
            import requests

            url = "https://api.bilibili.com/x/web-interface/popular"
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.bilibili.com",
            }
            resp = requests.get(url, params={"pn": 1, "ps": 15}, headers=headers, timeout=10)
            data = resp.json()
            items = data.get("data", {}).get("list", [])
            return [
                {
                    "source": "bilibili",
                    "competitor": i.get("owner", {}).get("name", "B站UP主"),
                    "title": i.get("title", ""),
                    "content": i.get("desc", ""),
                    "url": f"https://www.bilibili.com/video/{i.get('bvid', '')}",
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {
                        "view": i.get("stat", {}).get("view", 0) or 0,
                        "like": i.get("stat", {}).get("like", 0) or 0,
                    },
                }
                for i in items
                if i.get("title")
            ]
        except Exception as e:
            logger.warning(f"B站采集失败: {e}")
            return []

    async def _collect_douyin(self) -> List[dict]:
        """采集抖音数据（热搜榜）"""
        try:
            import requests

            url = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.douyin.com",
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            items = data.get("data", {}).get("word_list", [])[:15]
            return [
                {
                    "source": "douyin",
                    "competitor": "抖音热搜",
                    "title": i.get("word", ""),
                    "content": f"抖音热搜第{i.get('rank', 0)}名",
                    "url": "",
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {
                        "hot": i.get("hot_value", 0) or 0,
                        "view": i.get("value", 0) or 0,
                    },
                }
                for i in items
                if i.get("word")
            ]
        except Exception as e:
            logger.warning(f"抖音采集失败: {e}")
            return []

    async def _analyze(self, raw_data: List[dict], industry: str) -> dict:
        """AI分析数据"""
        # 构建数据摘要
        summary_lines = []
        for item in raw_data[:30]:
            m = item.get("metrics", {})
            metrics_str = ", ".join(f"{k}={v}" for k, v in m.items() if v)
            summary_lines.append(
                f"[{item['source']}] {item.get('competitor','')} | "
                f"{item.get('title','')[:40]} | {metrics_str}"
            )
        data_summary = "\n".join(summary_lines)

        # 并行：趋势 + 机会 + 风险
        trends_prompt = f"""从以下{industry}领域数据中识别3-5个正在兴起的技术/产品/市场趋势。

行业：{industry}
数据：
{data_summary}

输出严格JSON（不要有任何其他文字）：
{{"trends": [{{"keyword": "关键词", "description": "描述", "evidence_count": 数字, "severity": "high/medium/low", "reasoning": "推理"}}]}}"""

        opps_prompt = f"""从以下{industry}领域数据中识别3-5个商业机会（蓝海市场/细分赛道/差异化方向）。

行业：{industry}
数据：
{data_summary}

输出严格JSON（不要有任何其他文字）：
{{"opportunities": [{{"type": "market_gap/tech_gap/content_gap", "description": "描述", "target_audience": "目标用户", "difficulty": "high/medium/low", "potential": "large/medium/small", "action": "可行行动"}}]}}"""

        risks_prompt = f"""从以下{industry}领域数据中识别3-5个威胁/风险。

行业：{industry}
数据：
{data_summary}

输出严格JSON（不要有任何其他文字）：
{{"risks": [{{"type": "competition/technology/policy", "description": "描述", "likelihood": "high/medium/low", "impact": "high/medium/low", "mitigation": "应对策略"}}]}}"""

        # 并行执行3个分析
        trend_task = _minimax_chat(
            trends_prompt, system=self.SYSTEM_PROMPT,
            api_key=self.api_key, base_url=self.base_url, model=self.model
        )
        opp_task = _minimax_chat(
            opps_prompt, system=self.SYSTEM_PROMPT,
            api_key=self.api_key, base_url=self.base_url, model=self.model
        )
        risk_task = _minimax_chat(
            risks_prompt, system=self.SYSTEM_PROMPT,
            api_key=self.api_key, base_url=self.base_url, model=self.model
        )

        trend_resp, opp_resp, risk_resp = await asyncio.gather(
            trend_task, opp_task, risk_task, return_exceptions=True
        )

        def parse_json(text):
            if not text:
                return {}
            import re
            m = re.search(r"\{.*\}", text, re.DOTALL)
            return json.loads(m.group()) if m else {}

        trends = parse_json(trend_resp if not isinstance(trend_resp, Exception) else "").get("trends", [])
        opps = parse_json(opp_resp if not isinstance(opp_resp, Exception) else "").get("opportunities", [])
        risks = parse_json(risk_resp if not isinstance(risk_resp, Exception) else "").get("risks", [])

        # 生成执行摘要
        top_trend = (trends[0]["keyword"] if trends else "无")
        top_opp = (opps[0]["description"] if opps else "无")
        top_risk = (risks[0]["description"] if risks else "无")

        summary_prompt = f"用2-3句话生成执行摘要：核心趋势={top_trend}，核心机会={top_opp}，核心风险={top_risk}。直接输出文字。"
        summary_resp = await _minimax_chat(
            summary_prompt,
            api_key=self.api_key, base_url=self.base_url, model=self.model,
            max_tokens=256
        )
        executive_summary = summary_resp or f"{len(trends)}个趋势、{len(opps)}个机会、{len(risks)}个风险"

        # 生成建议
        recommendations = []
        for t in trends[:3]:
            recommendations.append({
                "type": "trend",
                "priority": t.get("severity", "medium"),
                "action": f"关注【{t['keyword']}】趋势",
                "details": t.get("reasoning", ""),
            })
        for o in opps[:2]:
            recommendations.append({
                "type": "opportunity",
                "priority": o.get("difficulty", "medium"),
                "action": f"探索【{o['description']}】",
                "details": f"潜力:{o.get('potential','未知')} | 行动:{o.get('action','')}",
            })

        return {
            "trends": trends,
            "opportunities": opps,
            "risks": risks,
            "executive_summary": executive_summary,
            "recommendations": recommendations,
        }

    def _save_report(
        self, report: dict, output_format: str, output_dir: str
    ) -> str:
        """保存报告"""
        report_id = report["report_id"]

        if output_format == "json":
            path = os.path.join(output_dir, f"{report_id}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            return path

        elif output_format == "markdown":
            path = os.path.join(output_dir, f"{report_id}.md")
            lines = [
                f"# 📊 竞争情报报告",
                f"",
                f"**报告ID**: {report['report_id']}",
                f"**生成时间**: {report['generated_at']}",
                f"**行业**: {report['industry']}",
                f"**数据源**: {', '.join(report['sources'])}",
                f"**数据量**: {report['data_count']}条",
                f"",
                f"## 📈 执行摘要",
                f"",
                f"{report.get('executive_summary', 'N/A')}",
                f"",
                f"## 🎯 趋势发现",
                f"",
            ]
            for t in report.get("trends", []):
                lines.append(f"- **[{t.get('severity','medium').upper()}] {t.get('keyword','')}**: {t.get('description','')}")
            lines.extend(["", f"## 💡 商业机会", ""])
            for o in report.get("opportunities", []):
                lines.append(f"- **[{o.get('type','')}] {o.get('description','')}** (难度:{o.get('difficulty','')})")
            lines.extend(["", f"## ⚠️ 风险提示", ""])
            for r in report.get("risks", []):
                lines.append(f"- **[{r.get('impact','')}] {r.get('description','')}** - 应对:{r.get('mitigation','')}")
            lines.extend(["", f"## 🚀 行动建议", ""])
            for i, rec in enumerate(report.get("recommendations", []), 1):
                lines.append(f"{i}. **{rec.get('action','')}** [{rec.get('priority','')}]")
                if rec.get("details"):
                    lines.append(f"   {rec['details']}")

            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return path

        elif output_format == "html":
            import html
            path = os.path.join(output_dir, f"{report_id}.html")
            # 简单HTML模板
            html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{report['industry']}情报报告</title>
<style>
body{{font-family:system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}}
h1{{color:#1a1a2e}}h2{{color:#16213e;margin-top:2rem}}
.card{{background:#f8f9fa;border-radius:8px;padding:1rem;margin:0.5rem 0}}
.high{{border-left:4px solid #e63946}} .medium{{border-left:4px solid #f4a261}}
.low{{border-left:4px solid #2a9d8f}} .meta{{color:#666;font-size:0.9rem}}
table{{width:100%;border-collapse:collapse}}td,th{{padding:0.5rem;border:1px solid #ddd}}
</style></head><body>
<h1>📊 {report['industry']} 竞争情报报告</h1>
<div class="meta">
<p><strong>报告ID:</strong> {report['report_id']} | <strong>生成:</strong> {report['generated_at']} | <strong>数据:</strong> {report['data_count']}条 | <strong>耗时:</strong> {report.get('generation_time_seconds','N/A')}秒</p>
</div>
<h2>📈 执行摘要</h2><p>{html.escape(report.get('executive_summary',''))}</p>
<h2>🎯 趋势</h2>"""
            for t in report.get("trends", []):
                severity = t.get("severity", "medium")
                html_content += f'<div class="card {severity}"><strong>{html.escape(t.get("keyword",""))}</strong> [{severity}]<br>{html.escape(t.get("description",""))}</div>'
            html_content += "<h2>💡 机会</h2>"
            for o in report.get("opportunities", []):
                html_content += f'<div class="card"><strong>{html.escape(o.get("description",""))}</strong> [{o.get("type","")}]<br>难度:{o.get("difficulty","")} | 潜力:{o.get("potential","")}</div>'
            html_content += "<h2>⚠️ 风险</h2>"
            for r in report.get("risks", []):
                html_content += f'<div class="card"><strong>{html.escape(r.get("description",""))}</strong> [{r.get("impact","")}]<br>应对:{html.escape(r.get("mitigation",""))}</div>'
            html_content += "<h2>🚀 建议</h2><ol>"
            for rec in report.get("recommendations", []):
                html_content += f'<li><strong>{html.escape(rec.get("action",""))}</strong> [{rec.get("priority","")}]<br>{html.escape(rec.get("details",""))}</li>'
            html_content += "</ol></body></html>"
            with open(path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return path

        return ""


# ─── REST API 服务 ────────────────────────────────────────────────


async def run_api_server(port: int = 8081, api_key: str = None):
    """启动REST API服务"""
    from aiohttp import web

    generator = IntelReportGenerator()

    async def handle_report(request):
        """POST /api/intel/report - 生成情报报告"""
        # API密钥验证
        if api_key:
            provided = request.headers.get("X-API-Key", "")
            if provided != api_key:
                return web.json_response({"error": "Unauthorized"}, status=401)

        data = await request.json()
        sources = data.get("sources", ["toutiao", "bilibili"])
        industry = data.get("industry", "AI工具")
        depth = data.get("depth", "full")
        output_format = data.get("format", "json")

        try:
            report = await generator.generate(
                sources=sources,
                industry=industry,
                depth=depth,
                output_format=output_format,
            )
            return web.json_response(report)
        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_health(request):
        return web.json_response({"status": "ok", "service": "intel-report-api"})

    app = web.Application()
    app.router.add_post("/api/intel/report", handle_report)
    app.router.add_get("/api/intel/health", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🚀 情报API服务启动: http://0.0.0.0:{port}")
    logger.info(f"   POST /api/intel/report  - 生成报告")
    logger.info(f"   GET  /api/intel/health  - 健康检查")

    # 保持运行
    await asyncio.Event().wait()


# ─── CLI 入口 ────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="AI竞争情报报告生成工具")
    parser.add_argument("--industry", default="AI工具", help="行业/竞品领域")
    parser.add_argument("--sources", default="toutiao,bilibili", help="数据源（逗号分隔）")
    parser.add_argument("--depth", default="full", choices=["quick", "standard", "full"])
    parser.add_argument("--format", default="json", choices=["json", "markdown", "html"], help="输出格式")
    parser.add_argument("--output-dir", help="输出目录")
    parser.add_argument("--serve", action="store_true", help="启动API服务")
    parser.add_argument("--port", type=int, default=8081, help="API服务端口")
    parser.add_argument("--api-key", help="API密钥（用于服务鉴权）")
    args = parser.parse_args()

    sources = [s.strip() for s in args.sources.split(",")]

    if args.serve:
        print("启动API服务...")
        asyncio.run(run_api_server(port=args.port, api_key=args.api_key))
    else:
        print(f"生成报告: industry={args.industry}, sources={sources}")
        report = asyncio.run(
            IntelReportGenerator().generate(
                sources=sources,
                industry=args.industry,
                depth=args.depth,
                output_format=args.format,
                output_dir=args.output_dir,
            )
        )
        print(f"\n报告生成完成!")
        print(f"  ID: {report.get('report_id')}")
        print(f"  数据: {report.get('data_count')}条")
        print(f"  趋势: {len(report.get('trends', []))}个")
        print(f"  机会: {len(report.get('opportunities', []))}个")
        print(f"  风险: {len(report.get('risks', []))}个")
        print(f"  摘要: {report.get('executive_summary', '')[:80]}")
        print(f"  文件: {report.get('report_file')}")


if __name__ == "__main__":
    main()
