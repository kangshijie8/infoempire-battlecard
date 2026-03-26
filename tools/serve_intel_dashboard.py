#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
情报报告仪表盘服务器
=====================
轻量级Web服务，暴露IntelReportGenerator为REST API + 仪表盘UI

启动：
    python tools/serve_intel_dashboard.py --port 8082

访问：
    http://localhost:8082/  → 仪表盘
    POST http://localhost:8082/api/intel/report  → 生成报告
    GET  http://localhost:8082/output/  → 浏览历史报告
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from aiohttp import web

# 路径
_TOOL_DIR = Path(__file__).parent.resolve()
_SYS_PATH = str(_TOOL_DIR.parent)
if _SYS_PATH not in sys.path:
    sys.path.insert(0, _SYS_PATH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("intel_dashboard")


# ─── 导入报告生成器 ───────────────────────────────────────────────


async def init_generator():
    """延迟导入，避免循环依赖"""
    from tools.generate_intel_report import IntelReportGenerator
    return IntelReportGenerator()


# ─── 路由处理 ───────────────────────────────────────────────────


async def handle_dashboard(request):
    """情报仪表盘"""
    dashboard_path = _TOOL_DIR.parent / "web" / "static" / "intel_dashboard.html"
    if dashboard_path.exists():
        return web.FileResponse(dashboard_path)
    return web.Response(text="Dashboard not found", status=404)


async def handle_landing(request):
    """落地页"""
    landing_path = _TOOL_DIR.parent / "web" / "static" / "landing.html"
    if landing_path.exists():
        return web.FileResponse(landing_path)
    return web.Response(text="Landing page not found", status=404)


async def handle_battlecard_generate(request):
    """POST /api/battlecard/generate - 生成Battlecard"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    url = data.get("url", "").strip()
    my_product = data.get("my_product")

    if not url:
        return web.json_response({"error": "请输入竞品URL"}, status=400)

    try:
        # 延迟导入battlecard生成器（函数，不是类）
        from tools.battlecard_generator import generate_battlecard

        result = await generate_battlecard(
            target_url=url,
            my_positioning=my_product,
            output_format="html",
        )

        # generate_battlecard返回dict，包含output_file
        if result.get("output_file"):
            result["output_file"] = str(result["output_file"])

        return web.json_response(result)
    except Exception as e:
        logger.error(f"Battlecard生成失败: {e}")
        return web.json_response({"error": str(e)}, status=500)
    """POST /api/intel/report - 生成情报报告"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    sources = data.get("sources", ["toutiao", "bilibili"])
    industry = data.get("industry", "AI工具")
    depth = data.get("depth", "full")
    output_format = data.get("format", "html")

    try:
        # 延迟初始化生成器
        generator = request.app["generator"]
        if generator is None:
            generator = await init_generator()
            request.app["generator"] = generator

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


async def handle_output_static(request):
    """静态文件服务 - output目录"""
    path = request.match_info.get("path", "")
    safe_path = _SYS_PATH + "/output/" + path
    p = Path(safe_path).resolve()
    # 安全检查：不允许路径穿越
    if not str(p).startswith(str(Path(_SYS_PATH + "/output").resolve())):
        return web.Response(text="Forbidden", status=403)
    if p.is_file():
        return web.FileResponse(p)
    # 目录列表
    if p.is_dir():
        files = sorted([f.name for f in p.glob("intel_*.json")], reverse=True)[:20]
        html = "<html><body><h2>Recent Reports</h2><ul>"
        for f in files:
            html += f'<li><a href="/output/{f}">{f}</a></li>'
        html += "</ul></body></html>"
        return web.Response(text=html, content_type="text/html")
    return web.Response(text="Not found", status=404)


async def handle_api_report(request):
    """POST /api/intel/report - 生成情报报告"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    sources = data.get("sources", ["toutiao", "bilibili"])
    industry = data.get("industry", "AI工具")
    depth = data.get("depth", "full")
    output_format = data.get("format", "html")

    try:
        from tools.generate_intel_report import IntelReportGenerator
        generator = IntelReportGenerator()
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
    return web.json_response({
        "status": "ok",
        "service": "intel-dashboard",
        "version": "1.0",
    })


# ─── 应用工厂 ───────────────────────────────────────────────────


def create_app() -> web.Application:
    app = web.Application()
    app["generator"] = None  # 延迟初始化

    app.router.add_get("/", handle_landing)
    app.router.add_get("/dashboard", handle_dashboard)
    app.router.add_post("/api/intel/report", handle_api_report)
    app.router.add_post("/api/battlecard/generate", handle_battlecard_generate)
    app.router.add_get("/api/intel/health", handle_health)
    app.router.add_get("/output/{path:.+}", handle_output_static)

    logger.info("Intel Dashboard API 注册完成")
    return app


# ─── 启动 ──────────────────────────────────────────────────────


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8082)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    app = create_app()
    logger.info(f"🚀 情报仪表盘启动: http://{args.host}:{args.port}/")
    logger.info(f"   仪表盘: http://{args.host}:{args.port}/")
    logger.info(f"   生成报告: POST http://{args.host}:{args.port}/api/intel/report")
    logger.info(f"   健康检查: GET http://{args.host}:{args.port}/api/intel/health")
    web.run_app(app, host=args.host, port=args.port, access_log=None)


if __name__ == "__main__":
    main()
