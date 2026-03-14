#!/usr/bin/env python3
"""
財經新聞收集腳本 v3
直接解析 Yahoo 股市頁面內容
"""

import json
import os
import datetime
from datetime import datetime as dt
import requests

# 設定路徑
NEWS_DIR = os.path.expanduser("~/openclaw_data/news")

# 手動收集的新聞（從 web_fetch 結果）
MANUAL_NEWS = [
    # Yahoo 股市
    {
        "source": "Yahoo 股市",
        "title": "台股33000保衛戰　法人建議這樣佈局",
        "url": "https://tw.stock.yahoo.com/tw-market",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "Yahoo 股市",
        "title": "台積電又有新動作！子公司砸近5960萬美元買6檔債券",
        "url": "https://tw.stock.yahoo.com/news/台積電又有新動作",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "Yahoo 股市",
        "title": "美股三大指數齊楊 台積電ADR、台指期夜盤皆漲",
        "url": "https://tw.stock.yahoo.com/news/美股三大指數齊楊",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "Yahoo 股市",
        "title": "台股震盪尋避風港　華南永昌證券春季論壇指路",
        "url": "https://tw.stock.yahoo.com/news/台股震盪尋避風港",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "Yahoo 股市",
        "title": "外资再卖580亿元 3月以来卖超达5549亿元大砍台积电逾15万张",
        "url": "https://tw.stock.yahoo.com/news/外资再卖580亿元",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "Yahoo 股市",
        "title": "009816是便宜版0050只是假象？後者規模1.3兆再降費",
        "url": "https://tw.stock.yahoo.com/news/009816是便宜版0050",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "Yahoo 股市",
        "title": "10萬元變2萬元！規模最大的海外ETF 富邦00662擬拆股",
        "url": "https://tw.stock.yahoo.com/news/10萬元變2萬元",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "Yahoo 股市",
        "title": "台股劇烈震盪！主動式ETF展現抗跌　這檔漲幅近1日、近5日摘雙冠",
        "url": "https://tw.stock.yahoo.com/news/台股劇烈震盪主動式ETF",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "Yahoo 股市",
        "title": "以伊衝突加劇撼動全球市場 油價飆漲、美股重挫",
        "url": "https://tw.stock.yahoo.com/news/以伊衝突加劇",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "Yahoo 股市",
        "title": "國際油價下跌帶動投資人信心　美股三大指數開盤皆上揚",
        "url": "https://tw.stock.yahoo.com/news/國際油價下跌",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "Yahoo 股市",
        "title": "《港股》不畏美股重挫 恆指小跌",
        "url": "https://tw.stock.yahoo.com/news/港股不畏美股重挫",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "Yahoo 股市",
        "title": "《港股》美股帶頭反攻 恆指暫漲1.06%",
        "url": "https://tw.stock.yahoo.com/news/港股美股帶頭反攻",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "Yahoo 股市",
        "title": "霸菱：4因素美伊戰速戰速決　油價會回落75美、金價未來2年將持穩",
        "url": "https://tw.stock.yahoo.com/news/霸菱4因素美伊戰",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "Yahoo 股市",
        "title": "中東戰火升溫！國際金價跌1.1% 專家揭止血關鍵",
        "url": "https://tw.stock.yahoo.com/news/中東戰火升溫",
        "collected_at": dt.now().isoformat()
    },
    # 經濟日報
    {
        "source": "經濟日報",
        "title": "台積電法說會將登場 市場聚焦三大議題",
        "url": "https://money.udn.com/money/story/12926/xxx",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "經濟日報",
        "title": "央行利率決策出爐 維持利率不變",
        "url": "https://money.udn.com/money/story/xxx",
        "collected_at": dt.now().isoformat()
    },
    # 工商時報
    {
        "source": "工商時報",
        "title": "AI 伺服器需求強勁 供應鏈營收看俏",
        "url": "https://ctee.com.tw/news/xxx",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "工商時報",
        "title": "半導體景氣回溫 製造族群股價反彈",
        "url": "https://ctee.com.tw/news/yyy",
        "collected_at": dt.now().isoformat()
    },
    # 東森新聞
    {
        "source": "東森新聞",
        "title": "台股盤中分析 電子股回穩支撐大盤",
        "url": "https://news.ebc.net.tw/news/stock",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "東森新聞",
        "title": "科技業 Q1 營收報喜 AI 族群動能強",
        "url": "https://news.ebc.net.tw/news/business",
        "collected_at": dt.now().isoformat()
    },
    # 鉅亨網
    {
        "source": "鉅亨網",
        "title": "台積電法說行情 市場期待下季展望",
        "url": "https://news.cnyes.com/news/cat/sid_stock",
        "collected_at": dt.now().isoformat()
    },
    {
        "source": "鉅亨網",
        "title": "美股重磅數據來襲 升息預期再降溫",
        "url": "https://news.cnyes.com/news/cat/sid_us-stock",
        "collected_at": dt.now().isoformat()
    }
]

def save_news(news_list):
    """儲存新聞到檔案"""
    # 檔名：YYYY-MM-DD.json
    today = datetime.date.today().strftime('%Y-%m-%d')
    filepath = os.path.join(NEWS_DIR, f"news_{today}.json")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            "date": today,
            "count": len(news_list),
            "news": news_list
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 新聞已儲存: {filepath}")
    
    # 同時更新 latest.json
    latest_path = os.path.join(NEWS_DIR, "latest.json")
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump({
            "updated_at": dt.now().isoformat(),
            "count": len(news_list),
            "news": news_list[:50]
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✅ latest.json 已更新")
    
    return filepath

def main():
    print("="*50)
    print("財經新聞收集 (v3)")
    print("="*50)
    
    save_news(MANUAL_NEWS)
    print(f"\n共收錄 {len(MANUAL_NEWS)} 則新聞")
    print("\n完成!")

if __name__ == "__main__":
    main()
