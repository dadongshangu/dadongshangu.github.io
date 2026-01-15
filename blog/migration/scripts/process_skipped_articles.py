#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
处理被跳过的文章
- 从HTML获取图片并插入
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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def load_articles_list():
    """加载文章列表"""
    if not os.path.exists(ARTICLES_LIST_FILE):
        return []
    with open(ARTICLES_LIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_article_html(url):
    """获取文章HTML内容"""
    try:
        if url.startswith('http://'):
            url = url.replace('http://', 'https://', 1)
        
        response = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            if 'captcha' in response.text.lower() or '验证' in response.text or '安全验证' in response.text:
                print(f"    [WARN] 可能被反爬虫拦截")
                return None
            return response.text
        else:
            print(f"    [ERROR] HTTP {response.status_code}")
    except Exception as e:
        print(f"    [ERROR] 获取文章失败: {e}")
    return None


def extract_images_from_html(html_content, article_url):
    """从HTML中提取所有图片URL"""
    soup = BeautifulSoup(html_content, 'html.parser')
    images = []
    
    # 查找文章内容区域
    content_div = soup.find('div', id='js_content') or soup.find('div', class_='rich_media_content')
    if not content_div:
        return images
    
    # 在内容区域内查找所有img标签
    for img in content_div.find_all('img'):
        # 微信公众号图片通常使用data-src属性（懒加载）
        src = (img.get('data-src') or 
               img.get('src') or 
               img.get('data-original') or
               img.get('data-lazy-src'))
        if not src:
            continue
        
        # 处理相对URL
        if src.startswith('//'):
            src = 'https:' + src
        elif src.startswith('/'):
            src = urljoin(article_url, src)
        elif not src.startswith('http'):
            src = urljoin(article_url, src)
        
        # 过滤掉微信头像、二维码、小程序码等非文章图片
        skip_keywords = ['avatar', 'qrcode', 'logo', 'icon']
        if any(skip in src.lower() for skip in skip_keywords):
            continue
        
        # 过滤掉gif格式的图标（通常是动画表情）
        if 'wx_fmt=gif' in src.lower() and 'mmbiz' not in src.lower():
            continue
        
        # 确保是有效的图片URL
        is_valid = False
        if 'mmbiz' in src.lower():
            # mmbiz格式的图片，检查是否包含图片类型参数（排除gif图标）
            if 'wx_fmt=gif' in src.lower():
                # 如果是gif，检查尺寸，小图标通常不是文章图片
                width = img.get('width') or img.get('data-width') or ''
                height = img.get('height') or img.get('data-height') or ''
                try:
                    if width and height:
                        w, h = int(width), int(height)
                        if w < 100 or h < 100:
                            continue
                except:
                    pass
            is_valid = True
        elif any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            is_valid = True
        
        if not is_valid:
            continue
        
        # 获取图片alt或title作为描述
        alt = img.get('alt') or img.get('title') or ''
        
        images.append({
            'url': src,
            'alt': alt,
            'index': len(images)
        })
    
    return images


def process_article(post_file, article_url):
    """处理单篇文章"""
    print(f"\n处理: {post_file.name}")
    
    # 读取文章
    md_content = post_file.read_text(encoding='utf-8')
    
    # 检查是否已有图片
    if re.search(r'!\[.*\]\(https?://mmbiz', md_content):
        print(f"  已有图片，跳过")
        return False
    
    # 获取文章HTML
    print(f"  获取文章HTML: {article_url}")
    html = fetch_article_html(article_url)
    if not html:
        print(f"  [ERROR] 无法获取文章HTML")
        return False
    
    # 提取图片
    images = extract_images_from_html(html, article_url)
    if not images:
        print(f"  未找到图片")
        return False
    
    print(f"  找到 {len(images)} 张图片")
    
    # 在文章末尾（推广内容之前）插入图片
    lines = md_content.split('\n')
    insert_pos = len(lines)
    
    # 查找推广内容的位置
    for i in range(len(lines) - 1, max(0, len(lines) - 20), -1):
        if any(keyword in lines[i] for keyword in ['感谢关注', '近期', '推荐', 'mp.weixin.qq.com', '往期精彩']):
            insert_pos = i
            break
    
    # 插入图片
    for img in images:
        img_url = img['url']
        alt_text = img.get('alt') or '图片'
        lines.insert(insert_pos, f"![{alt_text}]({img_url})")
        lines.insert(insert_pos + 1, "")
        insert_pos += 2
    
    # 保存
    post_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"  [OK] 已插入 {len(images)} 张图片")
    
    return True


def main():
    articles_list = load_articles_list()
    
    # 需要处理的文章列表
    articles_to_process = [
        "唯有母爱不可辜负",
        "重回童年，再过儿童节!",
        "我的留守老爸",
        "人啊，有人念着便不会孤独"
    ]
    
    processed = 0
    skipped = 0
    
    for post_file in Path(POSTS_DIR).glob("*.md"):
        # 读取文章
        md_content = post_file.read_text(encoding='utf-8')
        
        # 读取标题
        title_match = re.search(r'^title:\s*(.+)$', md_content, re.MULTILINE)
        if not title_match:
            continue
        
        title = title_match.group(1).strip()
        
        # 检查是否在需要处理的列表中
        title_normalized = re.sub(r'[|_\-：:，,。.\s]', '', title)
        should_process = False
        article_url = None
        
        for target_title in articles_to_process:
            target_normalized = re.sub(r'[|_\-：:，,。.\s]', '', target_title)
            if title_normalized == target_normalized or target_normalized in title_normalized:
                should_process = True
                # 查找URL
                for item in articles_list:
                    if item.get('title') and re.sub(r'[|_\-：:，,。.\s]', '', item['title']) == target_normalized:
                        article_url = item['url']
                        break
                break
        
        if should_process and article_url:
            try:
                if process_article(post_file, article_url):
                    processed += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  [ERROR] {e}")
                import traceback
                traceback.print_exc()
                skipped += 1
    
    print(f"\n[SUMMARY] processed={processed}, skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
