#!/bin/bash
# 每日股票資料更新腳本
# 每天 16:00 (台灣收盤後) 執行

cd /Users/changrunlin/.openclaw/workspace/scripts

# 執行 Python 更新腳本
python3 daily_update.py >> /Users/changrunlin/openclaw_data/logs/daily_update.log 2>&1

echo "$(date): 更新完成" >> /Users/changrunlin/openclaw_data/logs/daily_update.log
