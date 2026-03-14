#!/usr/bin/env python3
"""
Parabolic SAR 策略
- 停損點轉向指標 (Parabolic Stop and Reverse)
- 適用於趨勢市場
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


def calculate_sar(df: pd.DataFrame, af_start: float = 0.02, af_increment: float = 0.02, 
                  af_max: float = 0.2) -> pd.Series:
    """
    計算 Parabolic SAR
    
    Args:
        df: 包含 High, Low 的資料
        af_start: 初始加速因子
        af_increment: 加速因子增量
        af_max: 最大加速因子
    
    Returns:
        SAR 值序列
    """
    sar = pd.Series(np.nan, index=df.index)
    
    # 初始化
    trend = 1  # 1 = 上漲趨勢, -1 = 下跌趨勢
    af = af_start
    ep = df['High'].iloc[0]  # 極端點
    sar.iloc[0] = df['Low'].iloc[0]
    
    for i in range(1, len(df)):
        prev_sar = sar.iloc[i-1]
        
        if trend == 1:  # 上漲趨勢
            sar.iloc[i] = prev_sar + af * (ep - prev_sar)
            
            # 檢查是否反轉
            if df['Low'].iloc[i] < sar.iloc[i]:
                trend = -1
                sar.iloc[i] = ep
                ep = df['Low'].iloc[i]
                af = af_start
            else:
                # 更新極端點
                if df['High'].iloc[i] > ep:
                    ep = df['High'].iloc[i]
                    af = min(af + af_increment, af_max)
        
        else:  # 下跌趨勢
            sar.iloc[i] = prev_sar - af * (prev_sar - ep)
            
            # 檢查是否反轉
            if df['High'].iloc[i] > sar.iloc[i]:
                trend = 1
                sar.iloc[i] = ep
                ep = df['High'].iloc[i]
                af = af_start
            else:
                # 更新極端點
                if df['Low'].iloc[i] < ep:
                    ep = df['Low'].iloc[i]
                    af = min(af + af_increment, af_max)
    
    return sar


def generate_sar_signals(df: pd.DataFrame) -> Dict:
    """
    產生 SAR 交易訊號
    
    Args:
        df: 包含 Open, High, Low, Close 的資料
    
    Returns:
        包含訊號的字典
    """
    sar = calculate_sar(df)
    df = df.copy()
    df['SAR'] = sar
    
    signals = []
    positions = []
    
    for i in range(1, len(df)):
        # SAR 在價格下方 = 多頭趨勢
        if df['SAR'].iloc[i] < df['Close'].iloc[i] and df['SAR'].iloc[i-1] >= df['Close'].iloc[i-1]:
            signals.append({
                "date": str(df.index[i].date()),
                "type": "BUY",
                "price": float(df['Close'].iloc[i]),
                "sar": float(df['SAR'].iloc[i]),
                "reason": "SAR 突破價格上漲趨勢確認"
            })
        
        # SAR 在價格上方 = 空頭趨勢
        elif df['SAR'].iloc[i] > df['Close'].iloc[i] and df['SAR'].iloc[i-1] <= df['Close'].iloc[i-1]:
            signals.append({
                "date": str(df.index[i].date()),
                "type": "SELL",
                "price": float(df['Close'].iloc[i]),
                "sar": float(df['SAR'].iloc[i]),
                "reason": "SAR 跌破價格下跌趨勢確認"
            })
        
        # 記錄當前趨勢
        positions.append({
            "date": str(df.index[i].date()),
            "trend": "bullish" if df['SAR'].iloc[i] < df['Close'].iloc[i] else "bearish",
            "close": float(df['Close'].iloc[i]),
            "sar": float(df['SAR'].iloc[i])
        })
    
    return {
        "signals": signals,
        "positions": positions,
        "current_trend": positions[-1]["trend"] if positions else None,
        "current_sar": float(sar.iloc[-1]) if pd.notna(sar.iloc[-1]) else None,
        "current_price": float(df['Close'].iloc[-1])
    }


def calculate_sar_metrics(df: pd.DataFrame) -> Dict:
    """
    計算 SAR 相關指標
    
    Args:
        df: 價格資料
    
    Returns:
        指標字典
    """
    sar = calculate_sar(df)
    df = df.copy()
    df['SAR'] = sar
    
    # 計算 SAR 與價格的距離
    df['sar_distance'] = (df['Close'] - df['SAR']) / df['Close'] * 100
    
    # 計算趨勢強度
    bullish_bars = (df['SAR'] < df['Close']).sum()
    bearish_bars = (df['SAR'] > df['Close']).sum()
    total_bars = len(df[df['SAR'].notna()])
    
    trend_strength = bullish_bars / total_bars * 100 if total_bars > 0 else 50
    
    # 最新值
    latest = df.iloc[-1]
    
    return {
        "current_sar": float(latest['SAR']) if pd.notna(latest['SAR']) else None,
        "current_distance": float(latest['sar_distance']) if pd.notna(latest['sar_distance']) else None,
        "trend_strength": round(trend_strength, 2),
        "bullish_bars": bullish_bars,
        "bearish_bars": bearish_bars,
        "total_bars": total_bars
    }


def analyze_sar(ticker_symbol: str, period: str = "6mo") -> Dict:
    """
    完整分析 SAR 策略
    
    Args:
        ticker_symbol: 股票代碼
        period: 資料週期
    
    Returns:
        完整分析結果
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        
        if df.empty or len(df) < 20:
            return {"symbol": ticker_symbol, "error": "Insufficient data"}
        
        # 計算訊號和指標
        signals = generate_sar_signals(df)
        metrics = calculate_sar_metrics(df)
        
        # 產生結論
        current_trend = signals["current_trend"]
        
        if current_trend == "bullish":
            if metrics["current_distance"] and metrics["current_distance"] > 5:
                conclusion = "🟢 強勢多頭趨勢 SAR 支撐明確"
            elif metrics["current_distance"] and metrics["current_distance"] > 2:
                conclusion = "🟢 多頭趨勢 SAR 支撐中"
            else:
                conclusion = "🟡 接近 SAR 支撐，多頭防守點"
        else:
            if metrics["current_distance"] and metrics["current_distance"] > 5:
                conclusion = "🔴 強勢空頭趨勢 SAR 壓力明確"
            elif metrics["current_distance"] and metrics["current_distance"] > 2:
                conclusion = "🔴 空頭趨勢 SAR 壓力中"
            else:
                conclusion = "🟡 接近 SAR 壓力，需觀察反轉"
        
        return {
            "symbol": ticker_symbol,
            "current_price": signals["current_price"],
            "current_sar": signals["current_sar"],
            "current_trend": current_trend,
            "trend_strength": metrics["trend_strength"],
            "conclusion": conclusion,
            "recent_signals": signals["signals"][-5:] if signals["signals"] else [],
            "metrics": metrics
        }
        
    except Exception as e:
        return {"symbol": ticker_symbol, "error": str(e)}


def main():
    """測試函數"""
    test_stocks = ["2330.TW", "AAPL", "TSLA", "NVDA"]
    
    print("=" * 60)
    print("Parabolic SAR 策略分析")
    print("=" * 60)
    
    for symbol in test_stocks:
        result = analyze_sar(symbol)
        
        if "error" in result:
            print(f"\n{symbol}: 錯誤 - {result['error']}")
            continue
        
        print(f"\n{'='*40}")
        print(f"股票: {symbol}")
        print(f"價格: {result['current_price']:.2f}")
        print(f"SAR: {result['current_sar']:.2f}" if result['current_sar'] else "SAR: N/A")
        print(f"趨勢: {result['current_trend']}")
        print(f"趨勢強度: {result['trend_strength']:.1f}%")
        print(f"結論: {result['conclusion']}")
        
        if result['recent_signals']:
            print("近期訊號:")
            for sig in result['recent_signals'][-3:]:
                print(f"  {sig['date']}: {sig['type']} @ {sig['price']:.2f}")


if __name__ == "__main__":
    main()
