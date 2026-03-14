#!/usr/bin/env python3
"""
每日股票資料更新腳本
- 基本面資料
- 技術指標
- 籌碼資料
"""

import os
import sys

# 加入 scripts 目錄到路徑
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from fundamental_data import main as run_fundamental
from calculate_indicators import main as run_indicators
from chips_data import main as run_chips


def main():
    print("=" * 60)
    print("開始每日股票資料更新")
    print("=" * 60)
    
    # 1. 基本面資料
    print("\n[1/3] 更新基本面資料...")
    try:
        run_fundamental()
    except Exception as e:
        print(f"基本面資料更新失敗: {e}")
    
    # 2. 技術指標
    print("\n[2/3] 更新技術指標...")
    try:
        run_indicators()
    except Exception as e:
        print(f"技術指標更新失敗: {e}")
    
    # 3. 籌碼資料
    print("\n[3/3] 更新籌碼資料...")
    try:
        run_chips()
    except Exception as e:
        print(f"籌碼資料更新失敗: {e}")
    
    print("\n" + "=" * 60)
    print("每日更新完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
