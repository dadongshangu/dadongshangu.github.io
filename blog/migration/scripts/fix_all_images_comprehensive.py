#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
综合图片修复脚本
- 从原始WeChatSync文件提取图片说明及上下文
- 从HTML提取图片URL（过滤小图片）
- 根据上下文匹配，将图片插入到正确位置
- 确保所有图片说明都有对应的图片
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
WECHATSYNC_MD_DIR = os.path.join(DATA_DIR, "wechatsync_md")

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


def extract_captions_from_original(original_md):
    """从原始WeChatSync文件中提取图片说明及其上下文"""
    lines = original_md.split('\n')
    captions = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        matches = []
        
        # 方法1: 查找行内的括号图片说明（标准格式）
        matches = list(re.finditer(r'[（(]([^）)]*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐|假设|价格)[^）)]*)[）)]', line))
        
        # 方法2: 如果没找到，尝试匹配斜体格式的图片说明（如 _（图片说明）_）
        if not matches:
            # 检查是否是斜体格式且包含图片说明关键词
            if re.search(r'_(.*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐|假设|价格).*)_', stripped):
                # 提取括号内的内容
                bracket_match = re.search(r'[（(]([^）)]*)[）)]', stripped)
                if bracket_match:
                    class MatchObj:
                        def __init__(self, full_text, bracket_text):
                            self.full_text = full_text
                            self.bracket_text = bracket_text
                            self.start = lambda: 0
                            self.end = lambda: len(full_text)
                            self.group = lambda n=0: bracket_text if n == 1 else full_text
                    caption_text = bracket_match.group(0)  # 包含括号
                    matches = [MatchObj(stripped, caption_text)]
        
        # 方法3: 如果还是没找到，检查是否是单独一行的图片说明（不带斜体）
        if not matches:
            if re.match(r'^[（(].*[）)]$', stripped):
                if re.search(r'(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐|假设|价格)', stripped):
                    class MatchObj:
                        def __init__(self, text):
                            self.text = text
                            self.start = lambda: 0
                            self.end = lambda: len(text)
                            self.group = lambda n=0: text
                    matches = [MatchObj(stripped)]
        
        # 方法4: 查找斜体格式的图片说明（如 _（小时候带你散步，你经常会睡着）_）
        if not matches:
            # 匹配 _（...）_ 或 _（...）_ __ 格式
            italic_match = re.search(r'_[（(]([^）)]+)[）)]_\s*_*', stripped)
            if italic_match:
                class MatchObj:
                    def __init__(self, text, bracket_text):
                        self.text = text
                        self.bracket_text = bracket_text
                        self.start = lambda: 0
                        self.end = lambda: len(text)
                        self.group = lambda n=0: bracket_text if n == 1 else italic_match.group(0)
                # 提取括号内的内容作为图片说明
                full_match = italic_match.group(0)  # 包含斜体和括号
                # 只提取括号部分
                bracket_only = re.search(r'[（(]([^）)]+)[）)]', full_match)
                if bracket_only:
                    caption_text = bracket_only.group(0)  # 只包含括号
                else:
                    caption_text = full_match
                matches = [MatchObj(stripped, caption_text)]
        
        # 方法5: 查找任何包含括号的斜体行（更宽松的匹配）
        if not matches:
            # 如果行包含斜体和括号，且不是明显的推广内容
            if ('_' in stripped) and ('（' in stripped or '(' in stripped):
                # 排除明显的推广内容
                if any(keyword in stripped for keyword in ['感谢关注', '近期', '推荐', 'mp.weixin.qq.com', '往期精彩', '猜你喜欢']):
                    pass
                else:
                    # 提取括号内的内容
                    bracket_match = re.search(r'[（(]([^）)]+)[）)]', stripped)
                    if bracket_match:
                        class MatchObj:
                            def __init__(self, text, bracket_text):
                                self.text = text
                                self.bracket_text = bracket_text
                                self.start = lambda: 0
                                self.end = lambda: len(text)
                                self.group = lambda n=0: bracket_text
                        caption_text = bracket_match.group(0)  # 包含括号
                        matches = [MatchObj(stripped, caption_text)]
        
        for match in matches:
            # 如果match有bracket_text属性，使用它；否则使用group(0)
            if hasattr(match, 'bracket_text'):
                caption_text = match.bracket_text
            else:
                caption_text = match.group(0)
            start_pos = match.start()
            end_pos = match.end()
            
            # 提取说明前后的文本
            before_text = line[:start_pos].strip() if start_pos > 0 else ""
            after_text = line[end_pos:].strip() if end_pos < len(line) else ""
            
            # 获取前后行的文本作为上下文（跳过空行）
            prev_line = ""
            for j in range(i-1, -1, -1):
                if lines[j].strip():
                    prev_line = lines[j].strip()
                    break
            
            next_line = ""
            for j in range(i+1, len(lines)):
                if lines[j].strip():
                    next_line = lines[j].strip()
                    break
            
            captions.append({
                'text': caption_text,
                'before_text': before_text,
                'after_text': after_text,
                'prev_line': prev_line,
                'next_line': next_line,
                'line_index': i
            })
    
    return captions


