#!/usr/bin/env python3
"""
完整技術指標計算模組
包含：MA, EMA, MACD, SAR, RSI, KD, Stochastic, Bollinger Bands, 維加斯通道, 背離
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime, timedelta
import json


class TechnicalIndicators:
    """完整技術指標計算類別"""
    
    def __init__(self, ticker_symbol: str, period: str = "2y"):
        """
        初始化
        
        Args:
            ticker_symbol: 股票代碼
            period: 資料週期 (如 "2y", "1y", "6mo")
        """
        self.symbol = ticker_symbol
        self.period = period
        self.df = self._load_data()
        self.data = {}
        
    def _load_data(self) -> pd.DataFrame:
        """載入股票數據"""
        try:
            ticker = yf.Ticker(self.symbol)
            df = ticker.history(period=self.period)
            df = df.dropna()
            return df
        except Exception as e:
            print(f"Error loading data for {self.symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_all(self) -> Dict:
        """計算所有指標"""
        if self.df.empty:
            return {"error": "No data available"}
        
        # 計算各項指標
        self._ma()
        self._ema()
        self._macd()
        self._sar()
        self._rsi()
        self._kd()
        self._stochastic()
        self._bollinger_bands()
        self._vegas_channel()
        
        # 組合最新數據
        self._combine_latest()
        
        return self.data
    
    # ==================== 均線系列 ====================
    
    def _ma(self):
        """計算移動平均線"""
        for period in [5, 10, 20, 60, 120, 240]:
            self.df[f'MA{period}'] = self.df['Close'].rolling(window=period).mean()
    
    def _ema(self):
        """計算指數移動平均線"""
        for period in [12, 26, 50, 200]:
            self.df[f'EMA{period}'] = self.df['Close'].ewm(span=period, adjust=False).mean()
    
    # ==================== MACD ====================
    
    def _macd(self):
        """計算 MACD 指標"""
        ema12 = self.df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = self.df['Close'].ewm(span=26, adjust=False).mean()
        
        self.df['MACD'] = ema12 - ema26
        self.df['MACD_Signal'] = self.df['MACD'].ewm(span=9, adjust=False).mean()
        self.df['MACD_Histogram'] = self.df['MACD'] - self.df['MACD_Signal']
    
    # ==================== SAR ====================
    
    def _sar(self):
        """計算 SAR 指標 (Parabolic Stop and Reverse)"""
        df = self.df.copy()
        
        # 初始化
        sar = [df['Low'].iloc[0]]
        trend = [1]  # 1 = 上漲趨勢, -1 = 下跌趨勢
        af = [0.02]  # 加速因子
        ep = [df['High'].iloc[0]]  # 極值點
        
        for i in range(1, len(df)):
            prev_sar = sar[-1]
            prev_af = af[-1]
            prev_ep = ep[-1]
            prev_trend = trend[-1]
            
            # 計算 SAR
            new_sar = prev_sar + prev_af * (prev_ep - prev_sar)
            
            # 判斷趨勢反轉
            if prev_trend == 1:  # 上漲趨勢
                if df['Low'].iloc[i] < new_sar:
                    # 趨勢反轉為下跌
                    new_trend = -1
                    new_ep = df['Low'].iloc[i-1]
                    new_af = 0.02
                else:
                    new_trend = 1
                    new_ep = max(prev_ep, df['High'].iloc[i])
                    new_af = min(0.2, prev_af + 0.02)
            else:  # 下跌趨勢
                if df['High'].iloc[i] > new_sar:
                    # 趨勢反轉為上漲
                    new_trend = 1
                    new_ep = df['High'].iloc[i-1]
                    new_af = 0.02
                else:
                    new_trend = -1
                    new_ep = min(prev_ep, df['Low'].iloc[i])
                    new_af = min(0.2, prev_af + 0.02)
            
            sar.append(new_sar)
            trend.append(new_trend)
            af.append(new_af)
            ep.append(new_ep)
        
        self.df['SAR'] = sar
        self.df['SAR_Trend'] = trend
    
    # ==================== RSI ====================
    
    def _rsi(self):
        """計算 RSI 指標"""
        delta = self.df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        # 使用 EMA 計算
        avg_gain = gain.ewm(span=14, adjust=False).mean()
        avg_loss = loss.ewm(span=14, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        self.df['RSI'] = 100 - (100 / (1 + rs))
    
    # ==================== KD 指標 ====================
    
    def _kd(self):
        """計算 KD 指標"""
        low_min = self.df['Low'].rolling(window=9).min()
        high_max = self.df['High'].rolling(window=9).max()
        
        rsv = (self.df['Close'] - low_min) / (high_max - low_min) * 100
        rsv = rsv.fillna(50)
        
        self.df['K'] = rsv.ewm(alpha=1/3, adjust=False).mean()
        self.df['D'] = self.df['K'].ewm(alpha=1/3, adjust=False).mean()
        self.df['J'] = 3 * self.df['K'] - 2 * self.df['D']
    
    # ==================== Stochastic ====================
    
    def _stochastic(self):
        """計算 Stochastic 指標 (Slow Stochastic)"""
        low_min = self.df['Low'].rolling(window=14).min()
        high_max = self.df['High'].rolling(window=14).max()
        
        # Fast %K
        self.df['Stoch_K_Fast'] = (self.df['Close'] - low_min) / (high_max - low_min) * 100
        
        # Slow %K (3日平滑)
        self.df['Stoch_K'] = self.df['Stoch_K_Fast'].rolling(window=3).mean()
        
        # %D (3日平滑的平滑)
        self.df['Stoch_D'] = self.df['Stoch_K'].rolling(window=3).mean()
    
    # ==================== Bollinger Bands ====================
    
    def _bollinger_bands(self):
        """計算 Bollinger Bands"""
        # 標準 20日週期，2倍標準差
        self.df['BB_Middle'] = self.df['Close'].rolling(window=20).mean()
        std = self.df['Close'].rolling(window=20).std()
        
        self.df['BB_Upper'] = self.df['BB_Middle'] + (std * 2)
        self.df['BB_Lower'] = self.df['BB_Middle'] - (std * 2)
        
        # 計算 %B 和 BandWidth
        self.df['BB_Width'] = (self.df['BB_Upper'] - self.df['BB_Lower']) / self.df['BB_Middle'] * 100
        
        # 價格位置
        self.df['BB_Position'] = (self.df['Close'] - self.df['BB_Lower']) / (self.df['BB_Upper'] - self.df['BB_Lower'])
    
    # ==================== 維加斯通道 ====================
    
    def _vegas_channel(self):
        """計算維加斯通道"""
        self.df['Vegas_EMA144'] = self.df['Close'].ewm(span=144, adjust=False).mean()
        self.df['Vegas_EMA169'] = self.df['Close'].ewm(span=169, adjust=False).mean()
        
        # 通道
        self.df['Vegas_Upper'] = self.df['Vegas_EMA144']
        self.df['Vegas_Lower'] = self.df['Vegas_EMA169']
        self.df['Vegas_Mid'] = (self.df['Vegas_EMA144'] + self.df['Vegas_EMA169']) / 2
        
        # 通道寬度 (波動性)
        self.df['Vegas_Width'] = (self.df['Vegas_Upper'] - self.df['Vegas_Lower']) / self.df['Vegas_Lower'] * 100
    
    # ==================== 組合數據 ====================
    
    def _combine_latest(self):
        """組合最新數據"""
        latest = self.df.iloc[-1]
        prev = self.df.iloc[-2] if len(self.df) > 1 else latest
        
        self.data = {
            "symbol": self.symbol,
            "timestamp": datetime.now().isoformat(),
            "price": {
                "current": float(latest['Close']),
                "previous": float(prev['Close']),
                "change": float(latest['Close'] - prev['Close']),
                "change_pct": float((latest['Close'] - prev['Close']) / prev['Close'] * 100),
                "high": float(latest['High']),
                "low": float(latest['Low']),
                "volume": int(latest['Volume']),
                "open": float(latest['Open'])
            },
            "ma": {
                "MA5": round(float(latest['MA5']), 2) if pd.notna(latest['MA5']) else None,
                "MA10": round(float(latest['MA10']), 2) if pd.notna(latest['MA10']) else None,
                "MA20": round(float(latest['MA20']), 2) if pd.notna(latest['MA20']) else None,
                "MA60": round(float(latest['MA60']), 2) if pd.notna(latest['MA60']) else None,
                "MA120": round(float(latest['MA120']), 2) if pd.notna(latest['MA120']) else None,
                "MA240": round(float(latest['MA240']), 2) if pd.notna(latest['MA240']) else None,
            },
            "ema": {
                "EMA12": round(float(latest['EMA12']), 2) if pd.notna(latest['EMA12']) else None,
                "EMA26": round(float(latest['EMA26']), 2) if pd.notna(latest['EMA26']) else None,
                "EMA50": round(float(latest['EMA50']), 2) if pd.notna(latest['EMA50']) else None,
                "EMA200": round(float(latest['EMA200']), 2) if pd.notna(latest['EMA200']) else None,
            },
            "macd": {
                "MACD": round(float(latest['MACD']), 4) if pd.notna(latest['MACD']) else None,
                "Signal": round(float(latest['MACD_Signal']), 4) if pd.notna(latest['MACD_Signal']) else None,
                "Histogram": round(float(latest['MACD_Histogram']), 4) if pd.notna(latest['MACD_Histogram']) else None,
            },
            "sar": {
                "SAR": round(float(latest['SAR']), 2) if pd.notna(latest['SAR']) else None,
                "Trend": int(latest['SAR_Trend']) if pd.notna(latest['SAR_Trend']) else None,
            },
            "rsi": {
                "RSI": round(float(latest['RSI']), 2) if pd.notna(latest['RSI']) else None,
            },
            "kd": {
                "K": round(float(latest['K']), 2) if pd.notna(latest['K']) else None,
                "D": round(float(latest['D']), 2) if pd.notna(latest['D']) else None,
                "J": round(float(latest['J']), 2) if pd.notna(latest['J']) else None,
            },
            "stochastic": {
                "K": round(float(latest['Stoch_K']), 2) if pd.notna(latest['Stoch_K']) else None,
                "D": round(float(latest['Stoch_D']), 2) if pd.notna(latest['Stoch_D']) else None,
            },
            "bollinger": {
                "Upper": round(float(latest['BB_Upper']), 2) if pd.notna(latest['BB_Upper']) else None,
                "Middle": round(float(latest['BB_Middle']), 2) if pd.notna(latest['BB_Middle']) else None,
                "Lower": round(float(latest['BB_Lower']), 2) if pd.notna(latest['BB_Lower']) else None,
                "Width": round(float(latest['BB_Width']), 2) if pd.notna(latest['BB_Width']) else None,
                "Position": round(float(latest['BB_Position']), 2) if pd.notna(latest['BB_Position']) else None,
            },
            "vegas": {
                "EMA144": round(float(latest['Vegas_EMA144']), 2) if pd.notna(latest['Vegas_EMA144']) else None,
                "EMA169": round(float(latest['Vegas_EMA169']), 2) if pd.notna(latest['Vegas_EMA169']) else None,
                "Upper": round(float(latest['Vegas_Upper']), 2) if pd.notna(latest['Vegas_Upper']) else None,
                "Lower": round(float(latest['Vegas_Lower']), 2) if pd.notna(latest['Vegas_Lower']) else None,
                "Width": round(float(latest['Vegas_Width']), 2) if pd.notna(latest['Vegas_Width']) else None,
            }
        }
    
    def get_signals(self) -> Dict:
        """產生交易訊號"""
        if not self.data or "error" in self.data:
            return {"error": "No data"}
        
        latest = self.data
        signals = {
            "overall": "NEUTRAL",
            "signals": [],
            "warnings": [],
            "summary": ""
        }
        
        price = latest['price']['current']
        signal_list = []
        
        # ==================== 均線訊號 ====================
        ma = latest['ma']
        if ma['MA5'] and ma['MA20']:
            if ma['MA5'] > ma['MA20']:
                signal_list.append(("MA", "🟢", "MA5 > MA20 多頭排列"))
            else:
                signal_list.append(("MA", "🔴", "MA5 < MA20 空頭排列"))
        
        # ==================== MACD 訊號 ====================
        macd = latest['macd']
        if macd['MACD'] and macd['Signal']:
            if macd['MACD'] > macd['Signal']:
                signal_list.append(("MACD", "🟢", "MACD > Signal"))
            else:
                signal_list.append(("MACD", "🔴", "MACD < Signal"))
            
            # MACD 穿越
            prev_macd = self.df['MACD'].iloc[-2]
            prev_signal = self.df['MACD_Signal'].iloc[-2]
            if prev_macd < prev_signal and macd['MACD'] > macd['Signal']:
                signal_list.append(("MACD", "🟢", "MACD 金叉"))
            elif prev_macd > prev_signal and macd['MACD'] < macd['Signal']:
                signal_list.append(("MACD", "🔴", "MACD 死叉"))
        
        # ==================== RSI 訊號 ====================
        rsi = latest['rsi']['RSI']
        if rsi:
            if rsi > 70:
                signal_list.append(("RSI", "🔴", f"RSI 超買 {rsi:.1f}"))
            elif rsi < 30:
                signal_list.append(("RSI", "🟢", f"RSI 超賣 {rsi:.1f}"))
            else:
                signal_list.append(("RSI", "⚪", f"RSI 中性 {rsi:.1f}"))
        
        # ==================== KD 訊號 ====================
        kd = latest['kd']
        if kd['K'] and kd['D']:
            if kd['K'] > kd['D'] and kd['K'] < 80:
                signal_list.append(("KD", "🟢", "KD 金叉"))
            elif kd['K'] < kd['D'] and kd['K'] > 20:
                signal_list.append(("KD", "🔴", "KD 死叉"))
            
            if kd['K'] < 20:
                signal_list.append(("KD", "🟢", f"KD 超賣 {kd['K']:.1f}"))
            elif kd['K'] > 80:
                signal_list.append(("KD", "🔴", f"KD 超買 {kd['K']:.1f}"))
        
        # ==================== Stochastic 訊號 ====================
        stoch = latest['stochastic']
        if stoch['K'] and stoch['D']:
            if stoch['K'] < 20 and stoch['D'] < 20:
                signal_list.append(("Stoch", "🟢", f"Stochastic 超賣 K={stoch['K']:.1f}"))
            elif stoch['K'] > 80 and stoch['D'] > 80:
                signal_list.append(("Stoch", "🔴", f"Stochastic 超買 K={stoch['K']:.1f}"))
        
        # ==================== Bollinger Bands 訊號 ====================
        bb = latest['bollinger']
        if bb['Position'] is not None:
            if bb['Position'] > 1:
                signal_list.append(("BB", "🔴", "價格突破上軌"))
            elif bb['Position'] < 0:
                signal_list.append(("BB", "🟢", "價格跌破下軌"))
            
            if bb['Width']:
                if bb['Width'] > 5:
                    signal_list.append(("BB", "⚠️", f"波動性高 {bb['Width']:.1f}%"))
                elif bb['Width'] < 2:
                    signal_list.append(("BB", "⚪", f"波動性低 {bb['Width']:.1f}%"))
        
        # ==================== 維加斯通道訊號 ====================
        vegas = latest['vegas']
        if vegas['EMA144'] and vegas['EMA169']:
            if price > vegas['EMA144']:
                signal_list.append(("Vegas", "🟢", "價格 > 144 EMA"))
            elif price < vegas['EMA169']:
                signal_list.append(("Vegas", "🔴", "價格 < 169 EMA"))
            
            if vegas['EMA144'] > vegas['EMA169']:
                signal_list.append(("Vegas", "🟢", "多頭排列 (144 > 169)"))
            else:
                signal_list.append(("Vegas", "🔴", "空頭排列 (144 < 169)"))
        
        # ==================== SAR 訊號 ====================
        sar = latest['sar']
        if sar['Trend']:
            if sar['Trend'] > 0:
                signal_list.append(("SAR", "🟢", "SAR 趨勢向上"))
            else:
                signal_list.append(("SAR", "🔴", "SAR 趨勢向下"))
        
        # 統計多空訊號
        green_signals = [s for s in signal_list if s[1] == "🟢"]
        red_signals = [s for s in signal_list if s[1] == "🔴"]
        
        # 決定整體訊號
        if len(green_signals) > len(red_signals) + 2:
            signals["overall"] = "BULLISH"
        elif len(red_signals) > len(green_signals) + 2:
            signals["overall"] = "BEARISH"
        
        signals["signals"] = [{"indicator": s[0], "icon": s[1], "message": s[2]} for s in signal_list]
        signals["summary"] = f"多頭訊號: {len(green_signals)} | 空頭訊號: {len(red_signals)} | 整體: {signals['overall']}"
        
        return signals
    
    def get_historical_data(self, days: int = 30) -> List[Dict]:
        """取得歷史指標數據"""
        if self.df.empty:
            return []
        
        df = self.df.tail(days).copy()
        df = df.reset_index()
        
        records = []
        for _, row in df.iterrows():
            records.append({
                "date": str(row['Date'].date()) if 'Date' in row else str(row.index.date()),
                "close": float(row['Close']),
                "volume": int(row['Volume']),
                "MA5": round(float(row['MA5']), 2) if pd.notna(row['MA5']) else None,
                "MA20": round(float(row['MA20']), 2) if pd.notna(row['MA20']) else None,
                "RSI": round(float(row['RSI']), 2) if pd.notna(row['RSI']) else None,
                "K": round(float(row['K']), 2) if pd.notna(row['K']) else None,
                "D": round(float(row['D']), 2) if pd.notna(row['D']) else None,
                "MACD": round(float(row['MACD']), 4) if pd.notna(row['MACD']) else None,
                "MACD_Signal": round(float(row['MACD_Signal']), 4) if pd.notna(row['MACD_Signal']) else None,
            })
        
        return records


# ==================== 便捷函數 ====================

def get_indicators(ticker: str, period: str = "2y") -> Dict:
    """取得完整技術指標"""
    ti = TechnicalIndicators(ticker, period)
    data = ti.calculate_all()
    data['signals'] = ti.get_signals()
    return data


def get_signals_only(ticker: str, period: str = "1y") -> Dict:
    """只取得訊號"""
    ti = TechnicalIndicators(ticker, period)
    ti.calculate_all()
    return ti.get_signals()


# ==================== 主程式 ====================

if __name__ == "__main__":
    import sys
    
    # 測試
    test_stocks = ["2330.TW", "AAPL", "TSLA", "0050.TW"]
    
    print("=" * 70)
    print("完整技術指標計算")
    print("=" * 70)
    
    for symbol in test_stocks:
        print(f"\n{'='*50}")
        print(f"股票: {symbol}")
        print("=" * 50)
        
        result = get_indicators(symbol)
        
        if "error" in result:
            print(f"錯誤: {result['error']}")
            continue
        
        # 價格資訊
        print(f"\n💰 價格: {result['price']['current']:.2f} ({result['price']['change_pct']:+.2f}%)")
        
        # 主要指標
        print(f"\n📊 技術指標:")
        print(f"   MA20: {result['ma']['MA20']}")
        print(f"   RSI: {result['rsi']['RSI']}")
        print(f"   KD: K={result['kd']['K']}, D={result['kd']['D']}")
        print(f"   MACD: {result['macd']['MACD']:.4f}")
        print(f"   BB: {result['bollinger']['Upper']:.2f} / {result['bollinger']['Middle']:.2f} / {result['bollinger']['Lower']:.2f}")
        
        # 訊號
        signals = result['signals']
        print(f"\n📈 訊號 summary: {signals['summary']}")
        print("\n詳細訊號:")
        for s in signals['signals']:
            print(f"   {s['icon']} {s['indicator']}: {s['message']}")
