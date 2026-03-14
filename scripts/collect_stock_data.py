#!/usr/bin/env python3
"""
Stock and Crypto Data Collector - V2
Uses more reliable data sources
"""

import json
import os
from datetime import datetime

# Install dependencies
os.system("pip install yfinance requests -q 2>/dev/null")

import yfinance as yf
import requests

BASE_DIR = os.path.expanduser("~/openclaw_data")

def get_taiwan_top100():
    """Get Taiwan stock top 100 - curated major stocks"""
    
    # Major Taiwan stocks (TWSE + OTC major companies)
    tw_major_stocks = [
        ('2330', '台積電'), ('2317', '鴻海'), ('2454', '聯發科'), ('6505', '台塑化'),
        ('2412', '中華電'), ('2881', '富邦金'), ('2882', '國泰金'), ('2891', '中信金'),
        ('2892', '第一金'), ('2308', '台達電'), ('2382', '廣達'), ('2395', '研華'),
        ('3008', '大立光'), ('2002', '中鋼'), ('1216', '統一'), ('1707', '葡萄王'),
        ('2006', '東和鋼鐵'), ('2015', '豐興'), ('2027', '大同'), ('2201', '裕隆'),
        ('2204', '中華'), ('2301', '光寶科'), ('2303', '聯電'), ('2316', '仁寶'),
        ('2327', '國巨'), ('2332', '友訊'), ('2337', '旺宏'), ('2344', '彩晶'),
        ('2347', '聯強'), ('2353', '宏碁'), ('2356', '英業達'), ('2357', '華碩'),
        ('2365', '昆盈'), ('2376', '技嘉'), ('2377', '微星'), ('2379', '瑞儀'),
        ('2383', '台光電'), ('2385', '群光'), ('2393', '億光'), ('2408', '南亞科'),
        ('2409', '友達'), ('2413', '環科'), ('2417', '圓剛'), ('2420', '新巨'),
        ('2421', '建準'), ('2423', '固緯'), ('2474', '可成'), ('2475', '華擎'),
        ('2476', '鉅祥'), ('2477', '美隆電'), ('2478', '大毅'), ('2480', '敦陽科'),
        ('2481', '強茂'), ('2485', '兆赫'), ('2486', '一詮'), ('2487', '慧友'),
        ('2492', '華新科'), ('2495', '普安'), ('2497', '怡利電'), ('2498', '宏達電'),
        ('3004', '臻鼎'), ('3005', '神基'), ('3006', '晶豪科'), ('3008', '大立光'),
        ('3014', '聯陽'), ('3015', '青雲'), ('3016', '嘉晶'), ('3017', '奇鋐'),
        ('3019', '亞光'), ('3034', '聯詠'), ('3035', '智原'), ('3036', '文曄'),
        ('3037', '欣興'), ('3038', '和碩'), ('3039', '中光電'), ('3041', '揚智'),
        ('3042', '晶技'), ('3045', '訊連'), ('3050', '豐達科'), ('3051', '創意'),
        ('3105', '穩懋'), ('3164', '景碩'), ('3171', '新天堂'), ('3176', '基亞'),
        ('3188', '鑫科'), ('3211', '順達'), ('3213', '茂迪'), ('3217', '大田'),
        ('3218', '大學光'), ('3221', '台嘉碩'), ('3227', '原相'), ('3228', '金麗科'),
        ('3230', '台硝'), ('3231', '航天'), ('3232', '中美晶'), ('3234', '光環'),
        ('3236', '千如'), ('3249', '鑫科'), ('3257', '虹冠電'), ('3260', '威剛'),
        ('3264', '欣銓'), ('3265', '台星科'), ('3266', '昇陽'), ('3272', '台塑生'),
        ('3276', '宇環'), ('3284', '太普高'), ('3285', '微端'), ('3287', '台原生'),
        ('3290', '東浦'), ('3291', '遠見'), ('3293', '矽瑪'), ('3294', '景碩'),
        ('3303', '岱稜'), ('3308', '崇越'), ('3310', '彩研'), ('3311', '景碩'),
        ('3312', '益通'), ('3313', '互動'), ('3316', '藻油'), ('3317', '尼克森'),
        ('3321', '大甲'), ('3323', '加高'), ('3324', '志超'), ('3325', '志超'),
        ('3332', '幸康'), ('3338', '泰碩'), ('3340', '光洋科'), ('3346', '理漢'),
        ('3356', '奇偶'), ('3360', '尚立'), ('3362', '先擎'), ('3379', '彬台'),
        ('3380', '明泰'), ('3388', '崇友'), ('3390', '旭隼'), ('3406', '玉山金控'),
        ('3413', '友達'), ('3416', '融程電'), ('3432', '台生材'), ('3437', '榮創'),
        ('3443', '創意'), ('3444', '利機'), ('3450', '聯傑'), ('3455', '由田'),
        ('3465', '科誠'), ('3466', '致振'), ('3467', '全局'), ('3479', '萊地利'),
        ('3483', '能耗'), ('3484', '牧德'), ('3489', '謙華'), ('3490', '朋程'),
        ('3491', '昇達科'), ('3492', '應華'), ('3494', '斐成'), ('3498', '陽程'),
        ('3499', '洋華'), ('3504', '研鼎'), ('3508', '位速'), ('3511', '矽瑪'),
        ('3512', '國巨'), ('3515', '佳必琪'), ('3516', '碩天'), ('3518', '柏騰'),
        ('3520', '振維'), ('3521', '鴝抆'), ('3522', '御新生'), ('3523', '守信'),
        ('3526', '鼎天'), ('3527', '聚積'), ('3528', '安馳'), ('3529', '力旺'),
        ('3530', '合邦'), ('3531', '先益'), ('3532', '台勝科'), ('3533', '嘉澤'),
        ('3535', '晶技'), ('3536', '弘塑'), ('3540', '曜越'), ('3541', '西柏'),
        ('3543', '達威'), ('3545', '敦泰'), ('3546', '宇峻'), ('3548', '居易'),
        ('3550', '亨泰光'), ('3551', '陶瓷'), ('3552', '同致'), ('3553', '力麒'),
        ('3555', '重力'), ('3556', '森霸'), ('3563', '威格'), ('3567', '逸昌'),
        ('3570', '大將'), ('3571', '三集'), ('3572', '迅德'), ('3576', '聯光通'),
        ('3580', '友威科'), ('3581', '博智'), ('3583', '辛耘'), ('3587', '耀發'),
        ('3588', '通嘉'), ('3591', '艾笛森'), ('3592', '亞泰'), ('3593', '力成'),
        ('3594', '磐儀'), ('3595', '山二'), ('3596', '帆宣'), ('3597', '映興'),
    ]
    
    # Remove duplicates
    seen = set()
    unique_stocks = []
    for s in tw_major_stocks:
        code = s[0]
        if code not in seen:
            seen.add(code)
            unique_stocks.append({'code': code, 'name': s[1], 'volume': 0})
    
    return unique_stocks[:100]

