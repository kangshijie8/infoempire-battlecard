#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Battlecard Generator - 竞品作战卡生成器
"""
import asyncio
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx

_SYS_PATH = str(Path(__file__).parent.parent)
import sys
if _SYS_PATH not in sys.path:
    sys.path.insert(0, _SYS_PATH)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("battlecard")


def _get_minimax_config() -> dict:
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
    }


async def _llm_chat(prompt: str, system: str = None, max_tokens: int = 4096) -> Optional[str]:
    cfg = _get_minimax_config()
    if not cfg["api_key"]:
        return None
    try:
        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        messages = []
        if system:
            messages.append({"role": "assistant", "content": system})
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{cfg['base_url']}/messages",
                headers=headers,
                json={"model": cfg["model"], "max_tokens": max_tokens, "temperature": 0.3, "messages": messages},
            )
        if resp.status_code == 200:
            for block in resp.json().get("content", []):
                if block.get("type") == "text":
                    return block["text"].strip()
    except Exception as e:
        logger.error(f"LLM error: {e}")
    return None


async def phase1_fetch(target_url: str) -> Dict[str, Any]:
    logger.info(f"[P1] Fetch: {target_url}")
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "zh-CN"},
            timeout=30.0, follow_redirects=True
        ) as client:
            resp = await client.get(target_url)
        html = resp.text
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        title_m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        title = title_m.group(1).strip() if title_m else ""
        desc_m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        description = desc_m.group(1).strip() if desc_m else ""
        tech_hints = []
        for pat, tech in [
            ("react", "React"), ("vue", "Vue.js"), ("angular", "Angular"),
            ("nextjs", "Next.js"), ("stripe", "Stripe"), ("intercom", "Intercom"),
            ("mixpanel", "Mixpanel"), ("amplitude", "Amplitude"), ("heap", "Heap"),
            ("hotjar", "Hotjar"), ("cloudflare", "Cloudflare"), ("vercel", "Vercel"),
            ("netlify", "Netlify"), ("aws", "AWS"),
        ]:
            if re.search(pat, html.lower()):
                tech_hints.append(tech)
        logger.info(f"[P1] done: title={title[:50]}")
        return {"url": target_url, "title": title, "description": description,
                "content_preview": text[:2000], "tech_hints": list(set(tech_hints)), "status_code": resp.status_code}
    except Exception as e:
        logger.error(f"[P1] error: {e}")
        return {"url": target_url, "error": str(e)}


async def phase2_public(domain: str, name: str) -> Dict[str, Any]:
    logger.info(f"[P2] Public data: {name}")
    prompt = f"收集{domain}公司的公开信息：成立时间、团队规模、融资、产品定位、定价、目标客户。输出JSON：{{\"company_name\":\"\",\"founded\":\"\",\"team_size\":\"\",\"funding\":\"\",\"founders\":\"\",\"product_positioning\":\"\",\"pricing_hint\":\"\",\"target_audience\":\"\",\"known_metrics\":\"\",\"data_confidence\":\"high/medium/low\"}}。只输出JSON。"
    result = await _llm_chat(prompt, max_tokens=2048)
    if result:
        m = re.search(r"\{.*\}", result, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
                logger.info(f"[P2] done: funding={data.get('funding','N/A')}")
                return data
            except json.JSONDecodeError:
                pass
    return {"company_name": name, "data_confidence": "low"}


async def phase3_sentiment(domain: str, name: str) -> Dict[str, Any]:
    logger.info(f"[P3] Sentiment: {name}")
    prompt = f"分析{domain}的用户社区舆情。输出JSON：{{\"sentiment_overall\":\"positive/neutral/mixed/negative\",\"strengths\":[\"\"],\"weaknesses\":[\"\"],\"common_use_cases\":[\"\"],\"differentiators_vs_competitors\":\"\"}}。只输出JSON。"
    result = await _llm_chat(prompt, max_tokens=2048)
    if result:
        m = re.search(r"\{.*\}", result, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
                logger.info(f"[P3] done: sentiment={data.get('sentiment_overall','N/A')}")
                return data
            except json.JSONDecodeError:
                pass
    return {"sentiment_overall": "unknown"}


async def phase4_battlecard(p1: Dict, p2: Dict, p3: Dict, my_pos: str) -> Dict:
    logger.info("[P4] Generating battlecard...")
    prompt = f"""基于以下数据生成完整Battlecard（严格JSON格式）：

P1: title={p1.get('title','N/A')}, tech={p1.get('tech_hints',[])}, desc={p1.get('description','N/A')}
P2: company={p2.get('company_name','N/A')}, funding={p2.get('funding','N/A')}, pricing={p2.get('pricing_hint','N/A')}, audience={p2.get('target_audience','N/A')}
P3: sentiment={p3.get('sentiment_overall','N/A')}, strengths={p3.get('strengths',[])}, weaknesses={p3.get('weaknesses',[])}
My positioning: {my_pos or 'N/A'}

