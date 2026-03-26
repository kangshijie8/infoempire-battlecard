@echo off
REM 每日AI竞争情报自动报告生成
REM 计划任务：每天早上8点自动运行
REM 使用方式：
REM   手动运行: python tools/generate_intel_report.py --industry "AI工具" --sources toutiao,bilibili --format html
REM   或通过cron: openclaw cron add ...

cd /d D:\信息帝国
python -X utf8 tools\generate_intel_report.py --industry "AI工具" --sources toutiao,bilibili --format html --output-dir output
