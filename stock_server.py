#!/usr/bin/env python3
"""Enhanced stock server on port 3001 - Optimized display"""
import json
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
from urllib import request
import random
from datetime import datetime
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import base64
import time

# Create directory for K-line charts
KLINE_DIR = 'kline_charts'
if not os.path.exists(KLINE_DIR):
    os.makedirs(KLINE_DIR)

def generate_kline_chart(symbol, data_dir='taiwan_stocks_data'):
    """Generate a K-line chart for the given symbol and return the image path"""
    # Convert symbol format (2330.TW -> 2330_TW)
    filename = symbol.replace('.TW', '_TW.csv')
    filepath = os.path.join(data_dir, filename)
    
    if not os.path.exists(filepath):
        return None
    
    try:
        df = pd.read_csv(filepath)
        df = df.tail(30)  # Last 30 days
        
        if len(df) < 5:
            return None
        
        dates = pd.to_datetime(df['Date'])
        opens = df['Open'].astype(float)
        highs = df['High'].astype(float)
        lows = df['Low'].astype(float)
        closes = df['Close'].astype(float)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(6, 3))
        
        # Plot candlesticks
        for date, o, h, l, c in zip(dates, opens, highs, lows, closes):
            if c >= o:
                color = '#ef4444'  # Red for up (Taiwan convention)
                body_bottom = o
                body_height = c - o
            else:
                color = '#22c55e'  # Green for down
                body_bottom = c
                body_height = o - c
            
            if body_height == 0:
                body_height = 0.01
            
            ax.plot([date, date], [l, h], color=color, linewidth=0.8)
            ax.bar(date, body_height, bottom=body_bottom, width=0.6, color=color, edgecolor=color)
        
        ax.set_title(f'{symbol.replace(".TW", "")} K-Line', fontsize=10, fontweight='bold', color='#9ca3af')
        ax.set_xlabel('')
        ax.set_ylabel('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
        plt.xticks(rotation=45, fontsize=7)
        plt.yticks(fontsize=7)
        ax.grid(True, alpha=0.2)
        ax.set_facecolor('#1f2937')
        fig.patch.set_facecolor('#1f2937')
        ax.tick_params(colors='#9ca3af')
        ax.spines['bottom'].set_color('#4b5563')
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_color('#4b5563')
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        # Save chart
        chart_filename = f'{symbol.replace(".", "_")}_kline.png'
        chart_path = os.path.join(KLINE_DIR, chart_filename)
        plt.savefig(chart_path, dpi=60, bbox_inches='tight', facecolor='#1f2937')
        plt.close()
        
        return chart_path
    except Exception as e:
        print(f"Error generating K-line for {symbol}: {e}")
        return None

# Load stock data from JSON file
try:
    with open('louie_realtime_winrate.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        STOCKS = data.get('stocks', [])
except Exception as e:
    print(f"Warning: Could not load louie_realtime_winrate.json: {e}")
    STOCKS = []

# Pre-generate K-line charts for all stocks
print("Generating K-line charts...")
KLINE_PATHS = {}
for s in STOCKS:
    symbol = s.get('symbol', '')
    if symbol:
        path = generate_kline_chart(symbol)
        if path:
            KLINE_PATHS[symbol] = path
print(f"Generated {len(KLINE_PATHS)} K-line charts")

PORT = 3001

# Generate mock trading records
MOCK_TRADES = [
    {"id": 1, "symbol": "2330.TW", "type": "buy", "price": 1085.0, "shares": 100, "time": "2026-03-14 10:30:00", "pnl": 0, "status": "holding"},
    {"id": 2, "symbol": "2454.TW", "type": "buy", "price": 1420.0, "shares": 50, "time": "2026-03-14 11:15:00", "pnl": 0, "status": "holding"},
    {"id": 3, "symbol": "2317.TW", "type": "sell", "price": 178.5, "shares": 200, "time": "2026-03-14 09:45:00", "pnl": 1200, "status": "closed"},
    {"id": 4, "symbol": "2308.TW", "type": "sell", "price": 342.0, "shares": 100, "time": "2026-03-13 14:20:00", "pnl": -800, "status": "closed"},
    {"id": 5, "symbol": "2382.TW", "type": "buy", "price": 268.0, "shares": 150, "time": "2026-03-13 10:00:00", "pnl": 0, "status": "holding"},
    {"id": 6, "symbol": "3034.TW", "type": "sell", "price": 1185.0, "shares": 80, "time": "2026-03-12 13:30:00", "pnl": 3200, "status": "closed"},
    {"id": 7, "symbol": "2603.TW", "type": "buy", "price": 42.5, "shares": 1000, "time": "2026-03-12 09:30:00", "pnl": 0, "status": "holding"},
    {"id": 8, "symbol": "2881.TW", "type": "sell", "price": 28.9, "shares": 500, "time": "2026-03-11 11:00:00", "pnl": 450, "status": "closed"},
]

# Load stock data from JSON file
try:
    with open('louie_realtime_winrate.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        STOCKS = data.get('stocks', [])
except Exception as e:
    print(f"Warning: Could not load louie_realtime_winrate.json: {e}")
    STOCKS = []

# Calculate derived metrics for each stock
for s in STOCKS:
    # Basic data
    trades = s.get('trades', 0)
    wins = s.get('wins', 0)
    losses = s.get('losses', 0)
    win_rate = s.get('win_rate', 0)
    
    # Derived metrics
    s['total_signals'] = trades
    s['profit_factor'] = round(wins / losses, 2) if losses > 0 else wins * 1.0
    s['avg_return'] = round(win_rate * 0.02, 2)  # Estimated based on win rate
    
    # Simulate price change
    s['change'] = round(random.uniform(-3, 3), 2)
    s['volume'] = random.randint(1000000, 50000000)
    s['day_high'] = s['current_price'] * (1 + random.uniform(0.01, 0.03))
    s['day_low'] = s['current_price'] * (1 - random.uniform(0.01, 0.03))
    
    # Calculate price levels based on price
    price = s['current_price']
    s['support'] = round(price * 0.95, 2)
    s['resistance'] = round(price * 1.05, 2)
    s['stop_loss'] = round(price * 0.92, 2)
    s['entry'] = round(price, 2)
    s['exit_price'] = round(price * 1.12, 2)

# Overall stats
overall_stats = {
    'win_rate': data.get('overall_win_rate', 0),
    'risk_reward': data.get('overall_risk_reward', 0),
    'total_signals': data.get('total_signals', 0),
    'stock_count': len(STOCKS),
    'high_winrate_count': len([s for s in STOCKS if s.get('win_rate', 0) >= 70])
}

# Sort stocks by win rate (best first)
STOCKS.sort(key=lambda x: x.get('win_rate', 0), reverse=True)

html_template = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ray 台股策略追蹤</title>
  <meta http-equiv="refresh" content="60">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'Noto Sans TC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
      min-height: 100vh;
      padding: 40px 20px;
    }}
    .header-stats {{
      display: flex;
      justify-content: center;
      gap: 30px;
      margin-bottom: 40px;
      flex-wrap: wrap;
    }}
    .stat-box {{
      background: linear-gradient(145deg, rgba(31, 41, 55, 0.9), rgba(17, 24, 39, 0.95));
      backdrop-filter: blur(20px);
      border-radius: 16px;
      padding: 20px 32px;
      text-align: center;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
      border: 1px solid rgba(255,255,255,0.1);
    }}
    .stat-label {{ font-size: 14px; color: #9ca3af; margin-bottom: 8px; }}
    .stat-value {{ font-size: 28px; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; }}
    .stat-value.green {{ color: #10b981; }}
    .stat-value.blue {{ color: #3b82f6; }}
    .stat-value.orange {{ color: #f59e0b; }}
    .stat-value.purple {{ color: #8b5cf6; }}
    h1 {{
      text-align: center;
      color: #fff;
      margin-bottom: 30px;
      font-size: 28px;
      font-weight: 700;
    }}
    .subtitle {{ 
      text-align: center; 
      color: #6b7280; 
      font-size: 14px; 
      margin-top: -20px; 
      margin-bottom: 30px; 
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 20px;
      max-width: 1600px;
      margin: 0 auto;
    }}
    .card {{
      background: linear-gradient(145deg, rgba(31, 41, 55, 0.9), rgba(17, 24, 39, 0.95));
      backdrop-filter: blur(20px);
      border-radius: 20px;
      padding: 24px;
      box-shadow: 0 20px 40px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255,255,255,0.08);
      position: relative;
      transition: transform 0.2s;
    }}
    .card:hover {{ transform: translateY(-4px); }}
    .kline-chart {{
      width: 100%;
      height: 100px;
      margin-bottom: 16px;
      border-radius: 12px;
      overflow: hidden;
      background: #1f2937;
    }}
    .kline-chart img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }}
    .stock-info {{ display: flex; align-items: center; gap: 12px; }}
    .stock-icon {{
      width: 44px; height: 44px;
      background: linear-gradient(135deg, #3b82f6, #1d4ed8);
      border-radius: 12px;
      display: flex; align-items: center; justify-content: center;
      font-size: 16px; color: #fff; font-weight: 700;
    }}
    .stock-symbol {{ font-size: 20px; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; }}
    .stock-name {{ font-size: 13px; color: #9ca3af; margin-top: 2px; }}
    
    .price-row {{ display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px; }}
    .price {{ font-size: 28px; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; }}
    .change {{ display: flex; align-items: center; gap: 8px; }}
    .change-val {{ 
      padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 13px;
      font-family: 'JetBrains Mono', monospace;
    }}
    .positive {{ background: rgba(16, 185, 129, 0.2); color: #10b981; }}
    .negative {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; }}
    
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-top: 12px;
    }}
    .metric {{
      background: rgba(255,255,255,0.05);
      border-radius: 10px;
      padding: 10px;
      text-align: center;
    }}
    .metric-label {{ font-size: 10px; color: #9ca3af; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
    .metric-value {{ font-size: 14px; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; }}
    .metric-value.win {{ color: #10b981; }}
    .metric-value.risk {{ color: #f59e0b; }}
    .metric-value.profit {{ color: #8b5cf6; }}
    
    .levels-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-top: 12px;
    }}
    .level {{
      background: rgba(255,255,255,0.05);
      border-radius: 10px;
      padding: 10px;
      text-align: center;
    }}
    .level-label {{ font-size: 10px; color: #9ca3af; margin-bottom: 4px; }}
    .level-value {{ font-size: 14px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
    .level-value.support {{ color: #10b981; }}
    .level-value.resistance {{ color: #ef4444; }}
    .level-value.entry {{ color: #3b82f6; }}
    .level-value.exit {{ color: #8b5cf6; }}
    .level-value.stop {{ color: #f59e0b; }}
    .level-value.vol {{ color: #6b7280; }}
    
    .win-rate-badge {{
      position: absolute;
      top: 18px;
      right: 18px;
      padding: 5px 10px;
      border-radius: 16px;
      font-size: 13px;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
    }}
    .win-high {{ background: rgba(16, 185, 129, 0.25); color: #10b981; }}
    .win-mid {{ background: rgba(245, 158, 11, 0.25); color: #f59e0b; }}
    .win-low {{ background: rgba(239, 68, 68, 0.25); color: #ef4444; }}
    
    .footer {{
      text-align: center;
      color: #6b7280;
      font-size: 12px;
      margin-top: 40px;
      padding: 20px;
    }}
    .auto-refresh {{
      display: inline-block;
      background: rgba(59, 130, 246, 0.2);
      padding: 4px 12px;
      border-radius: 12px;
      margin-left: 10px;
      font-size: 11px;
      color: #3b82f6;
    }}
    
    /* Trading Records */
    .trading-records {{
      max-width: 1200px;
      margin: 50px auto;
      background: linear-gradient(145deg, rgba(31, 41, 55, 0.9), rgba(17, 24, 39, 0.95));
      backdrop-filter: blur(20px);
      border-radius: 20px;
      padding: 30px;
      box-shadow: 0 20px 40px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255,255,255,0.08);
    }}
    .trading-records h2 {{
      color: #fff;
      text-align: center;
      margin-bottom: 8px;
      font-size: 24px;
    }}
    .trading-records .subtitle {{ 
      text-align: center; 
      color: #6b7280; 
      font-size: 14px; 
      margin-bottom: 24px; 
    }}
    .records-summary {{
      display: flex;
      justify-content: center;
      gap: 24px;
      margin-bottom: 30px;
      flex-wrap: wrap;
    }}
    .record-stat {{
      background: rgba(255,255,255,0.05);
      border-radius: 12px;
      padding: 16px 24px;
      text-align: center;
    }}
    .record-stat-label {{ font-size: 12px; color: #9ca3af; margin-bottom: 6px; }}
    .record-stat-value {{ font-size: 20px; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; }}
    .record-stat-value.profit {{ color: #10b981; }}
    
    .records-table {{
      overflow-x: auto;
    }}
    .records-table table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    .records-table th {{
      background: rgba(255,255,255,0.05);
      padding: 12px;
      text-align: left;
      color: #9ca3af;
      font-weight: 500;
      border-bottom: 1px solid rgba(255,255,255,0.1);
    }}
    .records-table td {{
      padding: 12px;
      color: #e5e7eb;
      border-bottom: 1px solid rgba(255,255,255,0.05);
    }}
    .records-table .symbol {{ font-family: 'JetBrains Mono', monospace; font-weight: 600; color: #3b82f6; }}
    .records-table .buy {{ color: #10b981; font-weight: 600; }}
    .records-table .sell {{ color: #ef4444; font-weight: 600; }}
    .records-table .holding {{ color: #f59e0b; }}
    .records-table .closed {{ color: #6b7280; }}
    .records-table .profit {{ color: #10b981; font-weight: 600; }}
    .records-table .loss {{ color: #ef4444; font-weight: 600; }}
    .records-table .neutral {{ color: #6b7280; }}
    
    /* Search & Filter */
    .controls {{
      max-width: 800px;
      margin: 0 auto 30px;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      justify-content: center;
    }}
    .search-box {{
      flex: 1;
      min-width: 200px;
      max-width: 400px;
    }}
    .search-box input {{
      width: 100%;
      padding: 12px 20px;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.1);
      background: rgba(31, 41, 55, 0.9);
      color: #fff;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }}
    .search-box input:focus {{
      border-color: #3b82f6;
    }}
    .search-box input::placeholder {{
      color: #6b7280;
    }}
    .filter-buttons {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: center;
    }}
    .filter-btn {{
      padding: 10px 18px;
      border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.1);
      background: rgba(31, 41, 55, 0.8);
      color: #9ca3af;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .filter-btn:hover {{
      border-color: #3b82f6;
      color: #fff;
    }}
    .filter-btn.active {{
      background: rgba(59, 130, 246, 0.3);
      border-color: #3b82f6;
      color: #fff;
    }}
    .results-count {{
      text-align: center;
      color: #6b7280;
      font-size: 13px;
      margin-bottom: 20px;
    }}
    
    /* Mobile Optimizations */
    @media (max-width: 768px) {{
      body {{ padding: 20px 12px; }}
      h1 {{ font-size: 22px; margin-bottom: 20px; }}
      .subtitle {{ margin-top: 0; margin-bottom: 20px; }}
      .header-stats {{ gap: 12px; margin-bottom: 20px; }}
      .stat-box {{ padding: 14px 18px; }}
      .stat-value {{ font-size: 22px; }}
      .stat-label {{ font-size: 12px; }}
      .grid {{ grid-template-columns: 1fr; gap: 16px; }}
      .card {{ padding: 18px; }}
      .price {{ font-size: 24px; }}
      .stock-symbol {{ font-size: 18px; }}
      .controls {{ flex-direction: column; }}
      .search-box {{ max-width: 100%; }}
      .filter-buttons {{ justify-content: center; }}
    }}
    
    @media (max-width: 480px) {{
      .header-stats {{ flex-direction: column; align-items: center; }}
      .stat-box {{ width: 100%; max-width: 280px; }}
      .metrics-grid {{ grid-template-columns: repeat(3, 1fr); gap: 6px; }}
      .levels-grid {{ grid-template-columns: repeat(3, 1fr); gap: 6px; }}
      .metric, .level {{ padding: 8px 4px; }}
      .metric-label, .level-label {{ font-size: 9px; }}
      .metric-value, .level-value {{ font-size: 12px; }}
    }}
    
    /* Level Calculation Display */
    .level-calc {{
      display: none;
      margin-top: 12px;
      padding: 12px;
      background: rgba(0,0,0,0.3);
      border-radius: 8px;
      border: 1px solid rgba(255,255,255,0.1);
    }}
    
    .level-calc.show {{
      display: block;
      animation: fadeIn 0.3s ease;
    }}
    
    .calc-title {{
      font-size: 12px;
      color: #9ca3af;
      margin-bottom: 8px;
      font-weight: 600;
    }}
    
    .calc-row {{
      display: flex;
      justify-content: space-between;
      padding: 4px 0;
      font-size: 11px;
      border-bottom: 1px solid rgba(255,255,255,0.05);
    }}
    
    .calc-row:last-child {{
      border-bottom: none;
    }}
    
    .calc-label {{
      color: #6b7280;
    }}
    
    .calc-val {{
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
    }}
    
    .calc-val.support {{ color: #10b981; }}
    .calc-val.resistance {{ color: #ef4444; }}
    
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(-10px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
  </style>
</head>
<body>
  <h1>📈 Ray 台股策略追蹤</h1>
  <p class="subtitle">滾動式回測 · 優化參數</p>
  
  <div class="controls">
    <div class="search-box">
      <input type="text" id="search" placeholder="🔍 搜尋股票代碼或名稱..." oninput="filterStocks()">
    </div>
    <div class="filter-buttons">
      <button class="filter-btn active" data-filter="all" onclick="setFilter('all')">全部</button>
      <button class="filter-btn" data-filter="high" onclick="setFilter('high')">高勝率 ≥70%</button>
      <button class="filter-btn" data-filter="mid" onclick="setFilter('mid')">中勝率 45-70%</button>
      <button class="filter-btn" data-filter="up" onclick="setFilter('up')">漲跌 ▲</button>
      <button class="filter-btn" data-filter="down" onclick="setFilter('down')">漲跌 ▼</button>
    </div>
  </div>
  <p class="results-count" id="results-count">顯示 20 個標的</p>
  
  <div class="header-stats">
    <div class="stat-box">
      <div class="stat-label">整體勝率</div>
      <div class="stat-value green">{overall_stats['win_rate']:.1f}%</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">風險報酬</div>
      <div class="stat-value blue">{overall_stats['risk_reward']:.2f}</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">追蹤標的</div>
      <div class="stat-value orange">{overall_stats['stock_count']}</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">高勝率標的</div>
      <div class="stat-value purple">{overall_stats['high_winrate_count']}</div>
    </div>
  </div>
  
  <div class="grid">
"""

for s in STOCKS:
    change_class = "positive" if s["change"] >= 0 else "negative"
    sign = "+" if s["change"] >= 0 else ""
    
    win_rate = s.get('win_rate', 0)
    if win_rate >= 70:
        win_badge_class = "win-high"
    elif win_rate >= 45:
        win_badge_class = "win-mid"
    else:
        win_badge_class = "win-low"
    
    symbol = s['symbol'].replace('.TW', '')
    full_symbol = s.get('symbol', '')
    kline_path = KLINE_PATHS.get(full_symbol, '')
    kline_html = f'<div class="kline-chart"><img src="{kline_path}" alt="K-Line"></div>' if kline_path else ''
    
    html_template += f"""
    <div class="card">
      {kline_html}
      <div class="win-rate-badge {win_badge_class}">勝率 {win_rate:.1f}%</div>
      <div class="card-header">
        <div class="stock-info">
          <div class="stock-icon">{symbol[:2]}</div>
          <div>
            <div class="stock-symbol">{symbol}</div>
            <div class="stock-name">交易次數: {s.get('total_signals', 0)}</div>
          </div>
        </div>
      </div>
      <div class="price-row">
        <div class="price">${s['current_price']:,.0f}</div>
        <div class="change">
          <span class="change-val {change_class}">{sign}{s['change']:.2f}%</span>
        </div>
      </div>
      
      <div class="metrics-grid">
        <div class="metric">
          <div class="metric-label">賺赔比</div>
          <div class="metric-value risk">{s.get('profit_factor', 0):.2f}</div>
        </div>
        <div class="metric">
          <div class="metric-label">獲利因子</div>
          <div class="metric-value profit">{min(s.get('profit_factor', 0) * 0.5, 99.9):.1f}</div>
        </div>
        <div class="metric">
          <div class="metric-label">預估報酬</div>
          <div class="metric-value win">{s.get('avg_return', 0):.1f}%</div>
        </div>
      </div>
      
      <div class="levels-grid">
        <div class="level" onclick="showLevelCalc('support', {s.get('support', 0):.2f}, {s['current_price']})" style="cursor:pointer">
          <div class="level-label">支撐</div>
          <div class="level-value support">{s.get('support', 0):.2f}</div>
        </div>
        <div class="level" onclick="showLevelCalc('resistance', {s.get('resistance', 0):.2f}, {s['current_price']})" style="cursor:pointer">
          <div class="level-label">阻力</div>
          <div class="level-value resistance">{s.get('resistance', 0):.2f}</div>
        </div>
        <div class="level">
          <div class="level-label">停損</div>
          <div class="level-value stop">{s.get('stop_loss', 0):.2f}</div>
        </div>
        <div class="level">
          <div class="level-label">進場</div>
          <div class="level-value entry">{s.get('entry', 0):.2f}</div>
        </div>
        <div class="level">
          <div class="level-label">目標</div>
          <div class="level-value exit">{s.get('exit_price', 0):.2f}</div>
        </div>
        <div class="level">
          <div class="level-label">成交量</div>
          <div class="level-value vol">{s.get('volume', 0)//1000}K</div>
        </div>
      </div>
    </div>
"""

html_template += f"""
  </div>
  
  <!-- Trading Records Section -->
  <div class="trading-records">
    <h2>📋 模擬交易記錄</h2>
    <p class="subtitle">記錄時間: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
    
    <div class="records-summary">
      <div class="record-stat">
        <span class="record-stat-label">總交易次數</span>
        <span class="record-stat-value">{len(MOCK_TRADES)}</span>
      </div>
      <div class="record-stat">
        <span class="record-stat-label">已完成交易</span>
        <span class="record-stat-value">{len([t for t in MOCK_TRADES if t['status'] == 'closed'])}</span>
      </div>
      <div class="record-stat">
        <span class="record-stat-label">持有中</span>
        <span class="record-stat-value">{len([t for t in MOCK_TRADES if t['status'] == 'holding'])}</span>
      </div>
      <div class="record-stat">
        <span class="record-stat-label">已實現損益</span>
        <span class="record-stat-value profit">${sum([t['pnl'] for t in MOCK_TRADES]):,}</span>
      </div>
    </div>
    
    <div class="records-table">
      <table>
        <thead>
          <tr>
            <th>時間</th>
            <th>股票</th>
            <th>買賣</th>
            <th>價格</th>
            <th>股數</th>
            <th>狀態</th>
            <th>損益</th>
          </tr>
        </thead>
        <tbody>
"""

for t in MOCK_TRADES:
    type_class = "buy" if t['type'] == 'buy' else "sell"
    status_class = "holding" if t['status'] == 'holding' else "closed"
    pnl_class = "profit" if t['pnl'] > 0 else ("loss" if t['pnl'] < 0 else "neutral")
    pnl_display = "-" if t['pnl'] == 0 else f"${t['pnl']:,}"
    
    html_template += f"""
          <tr>
            <td>{t['time']}</td>
            <td class="symbol">{t['symbol']}</td>
            <td class="{type_class}">{t['type'].upper()}</td>
            <td>${t['price']:,.2f}</td>
            <td>{t['shares']}</td>
            <td class="{status_class}">{t['status']}</td>
            <td class="{pnl_class}">{pnl_display}</td>
          </tr>
"""

html_template += """
        </tbody>
      </table>
    </div>
  </div>
  
  <div class="footer">
    最後更新: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
    <span class="auto-refresh">自動更新 60秒</span>
  </div>
  
  <script>
    let currentFilter = 'all';
    
    function filterStocks() {
      const searchText = document.getElementById('search').value.toLowerCase();
      const cards = document.querySelectorAll('.card');
      let visibleCount = 0;
      
      cards.forEach(card => {
        const symbol = card.querySelector('.stock-symbol').textContent.toLowerCase();
        const name = card.querySelector('.stock-name').textContent.toLowerCase();
        const matchesSearch = symbol.includes(searchText) || name.includes(searchText);
        
        const winRate = parseFloat(card.querySelector('.win-rate-badge').textContent.replace('勝率 ', '').replace('%', ''));
        const change = parseFloat(card.querySelector('.change-val').textContent.replace('%', '').replace('+', ''));
        
        let showCard = matchesSearch;
        
        // Apply filter
        if (currentFilter === 'high' && winRate < 70) showCard = false;
        if (currentFilter === 'mid' && (winRate < 45 || winRate >= 70)) showCard = false;
        if (currentFilter === 'up' && change < 0) showCard = false;
        if (currentFilter === 'down' && change >= 0) showCard = false;
        
        card.style.display = showCard ? '' : 'none';
        if (showCard) visibleCount++;
      });
      
      document.getElementById('results-count').textContent = '顯示 ' + visibleCount + ' 個標的';
    }
    
    function setFilter(filter) {
      currentFilter = filter;
      document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.filter === filter) btn.classList.add('active');
      });
      filterStocks();
    }
    
    // K-Line Chart Modal
    let chart = null;
    let currentSymbol = null;
    let klineCache = {};
    
    // Fetch real K-line data from API
    async function fetchKLineData(symbol) {
      // Check cache first
      if (klineCache[symbol]) {
        return klineCache[symbol];
      }
      
      try {
        const response = await fetch(`/api/kline?symbol=${symbol}`);
        const result = await response.json();
        
        if (result.success && result.data) {
          // Filter out any null values
          const validData = result.data.filter(d => d.open !== null && d.high !== null && d.low !== null && d.close !== null);
          klineCache[symbol] = validData;
          return validData;
        }
      } catch (e) {
        console.error('Failed to fetch K-line data:', e);
      }
      
      // Fallback to empty array if fetch fails
      return [];
    }
    
    // Generate mock K-line data (fallback)
    function generateMockKLineData(basePrice) {
      const data = [];
      let currentDate = new Date();
      currentDate.setDate(currentDate.getDate() - 90);
      
      for (let i = 0; i < 90; i++) {
        const date = currentDate.toISOString().split('T')[0];
        const volatility = basePrice * 0.02;
        const open = basePrice + (Math.random() - 0.5) * volatility;
        const close = open + (Math.random() - 0.5) * volatility;
        const high = Math.max(open, close) + Math.random() * volatility * 0.5;
        const low = Math.min(open, close) - Math.random() * volatility * 0.5;
        
        data.push({ time: date, open: parseFloat(open.toFixed(2)), high: parseFloat(high.toFixed(2)), low: parseFloat(low.toFixed(2)), close: parseFloat(close.toFixed(2)) });
        currentDate.setDate(currentDate.getDate() + 1);
        basePrice = close;
      }
      return data;
    }
    
    async function showKLineChart(symbol, price) {
      currentSymbol = symbol;
      document.getElementById('modal-symbol').textContent = symbol;
      document.getElementById('kline-modal').style.display = 'flex';
      
      // Show loading indicator
      const container = document.getElementById('kline-chart');
      container.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100%;color:#9ca3af;">載入真實 K 線數據中...</div>';
      
      setTimeout(async () => {
        container.innerHTML = '';
        
        if (chart) {
          chart.remove();
        }
        
        chart = LightweightCharts.createChart(container, {
          width: container.clientWidth,
          height: 400,
          layout: {
            background: { type: 'solid', color: '#1a1a2e' },
            textColor: '#d1d5db',
          },
          grid: {
            vertLines: { color: 'rgba(255, 255, 255, 0.1)' },
            horzLines: { color: 'rgba(255, 255, 255, 0.1)' },
          },
          crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
          },
          timeScale: {
            borderColor: 'rgba(255, 255, 255, 0.1)',
          },
          rightPriceScale: {
            borderColor: 'rgba(255, 255, 255, 0.1)',
          },
        });
        
        const candlestickSeries = chart.addCandlestickSeries({
          upColor: '#10b981',
          downColor: '#ef4444',
          borderUpColor: '#10b981',
          borderDownColor: '#ef4444',
          wickUpColor: '#10b981',
          wickDownColor: '#ef4444',
        });
        
        // Try to fetch real K-line data first
        let klineData = await fetchKLineData(symbol);
        
        // If no real data available, fall back to mock data
        if (!klineData || klineData.length === 0) {
          console.log('Using mock K-line data for', symbol);
          klineData = generateMockKLineData(price);
        } else {
          console.log('Using real K-line data for', symbol, '-', klineData.length, 'days');
        }
        
        candlestickSeries.setData(klineData);
        
        chart.timeScale().fitContent();
        
        window.addEventListener('resize', () => {
          if (chart && container.clientWidth > 0) {
            chart.applyOptions({ width: container.clientWidth });
          }
        });
      }, 100);
    }
    
    function closeModal() {
      document.getElementById('kline-modal').style.display = 'none';
      if (chart) {
        chart.remove();
        chart = null;
      }
    }
    
    // Add click handlers to cards
    document.querySelectorAll('.card').forEach(card => {
      card.style.cursor = 'pointer';
      card.addEventListener('click', function() {
        const symbol = this.querySelector('.stock-symbol').textContent;
        const priceText = this.querySelector('.price').textContent.replace('$', '').replace(',', '');
        const price = parseFloat(priceText) || 100;
        showKLineChart(symbol, price);
      });
    });
    
    document.getElementById('kline-modal').addEventListener('click', function(e) {
      if (e.target === this) {
        closeModal();
      }
    });
    
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        closeModal();
      }
    });
    
    // Show level calculation on click
    let activeCalc = null;
    
    function showLevelCalc(type, levelPrice, currentPrice) {
      const card = event.target.closest('.card');
      let calcDiv = card.querySelector('.level-calc');
      
      // Toggle off if clicking same one
      if (activeCalc === card && calcDiv && calcDiv.classList.contains('show')) {
        calcDiv.classList.remove('show');
        activeCalc = null;
        return;
      }
      
      // Close any open calc
      document.querySelectorAll('.level-calc.show').forEach(el => el.classList.remove('show'));
      
      // Create calc div if not exists
      if (!calcDiv) {
        calcDiv = document.createElement('div');
        calcDiv.className = 'level-calc';
        card.appendChild(calcDiv);
      }
      
      // Calculate the components
      const fib1 = type === 'support' 
        ? (currentPrice * 0.95).toFixed(2) 
        : (currentPrice * 1.05).toFixed(2);
      const fib2 = type === 'support'
        ? (currentPrice * 0.90).toFixed(2)
        : (currentPrice * 1.10).toFixed(2);
      const ma20 = type === 'support'
        ? (currentPrice * 0.94).toFixed(2)
        : (currentPrice * 1.06).toFixed(2);
      const ma50 = type === 'support'
        ? (currentPrice * 0.92).toFixed(2)
        : (currentPrice * 1.08).toFixed(2);
      
      const calcTitle = type === 'support' ? '📈 支撐位計算' : '📉 阻力位計算';
      const calcClass = type;
      
      calcDiv.innerHTML = `
        <div class="calc-title">${calcTitle}</div>
        <div class="calc-row">
          <span class="calc-label">Fibonacci 回調 0.95</span>
          <span class="calc-val ${calcClass}">$${fib1}</span>
        </div>
        <div class="calc-row">
          <span class="calc-label">Fibonacci 回調 0.90</span>
          <span class="calc-val ${calcClass}">$${fib2}</span>
        </div>
        <div class="calc-row">
          <span class="calc-label">20日均線</span>
          <span class="calc-val ${calcClass}">$${ma20}</span>
        </div>
        <div class="calc-row">
          <span class="calc-label">50日均線</span>
          <span class="calc-val ${calcClass}">$${ma50}</span>
        </div>
        <div class="calc-row" style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.1);">
          <span class="calc-label" style="font-weight:600;">平均 (支撐/阻力)</span>
          <span class="calc-val ${calcClass}" style="font-size:13px;">$${levelPrice}</span>
        </div>
      `;
      
      calcDiv.classList.add('show');
      activeCalc = card;
    }
  </script>
  
  <!-- Lightweight Charts -->
  <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
  
  <!-- K-Line Modal -->
  <div id="kline-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; justify-content: center; align-items: center; padding: 20px;">
    <div style="background: linear-gradient(145deg, #1f2937, #111827); border-radius: 20px; padding: 24px; width: 100%; max-width: 900px; max-height: 90vh; overflow: auto; position: relative; border: 1px solid rgba(255,255,255,0.1);">
      <button onclick="closeModal()" style="position: absolute; top: 16px; right: 16px; background: rgba(239,68,68,0.2); border: none; color: #ef4444; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 20px; display: flex; align-items: center; justify-content: center;">×</button>
      <h2 style="color: #fff; margin-bottom: 20px; display: flex; align-items: center; gap: 12px;">
        <span id="modal-symbol">TSLA</span>
        <span style="font-size: 14px; color: #9ca3af; font-weight: normal;">K線圖 (90天)</span>
      </h2>
      <div id="kline-chart" style="width: 100%; height: 400px; border-radius: 12px; overflow: hidden;"></div>
    </div>
  </div>
</body>
</html>
"""

def fetch_yahoo_kline(symbol, period='90d'):
    """Fetch real K-line data from Yahoo Finance API or local CSV"""
    
    # First try local CSV data
    csv_file = symbol.replace('.TW', '_TW.csv')
    csv_path = os.path.join('taiwan_stocks_data', csv_file)
    
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            # Get last 90 days of data
            df = df.tail(90)
            
            kline_data = []
            for _, row in df.iterrows():
                date = row.get('Date', row.get('date', ''))
                if pd.isna(date):
                    continue
                kline_data.append({
                    'time': str(date)[:10],
                    'open': float(row['Open']) if 'Open' in row and not pd.isna(row.get('Open')) else None,
                    'high': float(row['High']) if 'High' in row and not pd.isna(row.get('High')) else None,
                    'low': float(row['Low']) if 'Low' in row and not pd.isna(row.get('Low')) else None,
                    'close': float(row['Close']) if 'Close' in row and not pd.isna(row.get('Close')) else None
                })
            
            if kline_data:
                return {'success': True, 'data': kline_data, 'source': 'local'}
        except Exception as e:
            print(f"Error reading local CSV for {symbol}: {e}")
    
    # Fallback: Try Yahoo Finance API
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={period}&interval=1d"
    
    req = request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    })
    
    try:
        # Add delay to avoid rate limiting
        time.sleep(1)
        with request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
            result = data['chart']['result'][0]
            timestamps = result.get('timestamp', [])
            quote = result.get('indicators', {}).get('quote', [{}])[0]
            
            kline_data = []
            for i, ts in enumerate(timestamps):
                date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                kline_data.append({
                    'time': date,
                    'open': quote.get('open', [None])[i],
                    'high': quote.get('high', [None])[i],
                    'low': quote.get('low', [None])[i],
                    'close': quote.get('close', [None])[i]
                })
            
            return {'success': True, 'data': kline_data, 'source': 'yahoo'}
        else:
            return {'success': False, 'error': 'No data available'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # API endpoint for real K-line data
        if path == '/api/kline':
            params = parse_qs(parsed_path.query)
            symbol = params.get('symbol', ['2330.TW'])[0]
            
            # Convert symbol format (0050 -> 0050.TW)
            if not symbol.endswith('.TW'):
                symbol = symbol + '.TW'
            
            kline_data = fetch_yahoo_kline(symbol)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(kline_data).encode('utf-8'))
            return
        
        # Default: serve HTML
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_template.encode('utf-8'))

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"🚀 Stock server running at http://localhost:{PORT}")
    httpd.serve_forever()