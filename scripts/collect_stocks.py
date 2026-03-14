#!/usr/bin/env python3
"""
股票資料收集腳本 - 擴展版
收集台股和美股資料
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import time

# 設定路徑
DATA_DIR = os.path.expanduser("~/openclaw_data/stocks")

# 確保目錄存在
os.makedirs(DATA_DIR, exist_ok=True)

# 台股清單 (20檔目標名單)
TAIWAN_STOCKS = {
    # 權值股
    "2330.TW": "台積電",
    "0050.TW": "元大台灣50",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
    # 航運
    "2603.TW": "長榮",
    # 金融
    "2885.TW": "元大金控",
    "2883.TW": "開發金",
    "2881.TW": "富邦金",
    "2882.TW": "國泰金",
    # 半導體
    "2303.TW": "聯電",
    "2379.TW": "瑞昱",
    "3034.TW": "聯詠",
    # 電子
    "2474.TW": "可成",
    "2395.TW": "研華",
    "2409.TW": "友達",
    "2412.TW": "中華電",
    "2439.TW": "聯傑",
    "2441.TW": "億亨",
    "2451.TW": "崇越",
    "2460.TW": "宣德",
    "2478.TW": "大毅",
    "2498.TW": "宏達電",
    # 其他熱門
    "6505.TW": "台塑化",
    "2892.TW": "中信金",
    "2105.TW": "正新",
    "9914.TW": "美利達",
    "9917.TW": "桂盟",
    # ETF
    "00878.TW": "國泰永續高股息",
    "00881.TW": "國泰台灣5G+",
    "00919.TW": "群益台灣精選高股息",
    # 其他
    "3008.TW": "大立光",
    "0052.TW": "富邦科技",
    # 新增 30 檔 (2026-03-14)
    "2301.TW": "光寶科",
    "2327.TW": "國巨",
    "2344.TW": "華邦電",
    "2353.TW": "宏碁",
    "2356.TW": "英業達",
    "2357.TW": "華碩",
    "2362.TW": "景碩",
    "2382.TW": "廣達",
    "2383.TW": "台光電",
    "2401.TW": "凌陽",
    "2408.TW": "南亞科",
    "2417.TW": "遠傳",
    "2421.TW": "建準",
    "2427.TW": "三商電",
    "2431.TW": "聯強",
    "2449.TW": "京元電",
    "2453.TW": "瑞儀",
    "2472.TW": "立隆電",
    "2481.TW": "強茂",
    "2492.TW": "華新科",
    "3004.TW": "融程電",
    "3005.TW": "神基",
    "3016.TW": "嘉澤",
    "3017.TW": "奇鋐",
    "3023.TW": "信邦",
    "3033.TW": "威健",
    "3044.TW": "健鼎",
    "3045.TW": "台灣大",
    "3481.TW": "群創",
    "3532.TW": "台勝科",
    "3686.TW": "達發",
    "3706.TW": "祥碩",
    "6415.TW": "矽力-KY",
    "6515.TW": "晶心科",
    "6533.TW": "創意",
    "6548.TW": "長科*",
    "6573.TW": "虹堡",
    "6592.TW": "合盈",
    "6603.TW": "巨路",
    "6703.TW": "嘉澤",
    "6754.TW": "蒙恬",
    "6781.TW": "AES-KY",
    "6792.TW": "鼎固",
    "6830.TW": "芯鼎",
    "6841.TW": "長科*",
    "6854.TW": "易威",
    "6885.TW": "桓鼎",
    "8016.TW": "矽創",
    "8028.TW": "元山",
    "8074.TW": "群聯",
    "8105.TW": "太景*",
    "8112.TW": "至上",
    "8255.TW": "敦陽",
    "8271.TW": "宇瞻",
    "8316.TW": "中磊",
    "8415.TW": "大國",
    "8450.TW": "微星",
    "8472.TW": "撼訊",
    # 新增 20 檔 (2026-03-14)
    "2227.TW": "裕日車",
    "2201.TW": "裕隆",
    "2207.TW": "和泰車",
    "2103.TW": "台橡",
    "1718.TW": "中纖",
    "1722.TW": "台肥",
    "1723.TW": "中化",
    "1711.TW": "永光",
    "1707.TW": "葡萄王",
    "1709.TW": "台聚集",
    "2618.TW": "長榮航",
    "2615.TW": "萬海",
    "2645.TW": "星宇航",
    "2633.TW": "台灣高鐵",
    "2637.TW": "慧洋-KY",
    "2609.TW": "陽明",
    "2605.TW": "新建",
    "2606.TW": "裕民",
    "2607.TW": "榮運",
    "2608.TW": "大榮",
    "2610.TW": "華航",
}

# 美股清單
US_STOCKS = {
    # 大型科技
    "META": "Meta Platforms",
    "GOOGL": "Alphabet (Google)",
    "AMZN": "Amazon",
    "MSFT": "Microsoft",
    "AAPL": "Apple",
    "NVDA": "NVIDIA",
    "AVGO": "Broadcom",
    "ORCL": "Oracle",
    # 動力股
    "AMD": "AMD",
    "INTC": "Intel",
    "QCOM": "Qualcomm",
    "TXN": "Texas Instruments",
    "MU": "Micron Technology",
    # 金融
    "JPM": "JPMorgan Chase",
    "BAC": "Bank of America",
    "GS": "Goldman Sachs",
    "MS": "Morgan Stanley",
    "V": "Visa",
    "MA": "Mastercard",
    # 消費
    "COST": "Costco",
    "WMT": "Walmart",
    "HD": "Home Depot",
    "MCD": "McDonald's",
    "NKE": "Nike",
    # 能源
    "XOM": "Exxon Mobil",
    "CVX": "Chevron",
    "COP": "ConocoPhillips",
    # 生技
    "UNH": "UnitedHealth",
    "JNJ": "Johnson & Johnson",
    "PFE": "Pfizer",
    "MRK": "Merck",
    "ABBV": "AbbVie",
}

def collect_stock(symbol, name, period="2y"):
    """收集單一股票資料"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            print(f"  ⚠️ {name} ({symbol}): 無數據")
            return None
        
        # 基本資訊
        info = ticker.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        market_cap = info.get('marketCap')
        
        result = {
            "symbol": symbol,
            "name": name,
            "data_points": len(df),
            "start_date": str(df.index.min().date()),
            "end_date": str(df.index.max().date()),
            "current_price": current_price,
            "market_cap": market_cap,
            "latest": {
                "date": str(df.index[-1].date()),
                "open": round(df['Open'].iloc[-1], 2) if pd.notna(df['Open'].iloc[-1]) else None,
                "high": round(df['High'].iloc[-1], 2) if pd.notna(df['High'].iloc[-1]) else None,
                "low": round(df['Low'].iloc[-1], 2) if pd.notna(df['Low'].iloc[-1]) else None,
                "close": round(df['Close'].iloc[-1], 2) if pd.notna(df['Close'].iloc[-1]) else None,
                "volume": int(df['Volume'].iloc[-1]) if pd.notna(df['Volume'].iloc[-1]) else None,
            },
            "statistics": {
                "latest_close": round(df['Close'].iloc[-1], 2) if pd.notna(df['Close'].iloc[-1]) else None,
                "highest": round(df['High'].max(), 2),
                "lowest": round(df['Low'].min(), 2),
                "avg_volume": int(df['Volume'].mean()) if len(df) > 0 else None,
            }
        }
        
        print(f"  ✅ {name} ({symbol}): {len(df)} 筆, 現在價: {current_price}")
        return result
        
    except Exception as e:
        print(f"  ❌ {name} ({symbol}): {e}")
        return None

