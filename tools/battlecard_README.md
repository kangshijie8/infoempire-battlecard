# battlecard-generator

> **竞品Battlecard生成器** — 信息帝国核心变现产品 v2

## 定位

替代 $10K/次 的策略顾问交付物。
30秒生成 vs 人工1周。

## 功能

4阶段深度研究 → 完整Battlecard：

| Phase | 内容 |
|-------|------|
| P1 网站抓取 | HTML内容、技术栈识别 |
| P2 公开数据 | 融资/团队/定价/产品定位 |
| P3 舆情分析 | 社区情绪、用户优缺点 |
| P4 Battlecard | 定位/SWOT/功能矩阵/销售话术 |

## 使用方式

```bash
# 单个竞品
python tools/battlecard_generator.py https://notion.so --my-product "AI workspace"

# 输出HTML
python tools/battlecard_generator.py https://notion.so --format html -o notion_bc.html

# 输出Markdown
python tools/battlecard_generator.py https://notion.so --format markdown
```

## 定价

| 套餐 | 价格 | 说明 |
|------|------|------|
| 单次生成 | $29/竞品 | 1份完整Battlecard |
| 月度订阅 | $99/月 | 无限竞品 + 每日变化监控 |
| 企业版 | $299/月 | 多团队 + API接入 + Slack推送 |

## 技术栈

- 采集：httpx + requests
- AI分析：MiniMax-M2.7
- 方法论：Porter's 5 Forces + SWOT + Dunford's Positioning
- 参考：recon(skill) + startup-skill + Subsignal

## 验证结果（2026-03-26）

Notion Battlecard（63秒）：
- 识别技术栈：React + Angular + Vercel
- 定价：$8/user/month
- 弱点5条：性能/离线/学习曲线/移动端/协作卡顿
- 针对性销售话术4条
- 分析师评价深刻

## 状态

✅ 正常运行 | 63秒生成 | MiniMax已接通
