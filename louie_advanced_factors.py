#!/usr/bin/env python3
"""
Louie 量化因子庫 - 進階量化因子研究
涵蓋：動量、波動率、成交量、趨勢、震盪指標等多維度因子
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Tuple

# ============================================================
# 價格/趨勢因子
# ============================================================

def factor_bollinger_position(df: pd.DataFrame, period: int = 20, num_std: float = 2.0) -> pd.Series:
    """
    波林格帶位置
    價格在布林帶中的相對位置，低於下軌為超賣，高於上軌為超買
    """
    ma = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    upper_band = ma + (std * num_std)
    lower_band = ma - (std * num_std)
    
    position = (df['close'] - lower_band) / (upper_band - lower_band)
    return position.fillna(0.5)


def factor_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    平均真實波幅 (Average True Range)
    衡量市場波動性
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    # 正規化為價格百分比
    atr_pct = (atr / close) * 100
    return atr_pct


def factor_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    商品通道指數 (Commodity Channel Index)
    衡量價格偏離統計均值程度
    """
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    
    cci = (tp - sma) / (0.015 * mad)
    return cci / 100  # 正規化


def factor_williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Williams %R
    類似 KD 指標的震盪指標，-100 到 0
    """
    highest_high = df['high'].rolling(window=period).max()
    lowest_low = df['low'].rolling(window=period).min()
    
    wr = -100 * (highest_high - df['close']) / (highest_high - lowest_low)
    return (wr + 100) / 100  # 正規化到 0-1


def factor_roc(df: pd.DataFrame, period: int = 12) -> pd.Series:
    """
    價格變動率 (Rate of Change)
    衡量價格變動速度
    """
    roc = ((df['close'] - df['close'].shift(period)) / df['close'].shift(period)) * 100
    # 使用 tanh 限制範圍
    return np.tanh(roc / 10)


def factor_keltner_position(df: pd.DataFrame, period: int = 20, atr_multiplier: float = 2.0) -> pd.Series:
    """
    凱勒通道位置
    基於 ATR 的趨勢通道
    """
    ma = df['close'].ewm(span=period).mean()
    atr = factor_atr(df, period)
    
    upper = ma + (atr * atr_multiplier)
    lower = ma - (atr * atr_multiplier)
    
    position = (df['close'] - lower) / (upper - lower)
    return position.fillna(0.5)


# ============================================================
# 成交量因子
# ============================================================

def factor_obv(df: pd.DataFrame) -> pd.Series:
    """
    能量潮 (On-Balance Volume)
    累積成交量，判斷資金流向
    """
    obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
    
    # 正規化
    obv_ma = obv.rolling(20).mean()
    return np.tanh((obv - obv_ma) / obv_ma.abs())


def factor_vpt(df: pd.DataFrame) -> pd.Series:
    """
    成交量價格趨勢 (Volume Price Trend)
    結合價格變動的成交量指標
    """
    price_change = df['close'].pct_change()
    vpt = (price_change * df['volume']).fillna(0).cumsum()
    
    # 正規化
    vpt_ma = vpt.rolling(20).mean()
    return np.tanh((vpt - vpt_ma) / 1000000)


def factor_mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    貨幣流量指數 (Money Flow Index)
    結合價量的 RSI
    """
    tp = (df['high'] + df['low'] + df['close']) / 3
    raw_money_flow = tp * df['volume']
    
    money_flow_sign = np.where(tp > tp.shift(1), 1, -1)
    signed_money_flow = raw_money_flow * money_flow_sign
    
    positive_flow = signed_money_flow.where(signed_money_flow > 0, 0).rolling(window=period).sum()
    negative_flow = signed_money_flow.where(signed_money_flow < 0, 0).rolling(window=period).sum()
    
    mfi = 100 - (100 / (1 + positive_flow / negative_flow))
    
    # 反轉: 高 MFI 可能意味著超買，低 MFI 超賣
    return (50 - mfi) / 50


