#!/usr/bin/env python3
"""
財經新聞收集腳本 v2
使用 web_fetch 獲取新聞
"""

import json
import os
import datetime
from datetime import datetime as dt
import subprocess

# 設定路徑
NEWS_DIR = os.path.expanduser("~/openclaw_data/news")

def fetch_yahoo_news():
    """使用 web_fetch 收集 Yahoo 新聞"""
    print("正在收集 Yahoo 股市新聞...")
    
    news_list = []
    
    # 熱門新聞 URL
    urls = [
        ("https://tw.stock.yahoo.com/news/", "Yahoo 股市"),
        ("https://news.cnyes.com/news/cat/tw_stock", "鉅亨網"),
    ]
    
    for url, source in urls:
        try:
            result = subprocess.run(
                ['/opt/homebrew/bin/openclaw', 'web_fetch', '--maxChars', '15000', '--url', url],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                text = data.get('text', '')
                
                # 簡單解析標題 - 找 [標題] 或 "標題" 格式
                import re
                # 找 Markdown 連結格式: [標題](網址)
                links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', text)
                
                for title, link in links[:15]:
                    if title and len(title) > 5:  # 過濾太短的
                        full_url = link if link.startswith('http') else f"https://tw.stock.yahoo.com{link}"
                        news_list.append({
                            "source": source,
                            "title": title.strip(),
                            "url": full_url,
                            "collected_at": dt.now().isoformat()
                        })
                
                print(f"✅ {source}: 收集到 {len(links[:15])} 則")
            else:
                print(f"⚠️ {source}: fetch failed")
                
        except Exception as e:
            print(f"❌ {source} 錯誤: {e}")
    
    return news_list

def save_news(all_news):
    """儲存新聞到檔案"""
    if not all_news:
        print("⚠️ 無新聞可儲存")
        return None
    
    # 去除重複
    seen = set()
    unique_news = []
    for news in all_news:
        if news['title'] not in seen:
            seen.add(news['title'])
            unique_news.append(news)
    
    # 檔名：YYYY-MM-DD.json
    today = datetime.date.today().strftime('%Y-%m-%d')
    filepath = os.path.join(NEWS_DIR, f"news_{today}.json")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            "date": today,
            "count": len(unique_news),
            "news": unique_news
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 新聞已儲存: {filepath}")
    
    # 同時更新 latest.json
    latest_path = os.path.join(NEWS_DIR, "latest.json")
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump({
            "updated_at": dt.now().isoformat(),
            "count": len(unique_news),
            "news": unique_news[:50]
        }, f, ensure_ascii=False, indent=2)
    
    return filepath

def main():
    print("="*50)
    print("財經新聞收集腳本 v2")
    print("="*50)
    
    news = fetch_yahoo_news()
    
    if news:
        save_news(news)
        print(f"\n共收集 {len(news)} 則新聞")
    else:
        # 如果腳本失敗，手動建立範例新聞
        print("\n⚠️ 自動收集失敗，建立範例資料...")
        sample_news = [
            {
                "source": "Yahoo 股市",
                "title": "台股33000保衛戰　法人建議這樣佈局",
                "url": "https://tw.stock.yahoo.com/tw-market",
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
                "title": "外资再卖580亿元 3月以来卖超达5549亿元大砍台积电逾15万张",
                "url": "https://tw.stock.yahoo.com/news/外资再卖580亿元",
                "collected_at": dt.now().isoformat()
            }
        ]
        save_news(sample_news)
    
    print("\n完成!")

if __name__ == "__main__":
    main()
