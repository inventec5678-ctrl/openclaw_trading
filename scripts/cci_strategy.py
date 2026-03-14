#!/usr/bin/env python3
"""
CCI 策略
- 商品通道指標 (Commodity Channel Index)
- 趨勢確認和動能指標
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


def calculate_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    計算 CCI 指標
    
    Args:
        df: 包含 High, Low, Close 的資料
        period: 計算週期
    
    Returns:
        CCI 值序列
    """
    # 典型價格 (TP) = (High + Low + Close) / 3
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    
    # 簡單移動平均
    sma = tp.rolling(window=period).mean()
    
    # 平均偏差
    mean_deviation = tp.rolling(window=period).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )
    
    # CCI = (TP - SMA) / (0.015 * MD)
    cci = (tp - sma) / (0.015 * mean_deviation)
    
    return cci


def generate_cci_signals(df: pd.DataFrame, period: int = 20) -> List[Dict]:
    """
    產生 CCI 交易訊號
    
    Args:
        df: 價格資料
        period: CCI 週期
    
    Returns:
        訊號列表
    """
    cci = calculate_cci(df, period)
    df = df.copy()
    df['CCI'] = cci
    
    signals = []
    
    for i in range(period + 1, len(df)):
        prev_cci = df['CCI'].iloc[i-1]
        curr_cci = df['CCI'].iloc[i]
        
        # CCI > 100 超買區
        if prev_cci <= 100 and curr_cci > 100:
            signals.append({
                "date": str(df.index[i].date()),
                "type": "SELL",
                "cci": round(curr_cci, 2),
                "reason": "CCI 進入超買區 (>100)"
            })
        
        # CCI 從超買區回落
        elif prev_cci > 100 and curr_cci <= 100:
            signals.append({
                "date": str(df.index[i].date()),
                "type": "SELL",
                "cci": round(curr_cci, 2),
                "reason": "CCI 離開超買區 - 趨勢可能反轉"
            })
        
        # CCI < -100 超賣區
        elif prev_cci >= -100 and curr_cci < -100:
            signals.append({
                "date": str(df.index[i].date()),
                "type": "BUY",
                "cci": round(curr_cci, 2),
                "reason": "CCI 進入超賣區 (<-100)"
            })
        
        # CCI 從超賣區回升
        elif prev_cci < -100 and curr_cci >= -100:
            signals.append({
                "date": str(df.index[i].date()),
                "type": "BUY",
                "cci": round(curr_cci, 2),
                "reason": "CCI 離開超賣區 - 趨勢可能反轉"
            })
        
        # CCI 零軸交叉
        elif prev_cci < 0 and curr_cci > 0:
            signals.append({
                "date": str(df.index[i].date()),
                "type": "BUY",
                "cci": round(curr_cci, 2),
                "reason": "CCI 上穿零軸 - 多頭趨勢"
            })
        
        elif prev_cci > 0 and curr_cci < 0:
            signals.append({
                "date": str(df.index[i].date()),
                "type": "SELL",
                "cci": round(curr_cci, 2),
                "reason": "CCI 下穿零軸 - 空頭趨勢"
            })
    
    return signals


def analyze_cci(ticker_symbol: str, period: str = "6mo", cci_period: int = 20) -> Dict:
    """
    完整 CCI 策略分析
    
    Args:
        ticker_symbol: 股票代碼
        period: 資料週期
        cci_period: CCI 計算週期
    
    Returns:
        分析結果
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            return {"symbol": ticker_symbol, "error": "No data"}
        
        cci = calculate_cci(df, cci_period)
        latest_cci = cci.iloc[-1]
        
        # 統計
        cci_stats = {
            "current": round(latest_cci, 2),
            "min_30d": round(cci.tail(30).min(), 2),
            "max_30d": round(cci.tail(30).max(), 2),
            "avg_30d": round(cci.tail(30).mean(), 2)
        }
        
        # 訊號
        signals = generate_cci_signals(df, cci_period)
        
        # 狀態判斷
        if latest_cci > 100:
            status = "overbought"
            status_text = "🔴 超買區 (CCI > 100)"
        elif latest_cci < -100:
            status = "oversold"
            status_text = "🟢 超賣區 (CCI < -100)"
        elif latest_cci > 0:
            status = "bullish"
            status_text = "🟡 偏多 (CCI > 0)"
        elif latest_cci < 0:
            status = "bearish"
            status_text = "🟡 偏空 (CCI < 0)"
        else:
            status = "neutral"
            status_text = "⚪ 中性"
        
        # 趨勢強度 (CCI 絕對值越大，趨勢越強)
        trend_strength = min(100, abs(latest_cci) / 2)
        
        return {
            "symbol": ticker_symbol,
            "current_price": float(df['Close'].iloc[-1]),
            "cci": cci_stats,
            "status": status,
            "status_text": status_text,
            "trend_strength": round(trend_strength, 2),
            "recent_signals": signals[-5:] if signals else [],
            "conclusion": f"CCI = {latest_cci:.1f} | {status_text}"
        }
        
    except Exception as e:
        return {"symbol": ticker_symbol, "error": str(e)}


def main():
    """測試函數"""
    test_stocks = ["2330.TW", "AAPL", "TSLA"]
    
    print("=" * 60)
    print("CCI 策略分析")
    print("=" * 60)
    
    for symbol in test_stocks:
        result = analyze_cci(symbol)
        
        if "error" in result:
            print(f"\n{symbol}: {result['error']}")
            continue
        
        print(f"\n{'='*40}")
        print(f"股票: {symbol}")
        print(f"價格: {result['current_price']:.2f}")
        print(f"CCI: {result['cci']['current']}")
        print(f"狀態: {result['status_text']}")
        print(f"趨勢強度: {result['trend_strength']:.1f}%")


if __name__ == "__main__":
    main()
