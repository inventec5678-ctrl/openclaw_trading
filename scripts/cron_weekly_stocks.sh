#!/bin/bash
# 每週股票資料更新 Cron 腳本
# 每周日 20:00 執行

export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH:/opt/homebrew/bin"

cd /Users/changrunlin/.openclaw/workspace/scripts

# 執行股票資料收集
python3.11 collect_taiwan_stocks.py >> /Users/changrunlin/openclaw_data/logs/stocks_cron.log 2>&1

echo "股票資料更新完成 $(date)" >> /Users/changrunlin/openclaw_data/logs/stocks_cron.log
