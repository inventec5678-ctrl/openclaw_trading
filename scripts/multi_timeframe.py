#!/usr/bin/env python3
"""
多時間段測試框架
- 日線 (1D)
- 週線 (1W)
- 4小時 (4H)
- 1小時 (1H)
- 15分鐘 (15M)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

# 對應的 yfinance interval
TIMEFRAME_MAP = {
    "15M": "15m",
    "1H": "1h", 
    "4H": "4h",
    "1D": "1d",
    "1W": "1wk"
}

# 建議的資料週期
PERIOD_MAP = {
    "15M": "5d",
    "1H": "60d",
    "4H": "60d",
    "1D": "2y",
    "1W": "5y"
}


def get_timeframe_data(ticker_symbol: str, timeframe: str) -> pd.DataFrame:
    """
    取得特定時間段的資料
    
    Args:
        ticker_symbol: 股票代碼
        timeframe: 時間段 (15M, 1H, 4H, 1D, 1W)
    
    Returns:
        價格資料 DataFrame
    """
    if timeframe not in TIMEFRAME_MAP:
        raise ValueError(f"Invalid timeframe: {timeframe}")
    
    interval = TIMEFRAME_MAP[frame]
    period = PERIOD_MAP[timeframe]
    
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period=period, interval=interval)
    
    return df


def calculate_indicators_for_tf(df: pd.DataFrame) -> Dict:
    """
    計算單一時間段的技術指標
    
    Args:
        df: 價格資料
    
    Returns:
        指標字典
    """
    result = {}
    
    # MA
    for ma in [5, 10, 20, 60]:
        result[f'MA{ma}'] = df['Close'].rolling(window=ma).mean().iloc[-1]
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    result['RSI'] = (100 - (100 / (1 + rs))).iloc[-1]
    
    # MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    result['MACD'] = macd.iloc[-1]
    result['MACD_Signal'] = signal.iloc[-1]
    result['MACD_Hist'] = (macd - signal).iloc[-1]
    
    # 趨勢判斷
    if result.get('MA5') and result.get('MA20'):
        result['trend'] = 'bullish' if result['MA5'] > result['MA20'] else 'bearish'
    
    return result


def multi_timeframe_analysis(ticker_symbol: str, 
                             timeframes: List[str] = None) -> Dict:
    """
    多時間段分析
    
    Args:
        ticker_symbol: 股票代碼
        timeframes: 要分析的時間段列表
    
    Returns:
        多時間段分析結果
    """
    if timeframes is None:
        timeframes = ["15M", "1H", "4H", "1D", "1W"]
    
    results = {
        "symbol": ticker_symbol,
        "analysis_time": datetime.now().isoformat(),
        "timeframes": {}
    }
    
    for tf in timeframes:
        try:
            df = get_timeframe_data(ticker_symbol, tf)
            
            if df.empty:
                results["timeframes"][tf] = {"error": "No data"}
                continue
            
            # 計算指標
            indicators = calculate_indicators_for_tf(df)
            
            # 基本資料
            results["timeframes"][tf] = {
                "data_points": len(df),
                "latest_price": float(df['Close'].iloc[-1]),
                "latest_date": str(df.index[-1]),
                "indicators": {k: round(v, 2) if pd.notna(v) else None 
                              for k, v in indicators.items()}
            }
            
        except Exception as e:
            results["timeframes"][tf] = {"error": str(e)}
    
    # 綜合判斷
    results["summary"] = generate_summary(results["timeframes"])
    
    return results


def generate_summary(timeframes_data: Dict) -> Dict:
    """
    產生多時間段綜合摘要
    
    Args:
        timeframes_data: 各時間段的資料
    
    Returns:
        摘要字典
    """
    # 統計趨勢
    trends = []
    for tf, data in timeframes_data.items():
        if "indicators" in data and "trend" in data["indicators"]:
            trends.append(data["indicators"]["trend"])
    
    if not trends:
        return {"overall_trend": "unknown", "signal": "⚪ 資料不足"}
    
    bullish_count = trends.count("bullish")
    bearish_count = trends.count("bearish")
    
    if bullish_count >= len(trends) * 0.6:
        overall_trend = "bullish"
        signal = "🟢 偏多"
    elif bearish_count >= len(trends) * 0.6:
        overall_trend = "bearish"
        signal = "🔴 偏空"
    else:
        overall_trend = "mixed"
        signal = "🟡 震盪"
    
    # RSI 綜合
    rsi_values = []
    for tf, data in timeframes_data.items():
        if "indicators" in data and data["indicators"].get("RSI"):
            rsi_values.append(data["indicators"]["RSI"])
    
    avg_rsi = sum(rsi_values) / len(rsi_values) if rsi_values else 50
    
    return {
        "overall_trend": overall_trend,
        "signal": signal,
        "bullish_timeframes": bullish_count,
        "bearish_timeframes": bearish_count,
        "average_rsi": round(avg_rsi, 2)
    }


def backtest_timeframes(ticker_symbol: str, timeframes: List[str] = None) -> Dict:
    """
    回測多時間段策略表現
    
    Args:
        ticker_symbol: 股票代碼
        timeframes: 要回測的時間段
    
    Returns:
        回測結果
    """
    if timeframes is None:
        timeframes = ["1H", "4H", "1D"]
    
    results = {
        "symbol": ticker_symbol,
        "backtest_results": {}
    }
    
    for tf in timeframes:
        try:
            df = get_timeframe_data(ticker_symbol, tf)
            
            if df.empty or len(df) < 50:
                results["backtest_results"][tf] = {"error": "Insufficient data"}
                continue
            
            # 簡單策略：MA5 > MA20 買入，MA5 < MA20 賣出
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            
            # 計算訊號
            df['Signal'] = np.where(df['MA5'] > df['MA20'], 1, -1)
            df['Returns'] = df['Close'].pct_change()
            df['Strategy_Returns'] = df['Signal'].shift(1) * df['Returns']
            
            # 計算績效
            total_return = (1 + df['Strategy_Returns'].dropna()).prod() - 1
            volatility = df['Strategy_Returns'].std() * np.sqrt(252 if tf == "1D" else 24*252)
            sharpe = total_return / volatility if volatility > 0 else 0
            
            results["backtest_results"][tf] = {
                "total_return": round(total_return * 100, 2),
                "sharpe_ratio": round(sharpe, 2),
                "volatility": round(volatility * 100, 2),
                "trades": int((df['Signal'].diff() != 0).sum())
            }
            
        except Exception as e:
            results["backtest_results"][tf] = {"error": str(e)}
    
    return results


def main():
    """測試函數"""
    test_symbols = ["2330.TW", "AAPL"]
    timeframes = ["15M", "1H", "4H", "1D"]
    
    print("=" * 60)
    print("多時間段分析")
    print("=" * 60)
    
    for symbol in test_symbols:
        print(f"\n{'='*40}")
        print(f"股票: {symbol}")
        
        # 多時間段分析
        mtf_result = multi_timeframe_analysis(symbol, timeframes)
        
        for tf, data in mtf_result["timeframes"].items():
            if "error" in data:
                print(f"  {tf}: {data['error']}")
            else:
                price = data.get("latest_price", 0)
                indicators = data.get("indicators", {})
                rsi = indicators.get("RSI", "N/A")
                trend = indicators.get("trend", "N/A")
                print(f"  {tf}: ${price:.2f} | RSI: {rsi} | Trend: {trend}")
        
        # 摘要
        summary = mtf_result.get("summary", {})
        print(f"\n  綜合判斷: {summary.get('signal', 'N/A')}")
        print(f"  平均 RSI: {summary.get('average_rsi', 'N/A')}")
        
        # 回測
        print(f"\n  回測結果:")
        bt_result = backtest_timeframes(symbol, ["1H", "4H", "1D"])
        for tf, data in bt_result.get("backtest_results", {}).items():
            if "error" not in data:
                print(f"    {tf}: 報酬 {data['total_return']}% | Sharpe: {data['sharpe_ratio']}")


if __name__ == "__main__":
    main()
