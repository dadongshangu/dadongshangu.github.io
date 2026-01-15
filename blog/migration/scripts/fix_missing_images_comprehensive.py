#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全面修复所有文章的缺失图片
- 检查所有文章
- 从HTML获取图片（过滤小图片/分隔符）
- 插入到合适位置
"""

import os
import re
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

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
    """从HTML中提取图片，过滤小图片（分隔符）"""
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
        
        # 过滤掉微信头像、二维码、logo等
        skip_keywords = ['avatar', 'qrcode', 'logo', 'icon']
        if any(skip in src.lower() for skip in skip_keywords):
            continue
        
        # 过滤掉gif格式的图标（通常是动画表情或分隔符）
        if 'wx_fmt=gif' in src.lower() and 'mmbiz' not in src.lower():
            continue
        
        is_valid = False
        width = None
        height = None
        
        if 'mmbiz' in src.lower():
            # 对于gif格式，检查尺寸，小图标通常不是文章图片
            if 'wx_fmt=gif' in src.lower():
                width = img.get('width') or img.get('data-width') or ''
                height = img.get('height') or img.get('data-height') or ''
                try:
                    if width and height:
                        w, h = int(width), int(height)
                        # 过滤掉小于200x200的图片（可能是分隔符）
                        if w < 200 or h < 200:
                            continue
                except:
                    pass
            is_valid = True
        elif any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            is_valid = True
        
        if not is_valid:
            continue
        
        alt = img.get('alt') or img.get('title') or ''
        
        images.append({
            'url': src,
            'alt': alt,
            'index': len(images)
        })
    
    return images

def find_captions_in_article(md_content):
    """查找文章中的所有图片说明"""
    lines = md_content.split('\n')
    captions = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 匹配 _（...）_ 格式的图片说明
        if re.search(r'_[（(]([^）)]+)[）)]_', stripped):
            match = re.search(r'[（(]([^）)]+)[）)]', stripped)
            if match:
                captions.append({
                    'line': i,
                    'text': match.group(0),
                    'has_image': False
                })
    
    # 检查每个图片说明后面是否有图片
    for cap in captions:
        line_idx = cap['line']
        for j in range(line_idx + 1, min(line_idx + 6, len(lines))):
            if re.match(r'^!\[.*\]\(https?://mmbiz', lines[j]):
                cap['has_image'] = True
                break
    
    return captions

def count_existing_images(md_content):
    """统计文章中已有的图片数量"""
    return len(re.findall(r'!\[.*\]\(https?://mmbiz', md_content))

def process_article(post_file):
    """处理单篇文章"""
    print(f"\n处理: {post_file.name}")
    
    # 读取文章
    md_content = post_file.read_text(encoding='utf-8')
    
    # 统计已有图片
    existing_count = count_existing_images(md_content)
    
    # 查找图片说明
    captions = find_captions_in_article(md_content)
    missing_captions = [cap for cap in captions if not cap['has_image']]
    
    # 从文章列表获取URL
    title_match = re.search(r'^title:\s*(.+)$', md_content, re.MULTILINE)
    if not title_match:
        print(f"  无法读取标题，跳过")
        return False
    
    title = title_match.group(1).strip()
    title_normalized = re.sub(r'[|_\-：:，,。.\s]', '', title)
    
    articles_list = load_articles_list()
    article_url = None
    for item in articles_list:
        if item.get('title'):
            item_title_normalized = re.sub(r'[|_\-：:，,。.\s]', '', item['title'])
            if title_normalized == item_title_normalized:
                article_url = item['url']
                break
    
    if not article_url:
        print(f"  未找到文章URL，跳过")
        return False
    
    # 获取HTML并提取图片
    print(f"  获取文章HTML: {article_url}")
    html = fetch_article_html(article_url)
    if not html:
        print(f"  [ERROR] 无法获取文章HTML")
        return False
    
    images = extract_images_from_html(html, article_url)
    print(f"  从HTML找到 {len(images)} 张图片（已有 {existing_count} 张）")
    
    # 如果HTML中没有图片，跳过
    if len(images) == 0:
        print(f"  HTML中没有图片，跳过")
        return False
    
    # 判断是否需要插入图片
    need_insert = False
    if existing_count == 0 and len(images) > 0:
        need_insert = True
        print(f"  文章中没有图片，需要插入 {len(images)} 张")
    elif len(images) > existing_count:
        need_insert = True
        print(f"  需要插入 {len(images) - existing_count} 张图片")
    elif missing_captions:
        need_insert = True
        print(f"  有 {len(missing_captions)} 个图片说明缺失图片，需要处理")
    
    if not need_insert:
        print(f"  图片数量足够，无需添加")
        return False
    
    # 计算需要插入的图片数量
    if existing_count == 0:
        need_insert_count = len(images)
    elif missing_captions:
        need_insert_count = max(len(missing_captions), len(images) - existing_count)
    else:
        need_insert_count = len(images) - existing_count
    
    lines = md_content.split('\n')
    inserted = 0
    
    # 如果有缺失的图片说明，优先为它们插入图片
    if missing_captions:
        print(f"  为 {len(missing_captions)} 个图片说明插入图片")
        # 从后往前插入，避免位置偏移
        for i in range(len(missing_captions) - 1, -1, -1):
            if inserted >= need_insert_count:
                break
            
            cap = missing_captions[i]
            line_idx = cap['line']
            
            # 使用对应的图片
            img_idx = existing_count + inserted
            if img_idx < len(images):
                img = images[img_idx]
                img_url = img['url']
                alt_text = cap['text'].strip('（）()')
                
                # 在图片说明后面插入图片
                lines.insert(line_idx + 1, f"![{alt_text}]({img_url})")
                lines.insert(line_idx + 2, "")
                inserted += 1
                print(f"    在第 {line_idx + 1} 行后插入图片: {alt_text[:30]}...")
    
    # 如果还需要插入更多图片（没有图片说明的情况）
    if inserted < need_insert_count:
        # 检查文章内容长度
        content_lines = [l for l in lines if l.strip() and not l.strip().startswith('---') and not l.strip().startswith('title:') and not l.strip().startswith('date:') and not l.strip().startswith('tags:')]
        
        if len(content_lines) >= 10:
            print(f"  文章有内容（{len(content_lines)} 行），在合适位置插入剩余图片")
            
            # 找到文章内容开始位置（跳过front-matter）
            content_start = 0
            for i, line in enumerate(lines):
                if line.strip() == '---' and i > 0:
                    content_start = i + 1
                    break
            
            # 在文章合适位置插入图片（大约1/3、1/2、2/3处）
            insert_positions = [
                content_start + len(content_lines) // 3,
                content_start + len(content_lines) // 2,
                content_start + len(content_lines) * 2 // 3
            ]
            
            pos_idx = 0
            for i in range(inserted, min(need_insert_count, len(images))):
                img = images[existing_count + i]
                img_url = img['url']
                alt_text = img.get('alt') or '图片'
                
                # 找到合适的插入位置（段落之间）
                if pos_idx < len(insert_positions):
                    insert_pos = insert_positions[pos_idx]
                    pos_idx += 1
                else:
                    # 如果位置用完了，在文章末尾（推广内容前）插入
                    insert_pos = len(lines)
                    for j in range(len(lines) - 1, max(0, len(lines) - 20), -1):
                        if any(keyword in lines[j] for keyword in ['感谢关注', '近期', '推荐', 'mp.weixin.qq.com', '往期精彩', '猜你喜欢', '* * *']):
                            insert_pos = j
                            break
                
                # 找到段落之间的位置
                while insert_pos < len(lines) and lines[insert_pos].strip() and not lines[insert_pos].strip().startswith('*'):
                    insert_pos += 1
                
                if insert_pos < len(lines):
                    lines.insert(insert_pos, f"![{alt_text}]({img_url})")
                    lines.insert(insert_pos + 1, "")
                    lines.insert(insert_pos + 2, "")
                    inserted += 1
                    print(f"    在第 {insert_pos + 1} 行插入图片")
        else:
            print(f"  文章内容较短（{len(content_lines)} 行），跳过剩余图片")
    
    if inserted > 0:
        post_file.write_text('\n'.join(lines), encoding='utf-8')
        print(f"  [OK] 已插入 {inserted} 张图片")
        return True
    
    return False

def main():
    processed = 0
    skipped = 0
    
    for post_file in Path(POSTS_DIR).glob("*.md"):
        try:
            if process_article(post_file):
                processed += 1
                time.sleep(1)  # 避免请求过快
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