def collect_taiwan_index():
    """收集台灣加權指數"""
    print("\n正在收集台灣加權指數...")
    try:
        ticker = yf.Ticker("^TWII")
        df = ticker.history(period="10y")
        
        if not df.empty:
            csv_path = os.path.join(DATA_DIR, "taiwan_index_10y.csv")
            df.to_csv(csv_path)
            print(f"  ✅ 台灣加權指數: {len(df)} 筆")
            return {"symbol": "^TWII", "name": "台灣加權指數", "data_points": len(df)}
    except Exception as e:
        print(f"  ❌ 台灣加權指數: {e}")
    return None

def main():
    print("="*60)
    print("股票資料收集腳本 - 擴展版")
    print("="*60)
    
    all_data = {
        "collected_at": datetime.now().isoformat(),
        "taiwan_stocks": [],
        "us_stocks": [],
        "taiwan_index": None,
    }
    
    # 收集台灣加權指數
    all_data["taiwan_index"] = collect_taiwan_index()
    
    # 收集台股
    print("\n正在收集台股資料...")
    for symbol, name in TAIWAN_STOCKS.items():
        result = collect_stock(symbol, name)
        if result:
            all_data["taiwan_stocks"].append(result)
        time.sleep(0.5)  # 避免請求過快
    
    # 收集美股
    print("\n正在收集美股資料...")
    for symbol, name in US_STOCKS.items():
        result = collect_stock(symbol, name)
        if result:
            all_data["us_stocks"].append(result)
        time.sleep(0.5)
    
    # 儲存完整 JSON
    json_path = os.path.join(DATA_DIR, "stocks_all.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已儲存: {json_path}")
    
    # 儲存摘要
    summary = {
        "collected_at": datetime.now().isoformat(),
        "taiwan_count": len(all_data["taiwan_stocks"]),
        "us_count": len(all_data["us_stocks"]),
        "taiwan_stocks": [{"symbol": s["symbol"], "name": s["name"], "current_price": s.get("current_price")} for s in all_data["taiwan_stocks"]],
        "us_stocks": [{"symbol": s["symbol"], "name": s["name"], "current_price": s.get("current_price")} for s in all_data["us_stocks"]],
    }
    
    summary_path = os.path.join(DATA_DIR, "stocks_summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"✅ 已儲存: {summary_path}")
    
    print(f"\n完成! 共收集 {len(all_data['taiwan_stocks'])} 檔台股, {len(all_data['us_stocks'])} 檔美股")

if __name__ == "__main__":
    main()
