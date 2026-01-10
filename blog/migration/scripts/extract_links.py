#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文章链接提取脚本
尝试从微信公众号精选页面提取所有文章链接
"""

import os
import sys
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# 配置
ALBUM_URL = "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&album_id=1417552598718332928&__biz=MzIxMjYyMDA2Nw==#wechat_redirect"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "articles_list.json")

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://mp.weixin.qq.com/',
}

def extract_links_from_html(html_content):
    """从HTML中提取文章链接"""
    articles = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 方法1: 查找所有包含文章链接的a标签
    links = soup.find_all('a', href=True)
    for link in links:
        href = link.get('href', '')
        if 'mp.weixin.qq.com/s' in href:
            # 处理相对链接
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                href = 'https://mp.weixin.qq.com' + href
            
            title = link.get_text(strip=True)
            if not title:
                # 尝试从父元素获取标题
                parent = link.parent
                if parent:
                    title = parent.get_text(strip=True)[:100]
            
            if href and not any(a['url'] == href for a in articles):
                articles.append({
                    'title': title or '未命名文章',
                    'url': href,
                    'timestamp': None
                })
    
    # 方法2: 从script标签中提取
    scripts = soup.find_all('script')
    for script in scripts:
        content = script.string or ''
        # 查找文章链接模式
        matches = re.findall(r'https?://mp\.weixin\.qq\.com/s/[A-Za-z0-9_-]+', content)
        for url in matches:
            if not any(a['url'] == url for a in articles):
                articles.append({
                    'title': '文章' + str(len(articles) + 1),
                    'url': url,
                    'timestamp': None
                })
    
    # 方法3: 从data属性中提取
    elements_with_data = soup.find_all(attrs={'data-link': True})
    for elem in elements_with_data:
        href = elem.get('data-link', '')
        if 'mp.weixin.qq.com/s' in href:
            title = elem.get_text(strip=True) or elem.get('data-title', '未命名文章')
            if not any(a['url'] == href for a in articles):
                articles.append({
                    'title': title,
                    'url': href,
                    'timestamp': None
                })
    
    return articles

def fetch_album_page():
    """获取精选页面内容"""
    print("正在访问精选文章页面...")
    print(f"URL: {ALBUM_URL}\n")
    
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        
        response = session.get(ALBUM_URL, timeout=30, allow_redirects=True)
        response.encoding = 'utf-8'
        
        print(f"状态码: {response.status_code}")
        print(f"最终URL: {response.url}\n")
        
        if response.status_code == 200:
            return response.text
        else:
            print(f"访问失败，状态码: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"访问页面时出错: {str(e)}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("微信公众号文章链接提取工具")
    print("=" * 60)
    print("\n注意：由于微信公众号的反爬虫机制，")
    print("      此脚本可能无法直接获取链接。")
    print("      如果失败，请使用浏览器控制台脚本。\n")
    
    # 尝试获取页面
    html_content = fetch_album_page()
    
    if not html_content:
        print("\n无法获取页面内容。")
        print("\n请使用以下方法：")
        print("1. 打开精选文章页面")
        print("2. 按F12打开开发者工具")
        print("3. 在Console中运行提取脚本")
        print("4. 或手动复制文章链接")
        return
    
    # 提取链接
    print("正在提取文章链接...")
    articles = extract_links_from_html(html_content)
    
    print(f"\n找到 {len(articles)} 篇文章链接\n")
    
    if articles:
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article['title']}")
            print(f"   {article['url']}\n")
        
        # 保存到文件
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] 文章列表已保存到: {OUTPUT_FILE}")
        print(f"\n共提取 {len(articles)} 篇文章")
        
        if len(articles) < 36:
            print(f"\n警告：只找到 {len(articles)} 篇，应该有36篇")
            print("可能需要使用浏览器控制台脚本或手动获取")
    else:
        print("未找到任何文章链接")
        print("\n建议使用浏览器控制台脚本提取链接")

if __name__ == '__main__':
    main()
