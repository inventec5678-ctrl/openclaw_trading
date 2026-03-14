#!/usr/bin/env python3
"""
基本面資料收集腳本
使用 yfinance 收集：營收、財報、EPS、市值、本益比
台股：2330.TW, 2317.TW, 2454.TW, 0050.TW
美股：AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA
"""

import yfinance as yf
import json
import os
from datetime import datetime

# 股票清單
TAIWAN_STOCKS = ['2330.TW', '2317.TW', '2454.TW', '0050.TW']
US_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA']
ALL_STOCKS = TAIWAN_STOCKS + US_STOCKS

OUTPUT_DIR = os.path.expanduser('~/openclaw_data/fundamental')

def get_fundamental_data(ticker_symbol):
    """取得單一股票的基本面資料"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        data = {
            'symbol': ticker_symbol,
            'name': info.get('longName', info.get('shortName', 'N/A')),
            'timestamp': datetime.now().isoformat(),
            'currency': info.get('currency', 'N/A'),
            'exchange': info.get('exchange', 'N/A'),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'fundamental': {
                'market_cap': info.get('marketCap'),  # 市值
                'market_cap_str': f"${info.get('marketCap', 0)/1e9:.2f}B" if info.get('marketCap') and info.get('marketCap') > 1e9 else f"${info.get('marketCap', 0)/1e6:.2f}M" if info.get('marketCap') else "N/A",
                'revenue': info.get('totalRevenue'),  # 營收
                'revenue_growth': info.get('revenueGrowth'),  # 營收成長率
                'pe_ratio': info.get('trailingPE'),  # 本益比
                'forward_pe': info.get('forwardPE'),
                'eps': info.get('trailingEps'),  # EPS
                'forward_eps': info.get('forwardEps'),
                'peg_ratio': info.get('pegRatio'),
                'profit_margin': info.get('profitMargin'),
                'operating_margin': info.get('operatingMargin'),
                'roe': info.get('returnOnEquity'),
                'debt_to_equity': info.get('debtToEquity'),
                'beta': info.get('beta'),
                'dividend_yield': info.get('dividendYield'),
                'dividend_rate': info.get('dividendRate'),
                'book_value': info.get('bookValue'),
                'price_to_book': info.get('priceToBook'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'fifty_day_average': info.get('fiftyDayAverage'),
                'two_hundred_day_average': info.get('twoHundredDayAverage'),
                'price': info.get('currentPrice', info.get('regularMarketPrice')),
            }
        }
            
        return data
        
    except Exception as e:
        return {
            'symbol': ticker_symbol,
            'error': str(e)
        }

def main():
    print("=" * 60)
    print("基本面資料收集")
    print("=" * 60)
    
    all_data = {}
    
    for symbol in ALL_STOCKS:
        print(f"\n正在收集 {symbol} 基本面資料...")
        data = get_fundamental_data(symbol)
        all_data[symbol] = data
        
        if 'error' in data:
            print(f"  ❌ 錯誤: {data['error']}")
        else:
            print(f"  ✓ {data.get('name', 'N/A')}")
            print(f"    市值: {data['fundamental'].get('market_cap', 'N/A')}")
            print(f"    本益比: {data['fundamental'].get('pe_ratio', 'N/A')}")
            print(f"    EPS: {data['fundamental'].get('eps', 'N/A')}")
    
    # 儲存為 JSON
    output_file = os.path.join(OUTPUT_DIR, 'fundamental_data.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n{'=' * 60}")
    print(f"✓ 基本面資料已儲存至: {output_file}")
    print("=" * 60)
    
    # 產生摘要報告
    print("\n📊 基本面摘要:")
    print("-" * 60)
    for symbol in ALL_STOCKS:
        if symbol in all_data and 'fundamental' in all_data[symbol]:
            fund = all_data[symbol]['fundamental']
            name = all_data[symbol].get('name', symbol)
            mc = fund.get('market_cap')
            pe = fund.get('pe_ratio')
            eps = fund.get('eps')
            
            mc_str = f"${mc/1e9:.2f}B" if mc and mc > 1e9 else f"${mc/1e6:.2f}M" if mc else "N/A"
            pe_str = f"{pe:.2f}" if pe else "N/A"
            eps_str = f"${eps:.2f}" if eps else "N/A"
            
            print(f"{symbol:8} | {name[:20]:20} | 市值: {mc_str:>12} | PE: {pe_str:>6} | EPS: {eps_str}")

if __name__ == '__main__':
    main()
