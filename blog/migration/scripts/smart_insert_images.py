#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能图片插入脚本
- 检查哪些文章有图片说明但缺少图片
- 从HTML中提取图片
- 根据上下文匹配，将图片插入到正确位置
- 确保不破坏段落结构、不重复、不删除文字
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
                print(f"    [WARN] 可能被反爬虫拦截")
                return None
            return response.text
        else:
            print(f"    [ERROR] HTTP {response.status_code}")
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
        
        # 尝试从URL中提取尺寸信息
        if 'wx_fmt=' in src:
            # 微信图片URL通常包含尺寸信息
            if 'mmbiz' in src:
                # 微信图片，通常都是正常尺寸
                pass
            else:
                continue
        
        # 如果明确标注了很小的尺寸，跳过
        try:
            if width and height:
                w = int(re.sub(r'[^\d]', '', str(width)))
                h = int(re.sub(r'[^\d]', '', str(height)))
                if w < MIN_IMAGE_WIDTH or h < MIN_IMAGE_HEIGHT:
                    continue
        except:
            pass
        
        # 获取图片的alt文本
        alt_text = img.get('alt') or ''
        
        images.append({
            'url': src,
            'alt': alt_text
        })
    
    return images


def find_captions_without_images(md_content):
    """查找有图片说明但缺少图片的位置"""
    lines = md_content.split('\n')
    captions = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 检查是否是图片说明行（单独的括号行或斜体括号行）
        is_caption = False
        caption_text = ""
        
        # 方法1: 单独的括号行
        if re.match(r'^[（(].*[）)]$', stripped):
            caption_keywords = ['摄', '照', 'photo', 'image', '©', '来源', 'via', '|', '图', '大东山谷', '孟祥志', '村子', '星轨', '大东峪', '宁国', '皖南', '推荐', '假设', '价格', '母亲', '电话机', '安徽宁国', '山东农村', '两岁的你', '有模有样', '画警车', '爷爷奶奶', '生日礼物', '小时候', '散步', '石榴树']
            if any(keyword in stripped for keyword in caption_keywords):
                is_caption = True
                caption_text = stripped
        
        # 方法2: 斜体括号行（可能以__结尾，可能有空格）
        if not is_caption:
            # 匹配 _（...）_ __ 或 _（...）_ 格式
            italic_match = re.match(r'^_?\s*[（(](.+?)[）)]\s*_?\s*_*$', stripped)
            if italic_match:
                caption_keywords = ['摄', '照', 'photo', 'image', '©', '来源', 'via', '|', '图', '大东山谷', '孟祥志', '村子', '星轨', '大东峪', '宁国', '皖南', '推荐', '假设', '价格', '母亲', '电话机', '安徽宁国', '山东农村', '两岁的你', '有模有样', '画警车', '爷爷奶奶', '生日礼物', '小时候', '散步', '石榴树', '爷爷', '院子', '睡着']
                caption_content = italic_match.group(1)
                if any(keyword in caption_content for keyword in caption_keywords):
                    is_caption = True
                    caption_text = stripped.strip('_').strip()
        
        if is_caption:
            # 检查前后是否有图片
            has_image_before = False
            has_image_after = False
            
            # 检查前10行是否有图片
            for j in range(max(0, i-10), i):
                if re.match(r'^!\[.*\]\(https?://mmbiz', lines[j]):
                    # 检查图片的alt文本是否与图片说明匹配
                    alt_match = re.match(r'^!\[([^\]]+)\]', lines[j])
                    if alt_match:
                        alt_text = alt_match.group(1)
                        caption_text_clean = caption_text.strip('（）()_').strip()
                        # 如果图片说明和图片alt文本匹配，说明已经有图片了
                        if caption_text_clean in alt_text or alt_text in caption_text_clean:
                            has_image_before = True
                            break
            
            # 检查后10行是否有图片
            for j in range(i+1, min(len(lines), i+11)):
                if re.match(r'^!\[.*\]\(https?://mmbiz', lines[j]):
                    # 检查图片的alt文本是否与图片说明匹配
                    alt_match = re.match(r'^!\[([^\]]+)\]', lines[j])
                    if alt_match:
                        alt_text = alt_match.group(1)
                        caption_text_clean = caption_text.strip('（）()_').strip()
                        # 如果图片说明和图片alt文本匹配，说明已经有图片了
                        if caption_text_clean in alt_text or alt_text in caption_text_clean:
                            has_image_after = True
                            break
            
            # 如果前后都没有匹配的图片，记录这个位置
            if not has_image_before and not has_image_after:
                # 获取上下文
                prev_line = ""
                for j in range(i-1, max(0, i-6), -1):
                    if lines[j].strip() and not re.match(r'^[（(].*[）)]$', lines[j].strip()):
                        prev_line = lines[j].strip()
                        break
                
                next_line = ""
                for j in range(i+1, min(len(lines), i+6)):
                    if lines[j].strip() and not re.match(r'^[（(].*[）)]$', lines[j].strip()):
                        next_line = lines[j].strip()
                        break
                
                captions.append({
                    'line_index': i,
                    'caption_text': caption_text,
                    'prev_line': prev_line,
                    'next_line': next_line,
                    'original_line': line
                })
    
    return captions


