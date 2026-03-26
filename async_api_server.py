# -*- coding: utf-8 -*-
"""
异步API服务器 - 长耗时任务立即返回job_id，轮询查结果
"""
import asyncio
import json
import os
import sys
import uuid
import logging
import time
from pathlib import Path
from datetime import datetime
from aiohttp import web

_SYS_PATH = str(Path(__file__).parent.parent)
if _SYS_PATH not in sys.path:
    sys.path.insert(0, _SYS_PATH)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("async_server")

# 任务存储
jobs = {}  # job_id -> {"status": "pending/running/done/error", "result": ..., "created_at": ...}

output_dir = Path(_SYS_PATH) / "output"
output_dir.mkdir(exist_ok=True)


async def handle_test_post(request):
    """测试POST"""
    return web.json_response({"test": "POST works", "delay": "0s"})


async def handle_battlecard_generate(request):
    """POST /api/battlecard/generate - 立即返回job_id，后台生成"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    url = data.get("url", "").strip()
    my_product = data.get("my_product")

    if not url:
        return web.json_response({"error": "请输入竞品URL"}, status=400)

    job_id = f"bc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    jobs[job_id] = {"status": "running", "result": None, "created_at": datetime.now().isoformat()}
    logger.info(f"[{job_id}] 任务开始: {url}")

    async def background():
        try:
            from tools.battlecard_generator import generate_battlecard
            result = await generate_battlecard(target_url=url, my_positioning=my_product, output_format="html")
            jobs[job_id]["status"] = "done"
            jobs[job_id]["result"] = result
            logger.info(f"[{job_id}] 完成: {result.get('company')}")
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["result"] = {"error": str(e)}
            logger.error(f"[{job_id}] 错误: {e}")

    asyncio.create_task(background())

    return web.json_response({
        "job_id": job_id,
        "status": "running",
        "message": f"Battlecard生成中，预计60-90秒。轮询 GET /api/battlecard/status/{job_id} 查看结果"
    })


async def handle_battlecard_status(request):
    """GET /api/battlecard/status/{job_id}"""
    job_id = request.match_info["job_id"]
    if job_id not in jobs:
        return web.json_response({"error": "Job不存在或已过期"}, status=404)

    job = jobs[job_id]
    if job["status"] == "done":
        result = job["result"]
        file_url = None
        if result and result.get("output_file"):
            fname = Path(result["output_file"]).name
            file_url = f"/output/{fname}"
        return web.json_response({
            "status": "done",
            "company": result.get("company") if result else "",
            "competitive_win_theme": result.get("competitive_win_theme") if result else "",
            "generation_time_seconds": result.get("generation_time_seconds") if result else 0,
            "file_url": file_url,
        })
    elif job["status"] == "running":
        return web.json_response({"status": "running", "message": "生成中，请稍候..."})
    elif job["status"] == "error":
        return web.json_response({"status": "error", "error": str(job["result"])}, status=500)
    else:
        return web.json_response({"status": "pending"})


# 继承原有仪表盘路由
from tools.serve_intel_dashboard import create_app

app = create_app()
app.router.add_post("/api/battlecard/generate", handle_battlecard_generate)
app.router.add_get(r"/api/battlecard/status/{job_id}", handle_battlecard_status)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8082)
    p.add_argument("--host", default="0.0.0.0")
    args = p.parse_args()
    logger.info(f"Async server启动: http://{args.host}:{args.port}")
    web.run_app(app, host=args.host, port=args.port, access_log=None)
