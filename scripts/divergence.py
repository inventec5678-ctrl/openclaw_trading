#!/usr/bin/env python3
"""
背離指標 (Divergence Indicator)
- 股價創新高但指標沒有 → 頂背離 (Bearish Divergence)
- 股價創新低但指標沒有 → 底背離 (Bullish Divergence)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


def find_peaks(values: pd.Series, lookback: int = 5) -> pd.Series:
    """找出局部高點"""
    peaks = pd.Series(False, index=values.index)
    
    for i in range(lookback, len(values) - lookback):
        if pd.notna(values.iloc[i]):
            is_peak = True
            # 檢查周圍是否都是較低值
            for j in range(1, lookback + 1):
                if values.iloc[i] <= values.iloc[i - j] or values.iloc[i] <= values.iloc[i + j]:
                    is_peak = False
                    break
            peaks.iloc[i] = is_peak
    
    return peaks


def find_troughs(values: pd.Series, lookback: int = 5) -> pd.Series:
    """找出局部低點"""
    troughs = pd.Series(False, index=values.index)
    
    for i in range(lookback, len(values) - lookback):
        if pd.notna(values.iloc[i]):
            is_trough = True
            # 檢查周圍是否都是較高值
            for j in range(1, lookback + 1):
                if values.iloc[i] >= values.iloc[i - j] or values.iloc[i] >= values.iloc[i + j]:
                    is_trough = False
                    break
            troughs.iloc[i] = is_trough
    
    return troughs


def calculate_divergence(df: pd.DataFrame, indicator_col: str, price_col: str = 'Close', 
                        lookback: int = 20) -> Dict:
    """
    計算背離訊號
    
    Args:
        df: 價格和指標資料
        indicator_col: 指標欄位名稱 (如 'RSI', 'MACD', 'KD')
        price_col: 價格欄位名稱
        lookback: 回溯週期
    
    Returns:
        包含背離訊號的字典
    """
    result = {
        "indicator": indicator_col,
        "divergence_type": None,  # 'bullish', 'bearish', None
        "strength": 0,  # 0-100
        "details": [],
        "latest_signal": None
    }
    
    # 找出價格和指標的高點與低點
    price_peaks = find_peaks(df[price_col], lookback=5)
    price_troughs = find_troughs(df[price_col], lookback=5)
    indicator_peaks = find_peaks(df[indicator_col], lookback=5)
    indicator_troughs = find_troughs(df[indicator_col], lookback=5)
    
    # 取得最近的高點/低點位置
    recent_price_peaks = df[price_peaks].dropna().tail(5)
    recent_indicator_peaks = df[indicator_peaks].dropna().tail(5)
    
    # 檢查頂背離 (Bearish Divergence): 價格創新高，指標沒有
    if len(recent_price_peaks) >= 2 and len(recent_indicator_peaks) >= 2:
        price_high_1 = recent_price_peaks.iloc[-2]
        price_high_2 = recent_price_peaks.iloc[-1]
        indicator_high_1 = recent_indicator_peaks.iloc[-2]
        indicator_high_2 = recent_indicator_peaks.iloc[-1]
        
        if price_high_2 > price_high_1 and indicator_high_2 <= indicator_high_1:
            result["divergence_type"] = "bearish"
            result["strength"] = min(100, int((price_high_2 - price_high_1) / price_high_1 * 1000))
            result["details"].append({
                "type": "頂背離",
                "price_change": f"+{((price_high_2/price_high_1)-1)*100:.2f}%",
                "indicator_change": f"{((indicator_high_2/indicator_high_1)-1)*100:.2f}%",
                "signal": "可能反轉向下"
            })
    
    # 檢查底背離 (Bullish Divergence): 價格創新低，指標沒有
    recent_price_troughs = df[price_troughs].dropna().tail(5)
    recent_indicator_troughs = df[indicator_troughs].dropna().tail(5)
    
    if len(recent_price_troughs) >= 2 and len(recent_indicator_troughs) >= 2:
        price_low_1 = recent_price_troughs.iloc[-2]
        price_low_2 = recent_price_troughs.iloc[-1]
        indicator_low_1 = recent_indicator_troughs.iloc[-2]
        indicator_low_2 = recent_indicator_troughs.iloc[-1]
        
        if price_low_2 < price_low_1 and indicator_low_2 >= indicator_low_1:
            result["divergence_type"] = "bullish"
            result["strength"] = min(100, int((price_low_1 - price_low_2) / price_low_1 * 1000))
            result["details"].append({
                "type": "底背離",
                "price_change": f"{((price_low_2/price_low_1)-1)*100:.2f}%",
                "indicator_change": f"+{((indicator_low_2/indicator_low_1)-1)*100:.2f}%",
                "signal": "可能反轉向上"
            })
    
    # 設定最新訊號
    if result["divergence_type"] == "bearish":
        result["latest_signal"] = "🔴 頂背離 - 小心回檔"
    elif result["divergence_type"] == "bullish":
        result["latest_signal"] = "🟢 底背離 - 可能反彈"
    else:
        result["latest_signal"] = "⚪ 無背離訊號"
    
    return result


def calculate_all_divergences(ticker_symbol: str, period: str = "1y") -> Dict:
    """
    計算股票的所有背離訊號
    
    Args:
        ticker_symbol: 股票代碼
        period: 資料週期
    
    Returns:
        包含所有背離分析的字典
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            return {"symbol": ticker_symbol, "error": "No data"}
        
        # 計算 RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 計算 MACD
        ema_fast = df['Close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_fast - ema_slow
        
        # 計算 KD
        low_min = df['Low'].rolling(window=9).min()
        high_max = df['High'].rolling(window=9).max()
        rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
        df['K'] = rsv.ewm(alpha=1/3, adjust=False).mean()
        df['D'] = df['K'].ewm(alpha=1/3, adjust=False).mean()
        
        # 計算各指標的背離
        divergences = {}
        
        # RSI 背離
        divergences["RSI"] = calculate_divergence(df, 'RSI')
        
        # MACD 背離
        divergences["MACD"] = calculate_divergence(df, 'MACD')
        
        # KD 背離
        divergences["KD"] = calculate_divergence(df, 'K')
        
        # 綜合判斷
        bullish_count = sum(1 for d in divergences.values() if d["divergence_type"] == "bullish")
        bearish_count = sum(1 for d in divergences.values() if d["divergence_type"] == "bearish")
        
        overall_signal = "neutral"
        if bullish_count >= 2:
            overall_signal = "bullish"
        elif bearish_count >= 2:
            overall_signal = "bearish"
        
        result = {
            "symbol": ticker_symbol,
            "price": float(df['Close'].iloc[-1]),
            "divergences": divergences,
            "overall_signal": overall_signal,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count
        }
        
        return result
        
    except Exception as e:
        return {"symbol": ticker_symbol, "error": str(e)}


def main():
    """測試函數"""
    test_stocks = ["2330.TW", "AAPL", "TSLA"]
    
    print("=" * 60)
    print("背離指標分析")
    print("=" * 60)
    
    for symbol in test_stocks:
        print(f"\n分析: {symbol}")
        result = calculate_all_divergences(symbol)
        
        if "error" in result:
            print(f"  錯誤: {result['error']}")
            continue
        
        print(f"  價格: {result['price']:.2f}")
        print(f"  整體訊號: {result['overall_signal']}")
        print(f"  底背離數量: {result['bullish_count']}")
        print(f"  頂背離數量: {result['bearish_count']}")
        
        for ind_name, div in result['divergences'].items():
            print(f"    {ind_name}: {div['latest_signal']}")


if __name__ == "__main__":
    main()
