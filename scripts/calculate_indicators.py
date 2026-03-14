#!/usr/bin/env python3
"""
技術指標計算腳本
- 均線：MA5, MA10, MA20, MA60, MA120, MA240
- KD 指標
- MACD 指標
- RSI 指標
"""

import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime, timedelta

DATA_DIR = os.path.expanduser("~/openclaw_data/indicators")

# 股票清單
TW_STOCKS = ["2330.TW", "2317.TW", "2454.TW", "0050.TW"]
US_STOCKS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]
ALL_STOCKS = TW_STOCKS + US_STOCKS


def calculate_ma(df, period):
    """計算移動平均線"""
    return df['Close'].rolling(window=period).mean()


def calculate_kd(df, period_k=9, period_d=3):
    """計算 KD 指標"""
    low_min = df['Low'].rolling(window=period_k).min()
    high_max = df['High'].rolling(window=period_k).max()
    
    rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
    rsv = rsv.fillna(50)
    
    k = rsv.ewm(alpha=1/period_d, adjust=False).mean()
    d = k.ewm(alpha=1/period_d, adjust=False).mean()
    
    return k, d


def calculate_macd(df, fast=12, slow=26, signal=9):
    """計算 MACD 指標"""
    ema_fast = df['Close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['Close'].ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_rsi(df, period=14):
    """計算 RSI 指標"""
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # 使用 EMA 方式計算後續值
    for i in range(period, len(avg_gain)):
        if pd.notna(avg_gain.iloc[i-1]) and pd.notna(avg_loss.iloc[i-1]):
            avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
            avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_indicators(ticker_symbol):
    """計算單一股票的所有技術指標"""
    try:
        # 取得 2 年資料 (確保有足夠資料計算 MA240)
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="2y")
        
        if df.empty:
            return {"symbol": ticker_symbol, "error": "No data"}
        
        # 計算均線
        df['MA5'] = calculate_ma(df, 5)
        df['MA10'] = calculate_ma(df, 10)
        df['MA20'] = calculate_ma(df, 20)
        df['MA60'] = calculate_ma(df, 60)
        df['MA120'] = calculate_ma(df, 120)
        df['MA240'] = calculate_ma(df, 240)
        
        # 計算 KD
        df['K'], df['D'] = calculate_kd(df)
        df['J'] = 3 * df['K'] - 2 * df['D']
        
        # 計算 MACD
        df['MACD'], df['Signal'], df['Histogram'] = calculate_macd(df)
        
        # 計算 RSI
        df['RSI'] = calculate_rsi(df)
        
        # 準備輸出資料
        # 取最新資料
        latest = df.iloc[-1]
        
        # 取最近 30 天資料 for 圖表
        recent_df = df.tail(30).copy()
        recent_df = recent_df.reset_index()
        recent_df['Date'] = recent_df['Date'].dt.strftime('%Y-%m-%d')
        
        result = {
            "symbol": ticker_symbol,
            "timestamp": datetime.now().isoformat(),
            "latest": {
                "date": df.index[-1].strftime('%Y-%m-%d'),
                "close": float(latest['Close']),
                "volume": int(latest['Volume']),
                "ma5": float(latest['MA5']) if pd.notna(latest['MA5']) else None,
                "ma10": float(latest['MA10']) if pd.notna(latest['MA10']) else None,
                "ma20": float(latest['MA20']) if pd.notna(latest['MA20']) else None,
                "ma60": float(latest['MA60']) if pd.notna(latest['MA60']) else None,
                "ma120": float(latest['MA120']) if pd.notna(latest['MA120']) else None,
                "ma240": float(latest['MA240']) if pd.notna(latest['MA240']) else None,
                "k": float(latest['K']) if pd.notna(latest['K']) else None,
                "d": float(latest['D']) if pd.notna(latest['D']) else None,
                "j": float(latest['J']) if pd.notna(latest['J']) else None,
                "macd": float(latest['MACD']) if pd.notna(latest['MACD']) else None,
                "signal": float(latest['Signal']) if pd.notna(latest['Signal']) else None,
                "histogram": float(latest['Histogram']) if pd.notna(latest['Histogram']) else None,
                "rsi": float(latest['RSI']) if pd.notna(latest['RSI']) else None,
            },
            "recent_30d": recent_df.to_dict(orient='records')
        }
        
        # 計算訊號
        signals = []
        
        # 均線訊號
        if pd.notna(latest['MA5']) and pd.notna(latest['MA20']):
            if latest['MA5'] > latest['MA20']:
                signals.append("MA5 > MA20: 偏多")
            else:
                signals.append("MA5 < MA20: 偏空")
        
        # KD 訊號
        if pd.notna(latest['K']) and pd.notna(latest['D']):
            if latest['K'] > latest['D'] and latest['K'] < 80:
                signals.append("KD 金叉: 偏多")
            elif latest['K'] < latest['D'] and latest['K'] > 20:
                signals.append("KD 死叉: 偏空")
            if latest['K'] < 20:
                signals.append("KD 超賣")
            if latest['K'] > 80:
                signals.append("KD 超買")
        
        # MACD 訊號
        if pd.notna(latest['MACD']) and pd.notna(latest['Signal']):
            if latest['MACD'] > latest['Signal']:
                signals.append("MACD > Signal: 偏多")
            else:
                signals.append("MACD < Signal: 偏空")
        
        # RSI 訊號
        if pd.notna(latest['RSI']):
            if latest['RSI'] > 70:
                signals.append("RSI 超買 (>70)")
            elif latest['RSI'] < 30:
                signals.append("RSI 超賣 (<30)")
            else:
                signals.append(f"RSI 中性 ({latest['RSI']:.1f})")
        
        result["signals"] = signals
        
        return result
        
    except Exception as e:
        print(f"Error processing {ticker_symbol}: {e}")
        import traceback
        traceback.print_exc()
        return {"symbol": ticker_symbol, "error": str(e)}


def main():
    print("=" * 50)
    print("開始計算技術指標")
    print("=" * 50)
    
    all_data = {}
    
    for symbol in ALL_STOCKS:
        print(f"\n處理: {symbol}")
        result = calculate_indicators(symbol)
        all_data[symbol] = result
        
        # 儲存個別檔案
        filename = os.path.join(DATA_DIR, f"{symbol}_indicators.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  已儲存: {filename}")
        
        # 顯示最新指標
        if "latest" in result:
            latest = result["latest"]
            print(f"  收盤: {latest['close']:.2f} | MA20: {latest['ma20']:.2f} | RSI: {latest['rsi']:.1f}")
    
    # 儲存完整資料
    full_filename = os.path.join(DATA_DIR, "all_indicators.json")
    with open(full_filename, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 50)
    print(f"完成！共處理 {len(ALL_STOCKS)} 檔股票")
    print(f"資料儲存於: {DATA_DIR}")
    print("=" * 50)


if __name__ == "__main__":
    main()