def clean_existing_images(md_content):
    """清理现有错误图片链接和重复的图片说明"""
    lines = md_content.split('\n')
    
    # 找到推广内容的开始位置
    promo_start = len(lines)
    for i in range(len(lines) - 1, max(0, len(lines) - 30), -1):
        line = lines[i].strip()
        if any(keyword in line for keyword in ['感谢关注', '近期', '推荐', 'mp.weixin.qq.com', '往期精彩', '猜你喜欢', '* * *', '延伸阅读']):
            promo_start = i
            break
    
    # 检查末尾是否有大量图片堆积
    image_count_at_end = 0
    end_image_start = len(lines)
    for i in range(len(lines) - 1, max(0, len(lines) - 30), -1):
        if re.match(r'^!\[.*\]\(https?://mmbiz', lines[i]):
            image_count_at_end += 1
            end_image_start = i
        elif image_count_at_end > 0 and lines[i].strip():
            # 如果遇到非图片行，停止计数
            if not any(keyword in lines[i] for keyword in ['感谢关注', '近期', '推荐', 'mp.weixin.qq.com', '往期精彩', '猜你喜欢', '* * *']):
                break
    
    # 如果末尾有3个以上图片堆积，标记为需要清理
    should_clean_end_images = image_count_at_end >= 3
    
    cleaned_lines = []
    seen_captions = set()  # 用于跟踪已见过的图片说明
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 如果应该清理末尾图片，且当前位置在末尾图片区域，删除图片
        if should_clean_end_images and i >= end_image_start:
            if re.match(r'^!\[.*\]\(https?://', line):
                continue
        
        # 删除所有图片链接（但保留在文章中间的图片，如果它们不在末尾堆积区域）
        if re.match(r'^!\[.*\]\(https?://', line):
            # 如果不在末尾堆积区域，保留（可能是正确插入的图片）
            if not should_clean_end_images or i < end_image_start:
                cleaned_lines.append(line)
            continue
        
        # 删除单独的图片说明行（但保留紧跟在图片后面的说明，且不重复）
        if re.match(r'^[（(].*[）)]$', stripped):
            caption_keywords = ['摄', '照', 'photo', 'image', '©', '来源', 'via', '|', '图', '大东山谷', '孟祥志', '村子', '星轨', '大东峪', '宁国', '皖南', '推荐', '假设', '价格']
            if any(keyword in stripped for keyword in caption_keywords):
                # 检查前一行是否是图片，如果是，保留这个说明（但只保留一次）
                if i > 0 and re.match(r'^!\[.*\]\(https?://mmbiz', lines[i-1]):
                    if stripped not in seen_captions:
                        cleaned_lines.append(line)
                        seen_captions.add(stripped)
                    continue
                # 检查是否是重复的图片说明（连续多行相同或已见过）
                if stripped in seen_captions:
                    continue
                if i > 0 and i < len(lines) - 1:
                    prev_stripped = lines[i-1].strip() if i > 0 else ""
                    next_stripped = lines[i+1].strip() if i < len(lines) - 1 else ""
                    if stripped == prev_stripped or stripped == next_stripped:
                        continue
                # 记录这个图片说明
                seen_captions.add(stripped)
                continue
        
        # 删除行内的图片说明（但保留其他文本）
        if re.search(r'[（(].*[）)]', line):
            # 提取并删除图片说明
            line = re.sub(r'[（(][^）)]*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐|假设|价格)[^）)]*[）)]', '', line)
            # 如果删除后行为空，跳过
            if not line.strip():
                continue
        
        # 删除错误的URL片段和格式错误的行
        if 'wUPwDW5mooD9KmSpnzXp0WYF1Lia3e0UCAvZ95bWn2ONRSo9sa11ElibsT3vc7ekTb9TWVg' in line:
            continue
        if re.search(r'\]\(https?://[^\)]*\)[^\)]*\)', line):
            continue
        if stripped in [')', '）']:
            continue
        if stripped.startswith(')') or stripped.startswith('）'):
            if len(stripped) == 1:
                continue
            line = line.lstrip(')）').strip()
            if not line:
                continue
        
        cleaned_lines.append(line)
    
    # 清理多余空行和重复的图片说明，同时保留段落分隔
    # 注意：不要过度清理空行，保留段落之间的空行
    result = []
    prev_empty = False
    prev_caption = None
    caption_count = {}  # 跟踪每个图片说明出现的次数
    
    for i, line in enumerate(cleaned_lines):
        is_empty = not line.strip()
        stripped = line.strip()
        
        # 检查是否是重复的图片说明
        if re.match(r'^[（(].*[）)]$', stripped):
            if any(kw in stripped for kw in ['摄', '照', 'photo', 'image', '©', '来源', 'via', '大东山谷', '孟祥志', '村子', '星轨', '大东峪', '宁国', '皖南']):
                # 检查前一行是否是图片
                if len(result) > 0 and re.match(r'^!\[.*\]\(https?://mmbiz', result[-1]):
                    # 紧跟在图片后面，保留
                    caption_count[stripped] = caption_count.get(stripped, 0) + 1
                    result.append(line)
                    prev_caption = stripped
                    prev_empty = False
                    continue
                # 如果与上一个图片说明相同，跳过
                if prev_caption == stripped:
                    continue
                # 如果这个图片说明已经出现过多次（超过2次），跳过
                if caption_count.get(stripped, 0) >= 2:
                    continue
                caption_count[stripped] = caption_count.get(stripped, 0) + 1
                prev_caption = stripped
            else:
                prev_caption = None
        else:
            prev_caption = None
        
        if is_empty:
            # 保留空行以分隔段落，但不要连续多个空行（最多保留1个连续空行）
            # 如果上一行是文本内容，保留这个空行作为段落分隔
            if len(result) > 0 and result[-1].strip() and not prev_empty:
                result.append("")
            prev_empty = True
        else:
            result.append(line)
            prev_empty = False
    
    return '\n'.join(result)


