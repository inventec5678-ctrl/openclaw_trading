#!/usr/bin/env python3
"""
ADX 策略
- 平均趨向指數 (Average Directional Index)
- 衡量趨勢強度 (不論方向)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    計算 ADX、DMI+、DMI-
    
    Args:
        df: 包含 High, Low, Close 的資料
        period: 計算週期
    
    Returns:
        包含 ADX, +DI, -DI 的 DataFrame
    """
    # 計算 +DM 和 -DM
    high_diff = df['High'].diff()
    low_diff = -df['Low'].diff()
    
    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
    
    # 計算 True Range
    tr1 = df['High'] - df['Low']
    tr2 = abs(df['High'] - df['Close'].shift())
    tr3 = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # 平滑處理
    atr = tr.rolling(window=period).mean()
    plus_dm_smooth = plus_dm.rolling(window=period).mean()
    minus_dm_smooth = minus_dm.rolling(window=period).mean()
    
    # 計算 +DI 和 -DI
    plus_di = (plus_dm_smooth / atr) * 100
    minus_di = (minus_dm_smooth / atr) * 100
    
    # 計算 DX
    di_sum = plus_di + minus_di
    dx = (abs(plus_di - minus_di) / di_sum) * 100
    
    # 計算 ADX
    adx = dx.rolling(window=period).mean()
    
    return pd.DataFrame({
        'ADX': adx,
        '+DI': plus_di,
        '-DI': minus_di
    })


def generate_adx_signals(df: pd.DataFrame, period: int = 14, 
                        adx_threshold: float = 25) -> List[Dict]:
    """
    產生 ADX 交易訊號
    
    Args:
        df: 價格資料
        period: ADX 週期
        adx_threshold: 趨勢強度門檻
    
    Returns:
        訊號列表
    """
    adx_data = calculate_adx(df, period)
    df = df.copy()
    df['ADX'] = adx_data['ADX']
    df['+DI'] = adx_data['+DI']
    df['-DI'] = adx_data['-DI']
    
    signals = []
    
    for i in range(period * 2, len(df)):
        prev_plus_di = df['+DI'].iloc[i-1]
        prev_minus_di = df['-DI'].iloc[i-1]
        curr_plus_di = df['+DI'].iloc[i]
        curr_minus_di = df['-DI'].iloc[i]
        curr_adx = df['ADX'].iloc[i]
        
        # +DI 上穿 -DI (金叉)
        if prev_plus_di <= prev_minus_di and curr_plus_di > curr_minus_di:
            signal_type = "BUY" if curr_adx > adx_threshold else "WAIT"
            signals.append({
                "date": str(df.index[i].date()),
                "type": signal_type,
                "adx": round(curr_adx, 2),
                "plus_di": round(curr_plus_di, 2),
                "minus_di": round(curr_minus_di, 2),
                "reason": f"+DI 上穿 -DI | ADX={curr_adx:.1f}"
            })
        
        # -DI 上穿 +DI (死叉)
        elif prev_plus_di >= prev_minus_di and curr_plus_di < curr_minus_di:
            signal_type = "SELL" if curr_adx > adx_threshold else "WAIT"
            signals.append({
                "date": str(df.index[i].date()),
                "type": signal_type,
                "adx": round(curr_adx, 2),
                "plus_di": round(curr_plus_di, 2),
                "minus_di": round(curr_minus_di, 2),
                "reason": f"-DI 上穿 +DI | ADX={curr_adx:.1f}"
            })
    
    return signals


def analyze_adx(ticker_symbol: str, period: str = "6mo", adx_period: int = 14) -> Dict:
    """
    完整 ADX 策略分析
    
    Args:
        ticker_symbol: 股票代碼
        period: 資料週期
        adx_period: ADX 計算週期
    
    Returns:
        分析結果
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            return {"symbol": ticker_symbol, "error": "No data"}
        
        adx_data = calculate_adx(df, adx_period)
        latest = adx_data.iloc[-1]
        
        # 統計
        adx_stats = {
            "current": round(latest['ADX'], 2),
            "plus_di": round(latest['+DI'], 2),
            "minus_di": round(latest['-DI'], 2),
            "min_30d": round(adx_data['ADX'].tail(30).min(), 2),
            "max_30d": round(adx_data['ADX'].tail(30).max(), 2)
        }
        
        # 訊號
        signals = generate_adx_signals(df, adx_period)
        
        # 趨勢判斷
        current_adx = latest['ADX']
        
        if current_adx >= 50:
            trend_strength = "very_strong"
            trend_text = "🔴 非常強趨勢"
        elif current_adx >= 25:
            trend_strength = "strong"
            trend_text = "🟡 強趨勢"
        elif current_adx >= 20:
            trend_strength = "weak"
            trend_text = "🟢 弱趨勢/盤整"
        else:
            trend_strength = "very_weak"
            trend_text = "⚪ 無明顯趨勢"
        
        # 多空方向
        if latest['+DI'] > latest['-DI']:
            direction = "bullish"
            direction_text = "🟢 多頭趨勢 (+DI > -DI)"
        else:
            direction = "bearish"
            direction_text = "🔴 空頭趨勢 (-DI > +DI)"
        
        return {
            "symbol": ticker_symbol,
            "current_price": float(df['Close'].iloc[-1]),
            "adx": adx_stats,
            "trend_strength": trend_strength,
            "trend_text": trend_text,
            "direction": direction,
            "direction_text": direction_text,
            "recent_signals": signals[-5:] if signals else [],
            "conclusion": f"ADX={current_adx:.1f} | {trend_text} | {direction_text}"
        }
        
    except Exception as e:
        return {"symbol": ticker_symbol, "error": str(e)}


def main():
    """測試函數"""
    test_stocks = ["2330.TW", "AAPL", "TSLA"]
    
    print("=" * 60)
    print("ADX 策略分析")
    print("=" * 60)
    
    for symbol in test_stocks:
        result = analyze_adx(symbol)
        
        if "error" in result:
            print(f"\n{symbol}: {result['error']}")
            continue
        
        print(f"\n{'='*40}")
        print(f"股票: {symbol}")
        print(f"價格: {result['current_price']:.2f}")
        print(f"ADX: {result['adx']['current']}")
        print(f"+DI: {result['adx']['plus_di']} | -DI: {result['adx']['minus_di']}")
        print(f"趨勢: {result['trend_text']}")
        print(f"方向: {result['direction_text']}")


if __name__ == "__main__":
    main()