def match_image_to_caption(caption, images):
    """根据上下文匹配图片和图片说明"""
    caption_text = caption['caption_text'].strip('（）()_')
    prev_line = caption['prev_line']
    next_line = caption['next_line']
    
    best_match = None
    best_score = 0
    
    for img in images:
        score = 0
        alt_text = img['alt'].strip()
        url = img['url']
        
        # 如果图片已经被使用过，跳过
        if 'used' in img and img['used']:
            continue
        
        # 1. 检查alt文本是否包含图片说明的关键词
        caption_keywords = re.findall(r'[\u4e00-\u9fa5]+', caption_text)
        for keyword in caption_keywords:
            if len(keyword) >= 2 and keyword in alt_text:
                score += 10
            if keyword in url:
                score += 5
        
        # 2. 检查图片说明是否包含在alt文本中
        if caption_text in alt_text or alt_text in caption_text:
            score += 20
        
        # 3. 检查上下文匹配
        if prev_line:
            prev_keywords = re.findall(r'[\u4e00-\u9fa5]+', prev_line)
            for keyword in prev_keywords:
                if len(keyword) >= 2 and keyword in alt_text:
                    score += 3
        
        if next_line:
            next_keywords = re.findall(r'[\u4e00-\u9fa5]+', next_line)
            for keyword in next_keywords:
                if len(keyword) >= 2 and keyword in alt_text:
                    score += 3
        
        if score > best_score:
            best_score = score
            best_match = img
    
    return best_match if best_score >= 5 else None


def insert_image_at_position(lines, caption, image):
    """在指定位置插入图片，不破坏段落结构"""
    line_index = caption['line_index']
    original_line = caption['original_line']
    
    # 构建图片markdown
    caption_text = caption['caption_text'].strip('（）()_')
    image_markdown = f"![{caption_text}]({image['url']})"
    
    # 检查原始行是否是斜体格式
    is_italic = original_line.strip().startswith('_') and original_line.strip().endswith('_')
    
    result_lines = lines[:]
    
    # 在图片说明行之前插入图片
    # 如果图片说明行是斜体格式，保留斜体格式的图片说明
    if is_italic:
        # 插入图片，然后保留斜体格式的图片说明
        result_lines.insert(line_index, image_markdown)
        # 图片说明行已经在正确位置，不需要修改
    else:
        # 插入图片，然后保留图片说明
        result_lines.insert(line_index, image_markdown)
        # 图片说明行已经在正确位置，不需要修改
    
    # 确保图片前后有空行（但不破坏现有段落结构）
    # 检查图片前是否有空行
    if line_index > 0 and result_lines[line_index - 1].strip():
        # 如果前一行不是空行，检查是否需要添加空行
        prev_line = result_lines[line_index - 1].strip()
        # 如果前一行不是特殊格式（列表、引用等），添加空行
        if not prev_line.startswith(('*', '-', '+', '1.', '2.', '3.', '>', '#')):
            result_lines.insert(line_index, "")
            line_index += 1
    
    # 检查图片说明后是否有空行
    caption_line_index = line_index + 1
    if caption_line_index < len(result_lines) and result_lines[caption_line_index].strip():
        # 如果图片说明后一行不是空行，检查是否需要添加空行
        next_line = result_lines[caption_line_index].strip()
        # 如果下一行不是特殊格式，添加空行
        if not next_line.startswith(('*', '-', '+', '1.', '2.', '3.', '>', '#')):
            result_lines.insert(caption_line_index + 1, "")
    
    return result_lines


