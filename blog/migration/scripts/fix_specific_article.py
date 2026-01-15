#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
专门修复"写给四岁儿子的信：你好阿勋（1）"这篇文章
"""

import os
import re
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
DATA_DIR = os.path.join(BASE_DIR, "data")
ARTICLES_LIST_FILE = os.path.join(DATA_DIR, "articles_list.json")
BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")
WECHATSYNC_MD_DIR = os.path.join(DATA_DIR, "wechatsync_md")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

def load_articles_list():
    if not os.path.exists(ARTICLES_LIST_FILE):
        return []
    with open(ARTICLES_LIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_article_html(url):
    try:
        if url.startswith('http://'):
            url = url.replace('http://', 'https://', 1)
        response = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            if 'captcha' in response.text.lower() or '验证' in response.text or '安全验证' in response.text:
                return None
            return response.text
    except Exception as e:
        print(f"    [ERROR] 获取文章失败: {e}")
    return None

def extract_images_from_html(html_content, article_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    images = []
    content_div = soup.find('div', id='js_content') or soup.find('div', class_='rich_media_content')
    if not content_div:
        return images
    
    for img in content_div.find_all('img'):
        src = (img.get('data-src') or img.get('src') or img.get('data-original') or img.get('data-lazy-src'))
        if not src:
            continue
        if src.startswith('//'):
            src = 'https:' + src
        elif src.startswith('/'):
            src = urljoin(article_url, src)
        elif not src.startswith('http'):
            src = urljoin(article_url, src)
        
        skip_keywords = ['avatar', 'qrcode', 'logo', 'icon']
        if any(skip in src.lower() for skip in skip_keywords):
            continue
        if 'wx_fmt=gif' in src.lower() and 'mmbiz' not in src.lower():
            continue
        
        is_valid = False
        if 'mmbiz' in src.lower():
            is_valid = True
        elif any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            is_valid = True
        
        if not is_valid:
            continue
        
        alt = img.get('alt') or img.get('title') or ''
        images.append({'url': src, 'alt': alt, 'index': len(images)})
    
    return images

def main():
    # 处理"写给四岁儿子的信：你好阿勋（1）"
    post_file = Path(POSTS_DIR) / "2019-04-13-写给四岁儿子的信：你好阿勋（1）.md"
    if not post_file.exists():
        print(f"文件不存在: {post_file}")
        return 1
    
    print(f"处理: {post_file.name}")
    
    # 读取文章
    md_content = post_file.read_text(encoding='utf-8')
    lines = md_content.split('\n')
    
    # 查找所有图片说明的位置
    caption_positions = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 匹配 _（...）_ 格式的图片说明
        if re.search(r'_[（(]([^）)]+)[）)]_', stripped):
            # 提取图片说明文本
            match = re.search(r'[（(]([^）)]+)[）)]', stripped)
            if match:
                caption_text = match.group(0)
                caption_positions.append({
                    'line': i,
                    'caption': caption_text,
                    'has_image': False
                })
    
    print(f"  找到 {len(caption_positions)} 个图片说明")
    
    # 检查每个图片说明后面是否有图片
    for cap in caption_positions:
        line_idx = cap['line']
        # 检查后面5行是否有图片
        for j in range(line_idx + 1, min(line_idx + 6, len(lines))):
            if re.match(r'^!\[.*\]\(https?://mmbiz', lines[j]):
                cap['has_image'] = True
                break
    
    # 找出没有图片的图片说明
    missing_images = [cap for cap in caption_positions if not cap['has_image']]
    print(f"  有 {len(missing_images)} 个图片说明缺少图片")
    
    if not missing_images:
        print("  所有图片说明都有对应的图片")
        return 0
    
    # 从HTML获取图片
    articles_list = load_articles_list()
    article_url = None
    for item in articles_list:
        if item.get('title') == "写给四岁儿子的信：你好阿勋（1）":
            article_url = item['url']
            break
    
    if not article_url:
        print("  未找到文章URL")
        return 1
    
    print(f"  获取文章HTML: {article_url}")
    html = fetch_article_html(article_url)
    if not html:
        print("  [ERROR] 无法获取文章HTML")
        return 1
    
    images = extract_images_from_html(html, article_url)
    print(f"  从HTML找到 {len(images)} 张图片")
    
    if len(images) < len(missing_images):
        print(f"  警告: 图片数量({len(images)})少于缺失的图片说明数量({len(missing_images)})")
    
    # 为缺失的图片说明插入图片
    # 从后往前插入，避免位置偏移
    for i in range(len(missing_images) - 1, -1, -1):
        cap = missing_images[i]
        line_idx = cap['line']
        
        if i < len(images):
            img = images[i]
            img_url = img['url']
            alt_text = cap['caption'].strip('（）()')
            
            # 在图片说明后面插入图片
            lines.insert(line_idx + 1, f"![{alt_text}]({img_url})")
            lines.insert(line_idx + 2, "")
            print(f"    在第 {line_idx + 1} 行后插入图片: {alt_text[:30]}...")
    
    # 保存
    post_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"  [OK] 已修复，插入了 {len(missing_images)} 张图片")
    
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
