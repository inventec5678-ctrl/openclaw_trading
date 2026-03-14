#!/usr/bin/env python3
"""
籌碼資料收集 (增強版)
- 法人買賣
- 外資持股
- 股權分散
- 融券/借券 (short_ratio)
- 主力買賣推斷 (from volume)
"""

import requests
import json
import os
from datetime import datetime, timedelta
import time
import yfinance as yf

DATA_DIR = os.path.expanduser("~/openclaw_data/chips")

# 擴展台股清單
TW_STOCKS = [
    "2330.TW",  # 台積電
    "2317.TW",  # 鴻海
    "2454.TW",  # 聯發科
    "0050.TW",  # 元大台灣50
    "0051.TW",  # 元大台灣50
    "2303.TW",  # 聯電
    "2308.TW",  # 台達電
    "2379.TW",  # 瑞昱
    "3034.TW",  # 聯詠
    "3413.TW",  # 友達
    "3481.TW",  # 群創
    "4938.TW",  # 和碩
    "6456.TW",  # 聯亞
    "6515.TW",  # 穎崴
    "6669.TW",  # 宏碁
    "6706.TW",  # 惠特
]

# 擴展美股清單
US_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX", "AMD",
    "INTC", "AVGO", "ORCL", "CRM", "ADBE", "PYPL", "SQ", "COIN", "UBER",
    "LYFT", "SNAP", "TWLO", "ZM", "SHOP", "SPOT", "SQ", "MAR", "DIS",
    "BA", "CAT", "GE", "MMM", "IBM", "XOM", "CVX", "COP", "SLB",
    "JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "V", "MA",
    "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "DHR",
    "KO", "PEP", "MCD", "SBUX", "NKE", "HD", "LOW", "TGT", "COST"
]


