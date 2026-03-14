#!/usr/bin/env python3
"""
基本面具資料收集 - 使用 yfinance
台股: 2330.TW, 2317.TW, 2454.TW, 0050.TW
美股: AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA
"""

import yfinance as yf
import json
import os
from datetime import datetime

DATA_DIR = os.path.expanduser("~/openclaw_data/fundamental")

# 股票清單
TW_STOCKS = ["2330.TW", "2317.TW", "2454.TW", "0050.TW"]
US_STOCKS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]
ALL_STOCKS = TW_STOCKS + US_STOCKS


def get_fundamental_data(ticker_symbol):
    """獲取單一股票的基本面資料"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        data = {
            "symbol": ticker_symbol,
            "name": info.get("longName") or info.get("shortName", "N/A"),
            "timestamp": datetime.now().isoformat(),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "beta": info.get("beta"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "volume": info.get("volume"),
            "avg_volume": info.get("averageVolume"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "eps": info.get("trailingEps"),
            "forward_eps": info.get("forwardEps"),
            "revenue": info.get("totalRevenue"),
            "revenue_per_share": info.get("revenuePerShare"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "gross_margin": info.get("grossMargins"),
            "operating_cashflow": info.get("operatingCashflow"),
            "free_cashflow": info.get("freeCashflow"),
        }
        return data
    except Exception as e:
        print(f"Error fetching {ticker_symbol}: {e}")
        return {"symbol": ticker_symbol, "error": str(e)}


def get_financials(ticker_symbol):
    """獲取財報資料"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # 季報
        quarterly = ticker.quarterly_financials
        # 年報
        annual = ticker.financials
        
        # 轉換並處理 Timestamp 問題
        def clean_data(df):
            if df is None or df.empty:
                return {}
            df_copy = df.copy()
            # 將所有欄位名稱轉為字串
            df_copy.columns = [str(c) for c in df_copy.columns]
            # 將索引轉為字串
            df_copy.index = [str(i) for i in df_copy.index]
            return df_copy.to_dict()
        
        return {
            "quarterly": clean_data(quarterly),
            "annual": clean_data(annual)
        }
    except Exception as e:
        print(f"Error fetching financials for {ticker_symbol}: {e}")
        return {}


def get_earnings(ticker_symbol):
    """獲取盈餘資料"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        earnings_dates = ticker.earnings_dates
        calendar = ticker.calendar
        
        # 處理可能的錯誤
        def clean_data(df):
            if df is None or (hasattr(df, 'empty') and df.empty):
                return {}
            try:
                df_copy = df.copy()
                # 將所有欄位名稱轉為字串
                df_copy.columns = [str(c) for c in df_copy.columns]
                # 將索引轉為字串
                df_copy.index = [str(i) for i in df_copy.index]
                return df_copy.to_dict()
            except:
                return {}
        
        return {
            "earnings_dates": clean_data(earnings_dates),
            "calendar": clean_data(calendar)
        }
    except Exception as e:
        print(f"Error fetching earnings for {ticker_symbol}: {e}")
        return {}


def main():
    print("=" * 50)
    print("開始收集基本面資料")
    print("=" * 50)
    
    all_data = {}
    
    for symbol in ALL_STOCKS:
        print(f"\n處理: {symbol}")
        
        # 基本面
        fundamental = get_fundamental_data(symbol)
        all_data[symbol] = fundamental
        
        # 財報
        financials = get_financials(symbol)
        all_data[symbol]["financials"] = financials
        
        # 盈餘
        earnings = get_earnings(symbol)
        all_data[symbol]["earnings"] = earnings
        
        # 儲存個別檔案
        filename = os.path.join(DATA_DIR, f"{symbol}_fundamental.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(all_data[symbol], f, ensure_ascii=False, indent=2)
        print(f"  已儲存: {filename}")
    
    # 儲存完整資料
    full_filename = os.path.join(DATA_DIR, "all_fundamentals.json")
    with open(full_filename, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 50)
    print(f"完成！共處理 {len(ALL_STOCKS)} 檔股票")
    print(f"資料儲存於: {DATA_DIR}")
    print("=" * 50)


if __name__ == "__main__":
    main()
