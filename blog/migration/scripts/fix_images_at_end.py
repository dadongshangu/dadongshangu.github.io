#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复图片堆在末尾的问题
- 检查所有文章，找出图片堆在末尾的文章
- 根据原始文件中的图片说明，将图片插入到正确位置
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
    """加载文章列表"""
    if not os.path.exists(ARTICLES_LIST_FILE):
        return []
    with open(ARTICLES_LIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_captions_with_context(original_md):
    """从原始文件中提取图片说明及其上下文"""
    lines = original_md.split('\n')
    captions = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        matches = []
        
        # 方法1: 查找行内的括号图片说明（标准格式）
        matches = list(re.finditer(r'[（(]([^）)]*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐)[^）)]*)[）)]', line))
        
        # 方法2: 如果没找到，尝试匹配斜体格式的图片说明（如 _（图片说明）_）
        if not matches:
            # 检查是否是斜体格式且包含图片说明关键词
            if re.search(r'_(.*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐).*)_', stripped):
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
                if re.search(r'(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐)', stripped):
                    class MatchObj:
                        def __init__(self, text):
                            self.text = text
                            self.start = lambda: 0
                            self.end = lambda: len(text)
                            self.group = lambda n=0: text
                    matches = [MatchObj(stripped)]
        
        # 方法4: 查找斜体格式的图片说明（如 _（小时候带你散步，你经常会睡着）_ 或 _（爷爷院子里的石榴树，现在已经很高了）_）
        if not matches:
            # 匹配 _（...）_ 或 _（...）_ __ 格式（使用中文括号或英文括号）
            # 先尝试匹配完整的斜体格式（包括后面的 __）
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


def find_insert_position(caption, imported_lines):
    """在导入后的文章中找到插入位置"""
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
    
    # 方法4: 通过prev_line和next_line的组合匹配
    if prev_line and next_line:
        for i in range(len(imported_lines) - 1):
            line1 = imported_lines[i].strip()
            line2 = imported_lines[i+1].strip() if i+1 < len(imported_lines) else ""
            if prev_line[:20] in line1 and next_line[:20] in line2:
                return i + 1
    
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
                return None
            return response.text
    except Exception as e:
        print(f"    [ERROR] 获取文章失败: {e}")
    return None


def extract_images_from_html(html_content, article_url):
    """从HTML中提取所有图片URL"""
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
        
        skip_keywords = ['avatar', 'qrcode', 'logo', 'icon']
        if any(skip in src.lower() for skip in skip_keywords):
            continue
        
        if 'wx_fmt=gif' in src.lower() and 'mmbiz' not in src.lower():
            continue
        
        is_valid = False
        if 'mmbiz' in src.lower():
            if 'wx_fmt=gif' in src.lower():
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
        
        alt = img.get('alt') or img.get('title') or ''
        
        images.append({
            'url': src,
            'alt': alt,
            'index': len(images)
        })
    
    return images


def clean_all_images_and_captions(md_content):
    """完全清理所有图片链接和图片说明"""
    lines = md_content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # 删除所有图片链接
        if re.match(r'^!\[.*\]\(https?://', line):
            continue
        
        # 删除单独的图片说明行
        if re.match(r'^[（(].*[）)]$', stripped):
            caption_keywords = ['摄', '照', 'photo', 'image', '©', '来源', 'via', '|', '图', '大东山谷', '孟祥志', '村子', '星轨', '大东峪', '宁国', '皖南']
            if any(keyword in stripped for keyword in caption_keywords):
                continue
        
        # 删除行内的图片说明（但保留其他文本）
        if re.search(r'[（(].*[）)]', line):
            line = re.sub(r'[（(][^）)]*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南)[^）)]*[）)]', '', line)
            if not line.strip():
                continue
        
        # 删除错误的URL片段
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
    
    # 清理多余空行
    result = []
    prev_empty = False
    for line in cleaned_lines:
        is_empty = not line.strip()
        if is_empty:
            if not prev_empty:
                result.append("")
            prev_empty = True
        else:
            result.append(line)
            prev_empty = False
    
    return '\n'.join(result)


def process_article(post_file):
    """处理单篇文章"""
    print(f"\n处理: {post_file.name}")
    
    # 读取文章
    md_content = post_file.read_text(encoding='utf-8')
    
    # 检查是否有图片堆在末尾（连续多张图片在文章末尾）
    lines = md_content.split('\n')
    image_count_at_end = 0
    end_image_start = len(lines)
    
    # 从末尾向前查找连续的图片
    for i in range(len(lines) - 1, -1, -1):
        if re.match(r'^!\[.*\]\(https?://mmbiz', lines[i]):
            image_count_at_end += 1
            end_image_start = i
        elif image_count_at_end > 0 and lines[i].strip():
            # 遇到非图片内容，停止计数
            # 但如果是推广内容，继续计数
            if any(keyword in lines[i] for keyword in ['感谢关注', '近期', '推荐', 'mp.weixin.qq.com', '往期精彩', '猜你喜欢', '* * *']):
                continue
            break
    
    # 检查是否有图片说明但没有对应的图片
    caption_count = len(re.findall(r' _\([^）)]+\)_', md_content))
    existing_image_count = len(re.findall(r'!\[.*\]\(https?://mmbiz', md_content))
    
    # 如果末尾有超过2张图片，或者有图片说明但没有对应的图片，认为需要修复
    needs_fix = False
    if image_count_at_end >= 2:
        needs_fix = True
        print(f"  发现 {image_count_at_end} 张图片堆在末尾，需要修复")
    elif caption_count > existing_image_count:
        needs_fix = True
        print(f"  发现 {caption_count} 个图片说明但只有 {existing_image_count} 张图片，需要修复")
    
    if not needs_fix:
        print(f"  图片位置正常（末尾只有 {image_count_at_end} 张图片，图片说明和图片数量匹配）")
        return False
    
    # 读取标题
    title_match = re.search(r'^title:\s*(.+)$', md_content, re.MULTILINE)
    if not title_match:
        return False
    
    title = title_match.group(1).strip()
    
    # 加载原始文件
    title_normalized = re.sub(r'[|_\-：:，,。.\s]', '', title)
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
        print(f"  未找到原始文件")
        return False
    
    print(f"  找到原始文件: {original_file}")
    
    # 从原始文件中提取图片说明
    captions = extract_captions_with_context(original_md)
    print(f"  找到 {len(captions)} 个图片说明")
    
    if not captions:
        print(f"  未找到图片说明，无法修复")
        return False
    
    # 从当前文章中提取所有图片URL（包括末尾堆放的）
    image_urls = re.findall(r'https?://mmbiz\.qpic\.cn/[^\s\)]+', md_content)
    
    # 如果文章中没有图片URL，尝试从HTML获取
    if not image_urls:
        print(f"  未找到图片URL，尝试从HTML获取")
        articles_list = load_articles_list()
        article_url = None
        for item in articles_list:
            if item.get('title') and re.sub(r'[|_\-：:，,。.\s]', '', item['title']) == title_normalized:
                article_url = item['url']
                break
        
        if article_url:
            print(f"  获取文章HTML: {article_url}")
            html = fetch_article_html(article_url)
            if html:
                images = extract_images_from_html(html, article_url)
                print(f"  从HTML找到 {len(images)} 张图片")
            else:
                print(f"  [ERROR] 无法获取文章HTML")
                return False
        else:
            print(f"  [ERROR] 未找到文章URL")
            return False
    else:
        # 去重并保持顺序
        seen = set()
        unique_urls = []
        for url in image_urls:
            url_clean = url.rstrip('.,;!?）)')
            if url_clean not in seen:
                seen.add(url_clean)
                unique_urls.append(url_clean)
        
        images = [{'url': url} for url in unique_urls[:len(captions)]]
        print(f"  找到 {len(images)} 张图片（共 {len(unique_urls)} 张）")
    
    # 清理所有图片和说明
    cleaned_md = clean_all_images_and_captions(md_content)
    lines = cleaned_md.split('\n')
    
    # 为每个图片说明找到插入位置
    insertions = []
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
    
    # 按位置从后往前排序
    insertions.sort(key=lambda x: x['position'], reverse=True)
    
    # 插入图片
    for item in insertions:
        pos = item['position']
        caption = item['caption']
        img = item['image']
        
        # 提取图片说明文本（保留原始格式）
        caption_text = caption['text']
        if not (caption_text.startswith('(') or caption_text.startswith('（')):
            bracket_match = re.search(r'[（(]([^）)]*)[）)]', caption_text)
            if bracket_match:
                caption_text = bracket_match.group(0)
        
        alt_text = caption_text.strip('（）()')
        img_url = img['url']
        
        # 检查该位置是否已经有图片（避免重复插入）
        if pos < len(lines) and re.match(r'^!\[.*\]\(https?://', lines[pos]):
            continue
        
        # 在指定位置插入图片和说明
        lines.insert(pos, f"![{alt_text}]({img_url})")
        lines.insert(pos + 1, "")
        lines.insert(pos + 2, caption_text)
    
    # 保存
    post_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"  [OK] 已修复，插入了 {len(insertions)} 张图片到正确位置")
    
    return True


def main():
    processed = 0
    skipped = 0
    
    for post_file in Path(POSTS_DIR).glob("*.md"):
        try:
            if process_article(post_file):
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