def find_insert_position(caption, imported_lines):
    """根据上下文找到插入位置"""
    after_text = caption['after_text']
    next_line = caption['next_line']
    before_text = caption['before_text']
    prev_line = caption.get('prev_line', '')
    
    # 方法1: 如果图片说明是单独一行（after_text为空），优先使用next_line匹配
    if not after_text or len(after_text) < 5:
        if next_line and len(next_line) > 5:
            next_clean = re.sub(r'^[，,。.\s]+', '', next_line)
            next_clean = next_clean.strip()
            
            search_text = next_clean[:30] if len(next_clean) > 30 else next_clean
            
            for i, line in enumerate(imported_lines):
                line_clean = line.strip()
                if line_clean.startswith(search_text):
                    return i
                if search_text in line_clean:
                    return i
    
    # 方法2: 通过after_text精确匹配
    if after_text and len(after_text) > 5:
        after_clean = re.sub(r'^[，,。.\s]+', '', after_text)
        after_clean = after_clean.strip()
        search_text = after_clean[:30] if len(after_clean) > 30 else after_clean
        
        for i, line in enumerate(imported_lines):
            line_clean = line.strip()
            if line_clean.startswith(search_text):
                return i
            if search_text in line_clean:
                return i
    
    # 方法3: 通过next_line模糊匹配
    if next_line and len(next_line) > 10:
        next_clean = next_line.strip()[:20]
        for i, line in enumerate(imported_lines):
            if next_clean in line:
                return i
    
    # 方法4: 组合prev_line和next_line匹配
    if prev_line and next_line:
        for i in range(len(imported_lines) - 1):
            line1 = imported_lines[i].strip()
            line2 = imported_lines[i+1].strip() if i+1 < len(imported_lines) else ""
            if prev_line[:20] in line1 and next_line[:20] in line2:
                return i + 1
    
    # 方法5: 通过before_text匹配
    if before_text and len(before_text) > 10:
        before_clean = before_text.strip()[:30]
        for i, line in enumerate(imported_lines):
            if before_clean in line:
                return i + 1 if i + 1 < len(imported_lines) else i
    
    return None


