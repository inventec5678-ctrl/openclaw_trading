#!/bin/bash
# 每日財經新聞收集 Cron 腳本
# 每天 08:00 執行

export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH:/opt/homebrew/bin"

cd /Users/changrunlin/.openclaw/workspace/scripts

# 執行新聞收集
python3.11 collect_news_v3.py >> /Users/changrunlin/openclaw_data/logs/news_cron.log 2>&1

echo "新聞收集完成 $(date)" >> /Users/changrunlin/openclaw_data/logs/news_cron.log