def process_article(post_file, articles_list):
    """处理单篇文章"""
    print(f"\n处理: {post_file.name}")
    
    # 读取markdown内容
    md_content = post_file.read_text(encoding='utf-8')
    
    # 查找有图片说明但缺少图片的位置
    captions = find_captions_without_images(md_content)
    
    if not captions:
        print(f"  无需修复（没有缺少图片的图片说明）")
        return False
    
    print(f"  找到 {len(captions)} 个缺少图片的图片说明")
    for cap in captions[:3]:  # 只显示前3个
        print(f"    - {cap['caption_text'][:50]}...")
    
    # 从文章列表中找到对应的URL
    article_title = post_file.stem
    # 从front-matter中提取标题
    title_match = re.search(r'^title:\s*(.+)$', md_content, re.MULTILINE)
    if title_match:
        article_title_from_md = title_match.group(1).strip()
    else:
        article_title_from_md = article_title
    
    article_url = None
    
    for article in articles_list:
        article_title_in_list = article.get('title', '')
        # 尝试多种匹配方式
        if (article_title in article_title_in_list or 
            article_title_from_md in article_title_in_list or
            article_title_in_list in article_title or
            article_title_in_list in article_title_from_md):
            article_url = article.get('url')
            break
    
    if not article_url:
        print(f"  [WARN] 未找到文章URL")
        return False
    
    print(f"  获取文章HTML: {article_url}")
    
    # 获取HTML内容
    html_content = fetch_article_html(article_url)
    if not html_content:
        print(f"  [ERROR] 无法获取文章HTML")
        return False
    
    # 提取图片
    images = extract_images_from_html(html_content, article_url)
    print(f"  从HTML找到 {len(images)} 张图片")
    
    if not images:
        print(f"  [WARN] HTML中没有找到图片")
        return False
    
    # 匹配图片和图片说明
    lines = md_content.split('\n')
    inserted_count = 0
    
    # 从后往前处理，避免索引变化
    for caption in reversed(captions):
        matched_image = match_image_to_caption(caption, images)
        
        if matched_image:
            print(f"    匹配图片: {caption['caption_text'][:30]}...")
            lines = insert_image_at_position(lines, caption, matched_image)
            matched_image['used'] = True
            inserted_count += 1
        else:
            print(f"    [WARN] 无法匹配图片: {caption['caption_text'][:30]}...")
    
    if inserted_count > 0:
        new_content = '\n'.join(lines)
        post_file.write_text(new_content, encoding='utf-8')
        print(f"  [OK] 已插入 {inserted_count} 张图片")
        return True
    
    print(f"  [WARN] 未插入任何图片")
    return False


def main():
    """主函数"""
    articles_list = load_articles_list()
    if not articles_list:
        print("[ERROR] 无法加载文章列表")
        return 1
    
    fixed = 0
    processed = 0
    
    for post_file in Path(POSTS_DIR).glob("*.md"):
        try:
            if process_article(post_file, articles_list):
                fixed += 1
            processed += 1
            time.sleep(1)  # 避免请求过快
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n[SUMMARY] processed={processed}, fixed={fixed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