def get_twse_institutional(stock_id):
    """從台灣證券交易所取得法人買賣資料"""
    try:
        if "." in stock_id:
            code = stock_id.split(".")[0]
        else:
            code = stock_id
        
        url = "https://www.twse.com.tw/rwd/zh/fund/T86"
        
        today = datetime.now()
        end_date = today.strftime("%Y%m%d")
        
        params = {
            "date": end_date,
            "stockNo": code,
            "response": "json",
            "dayDate": "",
            "weekDate": "",
            "monthDate": "",
            "fieldType": "ALL",
            "sortOrder": "ASC"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        return data
    except Exception as e:
        print(f"Error fetching institutional data for {stock_id}: {e}")
        return {}


def get_twse_shareholding(stock_id):
    """取得外公資持股資料"""
    try:
        if "." in stock_id:
            code = stock_id.split(".")[0]
        else:
            code = stock_id
        
        url = "https://www.twse.com.tw/rwd/zh/fund/BWIBBU_d"
        
        today = datetime.now()
        date_str = today.strftime("%Y%m%d")
        
        params = {
            "date": date_str,
            "stockNo": code,
            "response": "json"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        return data
    except Exception as e:
        print(f"Error fetching shareholding for {stock_id}: {e}")
        return {}


def get_us_institutional(symbol):
    """取得美股法人資料 (使用 Yahoo Finance)"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # 取得歷史成交量來推斷主力
        hist = ticker.history(period="20d")
        
        result = {
            "symbol": symbol,
            "institutional_ownership": info.get("institutionalOwnership"),
            "insider_ownership": info.get("insiderOwnership"),
            "float": info.get("floatShares"),
            "short_ratio": info.get("shortRatio"),
            "short_percent": info.get("shortPercentOfFloat"),
            "avg_volume": hist['Volume'].mean() if len(hist) > 0 else None,
            "volume_std": hist['Volume'].std() if len(hist) > 0 else None,
            "recent_volume": hist['Volume'].iloc[-5:].mean() if len(hist) >= 5 else None,
        }
        
        # 推斷主力買賣
        if len(hist) >= 5:
            recent = hist.tail(5)
            avg_vol = hist['Volume'].mean()
            
            # 近5日平均成交量是否大於20日平均的1.5倍
            volume_ratio = recent['Volume'].mean() / avg_vol if avg_vol > 0 else 1
            
            # 價格漲跌
            price_change = (recent['Close'].iloc[-1] - recent['Close'].iloc[0]) / recent['Close'].iloc[0] * 100
            
            # 主力判斷
            if volume_ratio > 1.5 and price_change > 3:
                result["main_force"] = "strong_buy"
            elif volume_ratio > 1.3 and price_change > 1:
                result["main_force"] = "buy"
            elif volume_ratio > 1.5 and price_change < -3:
                result["main_force"] = "strong_sell"
            elif volume_ratio > 1.3 and price_change < -1:
                result["main_force"] = "sell"
            else:
                result["main_force"] = "neutral"
                
            result["volume_ratio"] = round(volume_ratio, 2)
            result["price_change_5d"] = round(price_change, 2)
        
        return result
    except Exception as e:
        print(f"Error fetching US institutional for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


def get_taiwan_institutional(stock_id):
    """整合台股籌碼資料"""
    data = {
        "symbol": stock_id,
        "timestamp": datetime.now().isoformat()
    }
    
    # 法人買賣
    inst_data = get_twse_institutional(stock_id)
    if "data" in inst_data and inst_data["data"]:
        try:
            row = inst_data["data"][-1]  # 最新資料
            data["institutional"] = {
                "date": row[0],
                "foreign_net": row[3].replace(",", "") if row[3] else "0",
                "trust_net": row[6].replace(",", "") if row[6] else "0",
                "dealer_net": row[9].replace(",", "") if row[9] else "0",
            }
        except Exception as e:
            data["institutional"] = {}
            print(f"  Parse error: {e}")
    time.sleep(0.3)
    
    # 外資持股
    share_data = get_twse_shareholding(stock_id)
    if "data" in share_data and share_data["data"]:
        try:
            for row in share_data["data"]:
                if len(row) >= 3 and ("外资" in str(row[0]) or "Foreign" in str(row[0])):
                    data["shareholding"] = {
                        "foreign_holding": row[1].replace(",", "") if row[1] else "0",
                        "foreign_ratio": row[2].replace(",", "") if row[2] else "0",
                    }
                    break
        except Exception as e:
            data["shareholding"] = {}
            print(f"  Parse error: {e}")
    time.sleep(0.3)
    
    # 嘗試取得 short ratio (用 yfinance)
    try:
        ticker = yf.Ticker(stock_id)
        info = ticker.info
        hist = ticker.history(period="20d")
        
        data["short_ratio"] = info.get("shortRatio")
        data["avg_volume"] = hist['Volume'].mean() if len(hist) > 0 else None
        
        # 主力推斷
        if len(hist) >= 5:
            recent = hist.tail(5)
            avg_vol = hist['Volume'].mean()
            volume_ratio = recent['Volume'].mean() / avg_vol if avg_vol > 0 else 1
            price_change = (recent['Close'].iloc[-1] - recent['Close'].iloc[0]) / recent['Close'].iloc[0] * 100
            
            if volume_ratio > 1.5 and price_change > 3:
                data["main_force"] = "strong_buy"
            elif volume_ratio > 1.3 and price_change > 1:
                data["main_force"] = "buy"
            elif volume_ratio > 1.5 and price_change < -3:
                data["main_force"] = "strong_sell"
            elif volume_ratio > 1.3 and price_change < -1:
                data["main_force"] = "sell"
            else:
                data["main_force"] = "neutral"
                
            data["volume_ratio"] = round(volume_ratio, 2)
            data["price_change_5d"] = round(price_change, 2)
    except Exception as e:
        print(f"  Error getting yfinance data: {e}")
    
    return data


def main():
    print("=" * 60)
    print("開始收集籌碼資料 (增強版)")
    print("=" * 60)
    
    all_data = {}
    
    # 台股
    print("\n--- 台股籌碼資料 ---")
    for i, symbol in enumerate(TW_STOCKS):
        print(f"[{i+1}/{len(TW_STOCKS)}] 處理: {symbol}", end=" ... ")
        try:
            data = get_taiwan_institutional(symbol)
            all_data[symbol] = data
            
            # 儲存
            filename = os.path.join(DATA_DIR, f"{symbol}_chips.json")
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✓ ({data.get('main_force', 'N/A')})")
        except Exception as e:
            print(f"✗ Error: {e}")
        time.sleep(0.5)
    
    # 美股
    print("\n--- 美股籌碼資料 ---")
    for i, symbol in enumerate(US_STOCKS):
        print(f"[{i+1}/{len(US_STOCKS)}] 處理: {symbol}", end=" ... ")
        try:
            data = get_us_institutional(symbol)
            all_data[symbol] = data
            
            filename = os.path.join(DATA_DIR, f"{symbol}_chips.json")
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✓ ({data.get('main_force', 'N/A')})")
        except Exception as e:
            print(f"✗ Error: {e}")
        time.sleep(0.3)
    
    # 儲存完整資料
    full_filename = os.path.join(DATA_DIR, "all_chips.json")
    with open(full_filename, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"完成！共收集 {len(all_data)} 檔股票")
    print(f"資料儲存於: {DATA_DIR}")
    print("=" * 60)
    
    return all_data


if __name__ == "__main__":
    main()
