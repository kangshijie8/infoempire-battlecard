#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞品监控系统
==============
监控特定竞品，当网页内容变化时自动推送告警

商业模式（参考Subsignal $129/月）：
  - 监控10家公司，$29/月
  - 监控50家，$99/月
  - 企业版无限制，$299/月

核心功能：
  1. 添加竞品URL
  2. 定期抓取内容
  3. Diff检测变化
  4. 推送告警（微信/Slack/邮件）
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

_SYS_PATH = str(Path(__file__).parent.parent)
if _SYS_PATH not in sys.path:
    sys.path.insert(0, _SYS_PATH)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("competitor_monitor")


def _get_config() -> dict:
    env_path = Path(_SYS_PATH) / ".env"
    config = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
    return {
        "api_key": config.get("MINIMAX_API_KEY", ""),
        "base_url": config.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic/v1"),
        "model": config.get("MINIMAX_MODEL", "MiniMax-M2.7"),
        "storage_dir": os.path.join(_SYS_PATH, "monitor_data"),
    }


def _hash_content(content: str) -> str:
    """对内容做指纹"""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


async def fetch_page(url: str) -> Dict[str, Any]:
    """抓取页面，返回内容摘要"""
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (compatible; MonitorBot/1.0)"},
            timeout=30.0, follow_redirects=True
        ) as client:
            resp = await client.get(url)
            html = resp.text
            # 提取正文
            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            # 取前3000字符（控制成本）
            text = text[:3000]
            return {
                "url": url,
                "content": text,
                "content_hash": _hash_content(text),
                "status_code": resp.status_code,
                "fetched_at": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"Fetch error: {url}: {e}")
        return {"url": url, "error": str(e)}


async def analyze_changes(
    url: str,
    old_content: str,
    new_content: str,
    api_key: str,
    base_url: str,
    model: str,
) -> Dict[str, Any]:
    """用AI分析变化内容，生成简短告警"""
    if not api_key:
        return {"changes": [], "summary": "无API密钥"}

    # 计算变化的句子
    old_set = set(old_content.split("。")[:50])
    new_set = set(new_content.split("。")[:50])
    added = [s.strip() for s in new_set - old_set if len(s.strip()) > 10]
    removed = [s.strip() for s in old_set - new_set if len(s.strip()) > 10]

    if not added and not removed:
        return {"changes": [], "summary": "无明显变化", "added": [], "removed": []}

    # 用AI分析变化的影响
    prompt = f"""分析以下竞品网站内容变化，用2-3句话说明这对竞争对手意味着什么，以及对你们的影响。

变化内容（新增）：
{chr(10).join(added[:10])}

变化内容（删除）：
{chr(10).join(removed[:10])}

输出JSON：{{"impact":"影响描述（2-3句）","urgency":"high/medium/low","opportunity":"具体机会（如有）"}}
只输出JSON，不要其他文字。"""

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        messages = [
            {"role": "user", "content": prompt}
        ]
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/messages",
                headers=headers,
                json={"model": model, "max_tokens": 512, "temperature": 0.3, "messages": messages},
            )
        if resp.status_code == 200:
            text = resp.json().get("content", [])
            for block in text:
                if block.get("type") == "text":
                    result_str = block["text"].strip()
                    m = re.search(r"\{.*\}", result_str, re.DOTALL)
                    if m:
                        return json.loads(m.group())
    except Exception as e:
        logger.error(f"AI分析失败: {e}")

    return {
        "impact": f"发现{len(added)}处新增、{len(removed)}处删除",
        "urgency": "medium",
        "opportunity": "",
        "added": added[:5],
        "removed": removed[:5],
    }