def get_us_top500():
    """Get US stock top 500"""
    
    us_symbols = [
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B', 'UNH',
        'JNJ', 'V', 'XOM', 'JPM', 'WMT', 'LLY', 'PG', 'MA', 'HD', 'CVX',
        'ABBV', 'MRK', 'PEP', 'KO', 'COST', 'AVGO', 'TMO', 'MCD', 'CSCO', 'ACN',
        'WFC', 'ABT', 'DHR', 'ADBE', 'NKE', 'CRM', 'TXN', 'PM', 'NEE', 'BMY',
        'ORCL', 'UNP', 'AMD', 'LIN', 'HON', 'QCOM', 'LOW', 'INTC', 'UPS', 'MS',
        'AMGN', 'CAT', 'IBM', 'GE', 'DE', 'BA', 'RTX', 'SBUX', 'SPGI', 'BLK',
        'PFE', 'INTU', 'AMAT', 'GS', 'MDLZ', 'AXP', 'ISRG', 'T', 'BKNG', 'MMM',
        'ADI', 'GILD', 'C', 'TJX', 'MDT', 'ADP', 'CVS', 'VRTX', 'REGN', 'ZTS',
        'CI', 'SYK', 'MO', 'CB', 'TMUS', 'CME', 'PLD', 'BSX', 'SCHW', 'CMG',
        'DUK', 'SO', 'NOC', 'USB', 'PGR', 'CL', 'ETN', 'ICE', 'MCK', 'EOG',
        'APH', 'MMC', 'EQIX', 'APD', 'HUM', 'PSA', 'FI', 'NSC', 'ITW', 'SLB',
        'WM', 'TGT', 'CCI', 'MSCI', 'LRCX', 'KLAC', 'MCO', 'ORLY', 'SHW', 'GD',
        'NEM', 'AON', 'EW', 'PNC', 'GM', 'CARR', 'AMT', 'KMB', 'PH', 'MU',
        'EMR', 'FCX', 'AJG', 'TFC', 'MCHP', 'RSG', 'NXPI', 'AIG', 'COF', 'ROP',
        'HCA', 'AFL', 'SRE', 'AMP', 'PSX', 'ALL', 'AEP', 'PCAR', 'ECL', 'D',
        'OR', 'CNC', 'WELL', 'CTVA', 'FAST', 'CMI', 'O', 'HES', 'KMI', 'WMB',
        'TT', 'DD', 'OXY', 'FTNT', 'DFS', 'SNPS', 'KEYS', 'EBAY', 'BK', 'TDG',
        'ANSS', 'MSI', 'PCG', 'SYY', 'TEL', 'DLR', 'A', 'PAYX', 'CTAS', 'GLW',
        'IQV', 'HSY', 'YUM', 'MAR', 'VRSK', 'CPRT', 'TRV', 'ODFL', 'MLM', 'EA',
        'FTV', 'EXC', 'CDNS', 'IDXX', 'EIX', 'WEC', 'LHX', 'ROK', 'LH', 'AME',
        'PHM', 'MKC', 'DHI', 'APTV', 'GEHC', 'MTD', 'RMD', 'TTWO', 'WAB', 'VMC',
        'AZO', 'CTSH', 'ADSK', 'YUMC', 'MPWR', 'ALGN', 'BIIB', 'ZM', 'OKTA', 'SNOW',
        'CRWD', 'PANW', 'NET', 'MSTR', 'VEEV', 'BILL', 'TWLO', 'SPLK', 'HUBS', 'ZS',
        'ABNB', 'RBLX', 'U', 'PATH', 'SNAP', 'PINS', 'DBX', 'DOCU', 'WDAY', 'TTD',
        'COUP', 'SUMO', 'VE', 'FVRR', 'ESTC', 'MDB', 'NOW', 'WEX', 'PYPL', 'SQ',
        'SHOP', 'STNE', 'GLOB', 'UPWK', 'ASML', 'SAP', 'SNE', 'TSM', 'MELI', 'NIO',
        'XPEV', 'LI', 'BABA', 'BIDU', 'NTES', 'JD', 'PDD', 'TAL', 'EDU', 'BILI',
        'DOYU', 'MOMO', 'YY', 'IQ', 'TME', 'HUYA', 'BEKE', 'KE', 'TUYA', 'IQIYI',
    ]
    
    unique_symbols = list(set(us_symbols))[:500]
    
    stocks = []
    print(f"Fetching volume data for {len(unique_symbols)} US stocks...")
    
    for i, symbol in enumerate(unique_symbols):
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            volume = info.get('volume', 0) or 0
            name = info.get('longName', info.get('shortName', symbol)) or symbol
            
            stocks.append({
                'symbol': symbol,
                'name': name,
                'volume': volume
            })
            
            if (i + 1) % 20 == 0:
                print(f"Progress: {i+1}/{len(unique_symbols)}")
                
        except Exception as e:
            continue
    
    stocks.sort(key=lambda x: x['volume'], reverse=True)
    
    return stocks[:500]

