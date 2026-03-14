#!/usr/bin/env python3
"""
台灣股票資料收集腳本
使用 yfinance 收集台股大盤指數資料
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import json

# 設定路徑
DATA_DIR = os.path.expanduser("~/openclaw_data/stocks")

def collect_taiwan_index():
    """收集台灣加權指數 (^TWII) 歷史資料"""
    
    print("正在下載台灣加權指數 (^TWII) 資料...")
    
    # 計算 30 年前的日期
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*30 + 30)  # 30年 + 緩衝
    
    try:
        # 下載歷史數據
        ticker = yf.Ticker("^TWII")
        df = ticker.history(start=start_date.strftime('%Y-%m-%d'), 
                           end=end_date.strftime('%Y-%m-%d'))
        
        if df.empty:
            print("⚠️ 無法獲取數據，嘗試替代方案...")
            # 嘗試使用其他方式獲取
            df = yf.download("^TWII", period="30y", progress=False)
        
        print(f"成功獲取 {len(df)} 筆資料")
        print(f"日期範圍: {df.index.min()} ~ {df.index.max()}")
        
        # 存成 CSV
        csv_path = os.path.join(DATA_DIR, "taiwan_index_30y.csv")
        df.to_csv(csv_path)
        print(f"✅ CSV 已儲存: {csv_path}")
        
        # 存成 JSON (精簡版)
        json_path = os.path.join(DATA_DIR, "taiwan_index_30y.json")
        
        # 準備 JSON 資料
        json_data = {
            "symbol": "^TWII",
            "name": "台灣加權指數",
            "start_date": str(df.index.min().date()),
            "end_date": str(df.index.max().date()),
            "data_points": len(df),
            "data": []
        }
        
        # 轉換為易讀格式
        for idx, row in df.iterrows():
            json_data["data"].append({
                "date": str(idx.date()),
                "open": round(row['Open'], 2) if pd.notna(row['Open']) else None,
                "high": round(row['High'], 2) if pd.notna(row['High']) else None,
                "low": round(row['Low'], 2) if pd.notna(row['Low']) else None,
                "close": round(row['Close'], 2) if pd.notna(row['Close']) else None,
                "volume": int(row['Volume']) if pd.notna(row['Volume']) else None
            })
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ JSON 已儲存: {json_path}")
        
        # 顯示基本統計
        print("\n=== 基本統計 ===")
        print(f"最新收盤價: {df['Close'].iloc[-1]:.2f}")
        print(f"30年前收盤價: {df['Close'].iloc[0]:.2f}")
        print(f"最高價: {df['High'].max():.2f}")
        print(f"最低價: {df['Low'].min():.2f}")
        print(f"平均成交量: {df['Volume'].mean():,.0f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False

def collect_other_taiwan_etfs():
    """收集其他台灣相關 ETF"""
    
    etfs = {
        "^TAIEX": "台灣加權指數",
        "0050.TW": "元大台灣50",
        "0051.TW": "元大台灣50單日反向",
        "0052.TW": "富邦科技",
    }
    
    print("\n正在收集其他台灣 ETF 資料...")
    
    for symbol, name in etfs.items():
        if symbol == "^TAIEX":
            continue  # 已經收集過
            
        try:
            df = yf.download(symbol, period="5y", progress=False)
            if not df.empty:
                csv_path = os.path.join(DATA_DIR, f"{symbol.replace('.', '_')}_5y.csv")
                df.to_csv(csv_path)
                print(f"✅ {name} ({symbol}): {len(df)} 筆")
        except Exception as e:
            print(f"⚠️ {name}: {e}")

if __name__ == "__main__":
    print("="*50)
    print("台灣股票資料收集腳本")
    print("="*50)
    
    success = collect_taiwan_index()
    
    if success:
        collect_other_taiwan_etfs()
    
    print("\n完成!")