class CompetitorMonitor:
    """竞品监控器"""

    def __init__(self):
        cfg = _get_config()
        self.api_key = cfg["api_key"]
        self.base_url = cfg["base_url"]
        self.model = cfg["model"]
        self.storage_dir = Path(cfg["storage_dir"])
        self.storage_dir.mkdir(exist_ok=True)
        self.state_file = self.storage_dir / "monitor_state.json"
        self._state = self._load_state()

    def _load_state(self) -> Dict:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        return {"competitors": [], "snapshots": {}}

    def _save_state(self):
        self.state_file.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_competitor(self, name: str, url: str, tag: str = "general") -> str:
        """添加监控竞品"""
        if url in self._state["competitors"]:
            return f"已在监控列表: {url}"
        self._state["competitors"].append({"name": name, "url": url, "tag": tag})
        self._save_state()
        logger.info(f"添加监控: {name} ({url})")
        return f"已添加: {name}"

    def remove_competitor(self, url: str) -> str:
        """移除监控竞品"""
        self._state["competitors"] = [c for c in self._state["competitors"] if c["url"] != url]
        self._save_state()
        return f"已移除: {url}"

    async def check_all(self) -> List[Dict]:
        """检查所有竞品变化"""
        results = []
        competitors = self._state["competitors"]

        logger.info(f"开始检查 {len(competitors)} 个竞品...")
        t0 = time.time()

        for comp in competitors:
            result = await self._check_one(comp)
            results.append(result)
            await asyncio.sleep(1)  # 避免高频

        elapsed = round(time.time() - t0, 1)
        logger.info(f"检查完成: {len(results)} 个竞品，耗时 {elapsed}s")

        # 找出有变化的
        changed = [r for r in results if r.get("has_changes")]
        if changed:
            logger.info(f"⚠️ 发现 {len(changed)} 个竞品有变化！")
        else:
            logger.info("✅ 无变化")

        return results

    async def _check_one(self, comp: Dict) -> Dict:
        url = comp["url"]
        name = comp["name"]
        tag = comp.get("tag", "general")

        logger.info(f"检查: {name}")
        fetch_result = await fetch_page(url)

        if fetch_result.get("error"):
            return {"name": name, "url": url, "tag": tag, "error": fetch_result["error"], "has_changes": False}

        new_hash = fetch_result["content_hash"]
        new_content = fetch_result["content"]

        # 获取上次快照
        snapshots = self._state.get("snapshots", {})
        last = snapshots.get(url, {})

        result = {
            "name": name,
            "url": url,
            "tag": tag,
            "fetched_at": fetch_result["fetched_at"],
            "status_code": fetch_result.get("status_code"),
            "has_changes": False,
            "changes": None,
        }

        if not last:
            # 首次抓取，保存快照
            snapshots[url] = {
                "hash": new_hash,
                "content": new_content,
                "fetched_at": fetch_result["fetched_at"],
                "fetched_count": 1,
            }
            logger.info(f"  新增快照（首次）")
        elif last.get("hash") != new_hash:
            # 有变化
            old_content = last.get("content", "")
            logger.info(f"  ⚠️ 检测到变化！")

            # AI分析变化
            analysis = await analyze_changes(
                url, old_content, new_content,
                self.api_key, self.base_url, self.model
            )

            # 保存新快照
            snapshots[url] = {
                "hash": new_hash,
                "content": new_content,
                "fetched_at": fetch_result["fetched_at"],
                "fetched_count": last.get("fetched_count", 0) + 1,
            }

            result["has_changes"] = True
            result["changes"] = analysis
            logger.info(f"  变化分析: {analysis.get('impact', 'N/A')[:80]}")
        else:
            logger.info(f"  ✅ 无变化（已监控{last.get('fetched_count', 0)}次）")
            snapshots[url] = {
                **last,
                "fetched_count": last.get("fetched_count", 0) + 1,
                "last_check": datetime.now().isoformat(),
            }

        # 保存状态
        self._state["snapshots"] = snapshots
        self._save_state()

        return result

    def list_competitors(self) -> List[Dict]:
        return self._state["competitors"]

    def get_reports(self) -> List[Dict]:
        """获取历史监控报告"""
        results = []
        for url, snap in self._state.get("snapshots", {}).items():
            results.append({
                "url": url,
                "name": next((c["name"] for c in self._state["competitors"] if c["url"] == url), url),
                "fetched_count": snap.get("fetched_count", 0),
                "last_fetched": snap.get("fetched_at", "N/A"),
            })
        return sorted(results, key=lambda x: x["last_fetched"], reverse=True)


async def main():
    import argparse
    p = argparse.ArgumentParser(description="竞品监控系统")
    p.add_argument("--add", nargs=2, metavar=("NAME", "URL"), help="添加监控竞品")
    p.add_argument("--remove", metavar="URL", help="移除监控竞品")
    p.add_argument("--check", action="store_true", help="立即检查所有竞品")
    p.add_argument("--list", action="store_true", help="列出监控列表")
    p.add_argument("--reports", action="store_true", help="查看监控历史")
    args = p.parse_args()

    monitor = CompetitorMonitor()

    if args.add:
        name, url = args.add
        print(monitor.add_competitor(name, url))

    elif args.remove:
        print(monitor.remove_competitor(args.remove))

    elif args.check:
        results = await monitor.check_all()
        for r in results:
            status = "⚠️ 变化" if r.get("has_changes") else "✅ 无变化"
            if r.get("error"):
                status = f"❌ 错误: {r['error']}"
            print(f"  {r['name']}: {status}")
            if r.get("changes"):
                c = r["changes"]
                print(f"    影响: {c.get('impact', 'N/A')}")
                print(f"    紧急度: {c.get('urgency', 'N/A')}")

    elif args.list:
        for c in monitor.list_competitors():
            print(f"  [{c['tag']}] {c['name']}: {c['url']}")

    elif args.reports:
        for r in monitor.get_reports():
            print(f"  {r['name']}: 监控{r['fetched_count']}次，最后{r['last_fetched']}")

    else:
        p.print_help()


if __name__ == "__main__":
    asyncio.run(main())
