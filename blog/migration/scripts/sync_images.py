#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从微信公众号文章中提取图片并同步到博客
- 读取已导入的文章
- 从原始WeChatSync Markdown文件中恢复图片说明
- 从原始文章URL中提取图片
- 将图片插入到原始位置（根据图片说明的位置）
"""

import os
import re
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
DATA_DIR = os.path.join(BASE_DIR, "data")
ARTICLES_LIST_FILE = os.path.join(DATA_DIR, "articles_list.json")
BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")
IMAGES_DIR = os.path.join(BLOG_DIR, "source", "images", "wechat")
WECHATSYNC_MD_DIR = os.path.join(DATA_DIR, "wechatsync_md")

# 请求头，模拟浏览器
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# CDN配置（如果使用CDN）
CDN_BASE = "https://cdn.jsdelivr.net/gh/dadongshangu/CDN@master/images/"


def load_articles_list():
    """加载文章列表"""
    if not os.path.exists(ARTICLES_LIST_FILE):
        return []
    with open(ARTICLES_LIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


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


def find_image_captions_with_context(original_md):
    """从原始Markdown文件中查找图片说明及其上下文"""
    lines = original_md.split('\n')
    captions = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 模式1: 单独一行的括号说明
        if re.match(r'^[（(].*[）)]$', stripped):
            caption_keywords = ['摄', '照', 'photo', 'image', '©', '来源', 'via', '|', '图', '大东山谷', '孟祥志', '村子', '星轨', '大东峪', '宁国', '皖南', '推荐']
            if any(keyword in stripped for keyword in caption_keywords):
                # 获取上下文（前后各2行）
                context_before = []
                context_after = []
                for j in range(max(0, i-2), i):
                    if lines[j].strip():
                        context_before.append(lines[j].strip())
                for j in range(i+1, min(len(lines), i+3)):
                    if lines[j].strip():
                        context_after.append(lines[j].strip())
                
                captions.append({
                    'line_index': i,
                    'text': stripped,
                    'original_line': line,
                    'type': 'standalone',
                    'context_before': context_before,
                    'context_after': context_after
                })
        
        # 模式2: 行内的括号说明
        inline_captions = re.finditer(r'[（(]([^）)]*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南)[^）)]*)[）)]', line)
        for match in inline_captions:
            captions.append({
                'line_index': i,
                'text': match.group(0),
                'original_line': line,
                'type': 'inline',
                'start_pos': match.start(),
                'end_pos': match.end(),
                'context_before': [lines[i-1].strip()] if i > 0 and lines[i-1].strip() else [],
                'context_after': [lines[i+1].strip()] if i < len(lines)-1 and lines[i+1].strip() else []
            })
    
    return captions


def find_caption_position_in_imported_md(caption, imported_lines):
    """在导入后的文章中找到图片说明应该插入的位置"""
    # 使用上下文来定位
    context_before = caption.get('context_before', [])
    context_after = caption.get('context_after', [])
    
    # 尝试找到匹配的上下文位置
    best_match = None
    best_score = 0
    
    for i in range(len(imported_lines)):
        score = 0
        # 检查前文匹配
        for ctx in context_before:
            for j in range(max(0, i-5), i):
                if ctx in imported_lines[j]:
                    score += 1
                    break
        # 检查后文匹配
        for ctx in context_after:
            for j in range(i+1, min(len(imported_lines), i+6)):
                if ctx in imported_lines[j]:
                    score += 1
                    break
        
        if score > best_score:
            best_score = score
            best_match = i
    
    # 如果找到了较好的匹配，返回位置
    if best_match is not None and best_score >= 1:
        return best_match
    
    # 如果没找到，尝试通过图片说明文本本身来匹配
    caption_text = caption['text'].strip('（）()')
    for i, line in enumerate(imported_lines):
        # 检查是否在附近有相关的文本
        if caption_text[:10] in line or any(keyword in line for keyword in caption_text.split('|')[:1]):
            return i
    
    return None


def insert_images_at_correct_positions(imported_md, images, captions):
    """将图片插入到正确的位置（根据图片说明的位置）"""
    if not images:
        return imported_md
    
    # 先删除末尾堆放的图片
    lines = imported_md.split('\n')
    # 从后往前查找，删除所有图片链接
    new_lines = []
    for line in lines:
        if not re.match(r'^!\[.*\]\(https?://', line):
            new_lines.append(line)
    
    lines = new_lines
    
    # 为每个图片说明找到插入位置
    caption_positions = []
    for caption in captions:
        pos = find_caption_position_in_imported_md(caption, lines)
        if pos is not None:
            caption_positions.append({
                'position': pos,
                'caption': caption,
                'image_idx': len(caption_positions)  # 按顺序分配图片
            })
    
    # 按位置从后往前排序，这样插入时不会影响后续的位置
    caption_positions.sort(key=lambda x: x['position'], reverse=True)
    
    # 插入图片（从后往前插入，避免位置偏移）
    for item in caption_positions:
        pos = item['position']
        caption = item['caption']
        image_idx = item['image_idx']
        
        if image_idx < len(images):
            img = images[image_idx]
            img_url = img['url']
            # 使用图片说明作为alt文本
            alt_text = caption['text'].strip('（）()')
            
            # 在指定位置插入图片和说明
            if caption['type'] == 'standalone':
                # 单独一行的说明，在说明位置前插入图片
                # 先检查该位置是否已经有图片说明文本
                if pos < len(lines) and caption['text'] in lines[pos]:
                    # 说明已存在，在它前面插入图片
                    lines.insert(pos, f"![{alt_text}]({img_url})")
                    lines.insert(pos + 1, "")
                else:
                    # 说明不存在，插入图片和说明
                    lines.insert(pos, f"![{alt_text}]({img_url})")
                    lines.insert(pos + 1, "")
                    lines.insert(pos + 2, caption['text'])
            elif caption['type'] == 'inline':
                # 行内的说明，需要找到包含该说明的行
                # 由于导入时可能已经删除了说明，我们需要通过上下文来定位
                # 这里我们简化处理：在找到的位置插入图片，然后添加说明
                lines.insert(pos, f"![{alt_text}]({img_url})")
                lines.insert(pos + 1, "")
                lines.insert(pos + 2, caption['text'])
    
    # 如果还有未分配的图片，在文章末尾（推广内容前）插入
    used_indices = {item['image_idx'] for item in caption_positions}
    remaining_images = [img for i, img in enumerate(images) if i not in used_indices]
    
    if remaining_images:
        # 查找推广内容的位置
        promo_start = len(lines)
        for idx in range(len(lines) - 1, max(0, len(lines) - 20), -1):
            line = lines[idx].strip()
            if any(keyword in line for keyword in ['感谢关注', '近期', '推荐', 'mp.weixin.qq.com']):
                promo_start = idx
                break
        
        # 在推广内容前插入剩余图片
        for img in remaining_images:
            img_url = img['url']
            alt_text = img.get('alt') or '图片'
            lines.insert(promo_start, f"![{alt_text}]({img_url})")
            lines.insert(promo_start + 1, "")
            promo_start += 2
    
    return '\n'.join(lines)


def load_original_markdown(title):
    """从原始WeChatSync导出的Markdown文件中加载内容"""
    # 规范化标题用于匹配
    title_normalized = re.sub(r'[|_\-：:，,。.\s]', '', title)
    
    for md_file in Path(WECHATSYNC_MD_DIR).glob("*.md"):
        # 跳过带-1后缀的重复文件
        if md_file.stem.endswith('-1'):
            continue
        
        file_stem_normalized = re.sub(r'[|_\-：:，,。.\s]', '', md_file.stem)
        
        # 检查标题是否匹配
        if (title_normalized in file_stem_normalized or 
            file_stem_normalized in title_normalized or
            title in md_file.stem or
            md_file.stem in title):
            try:
                return md_file.read_text(encoding='utf-8')
            except Exception as e:
                print(f"    [WARN] 读取原始文件失败 {md_file.name}: {e}")
    
    return None


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


def process_article(post_file, article_url):
    """处理单篇文章，提取并插入图片"""
    print(f"\n处理文章: {post_file.name}")
    
    # 读取文章内容
    md_content = post_file.read_text(encoding='utf-8')
    
    # 读取文章标题
    title_match = re.search(r'^title:\s*(.+)$', md_content, re.MULTILINE)
    if not title_match:
        print(f"  [ERROR] 无法读取文章标题")
        return False
    
    title = title_match.group(1).strip()
    
    # 加载原始Markdown文件
    original_md = load_original_markdown(title)
    if not original_md:
        print(f"  [WARN] 未找到原始Markdown文件，跳过")
        return False
    
    print(f"  找到原始文件")
    
    # 从原始文件中提取图片说明
    captions = find_image_captions_with_context(original_md)
    print(f"  找到 {len(captions)} 个图片说明")
    
    if not captions:
        print(f"  [INFO] 原始文件中没有图片说明")
        return False
    
    # 获取文章HTML并提取图片
    print(f"  获取文章内容: {article_url}")
    html = fetch_article_html(article_url)
    if not html:
        print(f"  [ERROR] 无法获取文章HTML")
        return False
    
    images = extract_images_from_html(html, article_url)
    if not images:
        print(f"  [INFO] 未找到图片")
        return False
    
    print(f"  找到 {len(images)} 张图片")
    
    # 先删除末尾堆放的图片
    lines = md_content.split('\n')
    cleaned_lines = []
    for line in lines:
        if not re.match(r'^!\[.*\]\(https?://', line):
            cleaned_lines.append(line)
    md_content = '\n'.join(cleaned_lines)
    
    # 将图片插入到正确位置
    new_content = insert_images_at_correct_positions(md_content, images, captions)
    
    # 保存更新后的文章
    post_file.write_text(new_content, encoding='utf-8')
    
    inserted_count = min(len(images), len(captions))
    print(f"  [OK] 已更新文章，在正确位置插入了 {inserted_count} 张图片")
    
    return True


def main():
    """主函数"""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    # 加载文章列表
    articles_list = load_articles_list()
    if not articles_list:
        print(f"[ERROR] 无法加载文章列表: {ARTICLES_LIST_FILE}")
        return 1
    
    # 创建标题到URL的映射
    title_to_url = {}
    for article in articles_list:
        article_title = article.get('title', '').strip()
        url = article.get('url', '').strip()
        if article_title and url:
            title_normalized = re.sub(r'\s+', ' ', article_title)
            title_normalized = re.sub(r'[“”"\']', '', title_normalized)
            title_to_url[title_normalized] = url
    
    # 处理所有文章
    processed = 0
    skipped = 0
    failed = 0
    
    for post_file in Path(POSTS_DIR).glob("*.md"):
        # 读取文章标题
        content = post_file.read_text(encoding='utf-8', errors='ignore')
        title_match = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
        if not title_match:
            continue
        
        title = title_match.group(1).strip()
        title_normalized = re.sub(r'\s+', ' ', title)
        title_normalized = re.sub(r'[“”"\']', '', title_normalized)
        
        # 查找对应的URL
        article_url = None
        if title_normalized in title_to_url:
            article_url = title_to_url[title_normalized]
        else:
            for key, url in title_to_url.items():
                key_clean = re.sub(r'[|_\-：:，,。.]', '', key)
                title_clean = re.sub(r'[|_\-：:，,。.]', '', title_normalized)
                if title_clean in key_clean or key_clean in title_clean:
                    article_url = url
                    break
        
        if not article_url:
            print(f"\n[SKIP] 未找到URL: {title}")
            skipped += 1
            continue
        
        # 处理文章
        try:
            if process_article(post_file, article_url):
                processed += 1
            else:
                skipped += 1
            time.sleep(2)  # 避免请求过快
        except Exception as e:
            print(f"  [ERROR] 处理失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n[SUMMARY] processed={processed}, skipped={skipped}, failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