def restore_paragraph_breaks(md_content):
    """恢复段落分隔：在句号、问号、感叹号后添加空行"""
    lines = md_content.split('\n')
    result = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 如果当前行是空行，直接添加
        if not stripped:
            result.append("")
            continue
        
        result.append(line)
        
        # 如果当前行是文本（不是图片、不是空行、不是标题、不是列表、不是图片说明），检查是否需要添加段落分隔
        if (stripped and 
            not re.match(r'^!\[.*\]\(https?://', line) and 
            not line.strip().startswith('#') and
            not line.strip().startswith('*') and
            not line.strip().startswith('-') and
            not re.match(r'^[（(].*[）)]$', stripped) and
            not stripped.startswith('_') and
            not stripped.startswith('**')):
            
            # 如果行以句号、问号、感叹号结尾，且下一行不是空行且不是图片，添加空行
            if stripped and stripped[-1] in ['。', '！', '？', '.', '!', '?']:
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if (next_line and 
                        not re.match(r'^!\[.*\]\(https?://', lines[i + 1]) and
                        not lines[i + 1].strip().startswith('#') and
                        not next_line.startswith('*') and
                        not next_line.startswith('-') and
                        not re.match(r'^[（(].*[）)]$', next_line) and
                        not next_line.startswith('_') and
                        not next_line.startswith('**')):
                        # 如果当前行以句号结尾，且下一行不是空行，添加空行（更宽松的规则）
                        result.append("")
    
    return '\n'.join(result)


