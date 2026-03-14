#!/usr/bin/env python3
"""
RSI 策略
- 相對強弱指標
- 超買/超賣判斷
- 離開超買/超賣區的訊號
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """計算 RSI 指標"""
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # EMA 方式計算後續值
    for i in range(period, len(avg_gain)):
        if pd.notna(avg_gain.iloc[i-1]) and pd.notna(avg_loss.iloc[i-1]):
            avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
            avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_rsi_divergence(df: pd.DataFrame, period: int = 14) -> Dict:
    """
    計算 RSI 背離
    
    Returns:
        包含背離分析的字典
    """
    rsi = calculate_rsi(df, period)
    
    # 找出 RSI 和價格的頂底
    lookback = 5
    
    # 最近 30 天
    recent = df.tail(30).copy()
    recent['RSI'] = rsi.tail(30)
    
    # 簡單判斷：比較最近兩個高點/低點
    result = {
        "type": None,
        "signal": None,
        "strength": 0
    }
    
    # 檢查趨勢反轉
    if len(recent) >= 10:
        # 前半段和後半段比較
        first_half = recent.head(15)
        second_half = recent.tail(15)
        
        first_price_max = first_half['Close'].max()
        second_price_max = second_half['Close'].max()
        first_rsi_max = first_half['RSI'].max()
        second_rsi_max = second_half['RSI'].max()
        
        # 頂背離
        if second_price_max > first_price_max and second_rsi_max < first_rsi_max:
            result["type"] = "bearish_divergence"
            result["signal"] = "🔴 頂背離 - 潛在反轉向下"
            result["strength"] = min(100, int((second_price_max - first_price_max) / first_price_max * 500))
        
        # 底背離
        first_price_min = first_half['Close'].min()
        second_price_min = second_half['Close'].min()
        first_rsi_min = first_half['RSI'].min()
        second_rsi_min = second_half['RSI'].min()
        
        if second_price_min < first_price_min and second_rsi_min > first_rsi_min:
            result["type"] = "bullish_divergence"
            result["signal"] = "🟢 底背離 - 潛在反轉向上"
            result["strength"] = min(100, int((first_price_min - second_price_min) / first_price_min * 500))
    
    return result


def generate_rsi_signals(df: pd.DataFrame, period: int = 14, 
                        oversold: int = 30, overbought: int = 70) -> Dict:
    """
    產生 RSI 交易訊號
    
    Args:
        df: 價格資料
        period: RSI 週期
        oversold: 超賣門檻
        overbought: 超買門檻
    
    Returns:
        訊號字典
    """
    rsi = calculate_rsi(df, period)
    df = df.copy()
    df['RSI'] = rsi
    
    signals = []
    
    for i in range(period + 1, len(df)):
        prev_rsi = df['RSI'].iloc[i-1]
        curr_rsi = df['RSI'].iloc[i]
        
        # 進入超賣區
        if prev_rsi > oversold and curr_rsi <= oversold:
            signals.append({
                "date": str(df.index[i].date()),
                "type": "BUY",
                "rsi": round(curr_rsi, 2),
                "reason": f"RSI 進入超賣區 (<{oversold})"
            })
        
        # 離開超賣區 (潛在買點)
        elif prev_rsi <= oversold and curr_rsi > oversold:
            signals.append({
                "date": str(df.index[i].date()),
                "type": "BUY",
                "rsi": round(curr_rsi, 2),
                "reason": f"RSI 離開超賣區 - 潛在反彈"
            })
        
        # 進入超買區
        elif prev_rsi < overbought and curr_rsi >= overbought:
            signals.append({
                "date": str(df.index[i].date()),
                "type": "SELL",
                "rsi": round(curr_rsi, 2),
                "reason": f"RSI 進入超買區 (>{overbought})"
            })
        
        # 離開超買區 (潛在賣點)
        elif prev_rsi >= overbought and curr_rsi < overbought:
            signals.append({
                "date": str(df.index[i].date()),
                "type": "SELL",
                "rsi": round(curr_rsi, 2),
                "reason": f"RSI 離開超買區 - 潛在回調"
            })
    
    return signals


def analyze_rsi(ticker_symbol: str, period: str = "6mo", rsi_period: int = 14) -> Dict:
    """
    完整 RSI 策略分析
    
    Args:
        ticker_symbol: 股票代碼
        period: 資料週期
        rsi_period: RSI 計算週期
    
    Returns:
        分析結果
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            return {"symbol": ticker_symbol, "error": "No data"}
        
        rsi = calculate_rsi(df, rsi_period)
        latest_rsi = rsi.iloc[-1]
        
        # 計算 RSI 統計
        rsi_stats = {
            "current": round(latest_rsi, 2),
            "min_30d": round(rsi.tail(30).min(), 2),
            "max_30d": round(rsi.tail(30).max(), 2),
            "avg_30d": round(rsi.tail(30).mean(), 2)
        }
        
        # 產生訊號
        signals = generate_rsi_signals(df, rsi_period)
        
        # 背離分析
        divergence = calculate_rsi_divergence(df, rsi_period)
        
        # 判斷市場狀態
        if latest_rsi >= 70:
            status = "overbought"
            status_text = "🔴 超買區 - 慎防回調"
        elif latest_rsi <= 30:
            status = "oversold"
            status_text = "🟢 超賣區 - 留意反彈"
        elif latest_rsi >= 60:
            status = "bullish"
            status_text = "🟡 偏多區域"
        elif latest_rsi <= 40:
            status = "bearish"
            status_text = "🟡 偏空區域"
        else:
            status = "neutral"
            status_text = "⚪ 中性區域"
        
        return {
            "symbol": ticker_symbol,
            "current_price": float(df['Close'].iloc[-1]),
            "rsi": rsi_stats,
            "status": status,
            "status_text": status_text,
            "divergence": divergence,
            "recent_signals": signals[-5:] if signals else [],
            "conclusion": f"RSI = {latest_rsi:.1f} | {status_text}"
        }
        
    except Exception as e:
        return {"symbol": ticker_symbol, "error": str(e)}


def main():
    """測試函數"""
    test_stocks = ["2330.TW", "AAPL", "TSLA"]
    
    print("=" * 60)
    print("RSI 策略分析")
    print("=" * 60)
    
    for symbol in test_stocks:
        result = analyze_rsi(symbol)
        
        if "error" in result:
            print(f"\n{symbol}: {result['error']}")
            continue
        
        print(f"\n{'='*40}")
        print(f"股票: {symbol}")
        print(f"價格: {result['current_price']:.2f}")
        print(f"RSI: {result['rsi']['current']}")
        print(f"狀態: {result['status_text']}")
        print(f"結論: {result['conclusion']}")
        
        if result['divergence']['signal']:
            print(f"背離: {result['divergence']['signal']}")


if __name__ == "__main__":
    main()