def factor_volume_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    成交量比率
    當日成交量相對於平均成交量的比率
    """
    vol_ma = df['volume'].rolling(window=period).mean()
    ratio = df['volume'] / vol_ma
    
    # 使用 tanh 限制範圍
    return np.tanh((ratio - 1) * 2)


def factor_accumulation_distribution(df: pd.DataFrame) -> pd.Series:
    """
    累積/分配線
    判斷資金是否持續流入
    """
    clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
    clv = clv.fillna(0)
    
    ad_line = (clv * df['volume']).cumsum()
    
    # 正規化
    ad_ma = ad_line.rolling(20).mean()
    return np.tanh((ad_line - ad_ma) / ad_line.abs().replace(0, 1))


# ============================================================
# 動量因子
# ============================================================

def factor_stochastic_rsi(df: pd.DataFrame(), rsi_period: int = 14, k_period: int = 3, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    隨機 RSI (Stochastic RSI)
    RSI 的隨機指標，加強版的 RSI
    """
    rsi = df['close'].apply(lambda x: 0.5)  #  placeholder, 需要 RSI 函數
    
    # 計算 RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).ewm(span=rsi_period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(span=rsi_period, adjust=False).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Stochastic of RSI
    rsi_min = rsi.rolling(window=rsi_period).min()
    rsi_max = rsi.rolling(window=rsi_period).max()
    
    stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min)
    stoch_rsi = stoch_rsi.fillna(0.5)
    
    # K 和 D 線
    k = stoch_rsi.rolling(window=k_period).mean()
    d = k.rolling(window=d_period).mean()
    
    return k, d


def factor_ultimate_oscillator(df: pd.DataFrame(), period1: int = 7, period2: int = 14, period3: int = 28) -> pd.Series:
    """
    終極震盪指標 (Ultimate Oscillator)
    多時間框架震盪指標，減少假信號
    """
    # 買賣力
    bp = df['close'] - pd.concat([df['low'], df['close'].shift(1)], axis=1).min(axis=1)
    
    # 真正的範圍
    tr = pd.concat([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ], axis=1).max(axis=1)
    
    # 計算三個週期的 Average
    avg1 = bp.rolling(period1).sum() / tr.rolling(period1).sum()
    avg2 = bp.rolling(period2).sum() / tr.rolling(period2).sum()
    avg3 = bp.rolling(period3).sum() / tr.rolling(period3).sum()
    
    # 終極振盪器
    uo = 100 * ((4 * avg1) + (2 * avg2) + avg3) / (4 + 2 + 1)
    
    return (uo - 50) / 50  # 正規化到 -1 到 1


def factor_trix(df: pd.DataFrame, period: int = 15) -> pd.Series:
    """
    TRIX (Triple Exponential Average)
    三重指數平均，過濾市場噪音
    """
    ema1 = df['close'].ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()
    
    trix = ema3.pct_change() * 100
    
    return np.tanh(trix / 5)


def factor_mass_index(df: pd.DataFrame, fast_period: int = 9, slow_period: int = 25) -> pd.Series:
    """
    大眾指數 (Mass Index)
    識別趨勢反轉
    """
    hl = df['high'] - df['low']
    ema1 = hl.ewm(span=fast_period, adjust=False).mean()
    ema2 = ema1.ewm(span=fast_period, adjust=False).mean()
    
    mass = ema1 / ema2
    
    mass_index = mass.rolling(slow_period).sum()
    
    # 反轉: 指數 > 27 可能預示趨勢反轉
    return (27 - mass_index) / 10


# ============================================================
# 波動率因子
# ============================================================

