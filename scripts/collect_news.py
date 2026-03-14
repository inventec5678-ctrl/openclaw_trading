#!/usr/bin/env python3
"""
財經新聞收集爬蟲 - 擴展版
收集多個來源的新聞
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import datetime
from datetime import datetime as dt
import time
import random

# 設定路徑
NEWS_DIR = os.path.expanduser("~/openclaw_data/news")
os.makedirs(NEWS_DIR, exist_ok=True)

def get_headers():
    """偽裝瀏覽器 headers"""
    return {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    }

def collect_yahoo_finance():
    """收集 Yahoo 股市新聞 (台灣)"""
    print("正在收集 Yahoo 股市新聞...")
    news_list = []
    
    try:
        url = "https://tw.stock.yahoo.com/news/"
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            articles = soup.select('article') or soup.select('.news-item') or soup.select('li[data-ylk]')
            
            for article in articles[:15]:
                try:
                    title_elem = article.select_one('h3, .title, a')
                    link_elem = article.select_one('a')
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    link = link_elem.get('href', '') if link_elem else ""
                    
                    if title and link:
                        news_list.append({
                            "source": "Yahoo 股市 (台灣)",
                            "title": title,
                            "url": link if link.startswith('http') else f"https://tw.stock.yahoo.com{link}",
                            "collected_at": dt.now().isoformat()
                        })
                except:
                    continue
            print(f"  ✅ Yahoo 股市: {len(news_list)} 則")
    except Exception as e:
        print(f"  ❌ Yahoo 股市: {e}")
    
    return news_list

def collect_yahoo_us():
    """收集 Yahoo Finance 美國新聞"""
    print("正在收集 Yahoo Finance 新聞...")
    news_list = []
    
    try:
        url = "https://finance.yahoo.com/topic/stock-market-news/"
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            articles = soup.select('article')[:15]
            
            for article in articles:
                try:
                    title_elem = article.select_one('h3, h2, .title')
                    link_elem = article.select_one('a')
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    link = link_elem.get('href', '') if link_elem else ""
                    
                    if title and link:
                        news_list.append({
                            "source": "Yahoo Finance",
                            "title": title,
                            "url": f"https://finance.yahoo.com{link}" if not link.startswith('http') else link,
                            "collected_at": dt.now().isoformat()
                        })
                except:
                    continue
            print(f"  ✅ Yahoo Finance: {len(news_list)} 則")
    except Exception as e:
        print(f"  ❌ Yahoo Finance: {e}")
    
    return news_list

def collect_cnyes():
    """收集鉅亨網新聞"""
    print("正在收集鉅亨網新聞...")
    news_list = []
    
    try:
        url = "https://news.cnyes.com/news/cat/tw_stock"
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            articles = soup.select('article')[:15]
            
            for article in articles:
                title_elem = article.select_one('h3, .title a, a')
                link_elem = article.select_one('a')
                title = title_elem.get_text(strip=True) if title_elem else ""
                link = link_elem.get('href', '') if link_elem else ""
                
                if title and 'http' in link:
                    news_list.append({
                        "source": "鉅亨網",
                        "title": title,
                        "url": link,
                        "collected_at": dt.now().isoformat()
                    })
            print(f"  ✅ 鉅亨網: {len(news_list)} 則")
    except Exception as e:
        print(f"  ❌ 鉅亨網: {e}")
    
    return news_list

def collect_ec_times():
    """收集經濟日報"""
    print("正在收集經濟日報...")
    news_list = []
    
    try:
        url = "https://money.udn.com/money/index"
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            articles = soup.select('article, .story-list__item, .tab-content__item')[:15]
            
            for article in articles:
                title_elem = article.select_one('h3, .story__title, a')
                link_elem = article.select_one('a')
                title = title_elem.get_text(strip=True) if title_elem else ""
                link = link_elem.get('href', '') if link_elem else ""
                
                if title and link:
                    news_list.append({
                        "source": "經濟日报/聯合報",
                        "title": title,
                        "url": link if link.startswith('http') else f"https://money.udn.com{link}",
                        "collected_at": dt.now().isoformat()
                    })
            print(f"  ✅ 經濟日報/聯合報: {len(news_list)}則")
    except Exception as e:
        print(f"  ❌ 經濟日報: {e}")
    
    return news_list

def collect_ctee():
    """收集工商時報"""
    print("正在收集工商時報...")
    news_list = []
    
    try:
        url = "https://ctee.com.tw/"
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            articles = soup.select('article, .post-item, .listing-item')[:15]
            
            for article in articles:
                title_elem = article.select_one('h3, h2, .title a, a')
                link_elem = article.select_one('a')
                title = title_elem.get_text(strip=True) if title_elem else ""
                link = link_elem.get('href', '') if link_elem else ""
                
                if title and len(title) > 5:
                    news_list.append({
                        "source": "工商時報",
                        "title": title,
                        "url": link if link.startswith('http') else f"https://ctee.com.tw{link}",
                        "collected_at": dt.now().isoformat()
                    })
            print(f"  ✅ 工商時報: {len(news_list)}則")
    except Exception as e:
        print(f"  ❌ 工商時報: {e}")
    
    return news_list

def collect_ltneconomics():
    """收集自由時報財經"""
    print("正在收集自由時報財經...")
    news_list = []
    
    try:
        url = "https://ec.ltn.com.tw/list/3"
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            articles = soup.select('article, .news__item')[:15]
            
            for article in articles:
                title_elem = article.select_one('h3, .news__title, a')
                link_elem = article.select_one('a')
                title = title_elem.get_text(strip=True) if title_elem else ""
                link = link_elem.get('href', '') if link_elem else ""
                
                if title and link:
                    news_list.append({
                        "source": "自由時報財經",
                        "title": title,
                        "url": link if link.startswith('http') else f"https://ec.ltn.com.tw{link}",
                        "collected_at": dt.now().isoformat()
                    })
            print(f"  ✅ 自由時報財經: {len(news_list)}則")
    except Exception as e:
        print(f"  ❌ 自由時報財經: {e}")
    
    return news_list

def collect_mirrormedia():
    """收集鏡周刊"""
    print("正在收集鏡周刊...")
    news_list = []
    
    try:
        url = "https://www.mirrormedia.mg/projects/money"
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            articles = soup.select('article, .article-card, .story-card')[:15]
            
            for article in articles:
                title_elem = article.select_one('h3, h2, .title a, a')
                link_elem = article.select_one('a')
                title = title_elem.get_text(strip=True) if title_elem else ""
                link = link_elem.get('href', '') if link_elem else ""
                
                if title and len(title) > 5:
                    news_list.append({
                        "source": "鏡周刊",
                        "title": title,
                        "url": link if link.startswith('http') else f"https://www.mirrormedia.mg{link}",
                        "collected_at": dt.now().isoformat()
                    })
            print(f"  ✅ 鏡周刊: {len(news_list)}則")
    except Exception as e:
        print(f"  ❌ 鏡周刊: {e}")
    
    return news_list

def collect_bloomberg():
    """收集 Bloomberg 新聞"""
    print("正在收集 Bloomberg 新聞...")
    news_list = []
    
    try:
        url = "https://www.bloomberg.com/markets"
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            articles = soup.select('article, .story-package__item')[:15]
            
            for article in articles:
                title_elem = article.select_one('h3, h2, .headline a, a')
                link_elem = article.select_one('a')
                title = title_elem.get_text(strip=True) if title_elem else ""
                link = link_elem.get('href', '') if link_elem else ""
                
                if title and len(title) > 10:
                    news_list.append({
                        "source": "Bloomberg",
                        "title": title,
                        "url": f"https://www.bloomberg.com{link}" if not link.startswith('http') else link,
                        "collected_at": dt.now().isoformat()
                    })
            print(f"  ✅ Bloomberg: {len(news_list)}則")
    except Exception as e:
        print(f"  ❌ Bloomberg: {e}")
    
    return news_list

def collect_reuters():
    """收集 Reuters 新聞"""
    print("正在收集 Reuters 新聞...")
    news_list = []
    
    try:
        url = "https://www.reuters.com/markets"
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            articles = soup.select('article, .story-package__item')[:15]
            
            for article in articles:
                title_elem = article.select_one('h3, .story__title, a')
                link_elem = article.select_one('a')
                title = title_elem.get_text(strip=True) if title_elem else ""
                link = link_elem.get('href', '') if link_elem else ""
                
                if title and len(title) > 10:
                    news_list.append({
                        "source": "Reuters",
                        "title": title,
                        "url": f"https://www.reuters.com{link}" if not link.startswith('http') else link,
                        "collected_at": dt.now().isoformat()
                    })
            print(f"  ✅ Reuters: {len(news_list)}則")
    except Exception as e:
        print(f"  ❌ Reuters: {e}")
    
    return news_list

def collect_fortune():
    """收集 Fortune 新聞"""
    print("正在收集 Fortune 新聞...")
    news_list = []
    
    try:
        url = "https://fortune.com/section/finance/"
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            articles = soup.select('article, .card, .post-preview')[:15]
            
            for article in articles:
                title_elem = article.select_one('h3, .card-title a, a')
                link_elem = article.select_one('a')
                title = title_elem.get_text(strip=True) if title_elem else ""
                link = link_elem.get('href', '') if link_elem else ""
                
                if title and len(title) > 10:
                    news_list.append({
                        "source": "Fortune",
                        "title": title,
                        "url": f"https://fortune.com{link}" if not link.startswith('http') else link,
                        "collected_at": dt.now().isoformat()
                    })
            print(f"  ✅ Fortune: {len(news_list)}則")
    except Exception as e:
        print(f"  ❌ Fortune: {e}")
    
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
        if news['title'] not in seen and len(news['title']) > 5:
            seen.add(news['title'])
            unique_news.append(news)
    
    today = datetime.date.today().strftime('%Y-%m-%d')
    filepath = os.path.join(NEWS_DIR, f"news_{today}.json")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            "date": today,
            "count": len(unique_news),
            "sources": list(set(n['source'] for n in unique_news)),
            "news": unique_news
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 新聞已儲存: {filepath}")
    
    # latest.json
    latest_path = os.path.join(NEWS_DIR, "latest.json")
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump({
            "updated_at": dt.now().isoformat(),
            "count": len(unique_news),
            "news": unique_news[:50]
        }, f, ensure_ascii=False, indent=2)
    
    return filepath

def main():
    print("="*60)
    print("財經新聞收集腳本 - 擴展版")
    print("="*60)
    
    all_news = []
    
    # 台灣來源
    all_news.extend(collect_yahoo_finance())
    time.sleep(random.uniform(1, 2))
    
    all_news.extend(collect_cnyes())
    time.sleep(random.uniform(1, 2))
    
    all_news.extend(collect_ec_times())
    time.sleep(random.uniform(1, 2))
    
    all_news.extend(collect_ctee())
    time.sleep(random.uniform(1, 2))
    
    all_news.extend(collect_ltneconomics())
    time.sleep(random.uniform(1, 2))
    
    all_news.extend(collect_mirrormedia())
    time.sleep(random.uniform(1, 2))
    
    # 國際來源
    all_news.extend(collect_yahoo_us())
    time.sleep(random.uniform(1, 2))
    
    all_news.extend(collect_bloomberg())
    time.sleep(random.uniform(1, 2))
    
    all_news.extend(collect_reuters())
    time.sleep(random.uniform(1, 2))
    
    all_news.extend(collect_fortune())
    
    # 儲存
    if all_news:
        save_news(all_news)
        print(f"\n共收集 {len(all_news)} 則新聞")
    
    print("\n完成!")

if __name__ == "__main__":
    main()