输出格式：
{{"battlecard":{{"company":"","tagline":"","founded":"","funding":"","target_audience":"","positioning":"","pricing":{{"model":"","starting_price":"","free_tier":"","enterprise":""}},"key_features":[""],"strengths":[""],"weaknesses":[""],"customer_profile":"","security_compliance":""}},"swot":{{"strengths":[""],"weaknesses":[""],"opportunities":[""],"threats":[""]}},"battle_pro_tips":[""],"competitive_win_theme":"","analyst_take":""}}

只输出JSON。"""
    result = await _llm_chat(prompt, system="你是一个CI专家，严格输出JSON。", max_tokens=4096)
    if result:
        m = re.search(r"\{.*\}", result, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
                logger.info("[P4] done")
                return data
            except json.JSONDecodeError as e:
                logger.warning(f"[P4] parse error: {e}")
    return {"error": "generation failed"}


def _to_html(card: Dict) -> str:
    """生成HTML格式的Battlecard"""
    import html as _html
    bc = card.get("battlecard", {})
    swot = card.get("swot", {})
    tips = card.get("battle_pro_tips", [])
    pricing = bc.get("pricing", {})

    # Pre-extract all values to avoid f-string dict issues
    company = _html.escape(bc.get("company", ""))
    tagline = _html.escape(bc.get("tagline", ""))
    founded = _html.escape(bc.get("founded", "N/A"))
    funding = _html.escape(bc.get("funding", "N/A"))
    audience = _html.escape(bc.get("target_audience", "N/A"))
    security = _html.escape(bc.get("security_compliance", "N/A"))
    win_theme = _html.escape(card.get("competitive_win_theme", ""))
    analyst = _html.escape(card.get("analyst_take", ""))
    card_id = _html.escape(card.get("card_id", ""))
    gen_at = _html.escape(card.get("generated_at", ""))
    gen_time = str(card.get("generation_time_seconds", ""))

    pr_model = _html.escape(pricing.get("model", "N/A"))
    pr_start = _html.escape(pricing.get("starting_price", "N/A"))
    pr_free = _html.escape(pricing.get("free_tier", "N/A"))
    pr_enterprise = _html.escape(pricing.get("enterprise", "N/A"))

    def safe_esc(s):
        return _html.escape(str(s)) if s else ""

    features_html = "".join(f'<div class="feature">&bull; {safe_esc(f)}</div>' for f in bc.get("key_features", []))
    strength_html = "".join(f'<li>&bull; {safe_esc(s)}</li>' for s in bc.get("strengths", []))
    weakness_html = "".join(f'<li>&bull; {safe_esc(w)}</li>' for w in bc.get("weaknesses", []))
    tips_html = "".join(f'<li class="tip-item">&nbsp;&nbsp;{safe_esc(t)}</li>' for t in tips) if tips else "<li>N/A</li>"

    def swot_div(title, items, cls):
        items_h = "".join(f"<li>{safe_esc(i)}</li>" for i in items) if items else "<li>N/A</li>"
        return f'<div class="swot-{cls}"><h4>{title}</h4><ul>{items_h}</ul></div>'

    swot_html = (
        swot_div("Strengths", swot.get("strengths", []), "strengths") +
        swot_div("Weaknesses", swot.get("weaknesses", []), "weaknesses") +
        swot_div("Opportunities", swot.get("opportunities", []), "opportunities") +
        swot_div("Threats", swot.get("threats", []), "threats")
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Battlecard - {company}</title>
<style>
body{{font-family:system-ui;max-width:900px;margin:2rem auto;padding:0 1rem;background:#0f1117;color:#e2e8f0}}
h1{{color:#60a5fa;font-size:1.75rem}}h2{{color:#f1f5f9;margin-top:2rem;border-bottom:1px solid #1e293b;padding-bottom:0.5rem}}
h3{{color:#94a3b8;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.05em;margin-top:1.5rem}}
.header{{background:linear-gradient(135deg,#1e3a5f,#1a1a2e);border-radius:12px;padding:1.5rem;margin:1rem 0}}
.tagline{{color:#93c5fd;font-size:1.1rem;margin-top:0.5rem}}
.meta{{display:flex;gap:0.75rem;flex-wrap:wrap;margin-top:0.75rem;font-size:0.85rem;color:#94a3b8}}
.meta span{{background:#0f172a;padding:0.2rem 0.6rem;border-radius:4px}}
.card{{background:#1e293b;border-radius:12px;padding:1.5rem;margin:1rem 0}}
.feature-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:0.75rem}}
.feature{{background:#0f172a;padding:0.75rem;border-radius:6px;font-size:0.9rem}}
.win-theme{{background:linear-gradient(135deg,#3b82f6,#6366f1);padding:1.25rem;border-radius:10px;font-size:1rem;text-align:center;color:white;font-weight:700;margin:1rem 0}}
.swot-grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}
.swot-strengths{{background:linear-gradient(135deg,#064e3b,#065f46);border-radius:8px;padding:1rem}}
.swot-weaknesses{{background:linear-gradient(135deg,#7f1d1d,#991b1b);border-radius:8px;padding:1rem}}
.swot-opportunities{{background:linear-gradient(135deg,#1e3a5f,#1e40af);border-radius:8px;padding:1rem}}
.swot-threats{{background:linear-gradient(135deg,#78350f,#9a3412);border-radius:8px;padding:1rem}}
.tips{{background:#0f172a;padding:1rem;border-radius:8px}}
.tip-item{{padding:0.5rem 0;border-bottom:1px solid #1e293b}}
.tip-item:last-child{{border-bottom:none}}
.footer{{text-align:center;color:#475569;font-size:0.8rem;margin-top:2rem;padding:1rem}}
table{{width:100%;border-collapse:collapse;margin:0.5rem 0}}td,th{{padding:0.6rem 0.75rem;border:1px solid #334155;text-align:left;font-size:0.9rem}}
th{{background:#1e293b;color:#94a3b8;width:120px}}
</style></head><body>
<div class="header"><h1>Sword {company}</h1><p class="tagline">{tagline}</p>
<div class="meta"><span>Founded: {founded}</span><span>Funding: {funding}</span><span>Audience: {audience}</span><span>Security: {security}</span></div></div>
<div class="win-theme">Trophy {win_theme}</div>
<h2>Pricing</h2><div class="card"><table>
<tr><th>Model</th><td>{pr_model}</td></tr>
<tr><th>Starting</th><td>{pr_start}</td></tr>
<tr><th>Free Tier</th><td>{pr_free}</td></tr>
<tr><th>Enterprise</th><td>{pr_enterprise}</td></tr></table></div>
<h2>Key Features</h2><div class="feature-grid">{features_html or '<div class="feature">N/A</div>'}</div>
<h2>Strengths</h2><div class="card"><ul>{strength_html or '<li>N/A</li>'}</ul></div>
<h2>Weaknesses</h2><div class="card"><ul>{weakness_html or '<li>N/A</li>'}</ul></div>
<h2>SWOT</h2><div class="swot-grid">{swot_html}</div>
<h2>Sales Tips</h2><div class="tips"><ul>{tips_html}</ul></div>
<h2>Analyst Take</h2><div class="card"><p>{analyst}</p></div>
<div class="footer">Battlecard #{card_id} | {gen_at} | {gen_time}s</div>
</body></html>"""


