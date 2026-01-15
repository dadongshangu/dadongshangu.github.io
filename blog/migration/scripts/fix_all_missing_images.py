#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复所有文章的缺失图片
- 检查所有文章，找出有图片说明但缺少图片的
- 从HTML获取图片并插入
- 过滤掉小图片（分隔符或页面美化的小图）
"""

import os
import re
import json
import requests
import time
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

# 最小图片尺寸阈值（过滤小图片/分隔符）
MIN_IMAGE_WIDTH = 200
MIN_IMAGE_HEIGHT = 200


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
                return None
            return response.text
    except Exception as e:
        print(f"    [ERROR] 获取文章失败: {e}")
    return None


def extract_images_from_html(html_content, article_url):
    """从HTML中提取所有图片URL，过滤掉小图片"""
    soup = BeautifulSoup(html_content, 'html.parser')
    images = []
    content_div = soup.find('div', id='js_content') or soup.find('div', class_='rich_media_content')
    if not content_div:
        return images
    
    for img in content_div.find_all('img'):
        src = (img.get('data-src') or 
               img.get('src') or 
               img.get('data-original') or
               img.get('data-lazy-src'))
        if not src:
            continue
        
        if src.startswith('//'):
            src = 'https:' + src
        elif src.startswith('/'):
            src = urljoin(article_url, src)
        elif not src.startswith('http'):
            src = urljoin(article_url, src)
        
        # 过滤掉头像、二维码、logo等
        skip_keywords = ['avatar', 'qrcode', 'logo', 'icon']
        if any(skip in src.lower() for skip in skip_keywords):
            continue
        
        # 过滤掉gif格式的图标（通常是动画表情）
        if 'wx_fmt=gif' in src.lower() and 'mmbiz' not in src.lower():
            continue
        
        # 检查图片尺寸
        width = img.get('width') or img.get('data-width') or ''
        height = img.get('height') or img.get('data-height') or ''
        
        # 尝试解析尺寸
        img_width = None
        img_height = None
        try:
            if width:
                img_width = int(width)
            if height:
                img_height = int(height)
        except:
            pass
        
        # 如果尺寸太小，跳过（可能是分隔符或装饰图）
        if img_width and img_height:
            if img_width < MIN_IMAGE_WIDTH or img_height < MIN_IMAGE_HEIGHT:
                continue
        
        # 对于mmbiz格式的图片，如果没有尺寸信息，默认保留（可能是重要图片）
        # 但如果是gif且尺寸很小，跳过
        if 'wx_fmt=gif' in src.lower() and 'mmbiz' in src.lower():
            if img_width and img_height:
                if img_width < MIN_IMAGE_WIDTH or img_height < MIN_IMAGE_HEIGHT:
                    continue
        
        # 确保是有效的图片URL
        is_valid = False
        if 'mmbiz' in src.lower():
            is_valid = True
        elif any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            is_valid = True
        
        if not is_valid:
            continue
        
        alt = img.get('alt') or img.get('title') or ''
        images.append({
            'url': src,
            'alt': alt,
            'width': img_width,
            'height': img_height,
            'index': len(images)
        })
    
    return images


def find_captions_in_article(md_content):
    """查找文章中的所有图片说明"""
    lines = md_content.split('\n')
    captions = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 匹配各种格式的图片说明
        # 格式1: _（...）_ 或 _（...）_ __
        if re.search(r'_[（(]([^）)]+)[）)]_', stripped):
            match = re.search(r'[（(]([^）)]+)[）)]', stripped)
            if match:
                captions.append({
                    'line': i,
                    'text': match.group(0),
                    'has_image': False
                })
        # 格式2: （...）单独一行
        elif re.match(r'^[（(].*[）)]$', stripped):
            # 检查是否包含图片说明关键词
            if re.search(r'(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐|假设|价格)', stripped):
                captions.append({
                    'line': i,
                    'text': stripped,
                    'has_image': False
                })
        # 格式3: 图片的alt文本中包含图片说明（如 ![图片说明|作者摄](url)）
        elif re.match(r'^!\[.*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐).*\]\(https?://', line):
            # 提取alt文本作为图片说明
            match = re.match(r'^!\[([^\]]+)\]', line)
            if match:
                alt_text = match.group(1)
                # 检查下一行是否有重复的图片说明文本
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.match(r'^[（(].*[）)]$', next_line):
                        # 下一行有图片说明文本，检查是否缺少图片
                        captions.append({
                            'line': i + 1,
                            'text': next_line,
                            'has_image': False
                        })
    
    # 检查每个图片说明前后是否有图片
    for cap in captions:
        line_idx = cap['line']
        # 检查前面5行和后面5行是否有图片
        for j in range(max(0, line_idx - 5), min(line_idx + 6, len(lines))):
            if j != line_idx and re.match(r'^!\[.*\]\(https?://mmbiz', lines[j]):
                cap['has_image'] = True
                break
    
    return captions


def process_article(post_file, articles_list):
    """处理单篇文章"""
    print(f"\n处理: {post_file.name}")
    
    # 读取文章
    md_content = post_file.read_text(encoding='utf-8')
    
    # 查找所有图片说明
    captions = find_captions_in_article(md_content)
    
    if not captions:
        print(f"  没有找到图片说明")
        return False
    
    # 找出没有图片的图片说明
    missing = [cap for cap in captions if not cap['has_image']]
    
    if not missing:
        print(f"  所有 {len(captions)} 个图片说明都有对应的图片")
        return False
    
    print(f"  找到 {len(captions)} 个图片说明，其中 {len(missing)} 个缺少图片")
    
    # 显示缺失的图片说明
    for cap in missing:
        print(f"    - 第 {cap['line'] + 1} 行: {cap['text'][:50]}...")
    
    # 从文章列表中获取URL
    title_match = re.search(r'^title:\s*(.+)$', md_content, re.MULTILINE)
    if not title_match:
        print(f"  无法提取标题")
        return False
    
    title = title_match.group(1).strip()
    title_normalized = re.sub(r'[|_\-：:，,。.\s]', '', title)
    
    article_url = None
    for item in articles_list:
        item_title = item.get('title', '')
        item_title_normalized = re.sub(r'[|_\-：:，,。.\s]', '', item_title)
        if title_normalized == item_title_normalized or title in item_title or item_title in title:
            article_url = item['url']
            break
    
    if not article_url:
        print(f"  未找到文章URL")
        return False
    
    print(f"  获取文章HTML: {article_url}")
    html = fetch_article_html(article_url)
    if not html:
        print(f"  [ERROR] 无法获取文章HTML")
        return False
    
    # 提取图片（已过滤小图片）
    images = extract_images_from_html(html, article_url)
    print(f"  从HTML找到 {len(images)} 张图片（已过滤小图片）")
    
    if len(images) < len(missing):
        print(f"  警告: 图片数量({len(images)})少于缺失的图片说明数量({len(missing)})")
    
    # 为缺失的图片说明插入图片
    lines = md_content.split('\n')
    inserted_count = 0
    
    # 从后往前插入，避免位置偏移
    for i in range(len(missing) - 1, -1, -1):
        cap = missing[i]
        line_idx = cap['line']
        
        # 使用对应的图片（按顺序）
        if i < len(images):
            img = images[i]
            img_url = img['url']
            alt_text = cap['text'].strip('（）()')
            
            # 在图片说明后面插入图片
            lines.insert(line_idx + 1, f"![{alt_text}]({img_url})")
            lines.insert(line_idx + 2, "")
            inserted_count += 1
            print(f"    在第 {line_idx + 1} 行后插入图片: {alt_text[:30]}...")
    
    if inserted_count > 0:
        # 保存
        post_file.write_text('\n'.join(lines), encoding='utf-8')
        print(f"  [OK] 已插入 {inserted_count} 张图片")
        return True
    
    return False


def main():
    articles_list = load_articles_list()
    
    processed = 0
    fixed = 0
    skipped = 0
    
    for post_file in Path(POSTS_DIR).glob("*.md"):
        try:
            if process_article(post_file, articles_list):
                fixed += 1
            processed += 1
            # 添加延迟，避免请求过快
            time.sleep(1)
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
            skipped += 1
    
    print(f"\n[SUMMARY] processed={processed}, fixed={fixed}, skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