def insert_images_correctly(imported_md, images, captions):
    """将图片插入到正确位置"""
    cleaned_md = clean_existing_images(imported_md)
    # 恢复段落分隔
    cleaned_md = restore_paragraph_breaks(cleaned_md)
    lines = cleaned_md.split('\n')
    insertions = []
    
    # 为每个图片说明找到对应的图片和插入位置
    for i, caption in enumerate(captions):
        if i >= len(images):
            break
        
        pos = find_insert_position(caption, lines)
        if pos is not None:
            insertions.append({
                'position': pos,
                'caption': caption,
                'image': images[i],
                'caption_index': i
            })
        else:
            print(f"    警告: 未找到图片说明 '{caption['text'][:30]}...' 的插入位置")
    
    # 按位置从后往前排序，避免插入时位置偏移
    insertions.sort(key=lambda x: x['position'], reverse=True)
    
    # 执行插入
    for item in insertions:
        pos = item['position']
        caption = item['caption']
        img = item['image']
        
        # 检查位置是否已有图片
        if pos < len(lines) and re.match(r'^!\[.*\]\(https?://', lines[pos]):
            print(f"    跳过: 位置 {pos} 已有图片")
            continue
        
        caption_text = caption['text']
        if not (caption_text.startswith('(') or caption_text.startswith('（')):
            bracket_match = re.search(r'[（(]([^）)]*)[）)]', caption_text)
            if bracket_match:
                caption_text = bracket_match.group(0)
        
        alt_text = caption_text.strip('（）()')
        img_url = img['url']
        
        # 在图片说明位置插入图片
        # 确保图片前后有适当的空行以保持段落分隔
        insert_pos = pos
        # 如果插入位置前一行不是空行且不是图片，先插入一个空行
        if insert_pos > 0 and lines[insert_pos - 1].strip() and not re.match(r'^!\[.*\]\(https?://', lines[insert_pos - 1]):
            lines.insert(insert_pos, "")
            insert_pos += 1
        
        lines.insert(insert_pos, f"![{alt_text}]({img_url})")
        lines.insert(insert_pos + 1, "")
        lines.insert(insert_pos + 2, caption_text)
        
        # 如果插入位置后一行不是空行且不是图片，添加一个空行
        if insert_pos + 3 < len(lines) and lines[insert_pos + 3].strip() and not re.match(r'^!\[.*\]\(https?://', lines[insert_pos + 3]):
            lines.insert(insert_pos + 3, "")
    
    # 处理剩余的图片（没有匹配到图片说明的）
    used_image_indices = {item['image']['index'] for item in insertions}
    remaining_images = [img for img in images if img['index'] not in used_image_indices]
    
    if remaining_images:
        # 找到推广内容的位置
        promo_start = len(lines)
        for idx in range(len(lines) - 1, max(0, len(lines) - 20), -1):
            line = lines[idx].strip()
            if any(keyword in line for keyword in ['感谢关注', '近期', '推荐', 'mp.weixin.qq.com', '往期精彩', '猜你喜欢', '* * *']):
                promo_start = idx
                break
        
        # 在推广内容之前插入剩余图片
        for img in remaining_images:
            img_url = img['url']
            alt_text = img.get('alt') or '图片'
            lines.insert(promo_start, f"![{alt_text}]({img_url})")
            lines.insert(promo_start + 1, "")
            promo_start += 2
    
    # 最后清理：删除重复图片和末尾堆积的图片
    # 1. 删除重复的图片（相同URL的图片）
    seen_urls = set()
    lines_to_remove = []
    for idx, line in enumerate(lines):
        if re.match(r'^!\[.*\]\(https?://mmbiz', line):
            # 提取URL
            url_match = re.search(r'\(https?://[^\)]+\)', line)
            if url_match:
                url = url_match.group(0)
                if url in seen_urls:
                    # 这是重复的图片，标记删除
                    lines_to_remove.append(idx)
                else:
                    seen_urls.add(url)
    
    # 从后往前删除，避免索引偏移
    for idx in reversed(lines_to_remove):
        if idx < len(lines):
            del lines[idx]
            # 如果下一行是空行，也删除
            if idx < len(lines) and not lines[idx].strip():
                del lines[idx]
    
    # 2. 删除末尾堆积的无说明图片
    # 找到文章正文的结束位置（推广内容之前）
    content_end = len(lines)
    for idx in range(len(lines) - 1, max(0, len(lines) - 30), -1):
        line = lines[idx].strip()
        if any(keyword in line for keyword in ['感谢关注', '近期', '推荐', 'mp.weixin.qq.com', '往期精彩', '猜你喜欢', '* * *', '延伸阅读']):
            content_end = idx
            break
    
    # 检查末尾是否有大量无说明的图片
    end_images = []
    for idx in range(content_end - 1, max(0, content_end - 30), -1):
        if re.match(r'^!\[.*\]\(https?://mmbiz', lines[idx]):
            # 检查前后3行是否有图片说明
            has_caption = False
            for check_idx in range(max(0, idx - 3), min(len(lines), idx + 4)):
                if check_idx != idx:
                    check_line = lines[check_idx].strip()
                    # 检查是否是图片说明
                    if re.match(r'^[（(].*[）)]$', check_line):
                        if any(kw in check_line for kw in ['摄', '照', 'photo', 'image', '©', '来源', 'via', '大东山谷', '孟祥志', '村子', '星轨', '大东峪', '宁国', '皖南']):
                            has_caption = True
                            break
            if not has_caption:
                end_images.append(idx)
        elif end_images and lines[idx].strip() and not re.match(r'^[（(].*[）)]$', lines[idx].strip()):
            # 遇到非图片、非说明的行，停止
            break
    
    # 如果末尾有3个以上无说明的图片，删除它们
    if len(end_images) >= 3:
        end_images.sort(reverse=True)
        for idx in end_images:
            # 删除图片和后面的空行
            if idx < len(lines) and re.match(r'^!\[.*\]\(https?://mmbiz', lines[idx]):
                del lines[idx]
                if idx < len(lines) and not lines[idx].strip():
                    del lines[idx]
    
    # 3. 删除重复的图片说明行（连续重复的）
    lines_to_remove_captions = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if re.match(r'^[（(].*[）)]$', stripped):
            if any(kw in stripped for kw in ['摄', '照', 'photo', 'image', '©', '来源', 'via', '大东山谷', '孟祥志', '村子', '星轨', '大东峪', '宁国', '皖南']):
                # 检查后面是否有相同的图片说明
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and lines[j].strip() == stripped:
                    # 找到重复的，标记删除（保留第一个，删除后续的）
                    while j < len(lines):
                        next_stripped = lines[j].strip()
                        if next_stripped == stripped:
                            lines_to_remove_captions.append(j)
                            j += 1
                            # 跳过空行
                            while j < len(lines) and not lines[j].strip():
                                j += 1
                        else:
                            break
        i += 1
    
    # 从后往前删除重复的图片说明
    for idx in reversed(sorted(set(lines_to_remove_captions))):
        if idx < len(lines):
            del lines[idx]
            # 如果前后都是空行，删除一个空行
            if idx < len(lines) and not lines[idx].strip():
                if idx > 0 and not lines[idx-1].strip():
                    del lines[idx]
    
    return '\n'.join(lines)


