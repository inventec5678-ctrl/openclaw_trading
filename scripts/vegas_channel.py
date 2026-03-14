#!/usr/bin/env python3
"""
維加斯通道 (Vegas Channel)
- 使用 144 EMA 和 169 EMA (斐波那契數列)
- 通道突破策略
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


def calculate_vegas_channel(df: pd.DataFrame, 
                            fast_ema: int = 144, 
                            slow_ema: int = 169) -> pd.DataFrame:
    """
    計算維加斯通道
    
    Args:
        df: 包含 Close, High, Low 的資料
        fast_ema: 快速 EMA 週期 (預設 144)
        slow_ema: 慢速 EMA 週期 (預設 169)
    
    Returns:
        包含通道上軌/下軌的 DataFrame
    """
    # 計算 EMA
    ema_fast = df['Close'].ewm(span=fast_ema, adjust=False).mean()
    ema_slow = df['Close'].ewm(span=slow_ema, adjust=False).mean()
    
    # 通道上軌 = 較快的 EMA
    # 通道下軌 = 較慢的 EMA
    upper_channel = ema_fast
    lower_channel = ema_slow
    
    # 計算通道寬度 (波動性指標)
    channel_width = upper_channel - lower_channel
    
    return pd.DataFrame({
        'ema_144': ema_fast,
        'ema_169': ema_slow,
        'vegas_upper': upper_channel,
        'vegas_lower': lower_channel,
        'vegas_mid': (upper_channel + lower_channel) / 2,
        'channel_width': channel_width,
        'channel_width_pct': (channel_width / lower_channel) * 100
    })


def calculate_vegas_with_bands(df: pd.DataFrame,
                               fast_ema: int = 144,
                               slow_ema: int = 169,
                               std_multiplier: float = 1.5) -> pd.DataFrame:
    """
    計算維加斯通道 + 標準差帶
    
    Args:
        df: 價格資料
        fast_ema: 快速 EMA 週期
        slow_ema: 慢速 EMA 週期
        std_multiplier: 標準差倍數
    
    Returns:
        包含完整通道資訊的 DataFrame
    """
    vegas = calculate_vegas_channel(df, fast_ema, slow_ema)
    
    # 計算 ATR 作為波動性調整
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.ewm(span=14, adjust=False).mean()
    
    # 添加標準差帶
    mid = vegas['vegas_mid']
    std = df['Close'].rolling(window=20).std()
    
    return pd.DataFrame({
        'ema_144': vegas['ema_144'],
        'ema_169': vegas['ema_169'],
        'vegas_upper': vegas['vegas_upper'],
        'vegas_lower': vegas['vegas_lower'],
        'vegas_mid': mid,
        'channel_width': vegas['channel_width'],
        'channel_width_pct': vegas['channel_width_pct'],
        'atr': atr,
        'upper_band': mid + (std * std_multiplier),
        'lower_band': mid - (std * std_multiplier)
    })


def generate_vegas_signals(df: pd.DataFrame, 
                          fast_ema: int = 144, 
                          slow_ema: int = 169) -> List[Dict]:
    """
    產生維加斯通道交易訊號
    
    策略:
    - 多頭: 價格上穿通道上軌 (144 EMA)
    - 空頭: 價格下穿通道下軌 (169 EMA)
    - 確認: 通道宽度擴張表示趨勢確認
    
    Args:
        df: 價格資料
        fast_ema: 快速 EMA 週期
        slow_ema: 慢速 EMA 週期
    
    Returns:
        訊號列表
    """
    vegas = calculate_vegas_channel(df, fast_ema, slow_ema)
    df = df.copy()
    df['vegas_upper'] = vegas['vegas_upper']
    df['vegas_lower'] = vegas['vegas_lower']
    df['channel_width_pct'] = vegas['channel_width_pct']
    
    signals = []
    
    # 需要足夠的歷史數據
    warmup = slow_ema * 2
    
    for i in range(warmup, len(df)):
        current_price = df['Close'].iloc[i]
        prev_price = df['Close'].iloc[i-1]
        current_upper = df['vegas_upper'].iloc[i]
        prev_upper = df['vegas_upper'].iloc[i-1]
        current_lower = df['vegas_lower'].iloc[i]
        prev_lower = df['vegas_lower'].iloc[i-1]
        width_pct = df['channel_width_pct'].iloc[i]
        
        # 價格上穿上軌 (多頭突破)
        if prev_price <= prev_upper and current_price > current_upper:
            # 檢查通道是否擴張 (趨勢確認)
            confirm = "CONFIRMED" if width_pct > 2 else "WARNING"
            signals.append({
                "date": str(df.index[i].date()),
                "type": "BUY",
                "price": round(current_price, 2),
                "vegas_upper": round(current_upper, 2),
                "channel_width_pct": round(width_pct, 2),
                "confirm": confirm,
                "reason": f"價格突破 144 EMA | 通道寬度={width_pct:.2f}%"
            })
        
        # 價格下穿下軌 (空頭突破)
        elif prev_price >= prev_lower and current_price < current_lower:
            confirm = "CONFIRMED" if width_pct > 2 else "WARNING"
            signals.append({
                "date": str(df.index[i].date()),
                "type": "SELL",
                "price": round(current_price, 2),
                "vegas_lower": round(current_lower, 2),
                "channel_width_pct": round(width_pct, 2),
                "confirm": confirm,
                "reason": f"價格跌破 169 EMA | 通道寬度={width_pct:.2f}%"
            })
    
    return signals


def analyze_vegas_channel(ticker_symbol: str, 
                          period: str = "1y",
                          fast_ema: int = 144, 
                          slow_ema: int = 169) -> Dict:
    """
    完整維加斯通道策略分析
    
    Args:
        ticker_symbol: 股票代碼
        period: 資料週期
        fast_ema: 快速 EMA 週期
        slow_ema: 慢速 EMA 週期
    
    Returns:
        分析結果
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            return {"symbol": ticker_symbol, "error": "No data"}
        
        vegas = calculate_vegas_channel(df, fast_ema, slow_ema)
        latest = vegas.iloc[-1]
        
        current_price = df['Close'].iloc[-1]
        
        # 位置判斷
        if current_price > latest['vegas_upper']:
            position = "above_upper"
            position_text = "🟢 價格高於通道上軌 (強勢多頭)"
        elif current_price < latest['vegas_lower']:
            position = "below_lower"
            position_text = "🔴 價格低於通道下軌 (強勢空頭)"
        elif current_price > latest['vegas_mid']:
            position = "in_upper_half"
            position_text = "🟡 價格在通道上半部 (偏多)"
        else:
            position = "in_lower_half"
            position_text = "🟠 價格在通道下半部 (偏空)"
        
        # 通道狀態
        width_pct = latest['channel_width_pct']
        
        if width_pct > 5:
            volatility = "high"
            volatility_text = "🔴 高波動 (通道擴張)"
        elif width_pct > 2:
            volatility = "normal"
            volatility_text = "🟡 正常波動"
        else:
            volatility = "low"
            volatility_text = "🟢 低波動 (盤整)"
        
        # EMA 排列
        if latest['ema_144'] > latest['ema_169']:
            trend = "bullish"
            trend_text = "🟢 多頭排列 (144 > 169)"
        else:
            trend = "bearish"
            trend_text = "🔴 空頭排列 (144 < 169)"
        
        # 訊號
        signals = generate_vegas_signals(df, fast_ema, slow_ema)
        
        return {
            "symbol": ticker_symbol,
            "current_price": float(current_price),
            "vegas": {
                "ema_144": round(latest['ema_144'], 2),
                "ema_169": round(latest['ema_169'], 2),
                "upper": round(latest['vegas_upper'], 2),
                "lower": round(latest['vegas_lower'], 2),
                "mid": round(latest['vegas_mid'], 2),
                "channel_width_pct": round(width_pct, 2)
            },
            "position": position,
            "position_text": position_text,
            "volatility": volatility,
            "volatility_text": volatility_text,
            "trend": trend,
            "trend_text": trend_text,
            "recent_signals": signals[-5:] if signals else [],
            "conclusion": f"{position_text} | {volatility_text} | {trend_text}"
        }
        
    except Exception as e:
        return {"symbol": ticker_symbol, "error": str(e)}


def main():
    """測試函數"""
    test_stocks = ["2330.TW", "AAPL", "TSLA", "NVDA"]
    
    print("=" * 70)
    print("維加斯通道 (Vegas Channel) 策略分析")
    print("=" * 70)
    
    for symbol in test_stocks:
        result = analyze_vegas_channel(symbol, period="6mo")
        
        if "error" in result:
            print(f"\n{symbol}: {result['error']}")
            continue
        
        print(f"\n{'='*50}")
        print(f"股票: {symbol}")
        print(f"價格: {result['current_price']:.2f}")
        print(f"\n維加斯通道:")
        print(f"  144 EMA: {result['vegas']['ema_144']:.2f}")
        print(f"  169 EMA: {result['vegas']['ema_169']:.2f}")
        print(f"  上軌:    {result['vegas']['upper']:.2f}")
        print(f"  下軌:    {result['vegas']['lower']:.2f}")
        print(f"  通道寬度: {result['vegas']['channel_width_pct']:.2f}%")
        print(f"\n{result['position_text']}")
        print(f"{result['volatility_text']}")
        print(f"{result['trend_text']}")


if __name__ == "__main__":
    main()
