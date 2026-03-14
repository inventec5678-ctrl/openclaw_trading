#!/usr/bin/env python3
"""
即時交易分析模組
- 支撐位/壓力位計算
- 進場時間建議
- 當下最佳標的推薦
- 風險評估
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json
from collections import Counter


class RealtimeAnalysis:
    """即時交易分析類別"""
    
    def __init__(self, ticker_symbol: str, period: str = "3mo"):
        """
        初始化
        
        Args:
            ticker_symbol: 股票代碼
            period: 資料週期
        """
        self.symbol = ticker_symbol
        self.period = period
        self.df = self._load_data()
        
    def _load_data(self) -> pd.DataFrame:
        """載入股票數據"""
        try:
            ticker = yf.Ticker(self.symbol)
            df = ticker.history(period=self.period)
            return df.dropna()
        except:
            return pd.DataFrame()
    
    # ==================== 支撐位/壓力位 ====================
    
    def calculate_support_resistance(self, num_levels: int = 5) -> Dict:
        """
        計算支撐位和壓力位
        
        方法:
        - 局部高點/低點
        - 成交密集區
        - 整數關卡
        - 移動平均線
        - 趨勢線
        """
        if self.df.empty:
            return {"error": "No data"}
        
        prices = self.df['Close']
        highs = self.df['High']
        lows = self.df['Low']
        
        current_price = prices.iloc[-1]
        
        # 1. 局部高點和低點
        pivots = self._find_pivots()
        
        # 2. 成交密集區 (Volume Profile)
        volume_profile = self._volume_profile()
        
        # 3. 移動平均線支撐/壓力
        ma_levels = self._ma_levels()
        
        # 4. 計算支撐位 (低於 current_price)
        supports = []
        
        # 來自低點
        for low in pivots['lows']:
            if low < current_price * 0.98:
                supports.append({
                    "price": round(low, 2),
                    "type": "pivot_low",
                    "strength": self._calculate_level_strength(low, 'low')
                })
        
        # 來自 MA
        for ma_price in ma_levels['support']:
            if ma_price < current_price:
                supports.append({
                    "price": round(ma_price, 2),
                    "type": "ma",
                    "strength": self._calculate_level_strength(ma_price, 'ma')
                })
        
        # 來自密集區
        for vp in volume_profile['support_zones']:
            if vp < current_price:
                supports.append({
                    "price": round(vp, 2),
                    "type": "volume_cluster",
                    "strength": "medium"
                })
        
        # 5. 計算壓力位 (高於 current_price)
        resistances = []
        
        # 來自高點
        for high in pivots['highs']:
            if high > current_price * 1.02:
                resistances.append({
                    "price": round(high, 2),
                    "type": "pivot_high",
                    "strength": self._calculate_level_strength(high, 'high')
                })
        
        # 來自 MA
        for ma_price in ma_levels['resistance']:
            if ma_price > current_price:
                resistances.append({
                    "price": round(ma_price, 2),
                    "type": "ma",
                    "strength": self._calculate_level_strength(ma_price, 'ma')
                })
        
        # 來自密集區
        for vp in volume_profile['resistance_zones']:
            if vp > current_price:
                resistances.append({
                    "price": round(vp, 2),
                    "type": "volume_cluster",
                    "strength": "medium"
                })
        
        # 排序並取 top N
        supports = sorted(supports, key=lambda x: x['strength'], reverse=True)[:num_levels]
        resistances = sorted(resistances, key=lambda x: x['strength'], reverse=True)[:num_levels]
        
        return {
            "symbol": self.symbol,
            "current_price": round(current_price, 2),
            "supports": supports,
            "resistances": resistances,
            "nearest_support": supports[0] if supports else None,
            "nearest_resistance": resistances[0] if resistances else None,
            "distance_to_support": round((current_price - supports[0]['price']) / current_price * 100, 2) if supports else None,
            "distance_to_resistance": round((resistances[0]['price'] - current_price) / current_price * 100, 2) if resistances else None,
        }
    
    def _find_pivots(self, lookback: int = 20) -> Dict:
        """找出局部高點和低點"""
        highs = self.df['High']
        lows = self.df['Low']
        
        pivot_highs = []
        pivot_lows = []
        
        for i in range(lookback, len(self.df) - lookback):
            # 檢查是否為高點
            is_high = True
            for j in range(1, lookback + 1):
                if highs.iloc[i] <= highs.iloc[i-j] or highs.iloc[i] <= highs.iloc[i+j]:
                    is_high = False
                    break
            if is_high:
                pivot_highs.append(float(highs.iloc[i]))
            
            # 檢查是否為低點
            is_low = True
            for j in range(1, lookback + 1):
                if lows.iloc[i] >= lows.iloc[i-j] or lows.iloc[i] >= lows.iloc[i+j]:
                    is_low = False
                    break
            if is_low:
                pivot_lows.append(float(lows.iloc[i]))
        
        return {
            "highs": pivot_highs[-10:],  # 最近10個
            "lows": pivot_lows[-10:]
        }
    
    def _volume_profile(self, bins: int = 20) -> Dict:
        """計算成交量分佈"""
        prices = self.df['Close']
        volumes = self.df['Volume']
        
        # 價格分組
        price_min = prices.min()
        price_max = prices.max()
        bins_array = np.linspace(price_min, price_max, bins)
        
        # 計算每個區間的成交量
        volume_profile = {}
        for i in range(len(bins_array) - 1):
            mask = (prices >= bins_array[i]) & (prices < bins_array[i+1])
            volume_profile[(bins_array[i], bins_array[i+1])] = volumes[mask].sum()
        
        # 找出高成交量區間
        sorted_zones = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)[:3]
        
        support_zones = [round((z[0][0] + z[0][1])/2, 2) for z in sorted_zones]
        resistance_zones = [round((z[0][0] + z[0][1])/2, 2) for z in sorted_zones]
        
        return {
            "support_zones": support_zones,
            "resistance_zones": resistance_zones
        }
    
    def _ma_levels(self) -> Dict:
        """計算均線支撐/壓力"""
        ma_support = []
        ma_resistance = []
        
        for period in [5, 10, 20, 60]:
            ma = self.df['Close'].rolling(window=period).mean().iloc[-1]
            if pd.notna(ma):
                if ma < self.df['Close'].iloc[-1]:
                    ma_support.append(float(ma))
                else:
                    ma_resistance.append(float(ma))
        
        return {
            "support": ma_support,
            "resistance": ma_resistance
        }
    
    def _calculate_level_strength(self, level: float, level_type: str) -> str:
        """計算支撐/壓力強度"""
        touches = 0
        current_price = self.df['Close'].iloc[-1]
        
        if level_type == 'high':
            touches = sum(1 for h in self.df['High'] if abs(h - level) / level < 0.01)
        elif level_type == 'low':
            touches = sum(1 for l in self.df['Low'] if abs(l - level) / level < 0.01)
        
        if touches >= 3:
            return "strong"
        elif touches >= 2:
            return "medium"
        else:
            return "weak"
    
    # ==================== 進場時間建議 ====================
    
    def get_entry_timing(self) -> Dict:
        """取得進場時間建議"""
        if self.df.empty:
            return {"error": "No data"}
        
        current_price = self.df['Close'].iloc[-1]
        
        # 計算各項時機指標
        signals = []
        
        # 1. 日內時段分析
        hourly_return = self._intraday_pattern()
        signals.append(hourly_return)
        
        # 2. 週期分析
        cyclical = self._cyclical_analysis()
        signals.append(cyclical)
        
        # 3. 趨勢確認
        trend = self._trend_confirmation()
        signals.append(trend)
        
        # 4. 波動性分析
        volatility = self._volatility_analysis()
        
        # 綜合建議
        buy_signals = [s for s in signals if s.get('action') == 'buy']
        sell_signals = [s for s in signals if s.get('action') == 'sell']
        
        if len(buy_signals) >= 2:
            recommendation = "STRONG_BUY"
            action = "建議買入"
        elif len(buy_signals) >= 1:
            recommendation = "BUY"
            action = "可以考慮買入"
        elif len(sell_signals) >= 2:
            recommendation = "STRONG_SELL"
            action = "建議賣出"
        elif len(sell_signals) >= 1:
            recommendation = "SELL"
            action = "可以考慮賣出"
        else:
            recommendation = "HOLD"
            action = "觀望"
        
        return {
            "symbol": self.symbol,
            "current_price": round(current_price, 2),
            "recommendation": recommendation,
            "action": action,
            "signals": signals,
            "volatility": volatility,
            "best_entry": buy_signals[0] if buy_signals else None,
            "reason": " | ".join([s.get('reason', '') for s in signals])
        }
    
    def _intraday_pattern(self) -> Dict:
        """日內時段分析"""
        # 簡單分析：檢查過去幾天的盤中走勢
        recent = self.df.tail(5)
        
        # 計算平均漲跌幅
        returns = (recent['Close'] - recent['Open']) / recent['Open'] * 100
        
        if returns.mean() > 0.5:
            return {
                "type": "intraday",
                "action": "buy",
                "reason": "近期盤中走勢偏多",
                "strength": "medium"
            }
        elif returns.mean() < -0.5:
            return {
                "type": "intraday",
                "action": "sell",
                "reason": "近期盤中走勢偏空",
                "strength": "medium"
            }
        
        return {
            "type": "intraday",
            "action": "hold",
            "reason": "盤中走勢中性",
            "strength": "low"
        }
    
    def _cyclical_analysis(self) -> Dict:
        """週期分析 - 星期效應"""
        # 取得過去一年的數據
        df = self.df.copy()
        df['DayOfWeek'] = df.index.dayofweek
        
        # 計算每個星期幾的平均報酬
        avg_returns = df.groupby('DayOfWeek').apply(
            lambda x: (x['Close'].iloc[-1] - x['Close'].iloc[0]) / x['Close'].iloc[0] * 100
            if len(x) > 1 else 0
        )
        
        today = datetime.now().weekday()
        today_avg = avg_returns.get(today, 0)
        
        if today_avg > 1:
            return {
                "type": "cyclical",
                "action": "buy",
                "reason": f"今天是週{['一','二','三','四','五','六','日'][today]}，歷史表現較好",
                "strength": "low"
            }
        
        return {
            "type": "cyclical",
            "action": "hold",
            "reason": "無明顯週期效應",
            "strength": "low"
        }
    
    def _trend_confirmation(self) -> Dict:
        """趨勢確認"""
        ma5 = self.df['Close'].rolling(5).mean().iloc[-1]
        ma20 = self.df['Close'].rolling(20).mean().iloc[-1]
        
        if ma5 > ma20:
            return {
                "type": "trend",
                "action": "buy",
                "reason": "短期均線 > 長期均線，多頭趨勢",
                "strength": "high"
            }
        else:
            return {
                "type": "trend",
                "action": "sell",
                "reason": "短期均線 < 長期均碼，空頭趨勢",
                "strength": "high"
            }
    
    def _volatility_analysis(self) -> Dict:
        """波動性分析"""
        returns = self.df['Close'].pct_change().dropna()
        
        vol = returns.std() * np.sqrt(252) * 100  # 年化波動率
        recent_vol = returns.tail(5).std() * np.sqrt(252) * 100
        
        # RSI 計算
        delta = returns
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        return {
            "annualized_volatility": round(vol, 2),
            "recent_volatility": round(recent_vol, 2),
            "rsi_14": round(current_rsi, 2) if pd.notna(current_rsi) else None,
            "volatility_status": "high" if vol > 30 else "normal" if vol > 15 else "low"
        }
    
    # ==================== MA (移動平均線) 策略 ====================
    
    def calculate_ma(self, short_period: int = 20, long_period: int = 60) -> Dict:
        """
        計算 MA (移動平均線) 指標
        
        Args:
            short_period: 短期 MA 週期 (預設 20)
            long_period: 長期 MA 週期 (預設 60)
        
        Returns:
            MA 指標數據和信號
        """
        if self.df.empty or len(self.df) < long_period:
            return {"error": "數據不足無法計算 MA"}
        
        close = self.df['Close']
        
        # 計算 SMA (簡單移動平均)
        ma_short = close.rolling(window=short_period).mean()
        ma_long = close.rolling(window=long_period).mean()
        
        current_price = close.iloc[-1]
        current_ma_short = ma_short.iloc[-1]
        current_ma_long = ma_long.iloc[-1]
        
        prev_ma_short = ma_short.iloc[-2]
        prev_ma_long = ma_long.iloc[-2]
        
        # 計算更多週期的 MA 作為參考
        ma_5 = close.rolling(window=5).mean().iloc[-1]
        ma_10 = close.rolling(window=10).mean().iloc[-1]
        ma_20 = close.rolling(window=20).mean().iloc[-1] if short_period != 20 else current_ma_short
        ma_60 = close.rolling(window=60).mean().iloc[-1] if long_period != 60 else current_ma_long
        ma_120 = close.rolling(window=120).mean().iloc[-1]
        ma_240 = close.rolling(window=240).mean().iloc[-1]
        
        # 判斷趨勢
        if current_ma_short > current_ma_long:
            trend = "多頭 (短線 > 長線)"
        elif current_ma_short < current_ma_long:
            trend = "空頭 (短線 < 長線)"
        else:
            trend = "整理 (短線 = 長線)"
        
        # 判斷價格位置
        if current_price > current_ma_short:
            price_position = "高於短期MA"
        else:
            price_position = "低於短期MA"
        
        # 黃金交叉: 短期MA從下往上穿越長期MA
        golden_cross = prev_ma_short <= prev_ma_long and current_ma_short > current_ma_long
        # 死亡交叉: 短期MA從上往下穿越長期MA
        death_cross = prev_ma_short >= prev_ma_long and current_ma_short < current_ma_long
        
        # 多頭排列: MA5 > MA10 > MA20 > MA60
        if pd.notna(ma_5) and pd.notna(ma_10) and pd.notna(ma_20) and pd.notna(ma_60):
            bullish_arrangement = ma_5 > ma_10 > ma_20 > ma_60
        else:
            bullish_arrangement = False
        
        # 空頭排列: MA5 < MA10 < MA20 < MA60
        if pd.notna(ma_5) and pd.notna(ma_10) and pd.notna(ma_20) and pd.notna(ma_60):
            bearish_arrangement = ma_5 < ma_10 < ma_20 < ma_60
        else:
            bearish_arrangement = False
        
        # 計算 MA 角度 (趨勢強度)
        ma_short_change = (current_ma_short - ma_short.iloc[-5]) / ma_short.iloc[-5] * 100 if len(ma_short) >= 5 else 0
        ma_long_change = (current_ma_long - ma_long.iloc[-5]) / ma_long.iloc[-5] * 100 if len(ma_long) >= 5 else 0
        
        # 綜合信號
        if golden_cross or bullish_arrangement:
            signal = "強烈買入"
            action = "黃金交叉或多頭排列，建議買入"
        elif current_ma_short > current_ma_long and ma_short_change > 0:
            signal = "買入"
            action = "多頭趨勢持續，價格在均線上方"
        elif death_cross or bearish_arrangement:
            signal = "強烈賣出"
            action = "死亡交叉或空頭排列，建議賣出"
        elif current_ma_short < current_ma_long and ma_long_change < 0:
            signal = "賣出"
            action = "空頭趨勢持續，價格在均線下方"
        else:
            signal = "觀望"
            action = "無明確信號，建議觀望"
        
        return {
            "symbol": self.symbol,
            "current_price": round(current_price, 2),
            "ma": {
                "short": round(current_ma_short, 2),
                "long": round(current_ma_long, 2),
                "short_period": short_period,
                "long_period": long_period
            },
            "multi_ma": {
                "ma5": round(ma_5, 2) if pd.notna(ma_5) else None,
                "ma10": round(ma_10, 2) if pd.notna(ma_10) else None,
                "ma20": round(ma_20, 2) if pd.notna(ma_20) else None,
                "ma60": round(ma_60, 2) if pd.notna(ma_60) else None,
                "ma120": round(ma_120, 2) if pd.notna(ma_120) else None,
                "ma240": round(ma_240, 2) if pd.notna(ma_240) else None
            },
            "analysis": {
                "trend": trend,
                "price_position": price_position,
                "golden_cross": golden_cross,
                "death_cross": death_cross,
                "bullish_arrangement": bullish_arrangement,
                "bearish_arrangement": bearish_arrangement,
                "ma_angle_short": round(ma_short_change, 2),
                "ma_angle_long": round(ma_long_change, 2)
            },
            "signal": signal,
            "action": action,
            "recommendation": "BUY" if "買入" in signal else "SELL" if "賣出" in signal else "HOLD"
        }
    
    def get_ma_signal(self) -> Dict:
        """取得 MA 交易信號（快速接口）"""
        return self.calculate_ma()
    
    # ==================== MACD 策略 ====================
    
    def calculate_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """
        計算 MACD 指標
        
        Args:
            fast: 快線 EMA 週期 (預設 12)
            slow: 慢線 EMA 週期 (預設 26)
            signal: 訊號線週期 (預設 9)
        
        Returns:
            MACD 指標數據和信號
        """
        if self.df.empty or len(self.df) < slow + signal:
            return {"error": "數據不足無法計算 MACD"}
        
        close = self.df['Close']
        
        # 計算 EMA
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        
        # DIF (MACD 線) = 快線 - 慢線
        dif = ema_fast - ema_slow
        
        # DEA (訊號線) = DIF 的 EMA
        dea = dif.ewm(span=signal, adjust=False).mean()
        
        # MACD 柱狀圖 = (DIF - DEA) * 2
        macd_hist = (dif - dea) * 2
        
        current_dif = dif.iloc[-1]
        current_dea = dea.iloc[-1]
        current_hist = macd_hist.iloc[-1]
        
        prev_dif = dif.iloc[-2]
        prev_dea = dea.iloc[-2]
        
        # 判斷信號
        # 黃金交叉: DIF 從下往上穿越 DEA
        golden_cross = prev_dif <= prev_dea and current_dif > current_dea
        # 死亡交叉: DIF 從上往下穿越 DEA
        death_cross = prev_dif >= prev_dea and current_dif < current_dea
        
        # 零軸位置
        if current_dif > 0 and current_dea > 0:
            zero_line = "多方 (零軸之上)"
        elif current_dif < 0 and current_dea < 0:
            zero_line = "空方 (零軸之下)"
        else:
            zero_line = "整理區 (接近零軸)"
        
        # 柱狀圖動能
        prev_hist = macd_hist.iloc[-2]
        if current_hist > prev_hist:
            hist_momentum = "多方動能增強"
        elif current_hist < prev_hist:
            hist_momentum = "空方動能增強"
        else:
            hist_momentum = "動能持平"
        
        # 綜合信號
        if golden_cross and current_dif > 0:
            signal = "強烈買入"
            action = "黃金交叉 + 零軸之上，建議買入"
        elif golden_cross:
            signal = "買入"
            action = "黃金交叉出現，可考慮買入"
        elif death_cross and current_dif < 0:
            signal = "強烈賣出"
            action = "死亡交叉 + 零軸之下，建議賣出"
        elif death_cross:
            signal = "賣出"
            action = "死亡交叉出現，可考慮賣出"
        elif current_hist > 0 and current_hist > prev_hist:
            signal = "買入"
            action = "多方動能增強"
        elif current_hist < 0 and current_hist < prev_hist:
            signal = "賣出"
            action = "空方動能增強"
        else:
            signal = "觀望"
            action = "無明確信號，建議觀望"
        
        return {
            "symbol": self.symbol,
            "current_price": round(self.df['Close'].iloc[-1], 2),
            "macd": {
                "dif": round(current_dif, 4),
                "dea": round(current_dea, 4),
                "histogram": round(current_hist, 4),
                "fast": fast,
                "slow": slow,
                "signal_period": signal
            },
            "analysis": {
                "zero_line": zero_line,
                "histogram_momentum": hist_momentum,
                "crossover": {
                    "golden_cross": golden_cross,
                    "death_cross": death_cross
                }
            },
            "signal": signal,
            "action": action,
            "recommendation": "BUY" if "買入" in signal else "SELL" if "賣出" in signal else "HOLD"
        }
    
    def get_macd_signal(self) -> Dict:
        """取得 MACD 交易信號（快速接口）"""
        return self.calculate_macd()
    
    # ==================== KD (隨機指標) 策略 ====================
    
    def calculate_kd(self, n: int = 9, m1: int = 3, m2: int = 3, oversold: int = 20, overbought: int = 80) -> Dict:
        """
        計算 KD (隨機指標) 指標
        
        Args:
            n: RSV 週期 (預設 9)
            m1: K 值平滑週期 (預設 3)
            m2: D 值平滑週期 (預設 3)
            oversold: 超賣門檻 (預設 20)
            overbought: 超買門檻 (預設 80)
        
        Returns:
            KD 指標數據和信號
        """
        if self.df.empty or len(self.df) < n:
            return {"error": "數據不足無法計算 KD"}
        
        close = self.df['Close']
        high = self.df['High']
        low = self.df['Low']
        
        # 計算 RSV (Raw Stochastic Value)
        # RSV = (Close - Low_n) / (High_n - Low_n) * 100
        lowest_low = low.rolling(window=n).min()
        highest_high = high.rolling(window=n).max()
        
        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
        rsv = rsv.fillna(50)  # 處理除零情況
        
        # 計算 K 值 (RSV 的 m1 期 SMA)
        k_values = rsv.rolling(window=m1).mean()
        
        # 計算 D 值 (K 的 m2 期 SMA)
        d_values = k_values.rolling(window=m2).mean()
        
        current_k = k_values.iloc[-1]
        current_d = d_values.iloc[-1]
        prev_k = k_values.iloc[-2]
        prev_d = d_values.iloc[-2]
        
        # 計算 J 值 (3*K - 2*D)
        j_values = 3 * k_values - 2 * d_values
        current_j = j_values.iloc[-1]
        
        # 取得最近幾天的 K, D 值 (用於分析趨勢)
        k_history = k_values.tail(5).tolist()
        d_history = d_values.tail(5).tolist()
        
        # 判斷信號
        # 黃金交叉: K 從下往上穿越 D
        golden_cross = prev_k <= prev_d and current_k > current_d
        # 死亡交叉: K 從上往下穿越 D
        death_cross = prev_k >= prev_d and current_k < current_d
        
        # 區間判斷
        if current_k < oversold and current_d < oversold:
            zone = "超賣區"
            zone_signal = "可能反彈"
        elif current_k > overbought and current_d > overbought:
            zone = "超買區"
            zone_signal = "可能回調"
        elif current_k > current_d:
            zone = "多方區"
            zone_signal = "多頭趨勢"
        else:
            zone = "空方區"
            zone_signal = "空頭趨勢"
        
        # K、D 值變化趨勢
        k_slope = current_k - k_values.iloc[-3] if len(k_values) >= 3 else 0
        d_slope = current_d - d_values.iloc[-3] if len(d_values) >= 3 else 0
        
        # 綜合信號
        # 黃金交叉 + 超賣區 = 強烈買入
        if golden_cross and current_k < oversold:
            signal = "強烈買入"
            action = "KD 黃金交叉 + 超賣區，建議買入"
        # 單純黃金交叉 = 買入
        elif golden_cross:
            signal = "買入"
            action = "KD 黃金交叉，多方訊號"
        # 死亡交叉 + 超買區 = 強烈賣出
        elif death_cross and current_k > overbought:
            signal = "強烈賣出"
            action = "KD 死亡交叉 + 超買區，建議賣出"
        # 單純死亡交叉 = 賣出
        elif death_cross:
            signal = "賣出"
            action = "KD 死亡交叉，空方訊號"
        # K、D 都在超賣區 = 買入
        elif current_k < oversold and current_d < oversold:
            signal = "買入"
            action = "KD 進入超賣區，可能反彈"
        # K、D 都在超買區 = 賣出
        elif current_k > overbought and current_d > overbought:
            signal = "賣出"
            action = "KD 進入超買區，可能回調"
        # K > D 多頭排列 = 買入
        elif current_k > current_d:
            signal = "買入"
            action = "KD 多頭排列，多方趨勢"
        # K < D 空頭排列 = 賣出
        else:
            signal = "賣出"
            action = "KD 空頭排列，空方趨勢"
        
        return {
            "symbol": self.symbol,
            "current_price": round(self.df['Close'].iloc[-1], 2),
            "kd": {
                "k": round(current_k, 2),
                "d": round(current_d, 2),
                "j": round(current_j, 2),
                "n": n,
                "m1": m1,
                "m2": m2
            },
            "history": {
                "k": [round(k, 2) for k in k_history],
                "d": [round(d, 2) for d in d_history]
            },
            "analysis": {
                "zone": zone,
                "zone_signal": zone_signal,
                "golden_cross": golden_cross,
                "death_cross": death_cross,
                "k_slope": round(k_slope, 2),
                "d_slope": round(d_slope, 2)
            },
            "thresholds": {
                "oversold": oversold,
                "overbought": overbought
            },
            "signal": signal,
            "action": action,
            "recommendation": "BUY" if "買入" in signal else "SELL" if "賣出" in signal else "HOLD"
        }
    
    def get_kd_signal(self) -> Dict:
        """取得 KD 交易信號（快速接口）"""
        return self.calculate_kd()
    
    # ==================== SAR (拋物線轉向指標) 策略 ====================
    
    def calculate_sar(self, af_start: float = 0.02, af_max: float = 0.2, af_increment: float = 0.02) -> Dict:
        """
        計算 SAR (Parabolic Stop and Reverse) 指標
        
        Args:
            af_start: 初始加速因子 (預設 0.02)
            af_max: 最大加速因子 (預設 0.2)
            af_increment: 加速因子增量 (預設 0.02)
        
        Returns:
            SAR 指標數據和信號
        """
        if self.df.empty or len(self.df) < 30:
            return {"error": "數據不足無法計算 SAR"}
        
        high = self.df['High']
        low = self.df['Low']
        close = self.df['Close']
        
        # 初始化 SAR 陣列
        sar_values = [float(low.iloc[0])]
        trend = []  # 1 = uptrend, -1 = downtrend
        af_values = [af_start]  # 加速因子
        
        # 初始化：第一根 K 棒視為下跌趨勢
        ep = float(high.iloc[0])  # 極端價格 (Extreme Point)
        current_af = af_start
        
        for i in range(1, len(self.df)):
            current_high = float(high.iloc[i])
            current_low = float(low.iloc[i])
            
            # 計算 SAR
            prev_sar = sar_values[-1]
            sar = prev_sar + current_af * (ep - prev_sar)
            
            # 判斷趨勢
            if len(trend) > 0 and trend[-1] == -1:  # 上一根是下跌趨勢
                # 檢查是否反轉
                if current_high > ep:
                    # 反轉為上漲趨勢
                    trend.append(1)
                    ep = current_high
                    current_af = af_start
                    sar = ep  # SAR 跳到 EP
                else:
                    trend.append(-1)
                    if current_low < ep:
                        ep = current_low
                        current_af = min(current_af + af_increment, af_max)
            else:  # 上一根是上漲趨勢或第一根
                # 檢查是否反轉
                if len(trend) > 0 and trend[-1] == 1:
                    if current_low < sar:
                        # 反轉為下跌趨勢
                        trend.append(-1)
                        ep = current_low
                        current_af = af_start
                        sar = ep
                    else:
                        trend.append(1)
                        if current_high > ep:
                            ep = current_high
                            current_af = min(current_af + af_increment, af_max)
                else:
                    # 第一根，設為下跌趨勢
                    trend.append(-1)
            
            sar_values.append(sar)
            af_values.append(current_af)
        
        # 取得最新值
        current_sar = sar_values[-1]
        current_trend = trend[-1]
        current_af = af_values[-1]
        
        current_price = float(close.iloc[-1])
        
        # 判斷信號
        prev_trend_is_up = len(trend) >= 2 and trend[-2] == 1
        current_trend_is_up = current_trend == 1
        
        reversal_to_bullish = not prev_trend_is_up and current_trend_is_up
        reversal_to_bearish = prev_trend_is_up and not current_trend_is_up
        
        # 價格與 SAR 的關係
        if current_price > current_sar:
            price_vs_sar = "價格高於 SAR (多頭)"
        else:
            price_vs_sar = "價格低於 SAR (空頭)"
        
        # 計算 SAR 趨勢強度
        sar_dist = abs(current_price - current_sar) / current_price * 100
        
        # 綜合信號
        if reversal_to_bullish:
            signal = "強烈買入"
            action = "SAR 指標反轉向上，多頭趨勢確立，建議買入"
        elif reversal_to_bearish:
            signal = "強烈賣出"
            action = "SAR 指標反轉向下，空頭趨勢確立，建議賣出"
        elif current_trend == 1 and sar_dist > 2:
            signal = "買入"
            action = "多頭趨勢持續，價格遠高於 SAR"
        elif current_trend == -1 and sar_dist > 2:
            signal = "賣出"
            action = "空頭趨勢持續，價格遠低於 SAR"
        elif current_trend == 1:
            signal = "觀望偏多"
            action = "多頭趨勢，但價格接近 SAR，需觀察"
        elif current_trend == -1:
            signal = "觀望偏空"
            action = "空頭趨勢，但價格接近 SAR，需觀察"
        else:
            signal = "觀望"
            action = "無明確信號"
        
        # 取得歷史 SAR 值（最近5個）
        sar_history = sar_values[-5:]
        
        return {
            "symbol": self.symbol,
            "current_price": round(current_price, 2),
            "sar": {
                "value": round(current_sar, 4),
                "trend": "上漲" if current_trend == 1 else "下跌",
                "af": round(current_af, 4),
                "af_start": af_start,
                "af_max": af_max
            },
            "analysis": {
                "price_vs_sar": price_vs_sar,
                "reversal_to_bullish": reversal_to_bullish,
                "reversal_to_bearish": reversal_to_bearish,
                "sar_distance_percent": round(sar_dist, 2)
            },
            "history": {
                "sar": [round(s, 4) for s in sar_history]
            },
            "signal": signal,
            "action": action,
            "recommendation": "BUY" if "買入" in signal else "SELL" if "賣出" in signal else "HOLD"
        }
    
    def get_sar_signal(self) -> Dict:
        """取得 SAR 交易信號（快速接口）"""
        return self.calculate_sar()
    
    # ==================== ADX (Average Directional Index) 策略 ====================
    
    def calculate_adx(self, period: int = 14, adx_threshold: int = 25) -> Dict:
        """
        計算 ADX (Average Directional Index) 指標
        
        ADX 用於衡量趨勢強度:
        - ADX > 25: 強勢趨勢
        - ADX < 20: 趨勢不明
        
        +DI (Plus Directional Indicator): 上漲動能
        -DI (Minus Directional Indicator): 下跌動能
        
        Args:
            period: ADX 週期 (預設 14)
            adx_threshold: 趨勢強度門檻 (預設 25)
        
        Returns:
            ADX 指標數據和信號
        """
        if self.df.empty or len(self.df) < period * 2:
            return {"error": "數據不足無法計算 ADX"}
        
        high = self.df['High']
        low = self.df['Low']
        close = self.df['Close']
        
        # 計算 True Range (TR)
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 計算 +DM 和 -DM (Directional Movement)
        high_diff = high.diff()
        low_diff = -low.diff()
        
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        # 計算平滑後的 TR、+DM、-DM (使用 Wilder's Smoothing)
        atr = tr.rolling(window=period).mean()  # 簡化版 ATR
        plus_dm_smooth = plus_dm.rolling(window=period).mean()
        minus_dm_smooth = minus_dm.rolling(window=period).mean()
        
        # 計算 +DI 和 -DI
        plus_di = (plus_dm_smooth / atr) * 100
        minus_di = (minus_dm_smooth / atr) * 100
        
        # 計算 DX (Directional Index)
        di_sum = plus_di + minus_di
        di_diff = abs(plus_di - minus_di)
        dx = (di_diff / di_sum) * 100
        
        # 計算 ADX (DX 的平滑平均值)
        adx = dx.rolling(window=period).mean()
        
        # 取得當前值
        current_adx = adx.iloc[-1]
        current_plus_di = plus_di.iloc[-1]
        current_minus_di = minus_di.iloc[-1]
        
        prev_adx = adx.iloc[-2] if len(adx) >= 2 else current_adx
        prev_plus_di = plus_di.iloc[-2] if len(plus_di) >= 2 else current_plus_di
        prev_minus_di = minus_di.iloc[-2] if len(minus_di) >= 2 else current_minus_di
        
        # 計算歷史數據
        adx_history = adx.tail(5).tolist()
        plus_di_history = plus_di.tail(5).tolist()
        minus_di_history = minus_di.tail(5).tolist()
        
        # 趨勢強度判斷
        if current_adx > adx_threshold:
            trend_strength = "強勢趨勢"
        elif current_adx > 20:
            trend_strength = "中等趨勢"
        elif current_adx > 15:
            trend_strength = "弱勢趨勢"
        else:
            trend_strength = "趨勢不明"
        
        # +DI 與 -DI 交叉判斷
        golden_cross = prev_plus_di <= prev_minus_di and current_plus_di > current_minus_di
        death_cross = prev_plus_di >= prev_minus_di and current_plus_di < current_minus_di
        
        # 趨勢方向判斷
        if current_plus_di > current_minus_di and current_adx > adx_threshold:
            trend_direction = "多頭趨勢"
            direction_signal = "上漲動能較強"
        elif current_minus_di > current_plus_di and current_adx > adx_threshold:
            trend_direction = "空頭趨勢"
            direction_signal = "下跌動能較強"
        elif current_adx < adx_threshold:
            trend_direction = "橫盤整理"
            direction_signal = "趨勢不明顯"
        else:
            trend_direction = "觀望"
            direction_signal = "等待明確信號"
        
        # ADX 趨勢判斷 (上升代表趨勢正在增強)
        adx_rising = current_adx > prev_adx
        
        # 綜合信號
        # 強烈買入: ADX 上升 + +DI > -DI + ADX > 門檻
        if golden_cross and current_adx > adx_threshold and adx_rising:
            signal = "強烈買入"
            action = "ADX 上升 + DI 黃金交叉，強勢多頭趨勢形成"
        # 買入: +DI > -DI 且 ADX > 門檻
        elif current_plus_di > current_minus_di and current_adx > adx_threshold:
            signal = "買入"
            action = "多頭趨勢明確，建議買入"
        # 強烈賣出: ADX 上升 + -DI > +DI + ADX > 門檻
        elif death_cross and current_adx > adx_threshold and adx_rising:
            signal = "強烈賣出"
            action = "ADX 上升 + DI 死亡交叉，強勢空頭趨勢形成"
        # 賣出: -DI > +DI 且 ADX > 門檻
        elif current_minus_di > current_plus_di and current_adx > adx_threshold:
            signal = "賣出"
            action = "空頭趨勢明確，建議賣出"
        # ADX 從低點上升可能是趨勢開始
        elif current_adx > adx_threshold and adx_rising:
            signal = "趨勢開始"
            action = f"ADX 上升，趨勢正在增強 ({trend_strength})"
        # ADX < 門檻 = 觀望
        else:
            signal = "觀望"
            action = "趨勢不明顯，建議觀望等待明確信號"
        
        return {
            "symbol": self.symbol,
            "current_price": round(self.df['Close'].iloc[-1], 2),
            "adx": {
                "adx": round(current_adx, 2),
                "plus_di": round(current_plus_di, 2),
                "minus_di": round(current_minus_di, 2),
                "period": period,
                "threshold": adx_threshold
            },
            "history": {
                "adx": [round(a, 2) for a in adx_history],
                "plus_di": [round(p, 2) for p in plus_di_history],
                "minus_di": [round(m, 2) for m in minus_di_history]
            },
            "analysis": {
                "trend_strength": trend_strength,
                "trend_direction": trend_direction,
                "direction_signal": direction_signal,
                "adx_rising": adx_rising,
                "crossover": {
                    "golden_cross": golden_cross,
                    "death_cross": death_cross
                }
            },
            "signal": signal,
            "action": action,
            "recommendation": "BUY" if "買入" in signal else "SELL" if "賣出" in signal else "HOLD"
        }
    
    def get_adx_signal(self) -> Dict:
        """取得 ADX 交易信號（快速接口）"""
        return self.calculate_adx()
    
    # ==================== RSI (相對強弱指標) 策略 ====================
    
    def calculate_rsi(self, period: int = 14, oversold: int = 30, overbought: int = 70) -> Dict:
        """
        計算 RSI (相對強弱指標)
        
        Args:
            period: RSI 週期 (預設 14)
            oversold: 超賣門檻 (預設 30)
            overbought: 超買門檻 (預設 70)
        
        Returns:
            RSI 指標數據和信號
        """
        if self.df.empty or len(self.df) < period:
            return {"error": "數據不足無法計算 RSI"}
        
        close = self.df['Close']
        
        # 計算價格變化
        delta = close.diff()
        
        # 分離上漲和下跌
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        # 計算平均漲跌 (使用 EMA)
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()
        
        # 計算 RS 和 RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2] if len(rsi) >= 2 else current_rsi
        
        # 取得 RSI 歷史數據
        rsi_history = rsi.tail(10).tolist()
        
        # 計算 RSI 移動平均 (信號線)
        rsi_ma = rsi.rolling(window=period).mean()
        current_rsi_ma = rsi_ma.iloc[-1]
        
        # 判斷趨勢
        rsi_trend = "上升" if current_rsi > prev_rsi else "下降" if current_rsi < prev_rsi else "持平"
        
        # 區間判斷
        if current_rsi < oversold:
            zone = "超賣區"
            zone_signal = "可能反彈，建議買入"
        elif current_rsi > overbought:
            zone = "超買區"
            zone_signal = "可能回調，建議賣出"
        elif current_rsi > 50:
            zone = "多方區"
            zone_signal = "多頭趨勢"
        else:
            zone = "空方區"
            zone_signal = "空頭趨勢"
        
        # RSI 背離檢測 (價格創新高但 RSI 沒有)
        if len(self.df) >= period * 2:
            recent_high_idx = self.df['High'].iloc[-period:].idxmax()
            price_high = self.df.loc[recent_high_idx, 'High']
            current_price = close.iloc[-1]
            
            rsi_at_price_high = rsi.loc[recent_high_idx]
            
            # 價格創新高但 RSI 沒有 = 頂背離
            if current_price > price_high and current_rsi < rsi_at_price_high:
                divergence = "頂背離 (Bearish Divergence)"
                divergence_signal = "可能反轉下跌"
            # 價格創新低但 RSI 沒有 = 底背離
            elif current_price < price_high and current_rsi > rsi_at_price_high:
                divergence = "底背離 (Bullish Divergence)"
                divergence_signal = "可能反彈上漲"
            else:
                divergence = None
                divergence_signal = None
        else:
            divergence = None
            divergence_signal = None
        
        # RSI 變化率
        rsi_change = current_rsi - prev_rsi
        
        # 綜合信號
        if divergence == "底背離 (Bullish Divergence)":
            signal = "強烈買入"
            action = "RSI 底背離 + 超賣區，反彈機會大"
        elif current_rsi < oversold:
            signal = "買入"
            action = "RSI 進入超賣區，可能反彈"
        elif divergence == "頂背離 (Bearish Divergence)":
            signal = "強烈賣出"
            action = "RSI 頂背離 + 超買區，回調風險大"
        elif current_rsi > overbought:
            signal = "賣出"
            action = "RSI 進入超買區，可能回調"
        elif current_rsi > 50 and rsi_trend == "上升":
            signal = "買入"
            action = "RSI 在多方區且持續上升，多頭趨勢持續"
        elif current_rsi < 50 and rsi_trend == "下降":
            signal = "賣出"
            action = "RSI 在空方區且持續下降，空頭趨勢持續"
        elif current_rsi > 50:
            signal = "觀望"
            action = "RSI 在多方區但無明確趨勢"
        else:
            signal = "觀望"
            action = "RSI 在空方區但無明確趨勢"
        
        return {
            "symbol": self.symbol,
            "current_price": round(self.df['Close'].iloc[-1], 2),
            "rsi": {
                "value": round(current_rsi, 2),
                "period": period,
                "signal_line": round(current_rsi_ma, 2) if pd.notna(current_rsi_ma) else None,
                "change": round(rsi_change, 2)
            },
            "history": {
                "rsi": [round(r, 2) for r in rsi_history]
            },
            "analysis": {
                "zone": zone,
                "zone_signal": zone_signal,
                "trend": rsi_trend,
                "divergence": divergence,
                "divergence_signal": divergence_signal
            },
            "thresholds": {
                "oversold": oversold,
                "overbought": overbought,
                "neutral": 50
            },
            "signal": signal,
            "action": action,
            "recommendation": "BUY" if "買入" in signal else "SELL" if "賣出" in signal else "HOLD"
        }
    
    def get_rsi_signal(self) -> Dict:
        """取得 RSI 交易信號（快速接口）"""
        return self.calculate_rsi()
    
    # ==================== 風險評估 ====================
    
    def get_risk_assessment(self, position_size: float = 10000) -> Dict:
        """
        風險評估
        
        Args:
            position_size: 部位大小 (金額)
        """
        if self.df.empty:
            return {"error": "No data"}
        
        current_price = self.df['Close'].iloc[-1]
        returns = self.df['Close'].pct_change().dropna()
        
        # 1. 波動率風險
        volatility = returns.std() * np.sqrt(252) * 100
        volatility_risk = "high" if volatility > 30 else "medium" if volatility > 15 else "low"
        
        # 2. 價格位置風險
        current_ma20 = self.df['Close'].rolling(20).mean().iloc[-1]
        price_vs_ma20 = (current_price - current_ma20) / current_ma20 * 100
        
        if price_vs_ma20 > 10:
            price_position_risk = "high"
            price_position_note = "價格遠高於 MA20，可能回調"
        elif price_vs_ma20 < -10:
            price_position_risk = "medium"
            price_position_note = "價格低於 MA20，可能反彈"
        else:
            price_position_risk = "low"
            price_position_note = "價格在合理區間"
        
        # 3. 流動性風險
        avg_volume = self.df['Volume'].tail(20).mean()
        daily_value = current_price * avg_volume  # 日均成交金額
        
        if daily_value > 100000000:  # 10億
            liquidity_risk = "low"
        elif daily_value > 10000000:  # 1000萬
            liquidity_risk = "medium"
        else:
            liquidity_risk = "high"
        
        # 4. 趨勢風險
        ma5 = self.df['Close'].rolling(5).mean().iloc[-1]
        ma20 = self.df['Close'].rolling(20).mean().iloc[-1]
        
        if ma5 > ma20:
            trend_risk = "low"
            trend_note = "多頭趨勢"
        else:
            trend_risk = "medium"
            trend_note = "空頭趨勢"
        
        # 5. 計算建議停損
        atr = self._calculate_atr()
        stop_loss_price = current_price - (atr * 2)  # 2 ATR 停損
        risk_per_share = current_price - stop_loss_price
        risk_amount = risk_per_share * (position_size / current_price)
        risk_percentage = (risk_amount / position_size) * 100
        
        # 6. 風險評分 (0-100)
        risk_score = 0
        risk_factors = []
        
        if volatility_risk == "high":
            risk_score += 30
            risk_factors.append("高波動性")
        elif volatility_risk == "medium":
            risk_score += 15
        
        if price_position_risk == "high":
            risk_score += 25
            risk_factors.append("價格偏離均線")
        
        if liquidity_risk == "high":
            risk_score += 25
            risk_factors.append("流動性低")
        elif liquidity_risk == "medium":
            risk_score += 10
        
        if trend_risk == "medium":
            risk_score += 20
            risk_factors.append("趨勢不明")
        
        risk_level = "HIGH" if risk_score > 60 else "MEDIUM" if risk_score > 30 else "LOW"
        
        return {
            "symbol": self.symbol,
            "current_price": round(current_price, 2),
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "position_size_recommendation": {
                "max_position": int(position_size * (100 - risk_score) / 100),
                "suggested_position": int(position_size * (80 - risk_score) / 100),
            },
            "stop_loss": {
                "price": round(stop_loss_price, 2),
                "percentage": round(risk_percentage, 2),
                "atr_multiplier": 2
            },
            "risk_metrics": {
                "volatility": {
                    "value": round(volatility, 2),
                    "risk": volatility_risk
                },
                "price_position": {
                    "vs_ma20": round(price_vs_ma20, 2),
                    "risk": price_position_risk,
                    "note": price_position_note
                },
                "liquidity": {
                    "daily_value": round(daily_value, 0),
                    "risk": liquidity_risk
                },
                "trend": {
                    "status": trend_note,
                    "risk": trend_risk
                }
            },
            "recommendation": "謹慎進場" if risk_level == "HIGH" else "可以考慮" if risk_level == "MEDIUM" else "適合進場"
        }
    
    def _calculate_atr(self, period: int = 14) -> float:
        """計算 ATR"""
        high = self.df['High']
        low = self.df['Low']
        close = self.df['Close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        
        return atr if pd.notna(atr) else 0
    
    # ==================== 最佳標的推薦 ====================
    
    @staticmethod
    def find_best_targets(symbols: List[str], criteria: str = "all") -> List[Dict]:
        """
        找出最佳標的
        
        Args:
            symbols: 股票代碼列表
            criteria: 篩選條件
                - "momentum": 動能篩選
                - "value": 價值篩選
                - "growth": 成長篩選
                - "all": 综合篩選
        """
        results = []
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="3mo")
                
                if df.empty or len(df) < 30:
                    continue
                
                current_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(20).mean().iloc[-1]
                
                # 動能指標
                returns_1m = (df['Close'].iloc[-1] - df['Close'].iloc[-21]) / df['Close'].iloc[-21] * 100 if len(df) > 20 else 0
                returns_3m = (df['Close'].iloc[-1] - df['Close'].iloc[-63]) / df['Close'].iloc[-63] * 100 if len(df) > 60 else returns_1m
                
                # 趨勢判斷
                above_ma20 = current_price > ma20
                
                # 波動性
                volatility = df['Close'].pct_change().std() * np.sqrt(252) * 100
                
                # RSI
                delta = df['Close'].diff()
                gain = delta.where(delta > 0, 0)
                loss = (-delta).where(delta < 0, 0)
                avg_gain = gain.rolling(14).mean()
                avg_loss = loss.rolling(14).mean()
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[-1]
                
                # 評分
                score = 0
                if above_ma20:
                    score += 20
                if returns_1m > 0:
                    score += 15
                if returns_3m > 0:
                    score += 15
                if current_rsi < 70:
                    score += 10
                if volatility < 30:
                    score += 10
                
                results.append({
                    "symbol": symbol,
                    "price": round(current_price, 2),
                    "returns_1m": round(returns_1m, 2),
                    "returns_3m": round(returns_3m, 2),
                    "above_ma20": bool(above_ma20),
                    "rsi": round(float(current_rsi), 2),
                    "volatility": round(float(volatility), 2),
                    "score": int(score),
                    "recommendation": "推薦" if score >= 50 else "觀望"
                })
                
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                continue
        
        # 排序
        results = sorted(results, key=lambda x: x['score'], reverse=True)
        
        return results


# ==================== 主程式 ====================

if __name__ == "__main__":
    # 測試
    print("=" * 70)
    print("即時交易分析測試")
    print("=" * 70)
    
    # 支撐/壓力測試
    print("\n📊 支撐位/壓力位測試 (2330.TW):")
    analysis = RealtimeAnalysis("2330.TW")
    sr = analysis.calculate_support_resistance()
    print(f"  目前價格: {sr['current_price']}")
    print(f"  支撐位: {sr['supports'][:3]}")
    print(f"  壓力位: {sr['resistances'][:3]}")
    
    # 進場時間
    print("\n⏰ 進場時間建議:")
    entry = analysis.get_entry_timing()
    print(f"  建議: {entry['recommendation']} - {entry['action']}")
    print(f"  原因: {entry['reason']}")
    
    # 風險評估
    print("\n⚠️ 風險評估:")
    risk = analysis.get_risk_assessment(position_size=100000)
    print(f"  風險等級: {risk['risk_level']}")
    print(f"  風險分數: {risk['risk_score']}")
    print(f"  建議停損: {risk['stop_loss']['price']}")
    
    # 最佳標的
    print("\n🎯 最佳標的篩選:")
    targets = RealtimeAnalysis.find_best_targets(["2330.TW", "2317.TW", "2454.TW", "0050.TW", "AAPL", "TSLA"])
    for t in targets[:3]:
        print(f"  {t['symbol']}: {t['price']} | Score: {t['score']} | {t['recommendation']}")