def restore_paragraphs_from_original(imported_md, original_md):
    """从原始文件中恢复段落格式"""
    # 提取原始文件的主体内容（去掉front-matter和推广内容）
    original_lines = original_md.split('\n')
    original_content_start = 0
    for i, line in enumerate(original_lines):
        if line.strip() == '---' and i > 0:
            original_content_start = i + 1
            break
    
    # 提取导入文件的主体内容
    imported_lines = imported_md.split('\n')
    imported_content_start = 0
    for i, line in enumerate(imported_lines):
        if line.strip() == '---' and i > 0:
            imported_content_start = i + 1
            break
    
    # 获取front-matter
    front_matter = '\n'.join(imported_lines[:imported_content_start])
    
    # 获取原始内容的段落结构（按空行分割）
    original_content = '\n'.join(original_lines[original_content_start:])
    original_paragraphs = []
    current_para = []
    
    for line in original_content.split('\n'):
        stripped = line.strip()
        # 跳过推广内容
        if any(keyword in stripped for keyword in ['感谢关注', '近期', '推荐', 'mp.weixin.qq.com', '往期精彩', '猜你喜欢']):
            break
        
        if not stripped:
            if current_para:
                original_paragraphs.append('\n'.join(current_para))
                current_para = []
        else:
            current_para.append(line)
    
    if current_para:
        original_paragraphs.append('\n'.join(current_para))
    
    # 检查原始文件的段落格式：如果大部分段落都是单行+空行，则采用这种格式
    single_line_paragraphs = 0
    multi_line_paragraphs = 0
    for para in original_paragraphs:
        para_lines = [l.strip() for l in para.split('\n') if l.strip()]
        if len(para_lines) == 1:
            single_line_paragraphs += 1
        else:
            multi_line_paragraphs += 1
    
    use_single_line_format = single_line_paragraphs > multi_line_paragraphs * 2
    
    # 处理导入的内容，尝试匹配原始段落结构
    imported_content = '\n'.join(imported_lines[imported_content_start:])
    result_lines = imported_lines[:imported_content_start]
    new_content_lines = []
    
    # 将导入内容按行分割
    content_lines = imported_content.split('\n')
    
    # 如果原始文件每行之间都有空行，尝试恢复这种格式
    # 检查原始文件的段落格式：如果大部分段落都是单行+空行，则采用这种格式
    single_line_paragraphs = 0
    multi_line_paragraphs = 0
    for para in original_paragraphs:
        para_lines = [l.strip() for l in para.split('\n') if l.strip()]
        if len(para_lines) == 1:
            single_line_paragraphs += 1
        else:
            multi_line_paragraphs += 1
    
    use_single_line_format = single_line_paragraphs > multi_line_paragraphs * 2
    
    i = 0
    while i < len(content_lines):
        line = content_lines[i]
        stripped = line.strip()
        
        # 跳过推广内容
        if any(keyword in stripped for keyword in ['感谢关注', '近期', '推荐', 'mp.weixin.qq.com', '往期精彩', '猜你喜欢', '* * *']):
            break
        
        # 如果是图片或图片说明，直接添加
        if re.match(r'^!\[.*\]\(https?://', line) or re.match(r'^[（(].*[）)]$', stripped):
            new_content_lines.append(line)
            # 如果使用单行格式，在图片说明后添加空行
            if use_single_line_format and re.match(r'^[（(].*[）)]$', stripped):
                new_content_lines.append('')
            i += 1
            continue
        
        # 如果是超长行（超过200字符且不是图片），尝试匹配原始段落
        if len(line) > 200 and not line.strip().startswith('!'):
            matched = False
            for orig_para in original_paragraphs:
                # 检查原始段落的前50个字符是否在当前行中
                orig_start = orig_para.strip()[:50]
                if orig_start and orig_start in line:
                    # 找到匹配，使用原始段落的格式
                    para_lines = orig_para.split('\n')
                    new_content_lines.extend(para_lines)
                    new_content_lines.append('')  # 添加空行分隔
                    matched = True
                    break
            
            if not matched:
                # 如果没有匹配，尝试智能分段
                segments = re.split(r'([。！？])\s*', line)
                if len(segments) > 3:
                    current_seg = ''
                    for j in range(0, len(segments), 2):
                        if j < len(segments):
                            current_seg += segments[j]
                            if j + 1 < len(segments):
                                current_seg += segments[j + 1]
                            
                            if len(current_seg) > 150:
                                new_content_lines.append(current_seg.strip())
                                if use_single_line_format:
                                    new_content_lines.append('')
                                current_seg = ''
                    
                    if current_seg.strip():
                        new_content_lines.append(current_seg.strip())
                        if use_single_line_format:
                            new_content_lines.append('')
                else:
                    new_content_lines.append(line)
                    if use_single_line_format:
                        new_content_lines.append('')
        else:
            # 普通行，直接添加
            new_content_lines.append(line)
            # 如果使用单行格式，且当前行以句号、问号、感叹号结尾，添加空行
            if use_single_line_format and stripped and stripped[-1] in ['。', '！', '？', '.', '!', '?']:
                if i + 1 < len(content_lines):
                    next_line = content_lines[i + 1].strip()
                    if next_line and not re.match(r'^!\[.*\]\(https?://', content_lines[i + 1]):
                        new_content_lines.append('')
            # 即使不使用单行格式，如果当前行以句号、问号、感叹号结尾，且下一行不是空行，也添加空行
            elif not use_single_line_format and stripped and stripped[-1] in ['。', '！', '？', '.', '!', '?']:
                if i + 1 < len(content_lines):
                    next_line = content_lines[i + 1].strip()
                    if (next_line and 
                        not re.match(r'^!\[.*\]\(https?://', content_lines[i + 1]) and
                        not re.match(r'^[（(].*[）)]$', next_line) and
                        not next_line.startswith('*') and
                        not next_line.startswith('#')):
                        # 检查下一行是否以常见段落开头词开头
                        if len(next_line) > 0 and next_line[0] in ['我', '这', '那', '他', '她', '它', '你', '您', '我们', '他们', '它们', '你们', '抖音', '一个', '比如', '经过', '在', '**']:
                            new_content_lines.append('')
            # 如果当前行不是以句号结尾，但下一行以常见段落开头词开头，也添加空行
            elif stripped and i + 1 < len(content_lines):
                next_line = content_lines[i + 1].strip()
                if (next_line and 
                    not re.match(r'^!\[.*\]\(https?://', content_lines[i + 1]) and
                    not re.match(r'^[（(].*[）)]$', next_line) and
                    not next_line.startswith('*') and
                    not next_line.startswith('#') and
                    len(next_line) > 0):
                    # 检查下一行是否以常见段落开头词开头
                    if next_line[0] in ['我', '这', '那', '他', '她', '它', '你', '您', '我们', '他们', '它们', '你们', '抖音', '一个', '比如', '经过', '在', '**', '**', '**']:
                        # 检查当前行是否以句号、问号、感叹号结尾
                        if stripped[-1] in ['。', '！', '？', '.', '!', '?']:
                            new_content_lines.append('')
        
        i += 1
    
    result_lines.extend(new_content_lines)
    return '\n'.join(result_lines)