def get_crypto_top10():
    """Get Crypto top 10 with volume data"""
    
    crypto_ids = [
        'bitcoin', 'ethereum', 'solana', 'binancecoin', 'ripple', 
        'cardano', 'dogecoin', 'avalanche-2', 'polkadot', 'matic-network'
    ]
    
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'ids': ','.join(crypto_ids),
        'order': 'market_cap_desc',
        'per_page': 10,
        'page': 1,
        'sparkline': False,
        'price_change_percentage': '24h'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        cryptos = []
        for coin in data:
            cryptos.append({
                'symbol': coin['symbol'].upper(),
                'name': coin['name'],
                'volume': coin.get('total_volume', 0) or 0,
                'price': coin.get('current_price', 0),
                'change_24h': coin.get('price_change_percentage_24h', 0)
            })
        
        return cryptos
        
    except Exception as e:
        print(f"Crypto fetch error: {e}")
        
        return [
            {'symbol': 'BTC', 'name': 'Bitcoin', 'volume': 0, 'price': 0, 'change_24h': 0},
            {'symbol': 'ETH', 'name': 'Ethereum', 'volume': 0, 'price': 0, 'change_24h': 0},
            {'symbol': 'SOL', 'name': 'Solana', 'volume': 0, 'price': 0, 'change_24h': 0},
            {'symbol': 'BNB', 'name': 'BNB', 'volume': 0, 'price': 0, 'change_24h': 0},
            {'symbol': 'XRP', 'name': 'XRP', 'volume': 0, 'price': 0, 'change_24h': 0},
            {'symbol': 'ADA', 'name': 'Cardano', 'volume': 0, 'price': 0, 'change_24h': 0},
            {'symbol': 'DOGE', 'name': 'Dogecoin', 'volume': 0, 'price': 0, 'change_24h': 0},
            {'symbol': 'AVAX', 'name': 'Avalanche', 'volume': 0, 'price': 0, 'change_24h': 0},
            {'symbol': 'DOT', 'name': 'Polkadot', 'volume': 0, 'price': 0, 'change_24h': 0},
            {'symbol': 'MATIC', 'name': 'Polygon', 'volume': 0, 'price': 0, 'change_24h': 0}
        ]

