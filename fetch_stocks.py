#!/usr/bin/env python3
"""Fetch stock data with volume for Taiwan, US, and Crypto markets"""

import json
import yfinance as yf
from datetime import datetime, timedelta
import time

def fetch_volume_data(symbols, name_map):
    """Fetch volume data for a list of symbols"""
    result = []
    for i, sym in enumerate(symbols):
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            volume = info.get('volume', 0) or info.get('averageVolume', 0) or 0
            
            # Get historical data for the past month
            hist = ticker.history(period="1mo")
            history = []
            if not hist.empty:
                for date, row in hist.iterrows():
                    history.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "open": float(row['Open']) if 'Open' in row else None,
                        "high": float(row['High']) if 'High' in row else None,
                        "low": float(row['Low']) if 'Low' in row else None,
                        "close": float(row['Close']) if 'Close' in row else None,
                        "volume": int(row['Volume']) if 'Volume' in row else 0
                    })
            
            name = name_map.get(sym, sym)
            result.append({
                "symbol": sym,
                "name": name,
                "volume": int(volume),
                "history": history
            })
            print(f"[{i+1}/{len(symbols)}] {sym}: volume={volume}, history_days={len(history)}")
            time.sleep(0.1)  # Rate limiting
        except Exception as e:
            print(f"[{i+1}/{len(symbols)}] {sym}: ERROR - {e}")
            name = name_map.get(sym, sym)
            result.append({
                "symbol": sym,
                "name": name,
                "volume": 0,
                "history": []
            })
    return result

# Taiwan stocks
print("=== Processing Taiwan Top 100 ===")
with open('/Users/changrunlin/.openclaw/workspace/tw_top100_raw.json', 'r', encoding='utf-8') as f:
    tw_data = json.load(f)

tw_symbols = [item['symbol'] for item in tw_data]
tw_names = {item['symbol']: item['name'] for item in tw_data}
taiwan_result = fetch_volume_data(tw_symbols, tw_names)

with open('/Users/changrunlin/.openclaw/workspace/tw_top100.json', 'w', encoding='utf-8') as f:
    json.dump(taiwan_result, f, ensure_ascii=False, indent=2)
print(f"Taiwan: saved {len(taiwan_result)} stocks")

# US stocks
print("\n=== Processing US Top 500 ===")
with open('/Users/changrunlin/.openclaw/workspace/us_top500_raw.json', 'r', encoding='utf-8') as f:
    us_data = json.load(f)

us_symbols = [item['symbol'] for item in us_data]
us_names = {item['symbol']: item['name'] for item in us_data}
us_result = fetch_volume_data(us_symbols, us_names)

with open('/Users/changrunlin/.openclaw/workspace/us_top500.json', 'w', encoding='utf-8') as f:
    json.dump(us_result, f, ensure_ascii=False, indent=2)
print(f"US: saved {len(us_result)} stocks")

# Crypto
print("\n=== Processing Crypto ===")
crypto_symbols = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "MATIC-USD"
]
crypto_names = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "SOL-USD": "Solana",
    "BNB-USD": "Binance Coin",
    "XRP-USD": "XRP",
    "ADA-USD": "Cardano",
    "DOGE-USD": "Dogecoin",
    "AVAX-USD": "Avalanche",
    "DOT-USD": "Polkadot",
    "MATIC-USD": "Polygon"
}
crypto_result = fetch_volume_data(crypto_symbols, crypto_names)

with open('/Users/changrunlin/.openclaw/workspace/crypto.json', 'w', encoding='utf-8') as f:
    json.dump(crypto_result, f, ensure_ascii=False, indent=2)
print(f"Crypto: saved {len(crypto_result)} coins")

# Create final combined file
print("\n=== Creating combined file ===")
final_data = {
    "taiwan": taiwan_result,
    "us": us_result,
    "crypto": crypto_result
}

with open('/Users/changrunlin/.openclaw/workspace/stocks_data.json', 'w', encoding='utf-8') as f:
    json.dump(final_data, f, ensure_ascii=False, indent=2)

print(f"\nDone! Taiwan: {len(taiwan_result)}, US: {len(us_result)}, Crypto: {len(crypto_result)}")
