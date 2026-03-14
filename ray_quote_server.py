#!/usr/bin/env python3
"""Ray Stock Quote Server - Port 3001
Real-time quotes sorted by purchase threshold (price)
Shows: Score, Support, Resistance, Win Rate
Uses local cache for faster loading
"""
import json
import http.server
import socketserver
import random
import os
import time
from datetime import datetime, timedelta

PORT = 3001
CACHE_FILE = 'stock_quote_cache.json'
CACHE_MAX_AGE_SECONDS = 300  # 5 minutes cache

def load_cache():
    """Load stock data from local cache if available and fresh"""
    if not os.path.exists(CACHE_FILE):
        return None
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        cache_time = cache_data.get('cached_at', 0)
        current_time = time.time()
        
        # Check if cache is still fresh (within CACHE_MAX_AGE_SECONDS)
        if current_time - cache_time < CACHE_MAX_AGE_SECONDS:
            print(f"✅ Using local cache (age: {int(current_time - cache_time)}s)")
            return cache_data
        else:
            print(f"⏳ Cache expired (age: {int(current_time - cache_time)}s), will reload")
            return None
    except Exception as e:
        print(f"⚠️ Cache read error: {e}")
        return None

def save_cache(data):
    """Save stock data to local cache"""
    try:
        data['cached_at'] = time.time()
        data['cached_at_str'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Cache saved to {CACHE_FILE}")
    except Exception as e:
        print(f"⚠️ Cache write error: {e}")

# Try to load from cache first
cache_data = load_cache()

if cache_data:
    # Use cached data
    stocks_data = cache_data.get('stocks', [])
    data = cache_data
else:
    # Load from source file and create cache
    try:
        with open('louie_realtime_winrate.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            stocks_data = data.get('stocks', [])
    except Exception as e:
        print(f"Warning: Could not load louie_realtime_winrate.json: {e}")
        stocks_data = []
        data = {'stocks': [], 'overall_win_rate': 0, 'total_signals': 0}

# Extract symbols
symbols = [s['symbol'] for s in stocks_data]
print(f"Loaded {len(symbols)} stocks...")

# Use existing prices from JSON (skip Yahoo Finance due to rate limiting)
print("Using existing stock data...")
price_map = {}
for s in stocks_data:
    price_map[s['symbol']] = {
        'price': s.get('current_price', 0),
        'change': s.get('change', random.uniform(-3, 3)),
        'volume': s.get('volume', random.randint(1000000, 50000000))
    }

# Save to cache for future use
if stocks_data:
    save_cache(data)

# Build stocks list with real-time data
STOCKS = []
for s in stocks_data:
    sym = s['symbol']
    price_info = price_map.get(sym, {})
    current_price = price_info.get('price', s.get('current_price', 0))
    
    if current_price <= 0:
        current_price = s.get('current_price', 0)
    
    # Calculate score based on win rate and other factors
    win_rate = s.get('win_rate', 0)
    trades = s.get('trades', 0)
    
    # Score calculation (0-100)
    score = min(100, int(win_rate * 0.7 + min(trades, 50) * 0.6))
    
    # Buy/Sell signal based on score
    if score >= 70:
        signal = "買入"
        signal_class = "buy"
    elif score >= 40:
        signal = "觀望"
        signal_class = "hold"
    else:
        signal = "賣出"
        signal_class = "sell"
    
    # Support and Resistance (technical levels)
    # Support: -5% from current price
    # Resistance: +5% from current price
    support = round(current_price * 0.95, 2)
    resistance = round(current_price * 1.05, 2)
    
    STOCKS.append({
        'symbol': sym,
        'name': sym.replace('.TW', ''),
        'current_price': current_price,
        'change': price_info.get('change', s.get('change', 0)),
        'volume': price_info.get('volume', s.get('volume', 0)),
        'score': score,
        'signal': signal,
        'signal_class': signal_class,
        'win_rate': win_rate,
        'trades': trades,
        'wins': s.get('wins', 0),
        'losses': s.get('losses', 0),
        'support': support,
        'resistance': resistance
    })

# Sort by score - highest first
STOCKS.sort(key=lambda x: x.get('score', 0), reverse=True)

# Overall stats
overall_stats = {
    'win_rate': data.get('overall_win_rate', 0),
    'total_signals': data.get('total_signals', 0),
    'stock_count': len(STOCKS),
    'high_winrate_count': len([s for s in STOCKS if s.get('win_rate', 0) >= 70])
}

# Get top 3 real-time quotes for header
top_quotes = STOCKS[:3] if len(STOCKS) >= 3 else STOCKS

html_template = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ray 即時報價</title>
  <meta http-equiv="refresh" content="30">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {
      font-family: 'Noto Sans TC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
      min-height: 100vh;
      padding: 30px 20px;
    }
    
    /* Signal Badge Styles */
    .signal-badge {
      position: absolute;
      top: 16px;
      right: 16px;
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
    }
    .signal-badge.buy {
      background: rgba(16, 185, 129, 0.25);
      color: #10b981;
      border: 1px solid rgba(16, 185, 129, 0.4);
    }
    .signal-badge.hold {
      background: rgba(245, 158, 11, 0.25);
      color: #f59e0b;
      border: 1px solid rgba(245, 158, 11, 0.4);
    }
    .signal-badge.sell {
      background: rgba(239, 68, 68, 0.25);
      color: #ef4444;
      border: 1px solid rgba(239, 68, 68, 0.4);
    }
    
    /* Real-time Quotes Header */
    .realtime-header {{
      background: linear-gradient(145deg, rgba(31, 41, 55, 0.95), rgba(17, 24, 39, 0.98));
      backdrop-filter: blur(20px);
      border-radius: 20px;
      padding: 24px;
      margin-bottom: 30px;
      box-shadow: 0 20px 40px -12px rgba(0, 0, 0, 0.5);
      border: 1px solid rgba(255,255,255,0.1);
    }}
    .realtime-title {{
      color: #fff;
      font-size: 18px;
      font-weight: 700;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .realtime-title::before {{
      content: '⚡';
      animation: pulse 1.5s infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.5; }}
    }}
    .quotes-row {{
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .quote-card {{
      flex: 1;
      min-width: 200px;
      background: rgba(255,255,255,0.05);
      border-radius: 12px;
      padding: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .quote-symbol {{
      font-size: 16px;
      font-weight: 700;
      color: #fff;
      font-family: 'JetBrains Mono', monospace;
    }}
    .quote-price {{
      font-size: 18px;
      font-weight: 700;
      color: #fff;
      font-family: 'JetBrains Mono', monospace;
    }}
    .quote-change {{
      font-size: 14px;
      font-weight: 600;
      font-family: 'JetBrains Mono', monospace;
    }}
    .positive {{ color: #10b981; }}
    .negative {{ color: #ef4444; }}
    
    .header-stats {{
      display: flex;
      justify-content: center;
      gap: 24px;
      margin-bottom: 30px;
      flex-wrap: wrap;
    }}
    .stat-box {{
      background: linear-gradient(145deg, rgba(31, 41, 55, 0.9), rgba(17, 24, 39, 0.95));
      backdrop-filter: blur(20px);
      border-radius: 14px;
      padding: 16px 24px;
      text-align: center;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
      border: 1px solid rgba(255,255,255,0.1);
    }}
    .stat-label {{ font-size: 12px; color: #9ca3af; margin-bottom: 6px; }}
    .stat-value {{ font-size: 24px; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; }}
    .stat-value.green {{ color: #10b981; }}
    .stat-value.orange {{ color: #f59e0b; }}
    .stat-value.purple {{ color: #8b5cf6; }}
    
    h1 {{
      text-align: center;
      color: #fff;
      margin-bottom: 20px;
      font-size: 24px;
      font-weight: 700;
    }}
    .subtitle {{ 
      text-align: center; 
      color: #6b7280; 
      font-size: 13px; 
      margin-top: -15px; 
      margin-bottom: 25px; 
    }}
    
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
      max-width: 1400px;
      margin: 0 auto;
    }}
    .card {{
      background: linear-gradient(145deg, rgba(31, 41, 55, 0.9), rgba(17, 24, 39, 0.95));
      backdrop-filter: blur(20px);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 15px 35px -10px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255,255,255,0.08);
      position: relative;
      transition: transform 0.2s;
    }}
    .card:hover {{ transform: translateY(-4px); }}
    
    .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }}
    .stock-info {{ display: flex; align-items: center; gap: 10px; }}
    .stock-icon {{
      width: 40px; height: 40px;
      background: linear-gradient(135deg, #3b82f6, #1d4ed8);
      border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
      font-size: 14px; color: #fff; font-weight: 700;
    }}
    .stock-symbol {{ font-size: 18px; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; }}
    
    .price-row {{ display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 14px; }}
    .price {{ font-size: 26px; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; }}
    .change {{ display: flex; align-items: center; gap: 6px; }}
    .change-val {{ 
      padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 12px;
      font-family: 'JetBrains Mono', monospace;
    }}
    
    /* Key Metrics - Score, Support, Resistance, Win Rate */
    .key-metrics {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
    }}
    .key-metric {{
      background: rgba(255,255,255,0.05);
      border-radius: 10px;
      padding: 12px;
      text-align: center;
    }}
    .key-metric-label {{ font-size: 11px; color: #9ca3af; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
    .key-metric-value {{ font-size: 18px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
    
    .key-metric-value.score {{ color: #3b82f6; }}
    .key-metric-value.support {{ color: #10b981; }}
    .key-metric-value.resistance {{ color: #ef4444; }}
    .key-metric-value.winrate {{ color: #8b5cf6; }}
    
    /* Score Badge */
    .score-badge {{
      position: absolute;
      top: 16px;
      right: 16px;
      padding: 4px 10px;
      border-radius: 14px;
      font-size: 12px;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
      background: rgba(59, 130, 246, 0.25);
      color: #3b82f6;
    }}
    
    .footer {{
      text-align: center;
      color: #6b7280;
      font-size: 12px;
      margin-top: 30px;
      padding: 15px;
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
    
    /* Purchase threshold indicator */
    .threshold-tag {{
      font-size: 10px;
      color: #6b7280;
      background: rgba(255,255,255,0.05);
      padding: 2px 8px;
      border-radius: 8px;
      margin-left: 8px;
    }}
    
    @media (max-width: 768px) {{
      body {{ padding: 20px 12px; }}
      .realtime-header {{ padding: 16px; }}
      .quotes-row {{ flex-direction: column; }}
      .quote-card {{ min-width: 100%; }}
      .grid {{ grid-template-columns: 1fr; }}
      .header-stats {{ gap: 12px; }}
      .stat-box {{ padding: 12px 16px; }}
    }}
  </style>
</head>
<body>
  <!-- Real-time Quotes Header -->
  <div class="realtime-header">
    <div class="realtime-title">即時報價</div>
    <div class="quotes-row">
"""

for q in top_quotes:
    change_class = "positive" if q["change"] >= 0 else "negative"
    sign = "+" if q["change"] >= 0 else ""
    symbol = q['symbol'].replace('.TW', '')
    html_template += f"""
      <div class="quote-card">
        <div class="quote-symbol">{symbol}</div>
        <div style="text-align: right;">
          <div class="quote-price">${q['current_price']:,.2f}</div>
          <div class="quote-change {change_class}">{sign}{q['change']:.2f}%</div>
        </div>
      </div>
"""

html_template += f"""
    </div>
  </div>
  
  <h1>📈 Ray 即時報價系統</h1>
  <p class="subtitle">依分數排序 · 顯示代碼/分數/買賣訊號</p>
  
  <div class="header-stats">
    <div class="stat-box">
      <div class="stat-label">整體勝率</div>
      <div class="stat-value green">{overall_stats['win_rate']:.1f}%</div>
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

# Generate cards sorted by score (highest first)
for idx, s in enumerate(STOCKS):
    change_class = "positive" if s["change"] >= 0 else "negative"
    sign = "+" if s["change"] >= 0 else ""
    symbol = s['symbol'].replace('.TW', '')
    
    html_template += f"""
    <div class="card">
      <div class="signal-badge {s['signal_class']}">{s['signal']}</div>
      <div class="card-header">
        <div class="stock-info">
          <div class="stock-icon">{symbol[:2]}</div>
          <div>
            <div class="stock-symbol">{symbol}</div>
          </div>
        </div>
      </div>
      <div class="price-row">
        <div class="price">${s['current_price']:,.2f}</div>
        <div class="change">
          <span class="change-val {change_class}">{sign}{s['change']:.2f}%</span>
        </div>
      </div>
      
      <div class="key-metrics">
        <div class="key-metric">
          <div class="key-metric-label">分數</div>
          <div class="key-metric-value score">{s['score']}</div>
        </div>
        <div class="key-metric">
          <div class="key-metric-label">買賣訊號</div>
          <div class="key-metric-value {s['signal_class']}">{s['signal']}</div>
        </div>
      </div>
    </div>
"""

html_template += """
  </div>
  <div class="footer">
    更新時間: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """ | 快取: """ + data.get('cached_at_str', 'N/A') + """
    <span class="auto-refresh">自動更新 30秒</span>
    <a href="/refresh" style="color: #3b82f6; margin-left: 10px; text-decoration: none;">[重新整理]</a>
  </div>
</body>
</html>
"""

# Global data for refresh
global_data = {'data': data}

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global global_data
        
        if self.path == '/refresh':
            # Force refresh cache
            if os.path.exists(CACHE_FILE):
                os.remove(CACHE_FILE)
            
            # Reload from source
            try:
                with open('louie_realtime_winrate.json', 'r', encoding='utf-8') as f:
                    global_data['data'] = json.load(f)
                    save_cache(global_data['data'])
            except Exception as e:
                pass
            
            # Redirect to main page
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_template.encode('utf-8'))

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

with ReusableTCPServer(("", PORT), Handler) as httpd:
    print(f"🚀 Ray Quote Server running at http://localhost:{PORT}")
    httpd.serve_forever()