def main():
    print("=" * 50)
    print("Stock & Crypto Data Collector")
    print("=" * 50)
    
    # 1. Taiwan Top 100
    print("\n[1/3] Fetching Taiwan Top 100 stocks...")
    tw_stocks = get_taiwan_top100()
    print(f"Got {len(tw_stocks)} Taiwan stocks")
    
    # 2. US Top 500
    print("\n[2/3] Fetching US Top 500 stocks...")
    us_stocks = get_us_top500()
    print(f"Got {len(us_stocks)} US stocks")
    
    # 3. Crypto Top 10
    print("\n[3/3] Fetching Crypto Top 10...")
    cryptos = get_crypto_top10()
    print(f"Got {len(cryptos)} cryptos")
    
    # Save data
    print("\n[Saving Data]")
    
    # Taiwan
    tw_path = os.path.join(BASE_DIR, "stocks/tw/top100.json")
    os.makedirs(os.path.dirname(tw_path), exist_ok=True)
    with open(tw_path, 'w', encoding='utf-8') as f:
        json.dump({
            'updated_at': datetime.now().isoformat(),
            'count': len(tw_stocks),
            'data': tw_stocks
        }, f, ensure_ascii=False, indent=2)
    print(f"Saved: {tw_path}")
    
    # US
    us_path = os.path.join(BASE_DIR, "stocks/us/top500.json")
    os.makedirs(os.path.dirname(us_path), exist_ok=True)
    with open(us_path, 'w', encoding='utf-8') as f:
        json.dump({
            'updated_at': datetime.now().isoformat(),
            'count': len(us_stocks),
            'data': us_stocks
        }, f, ensure_ascii=False, indent=2)
    print(f"Saved: {us_path}")
    
    # Crypto
    crypto_path = os.path.join(BASE_DIR, "crypto/top10.json")
    os.makedirs(os.path.dirname(crypto_path), exist_ok=True)
    with open(crypto_path, 'w', encoding='utf-8') as f:
        json.dump({
            'updated_at': datetime.now().isoformat(),
            'count': len(cryptos),
            'data': cryptos
        }, f, ensure_ascii=False, indent=2)
    print(f"Saved: {crypto_path}")
    
    print("\n" + "=" * 50)
    print("Data collection completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()