def process_article(post_file, articles_list):
    """处理单篇文章"""
    print(f"\n处理: {post_file.name}")
    
    # 读取文章
    md_content = post_file.read_text(encoding='utf-8')
    
    # 提取标题
    title_match = re.search(r'^title:\s*(.+)$', md_content, re.MULTILINE)
    if not title_match:
        print(f"  无法提取标题")
        return False
    
    title = title_match.group(1).strip()
    title_normalized = re.sub(r'[|_\-：:，,。.\s]', '', title)
    
    # 查找原始WeChatSync文件
    original_md = None
    original_file = None
    for md_file in Path(WECHATSYNC_MD_DIR).glob("*.md"):
        if md_file.stem.endswith('-1'):
            continue
        file_stem_normalized = re.sub(r'[|_\-：:，,。.\s]', '', md_file.stem)
        if (title_normalized in file_stem_normalized or 
            file_stem_normalized in title_normalized or
            title in md_file.stem or
            md_file.stem in title):
            try:
                original_md = md_file.read_text(encoding='utf-8')
                original_file = md_file.name
                break
            except:
                pass
    
    if not original_md:
        print(f"  未找到原始WeChatSync文件")
        return False
    
    print(f"  找到原始文件: {original_file}")
    
    # 从原始文件提取图片说明
    captions = extract_captions_from_original(original_md)
    print(f"  找到 {len(captions)} 个图片说明")
    
    if not captions:
        print(f"  没有图片说明，跳过")
        return False
    
    # 从文章列表获取URL
    article_url = None
    for item in articles_list:
        item_title = item.get('title', '')
        if not item_title:
            continue
        item_title_normalized = re.sub(r'[|_\-：:，,。.\s]', '', item_title)
        # 更宽松的匹配
        if (title_normalized == item_title_normalized or 
            title_normalized in item_title_normalized or 
            item_title_normalized in title_normalized or
            title in item_title or 
            item_title in title):
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
    
    # 从HTML提取图片
    images = extract_images_from_html(html, article_url)
    print(f"  从HTML找到 {len(images)} 张图片（已过滤小图片）")
    
    if not images:
        print(f"  未找到图片，跳过")
        return False
    
    if len(images) < len(captions):
        print(f"  警告: 图片数量({len(images)})少于图片说明数量({len(captions)})")
    
    # 插入图片到正确位置
    new_content = insert_images_correctly(md_content, images, captions)
    
    # 从原始文件恢复段落格式（确保段落分隔正确）
    new_content = restore_paragraphs_from_original(new_content, original_md)
    
    # 再次应用段落分隔恢复（确保所有文章都有段落分隔）
    new_content = restore_paragraph_breaks(new_content)
    
    # 保存
    post_file.write_text(new_content, encoding='utf-8')
    print(f"  [OK] 已修复，插入了 {min(len(images), len(captions))} 张图片")
    return True


def main():
    """主函数"""
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
