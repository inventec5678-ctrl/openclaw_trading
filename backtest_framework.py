#!/usr/bin/env python3
"""
簡單的回測框架 - MA 和 RSI 策略
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime

# 嘗試導入 yfinance，如果沒有則使用模擬數據
try:
    import yfinance as yf
    USE_YFINANCE = True
except ImportError:
    USE_YFINANCE = False
    print("yfinance 未安裝，將使用模擬數據")


def get_stock_data(symbol, period="1y"):
    """獲取股票數據"""
    if USE_YFINANCE:
        try:
            stock = yf.Ticker(symbol)
            df = stock.history(period=period)
            df = df.reset_index()
            df.columns = [col.lower() if col != 'Date' else 'date' for col in df.columns]
            return df
        except Exception as e:
            print(f"獲取數據失敗: {e}")
            return None
    else:
        # 生成模擬數據
        dates = pd.date_range(start='2024-01-01', end='2025-01-01', freq='D')
        np.random.seed(42)
        price = 100
        prices = []
        for _ in range(len(dates)):
            price = price * (1 + np.random.randn() * 0.02)
            prices.append(price)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': [p * 1.02 for p in prices],
            'low': [p * 0.98 for p in prices],
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        })
        return df


def calculate_ma(df, period=20):
    """計算移動平均線"""
    return df['close'].rolling(window=period).mean()


def calculate_rsi(df, period=14):
    """計算 RSI"""
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


class Backtester:
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position = 0
        self.trades = []
        self.portfolio_values = []
    
    def buy(self, date, price, shares=None):
        """買入"""
        if shares is None:
            shares = self.cash // price
        
        cost = shares * price
        if cost <= self.cash:
            self.cash -= cost
            self.position += shares
            self.trades.append({
                'date': date,
                'action': 'BUY',
                'price': price,
                'shares': shares,
                'cost': cost
            })
            return True
        return False
    
    def sell(self, date, price, shares=None):
        """賣出"""
        if shares is None:
            shares = self.position
        
        if shares <= self.position:
            revenue = shares * price
            self.cash += revenue
            self.position -= shares
            self.trades.append({
                'date': date,
                'action': 'SELL',
                'price': price,
                'shares': shares,
                'revenue': revenue
            })
            return True
        return False
    
    def get_portfolio_value(self, price):
        """計算投資組合價值"""
        return self.cash + self.position * price
    
    def run_ma_strategy(self, df, short_ma=10, long_ma=30):
        """MA 策略: 短MA上穿長MA買入，下穿賣出"""
        print(f"\n{'='*50}")
        print(f"執行 MA 策略 (短MA={short_ma}, 長MA={long_ma})")
        print(f"{'='*50}")
        
        # 重新初始化
        self.__init__(self.initial_capital)
        
        df = df.copy()
        df['ma_short'] = calculate_ma(df, short_ma)
        df['ma_long'] = calculate_ma(df, long_ma)
        
        in_position = False
        
        for i in range(long_ma, len(df)):
            date = df.iloc[i]['date']
            price = df.iloc[i]['close']
            ma_short = df.iloc[i]['ma_short']
            ma_long = df.iloc[i]['ma_long']
            ma_short_prev = df.iloc[i-1]['ma_short']
            ma_long_prev = df.iloc[i-1]['ma_long']
            
            # 黃金交叉買入
            if not in_position and ma_short_prev <= ma_long_prev and ma_short > ma_long:
                self.buy(date, price)
                in_position = True
                print(f"買入 @ {price:.2f} on {date}")
            
            # 死亡交叉賣出
            elif in_position and ma_short_prev >= ma_long_prev and ma_short < ma_long:
                self.sell(date, price)
                in_position = False
                print(f"賣出 @ {price:.2f} on {date}")
            
            self.portfolio_values.append(self.get_portfolio_value(price))
        
        # 最後若還持有則賣出
        if in_position:
            final_price = df.iloc[-1]['close']
            self.sell(df.iloc[-1]['date'], final_price)
            print(f"最終賣出 @ {final_price:.2f}")
        
        return self.get_results()
    
    def run_rsi_strategy(self, df, rsi_period=14, oversold=30, overbought=70):
        """RSI 策略: RSI < oversold 買入，RSI > overbought 賣出"""
        print(f"\n{'='*50}")
        print(f"執行 RSI 策略 (週期={rsi_period}, 超賣={oversold}, 超買={overbought})")
        print(f"{'='*50}")
        
        # 重新初始化
        self.__init__(self.initial_capital)
        
        df = df.copy()
        df['rsi'] = calculate_rsi(df, rsi_period)
        
        in_position = False
        
        for i in range(rsi_period, len(df)):
            date = df.iloc[i]['date']
            price = df.iloc[i]['close']
            rsi = df.iloc[i]['rsi']
            
            # RSI 超賣買入
            if not in_position and rsi < oversold:
                self.buy(date, price)
                in_position = True
                print(f"買入 @ {price:.2f} (RSI={rsi:.1f}) on {date}")
            
            # RSI 超買賣出
            elif in_position and rsi > overbought:
                self.sell(date, price)
                in_position = False
                print(f"賣出 @ {price:.2f} (RSI={rsi:.1f}) on {date}")
            
            self.portfolio_values.append(self.get_portfolio_value(price))
        
        # 最後若還持有則賣出
        if in_position:
            final_price = df.iloc[-1]['close']
            self.sell(df.iloc[-1]['date'], final_price)
            print(f"最終賣出 @ {final_price:.2f}")
        
        return self.get_results()
    
    def run_multifactor_strategy(self, df, strategy):
        """
        執行多因子策略
        
        Args:
            df: 股票數據
            strategy: MultiFactorStrategy 實例
        """
        print(f"\n{'='*50}")
        print(f"執行多因子策略")
        print(f"  因子: {list(strategy.factors.keys())}")
        print(f"  權重: {strategy.weights}")
        print(f"  閾值: {strategy.threshold}")
        print(f"{'='*50}")
        
        # 重新初始化
        self.__init__(self.initial_capital)
        
        df = df.copy()
        signals = strategy.generate_signals(df)
        df['signal'] = signals
        
        in_position = False
        
        # 需要足夠的 warmup 數據
        warmup = 60
        
        for i in range(warmup, len(df)):
            date = df.iloc[i]['date']
            price = df.iloc[i]['close']
            signal = df.iloc[i]['signal']
            
            # 買入信號且未持倉
            if not in_position and signal == 1:
                self.buy(date, price)
                in_position = True
                print(f"買入 @ {price:.2f} on {date}")
            
            # 賣出信號且持有倉位
            elif in_position and signal == -1:
                self.sell(date, price)
                in_position = False
                print(f"賣出 @ {price:.2f} on {date}")
            
            self.portfolio_values.append(self.get_portfolio_value(price))
        
        # 最後若還持有則賣出
        if in_position:
            final_price = df.iloc[-1]['close']
            self.sell(df.iloc[-1]['date'], final_price)
            print(f"最終賣出 @ {final_price:.2f}")
        
        return self.get_results()
    
    def run_ma_rsi_strategy(self, df, short_ma=10, long_ma=30, rsi_period=14):
        """MA + RSI 組合策略"""
        print(f"\n{'='*50}")
        print(f"執行 MA + RSI 組合策略")
        print(f"{'='*50}")
        
        # 重新初始化
        self.__init__(self.initial_capital)
        
        df = df.copy()
        df['ma_short'] = calculate_ma(df, short_ma)
        df['ma_long'] = calculate_ma(df, long_ma)
        df['rsi'] = calculate_rsi(df, rsi_period)
        
        in_position = False
        
        for i in range(long_ma, len(df)):
            date = df.iloc[i]['date']
            price = df.iloc[i]['close']
            ma_short = df.iloc[i]['ma_short']
            ma_long = df.iloc[i]['ma_long']
            rsi = df.iloc[i]['rsi']
            ma_short_prev = df.iloc[i-1]['ma_short']
            ma_long_prev = df.iloc[i-1]['ma_long']
            
            # MA 黃金交叉 + RSI 非超買買入
            if not in_position and ma_short_prev <= ma_long_prev and ma_short > ma_long and rsi < 70:
                self.buy(date, price)
                in_position = True
                print(f"買入 @ {price:.2f} (MA交叉, RSI={rsi:.1f}) on {date}")
            
            # MA 死亡交叉 + RSI 超買賣出
            elif in_position and ma_short_prev >= ma_long_prev and ma_short < ma_long:
                self.sell(date, price)
                in_position = False
                print(f"賣出 @ {price:.2f} (MA交叉, RSI={rsi:.1f}) on {date}")
            
            self.portfolio_values.append(self.get_portfolio_value(price))
        
        if in_position:
            final_price = df.iloc[-1]['close']
            self.sell(df.iloc[-1]['date'], final_price)
        
        return self.get_results()
    
    def get_results(self):
        """取得回測結果"""
        final_value = self.portfolio_values[-1] if self.portfolio_values else self.initial_capital
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        # 計算風險報酬比
        risk_reward_ratio = self._calculate_risk_reward_ratio()
        
        # 計算勝率
        win_rate = 0.0
        winning_trades = 0
        completed_trades = 0
        
        for i in range(1, len(self.trades)):
            if self.trades[i-1]['action'] == 'BUY' and self.trades[i]['action'] == 'SELL':
                entry_price = self.trades[i-1]['price']
                exit_price = self.trades[i]['price']
                if exit_price > entry_price:
                    winning_trades += 1
                completed_trades += 1
        
        if completed_trades > 0:
            win_rate = (winning_trades / completed_trades) * 100
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'total_trades': len(self.trades),
            'completed_trades': completed_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'trades': self.trades,
            'portfolio_values': self.portfolio_values,
            'risk_reward_ratio': risk_reward_ratio
        }
    
    def _calculate_risk_reward_ratio(self):
        """計算風險報酬比 (平均盈利 / 平均虧損)"""
        if len(self.trades) < 2:
            return 0.0
        
        # 找出所有完整的買賣週期
        completed_trades = []
        entry = None
        
        for trade in self.trades:
            if trade['action'] == 'BUY':
                entry = trade
            elif trade['action'] == 'SELL' and entry is not None:
                # 計算這筆交易的盈虧
                pnl = trade['revenue'] - entry['cost']
                completed_trades.append(pnl)
                entry = None
        
        if not completed_trades:
            return 0.0
        
        # 分離盈利和虧損交易
        profits = [t for t in completed_trades if t > 0]
        losses = [t for t in completed_trades if t < 0]
        
        if not losses:
            return float('inf') if profits else 0.0
        
        avg_profit = sum(profits) / len(profits) if profits else 0
        avg_loss = abs(sum(losses) / len(losses))
        
        if avg_loss == 0:
            return float('inf') if avg_profit > 0 else 0.0
        
        return round(avg_profit / avg_loss, 2)


def calculate_strategy_score(results):
    """計算策略評分"""
    if not results['portfolio_values'] or len(results['portfolio_values']) < 2:
        return 0
    
    portfolio = np.array(results['portfolio_values'])
    returns = np.diff(portfolio) / portfolio[:-1]
    
    # 1. 總報酬率 (權重: 30%)
    total_return = results['total_return']
    
    # 2. 夏普比率 (權重: 25%) - 假設無風險利率為 0
    if len(returns) > 0 and np.std(returns) > 0:
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
    else:
        sharpe_ratio = 0
    
    # 3. 最大回撤 (權重: 20%) - 轉為正向分數
    peak = np.maximum.accumulate(portfolio)
    drawdown = (portfolio - peak) / peak
    max_drawdown = np.min(drawdown) * 100  # 轉為百分比
    drawdown_score = max(0, -max_drawdown)  # 回撤為負，取反轉正
    
    # 4. 勝率 (權重: 15%)
    if len(results['trades']) >= 2:
        winning_trades = 0
        for i in range(1, len(results['trades'])):
            if results['trades'][i-1]['action'] == 'BUY' and results['trades'][i]['action'] == 'SELL':
                entry_price = results['trades'][i-1]['price']
                exit_price = results['trades'][i]['price']
                if exit_price > entry_price:
                    winning_trades += 1
        # 計算完整買賣週期
        completed_trades = len([t for t in results['trades'] if t['action'] == 'SELL'])
        win_rate = (winning_trades / completed_trades * 100) if completed_trades > 0 else 0
    else:
        win_rate = 0
    
    # 5. 獲利因子 (權重: 10%) - 總獲利 / 總虧損
    total_profit = 0
    total_loss = 0
    for i in range(1, len(results['trades'])):
        if results['trades'][i-1]['action'] == 'BUY' and results['trades'][i]['action'] == 'SELL':
            pnl = results['trades'][i]['revenue'] - results['trades'][i-1]['cost']
            if pnl > 0:
                total_profit += pnl
            else:
                total_loss += abs(pnl)
    
    profit_factor = total_profit / total_loss if total_loss > 0 else (total_profit if total_profit > 0 else 0)
    
    # 6. 風險報酬比
    risk_reward_ratio = results.get('risk_reward_ratio', 0)
    
    # 計算綜合評分 (滿分 100)
    # 報酬率: 30分 (每6%得1分，上限30分)
    return_score = min(30, max(0, total_return / 6))
    # 夏普比率: 25分 (每0.1得1分，上限25分)
    sharpe_score = min(25, max(0, sharpe_ratio * 10))
    # 最大回撤: 20分 (每5%回撤得1分)
    drawdown_score_final = min(20, max(0, drawdown_score / 5))
    # 勝率: 15分
    win_rate_score = min(15, max(0, win_rate / 100 * 15))
    # 獲利因子: 10分 (每0.2得1分)
    profit_factor_score = min(10, max(0, profit_factor * 2))
    # 風險報酬比: 額外加分 (每0.5得1分，上限5分)
    rr_score = min(5, max(0, risk_reward_ratio * 2))
    
    total_score = return_score + sharpe_score + drawdown_score_final + win_rate_score + profit_factor_score + rr_score
    
    return {
        'total_score': round(total_score, 2),
        'scores': {
            'return': round(return_score, 2),
            'sharpe': round(sharpe_score, 2),
            'drawdown': round(drawdown_score_final, 2),
            'win_rate': round(win_rate_score, 2),
            'profit_factor': round(profit_factor_score, 2),
            'risk_reward': round(rr_score, 2)
        },
        'metrics': {
            'total_return': round(total_return, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'win_rate': round(win_rate, 2),
            'profit_factor': round(profit_factor, 2),
            'risk_reward_ratio': risk_reward_ratio,
            'total_trades': results['total_trades']
        }
    }


def rank_strategies(results_dict):
    """對策略進行排名"""
    scored_strategies = []
    
    for name, results in results_dict.items():
        score_data = calculate_strategy_score(results)
        scored_strategies.append({
            'strategy': name,
            'score': score_data['total_score'],
            'scores': score_data['scores'],
            'metrics': score_data['metrics'],
            'results': results
        })
    
    # 按評分排序
    scored_strategies.sort(key=lambda x: x['score'], reverse=True)
    
    # 加上排名
    for i, s in enumerate(scored_strategies):
        s['rank'] = i + 1
    
    return scored_strategies


def print_ranking(ranked_strategies):
    """打印策略排名"""
    print("\n" + "="*70)
    print("📊 策略評分與排名")
    print("="*70)
    
    for s in ranked_strategies:
        print(f"\n🏆 第 {s['rank']} 名: {s['strategy']}")
        print(f"   總評分: {s['score']}/100")
        print(f"   ─────────────────────────────────")
        print(f"   報酬率: {s['metrics']['total_return']:+.2f}% (得分: {s['scores']['return']}/30)")
        print(f"   夏普比率: {s['metrics']['sharpe_ratio']:.2f} (得分: {s['scores']['sharpe']}/25)")
        print(f"   最大回撤: {s['metrics']['max_drawdown']:.2f}% (得分: {s['scores']['drawdown']}/20)")
        print(f"   勝率: {s['metrics']['win_rate']:.1f}% (得分: {s['scores']['win_rate']}/15)")
        print(f"   獲利因子: {s['metrics']['profit_factor']:.2f} (得分: {s['scores']['profit_factor']}/10)")
        print(f"   風險報酬比: {s['metrics']['risk_reward_ratio']:.2f} (得分: {s['scores']['risk_reward']}/5)")
        print(f"   總交易次數: {s['metrics']['total_trades']}")
    
    print("\n" + "="*70)
    best = ranked_strategies[0]
    print(f"✅ 最佳策略: {best['strategy']} (評分: {best['score']}/100)")
    print("="*70)


# ============================================================
# 多因子策略框架
# ============================================================

class MultiFactorStrategy:
    """多因子策略框架"""
    
    def __init__(self, factors=None, weights=None, threshold=0.3):
        """
        初始化多因子策略
        
        Args:
            factors: dict, 每個因子的名稱和計算函數
                格式: {'factor_name': lambda df: series}
            weights: dict, 每個因子的權重
                格式: {'factor_name': weight}
            threshold: float, 買入/賣出閾值 (-threshold ~ +threshold 為持有)
        """
        self.factors = factors or {}
        self.weights = weights or {}
        self.threshold = threshold
        
        # 正規化權重
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v/total_weight for k, v in self.weights.items()}
    
    def add_factor(self, name, func, weight=1.0):
        """添加因子"""
        self.factors[name] = func
        self.weights[name] = weight
        # 正規化
        total_weight = sum(self.weights.values())
        self.weights = {k: v/total_weight for k, v in self.weights.items()}
    
    def calculate_composite_score(self, df):
        """
        計算綜合得分
        
        Returns:
            pd.Series: 綜合得分 (-1 到 1)
        """
        df = df.copy()
        composite = pd.Series(0, index=df.index)
        
        for factor_name, factor_func in self.factors.items():
            if factor_name in self.weights:
                # 計算因子信號並正規化到 -1 到 1
                signal = factor_func(df)
                
                # 正規化
                if signal.max() != signal.min():
                    signal = (signal - signal.min()) / (signal.max() - signal.min()) * 2 - 1
                
                weight = self.weights[factor_name]
                composite += signal * weight
        
        return composite
    
    def generate_signals(self, df):
        """
        生成交易信號
        
        Returns:
            pd.Series: 1=買入, 0=持有, -1=賣出
        """
        df = df.copy()
        df['composite_score'] = self.calculate_composite_score(df)
        
        # 生成信號
        signals = pd.Series(0, index=df.index)
        signals[df['composite_score'] > self.threshold] = 1   # 買入
        signals[df['composite_score'] < -self.threshold] = -1  # 賣出
        
        return signals


def factor_ma_trend(df, short_period=10, long_period=30):
    """
    因子: MA 趨勢
    短MA > 長MA 為正向信號
    """
    ma_short = df['close'].rolling(window=short_period).mean()
    ma_long = df['close'].rolling(window=long_period).mean()
    return (ma_short - ma_long) / ma_long


def factor_rsi(df, period=14):
    """
    因子: RSI
    RSI 低為正向信號 (超賣), RSI 高為負向信號 (超買)
    """
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    # 反轉: 低RSI = 高分 (超賣可能反彈)
    return (50 - rsi) / 50


def factor_momentum(df, period=10):
    """
    因子: 動量
    上漲動量為正向信號
    """
    return df['close'].pct_change(period)


def factor_volume(df):
    """
    因子: 成交量
    成交量高於平均為正向信號
    """
    volume_ma = df['volume'].rolling(window=20).mean()
    return (df['volume'] - volume_ma) / volume_ma


def factor_volatility(df, period=20):
    """
    因子: 波動率
    波動率低為正向信號 (較穩定)
    """
    returns = df['close'].pct_change()
    volatility = returns.rolling(window=period).std()
    # 反轉: 低波動率 = 高分
    max_vol = volatility.rolling(window=60).max()
    return 1 - (volatility / max_vol)


def factor_price_position(df, period=20):
    """
    因子: 價格位置
    價格在近期低位為正向信號
    """
    low_min = df['close'].rolling(window=period).min()
    high_max = df['close'].rolling(window=period).max()
    return (df['close'] - low_min) / (high_max - low_min)


# 預設因子工廠
DEFAULT_FACTORIES = {
    'ma_trend': factor_ma_trend,
    'rsi': factor_rsi,
    'momentum': factor_momentum,
    'volume': factor_volume,
    'volatility': factor_volatility,
    'price_position': factor_price_position,
}


def print_results(results, strategy_name):
    """打印回測結果"""
    print(f"\n{strategy_name} 回測結果:")
    print(f"  初始資金: ${results['initial_capital']:,.2f}")
    print(f"  最終價值: ${results['final_value']:,.2f}")
    print(f"  總報酬率: {results['total_return']:.2f}%")
    print(f"  總交易次數: {results['total_trades']}")
    print(f"  勝率: {results.get('win_rate', 0):.1f}% ({results.get('winning_trades', 0)}/{results.get('completed_trades', 0)})")


def recommend_best_strategy(df):
    """
    推薦當下最佳策略
    比較所有策略的歷史表現，回報最高者為推薦策略
    """
    print(f"\n{'='*60}")
    print("🔍 策略推薦分析")
    print(f"{'='*60}")
    
    # 測試不同的 MA 參數組合
    ma_combinations = [
        (5, 20), (10, 30), (10, 60), (20, 50), (20, 100)
    ]
    
    # 測試不同的 RSI 參數組合
    rsi_combinations = [
        (14, 30, 70), (14, 25, 75), (7, 30, 70), (21, 30, 70)
    ]
    
    all_results = []
    
    # 測試 MA 策略
    print("\n📊 測試 MA 策略...")
    for short_ma, long_ma in ma_combinations:
        backtester = Backtester(initial_capital=100000)
        results = backtester.run_ma_strategy(df, short_ma=short_ma, long_ma=long_ma)
        all_results.append({
            'strategy': 'MA',
            'params': f'MA({short_ma}/{long_ma})',
            'return': results['total_return'],
            'trades': results['total_trades'],
            'results': results
        })
        print(f"  MA({short_ma}/{long_ma}): {results['total_return']:.2f}%")
    
    # 測試 RSI 策略
    print("\n📊 測試 RSI 策略...")
    for rsi_period, oversold, overbought in rsi_combinations:
        backtester = Backtester(initial_capital=100000)
        results = backtester.run_rsi_strategy(df, rsi_period=rsi_period, oversold=oversold, overbought=overbought)
        all_results.append({
            'strategy': 'RSI',
            'params': f'RSI({rsi_period},{oversold},{overbought})',
            'return': results['total_return'],
            'trades': results['total_trades'],
            'results': results
        })
        print(f"  RSI({rsi_period},{oversold},{overbought}): {results['total_return']:.2f}%")
    
    # 測試 MA + RSI 組合策略
    print("\n📊 測試 MA + RSI 組合策略...")
    ma_rsi_combinations = [
        (10, 30, 14), (20, 50, 14), (10, 60, 14)
    ]
    for short_ma, long_ma, rsi_period in ma_rsi_combinations:
        backtester = Backtester(initial_capital=100000)
        results = backtester.run_ma_rsi_strategy(df, short_ma=short_ma, long_ma=long_ma, rsi_period=rsi_period)
        all_results.append({
            'strategy': 'MA+RSI',
            'params': f'MA({short_ma}/{long_ma})+RSI({rsi_period})',
            'return': results['total_return'],
            'trades': results['total_trades'],
            'results': results
        })
        print(f"  MA({short_ma}/{long_ma})+RSI({rsi_period}): {results['total_return']:.2f}%")
    
    # 排序找出最佳策略
    all_results.sort(key=lambda x: x['return'], reverse=True)
    
    # 顯示排名
    print(f"\n{'='*60}")
    print("📈 策略排名 (按報酬率)")
    print(f"{'='*60}")
    for i, result in enumerate(all_results, 1):
        print(f"  {i}. {result['strategy']} {result['params']}: {result['return']:.2f}% (交易次數: {result['trades']})")
    
    # 推薦最佳策略
    best = all_results[0]
    print(f"\n{'='*60}")
    print("🎯 推薦策略")
    print(f"{'='*60}")
    print(f"  策略: {best['strategy']} {best['params']}")
    print(f"  預期報酬率: {best['return']:.2f}%")
    print(f"  交易次數: {best['trades']}")
    
    # 計算夏普比率 (簡單版)
    if best['results']['portfolio_values']:
        portfolio = best['results']['portfolio_values']
        returns = [(portfolio[i] - portfolio[i-1]) / portfolio[i-1] for i in range(1, len(portfolio))]
        if returns and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
            print(f"  夏普比率: {sharpe:.2f}")
    
    return best


if __name__ == "__main__":
    import sys
    
    # 預設股票代碼
    symbol = "^GSPC"  # S&P 500
    
    # 預設模式: 策略推薦
    mode = "recommend"
    
    if len(sys.argv) > 1:
        # 檢查是否是推薦模式
        if sys.argv[1] == "--all":
            mode = "all"
            symbol = "^GSPC" if len(sys.argv) == 2 else sys.argv[2]
        elif sys.argv[1] == "--help":
            print("用法:")
            print("  python backtest_framework.py                    # 執行策略推薦")
            print("  python backtest_framework.py --all              # 執行所有策略並顯示結果")
            print("  python backtest_framework.py <股票代碼>          # 使用指定股票執行策略推薦")
            print("  python backtest_framework.py --help              # 顯示說明")
            sys.exit(0)
        else:
            symbol = sys.argv[1]
    
    print(f"正在獲取 {symbol} 的數據...")
    df = get_stock_data(symbol)
    
    if df is not None and len(df) > 0:
        print(f"成功獲取 {len(df)} 天的數據")
        
        if mode == "recommend":
            # 執行策略推薦
            best = recommend_best_strategy(df)
            print("\n" + "="*60)
            print("✅ 策略推薦完成!")
            print("="*60)
        else:
            # 執行所有策略回測
            backtester = Backtester(initial_capital=100000)
            
            # MA 策略
            ma_results = backtester.run_ma_strategy(df)
            print_results(ma_results, "MA (10/30)")
            
            # RSI 策略
            backtester = Backtester(initial_capital=100000)
            rsi_results = backtester.run_rsi_strategy(df)
            print_results(rsi_results, "RSI (14)")
            
            # MA + RSI 組合策略
            backtester = Backtester(initial_capital=100000)
            combined_results = backtester.run_ma_rsi_strategy(df)
            print_results(combined_results, "MA + RSI")
            
            # 策略評分與排名
            results_dict = {
                "MA (10/30)": ma_results,
                "RSI (14)": rsi_results,
                "MA + RSI": combined_results
            }
            ranked = rank_strategies(results_dict)
            print_ranking(ranked)
            
            # 策略推薦
            best = recommend_best_strategy(df)
            
            print("\n" + "="*60)
            print("回測完成!")
            print("="*60)
    else:
        print("無法獲取股票數據")