def factor_historical_volatility(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    歷史波動率
    衡量價格變動的標準差
    """
    returns = df['close'].pct_change()
    hv = returns.rolling(window=period).std() * np.sqrt(252) * 100
    
    # 反轉: 低波動率通常對應穩定上漲
    return np.tanh(-hv / 20)


def factor_price_volatility(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    價格波動率
    高低價範圍的波動
    """
    price_range = (df['high'] - df['low']) / df['close']
    pv = price_range.rolling(window=period).mean() * 100
    
    return np.tanh(-pv / 5)


def factor_donchian_breakout(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    唐奇安通道突破
    價格突破通道時產生信號
    """
    upper = df['high'].rolling(window=period).max()
    lower = df['low'].rolling(window=period).min()
    
    # 價格在通道中的位置
    position = (df['close'] - lower) / (upper - lower)
    position = position.fillna(0.5)
    
    # 突破信號
    breakout = np.where(df['close'] > upper.shift(1), 1,
               np.where(df['close'] < lower.shift(1), -1, 0))
    
    return pd.Series(breakout, index=df.index).fillna(0) * 0.5 + position * 0.5


# ============================================================
# 趨勢因子
# ============================================================

def factor_ichimoku(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    一目均衡表 (Ichimoku Cloud)
    日本經典趨勢指標
    """
    nine_period_high = df['high'].rolling(window=9).max()
    nine_period_low = df['low'].rolling(window=9).min()
    
    tenkan_sen = (nine_period_high + nine_period_low) / 2
    
    twenty_period_high = df['high'].rolling(window=20).max()
    twenty_period_low = df['low'].rolling(window=20).min()
    
    kijun_sen = (twenty_period_high + twenty_period_low) / 2
    
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
    
    fifty_period_high = df['high'].rolling(window=52).max()
    fifty_period_low = df['low'].rolling(window=52).min()
    
    senkou_span_b = ((fifty_period_high + fifty_period_low) / 2).shift(26)
    
    chikou_span = df['close'].shift(-26)
    
    # 雲帶信號
    cloud = senkou_span_a - senkou_span_b
    
    return {
        'tenkan': (tenkan_sen - df['close']) / df['close'],
        'kijun': (kijun_sen - df['close']) / df['close'],
        'cloud': np.tanh(cloud / df['close']),
        'chikou': (chikou_span - df['close']) / df['close']
    }


def factor_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """
    超級趨勢指標
    基於 ATR 的趨勢跟蹤指標
    """
    atr = factor_atr(df, period)
    
    hl_avg = (df['high'] + df['low']) / 2
    
    upper = hl_avg + (multiplier * atr)
    lower = hl_avg - (multiplier * atr)
    
    # 計算趨勢方向
    direction = pd.Series(1, index=df.index)
    
    for i in range(1, len(df)):
        if df['close'].iloc[i] > upper.iloc[i-1]:
            direction.iloc[i] = 1
        elif df['close'].iloc[i] < lower.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]
        
        # 更新上下軌
        if direction.iloc[i] == 1:
            upper.iloc[i] = min(upper.iloc[i], upper.iloc[i-1])
        else:
            lower.iloc[i] = max(lower.iloc[i], lower.iloc[i-1])
    
    return direction, (df['close'] - lower) / (upper - lower)


# ============================================================
# 複合因子策略
# ============================================================

class LouieMultiFactorStrategy:
    """
    Louie 多因子策略框架
    整合多種因子，自動計算權重
    """
    
    def __init__(self):
        # 因子註冊表
        self.factors: Dict[str, Callable] = {
            # 價格/趨勢因子
            'bollinger_position': factor_bollinger_position,
            'atr': factor_atr,
            'cci': factor_cci,
            'williams_r': factor_williams_r,
            'roc': factor_roc,
            'keltner_position': factor_keltner_position,
            
            # 成交量因子
            'obv': factor_obv,
            'vpt': factor_vpt,
            'mfi': factor_mfi,
            'volume_ratio': factor_volume_ratio,
            'a_d_line': factor_accumulation_distribution,
            
            # 動量因子
            'trix': factor_trix,
            'mass_index': factor_mass_index,
            
            # 波動率因子
            'historical_volatility': factor_historical_volatility,
            'price_volatility': factor_price_volatility,
            'donchian_breakout': factor_donchian_breakout,
        }
        
        # 預設因子組合 (適用於所有股票)
        self.default_factors = {
            # 趨勢因子 (權重較高)
            'bollinger_position': 0.15,
            'roc': 0.12,
            'atr': 0.08,
            
            # 動量因子
            'trix': 0.12,
            'williams_r': 0.10,
            'cci': 0.08,
            
            # 成交量因子
            'volume_ratio': 0.10,
            'obv': 0.08,
            'mfi': 0.07,
            
            # 波動率因子
            'historical_volatility': 0.05,
            'donchian_breakout': 0.05,
        }
        
        # 正規化權重
        self._normalize_weights()
    
    def _normalize_weights(self):
        total = sum(self.default_factors.values())
        self.default_factors = {k: v/total for k, v in self.default_factors.items()}
    
    def add_factor(self, name: str, func: Callable, weight: float = 0.1):
        """添加自定義因子"""
        self.factors[name] = func
        self.default_factors[name] = weight
        self._normalize_weights()
    
    def calculate_all_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算所有啟用的因子"""
        result = df.copy()
        
        for factor_name in self.default_factors.keys():
            if factor_name in self.factors:
                try:
                    result[factor_name] = self.factors[factor_name](df)
                except Exception as e:
                    print(f"計算因子 {factor_name} 失敗: {e}")
                    result[factor_name] = 0
        
        return result
    
    def calculate_composite_score(self, df: pd.DataFrame) -> pd.Series:
        """計算複合得分"""
        factors_df = self.calculate_all_factors(df)
        
        composite = pd.Series(0, index=df.index)
        
        for factor_name, weight in self.default_factors.items():
            if factor_name in factors_df.columns:
                signal = factors_df[factor_name].fillna(0)
                composite += signal * weight
        
        return composite
    
    def generate_signals(self, df: pd.DataFrame, buy_threshold: float = 0.3, 
                         sell_threshold: float = -0.3) -> pd.Series:
        """生成交易信號"""
        score = self.calculate_composite_score(df)
        
        signals = pd.Series(0, index=df.index)
        signals[score > buy_threshold] = 1    # 買入
        signals[score < sell_threshold] = -1  # 賣出
        
        return signals


# ============================================================
# 預設策略參數 (適用於所有股票)
# ============================================================

UNIVERSAL_STRATEGY_PARAMS = {
    # 風格: 保守型
    'conservative': {
        'score_threshold': 70,
        'stop_loss': 0.05,
        'take_profit': 0.10,
        'holding_days': 30,
        'factors': {
            'bollinger_position': 0.20,
            'atr': 0.15,
            'roc': 0.15,
            'volume_ratio': 0.15,
            'obv': 0.15,
            'williams_r': 0.10,
            'cci': 0.10,
        }
    },
    
    # 風格: 平衡型
    'balanced': {
        'score_threshold': 65,
        'stop_loss': 0.08,
        'take_profit': 0.15,
        'holding_days': 30,
        'factors': {
            'bollinger_position': 0.15,
            'roc': 0.12,
            'atr': 0.10,
            'trix': 0.12,
            'volume_ratio': 0.10,
            'obv': 0.08,
            'mfi': 0.08,
            'williams_r': 0.10,
            'cci': 0.08,
            'historical_volatility': 0.07,
        }
    },
    
    # 風格: 激進型
    'aggressive': {
        'score_threshold': 55,
        'stop_loss': 0.10,
        'take_profit': 0.20,
        'holding_days': 20,
        'factors': {
            'bollinger_position': 0.12,
            'roc': 0.15,
            'trix': 0.15,
            'cci': 0.12,
            'williams_r': 0.12,
            'volume_ratio': 0.10,
            'mfi': 0.10,
            'donchian_breakout': 0.09,
            'atr': 0.05,
        }
    },
}


# ============================================================
# 工廠函數
# ============================================================

def get_strategy_params(risk_tolerance: str = 'balanced') -> Dict:
    """
    取得策略參數
    
    Args:
        risk_tolerance: 'conservative', 'balanced', 或 'aggressive'
    
    Returns:
        Dict: 策略參數
    """
    return UNIVERSAL_STRATEGY_PARAMS.get(risk_tolerance, UNIVERSAL_STRATEGY_PARAMS['balanced'])


def create_custom_strategy(factor_weights: Dict[str, float], 
                           score_threshold: float = 65,
                           stop_loss: float = 0.08,
                           take_profit: float = 0.15,
                           holding_days: int = 30) -> Dict:
    """
    建立自定義策略
    """
    total = sum(factor_weights.values())
    normalized = {k: v/total for k, v in factor_weights.items()}
    
    return {
        'score_threshold': score_threshold,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'holding_days': holding_days,
        'factors': normalized
    }


if __name__ == '__main__':
    import yfinance as yf
    
    print("=" * 60)
    print("Louie 量化因子庫測試")
    print("=" * 60)
    
    # 測試股票
    symbol = "2330.TW"
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1y")
    
    if df is not None and len(df) > 60:
        df.columns = [col.lower() for col in df.columns]
        
        strategy = LouieMultiFactorStrategy()
        
        print(f"\n📊 計算 {symbol} 的因子...")
        factors_df = strategy.calculate_all_factors(df)
        
        print("\n最新因子值:")
        for col in list(strategy.default_factors.keys())[-10:]:
            if col in factors_df.columns:
                val = factors_df[col].iloc[-1]
                print(f"  {col}: {val:.4f}")
        
        print("\n複合得分:", strategy.calculate_composite_score(df).iloc[-1])
        print("交易信號:", strategy.generate_signals(df).iloc[-1])
        
        print("\n可用策略參數:")
        for style, params in UNIVERSAL_STRATEGY_PARAMS.items():
            print(f"\n{style.upper()}:")
            print(f"  閾值: {params['score_threshold']}")
            print(f"  停損: {params['stop_loss']}")
            print(f"  止盈: {params['take_profit']}")
            print(f"  持有天數: {params['holding_days']}")
    else:
        print("無法獲取股票數據")
