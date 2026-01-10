#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
微信公众号文章抓取脚本
从精选文章页面获取文章列表和内容
"""

import os
import sys
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置
ALBUM_URL = "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&album_id=1417552598718332928&__biz=MzIxMjYyMDA2Nw==#wechat_redirect"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ARTICLES_LIST_FILE = os.path.join(OUTPUT_DIR, "articles_list.json")
ARTICLES_RAW_DIR = os.path.join(OUTPUT_DIR, "articles_raw")

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def create_directories():
    """创建必要的目录"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTICLES_RAW_DIR, exist_ok=True)

def fetch_article_list():
    """
    从专辑页面获取文章列表
    注意：微信公众号页面可能需要登录或使用特殊方式访问
    """
    articles = []
    
    print("正在尝试获取文章列表...")
    print(f"专辑URL: {ALBUM_URL}")
    
    try:
        # 尝试访问专辑页面
        response = requests.get(ALBUM_URL, headers=HEADERS, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试解析文章列表
            # 注意：微信公众号的页面结构可能经常变化
            # 这里提供一个基础框架，可能需要根据实际情况调整
            
            # 查找文章链接
            article_links = soup.find_all('a', href=True)
            
            for link in article_links:
                href = link.get('href', '')
                if 'mp.weixin.qq.com/s' in href:
                    title = link.get_text(strip=True)
                    if title:
                        articles.append({
                            'title': title,
                            'url': href,
                            'timestamp': None
                        })
            
            print(f"找到 {len(articles)} 篇文章")
            
        else:
            print(f"访问失败，状态码: {response.status_code}")
            print("提示：微信公众号页面可能需要登录或使用特殊方式访问")
            
    except Exception as e:
        print(f"抓取文章列表时出错: {str(e)}")
        print("提示：可能需要手动提供文章链接列表")
    
    return articles

def fetch_article_content(article_url, article_title):
    """
    获取单篇文章的详细内容
    """
    try:
        print(f"正在抓取: {article_title}")
        
        response = requests.get(article_url, headers=HEADERS, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            # 保存原始HTML
            safe_title = "".join(c for c in article_title if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
            html_file = os.path.join(ARTICLES_RAW_DIR, f"{safe_title}.html")
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # 解析文章内容
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取文章内容
            # 微信公众号文章通常在 #js_content 或类似的容器中
            content_div = soup.find('div', id='js_content') or soup.find('div', class_='rich_media_content')
            
            if content_div:
                # 提取发布日期（如果可用）
                date_elem = soup.find('em', class_='rich_media_meta_text') or soup.find('span', class_='publish_time')
                publish_date = None
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    try:
                        publish_date = datetime.strptime(date_text, '%Y-%m-%d %H:%M')
                    except:
                        pass
                
                return {
                    'title': article_title,
                    'url': article_url,
                    'content': str(content_div),
                    'html_file': html_file,
                    'publish_date': publish_date.isoformat() if publish_date else None
                }
            else:
                print(f"  警告：无法找到文章内容区域")
                return None
                
        else:
            print(f"  错误：访问失败，状态码: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  错误：抓取文章内容时出错: {str(e)}")
        return None

def save_articles_list(articles):
    """保存文章列表到JSON文件"""
    with open(ARTICLES_LIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"\n文章列表已保存到: {ARTICLES_LIST_FILE}")

def main():
    """主函数"""
    print("=" * 60)
    print("微信公众号文章抓取工具")
    print("=" * 60)
    
    create_directories()
    
    # 尝试获取文章列表
    articles = fetch_article_list()
    
    if not articles:
        print("\n" + "=" * 60)
        print("无法自动获取文章列表")
        print("=" * 60)
        print("\n请手动创建文章列表文件:")
        print(f"文件路径: {ARTICLES_LIST_FILE}")
        print("\n格式示例:")
        print("""
[
  {
    "title": "文章标题1",
    "url": "https://mp.weixin.qq.com/s/...",
    "timestamp": 1597470506
  },
  {
    "title": "文章标题2",
    "url": "https://mp.weixin.qq.com/s/...",
    "timestamp": 1592705989
  }
]
        """)
        return
    
    # 保存文章列表
    save_articles_list(articles)
    
    # 抓取每篇文章的详细内容
    print("\n开始抓取文章内容...")
    articles_with_content = []
    
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] {article['title']}")
        
        content_data = fetch_article_content(article['url'], article['title'])
        
        if content_data:
            articles_with_content.append(content_data)
        
        # 控制请求频率
        time.sleep(2)
    
    # 更新文章列表，添加内容信息
    for article in articles:
        for content in articles_with_content:
            if article['url'] == content['url']:
                article.update(content)
                break
    
    save_articles_list(articles)
    
    print("\n" + "=" * 60)
    print(f"抓取完成！共获取 {len(articles_with_content)} 篇文章")
    print("=" * 60)

if __name__ == '__main__':
    main()