async def generate_battlecard(target_url: str, my_positioning: str = None, output_format: str = "html") -> Dict:
    t0 = time.time()
    card_id = f"bc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    parsed = urlparse(target_url)
    domain = parsed.netloc
    name = domain.replace("www.", "").split(".")[0].title()
    logger.info(f"[{card_id}] Start: {target_url}")

    p1, p2, p3 = await asyncio.gather(
        phase1_fetch(target_url),
        phase2_public(domain, name),
        phase3_sentiment(domain, name),
    )
    p4 = await phase4_battlecard(p1, p2, p3, my_positioning)

    card = {
        "card_id": card_id,
        "generated_at": datetime.now().isoformat(),
        "target_url": target_url,
        "company": p4.get("battlecard", {}).get("company", name),
        "data_sources": {"website": {k: v for k, v in p1.items() if k != "content_preview"}, "public_data": p2, "sentiment": p3},
        "battlecard": p4.get("battlecard", {}),
        "swot": p4.get("swot", {}),
        "battle_pro_tips": p4.get("battle_pro_tips", []),
        "competitive_win_theme": p4.get("competitive_win_theme", ""),
        "analyst_take": p4.get("analyst_take", ""),
        "generation_time_seconds": round(time.time() - t0, 1),
    }

    if output_format == "html":
        html = _to_html(card)
        output_dir = Path(_SYS_PATH) / "output"
        output_dir.mkdir(exist_ok=True)
        path = output_dir / f"{card_id}.html"
        path.write_text(html, encoding="utf-8")
        card["output_file"] = str(path)

    return card


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("--my-product", default=None)
    p.add_argument("--format", default="html", choices=["html", "json", "markdown"])
    p.add_argument("--output", "-o", default=None)
    args = p.parse_args()
    result = asyncio.run(generate_battlecard(args.url, args.my_product, args.format))
    if args.output:
        Path(args.output).write_text(str(result), encoding="utf-8")
        print(f"Saved: {args.output}")
    else:
        print(f"Generated: {result['card_id']} in {result['generation_time_seconds']}s")
        if result.get("output_file"):
            print(f"File: {result['output_file']}")
