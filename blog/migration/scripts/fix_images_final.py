#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终版本的图片修复脚本
- 完全清理所有错误的图片和说明
- 根据原始文件中的图片说明位置，在导入后的文章中精确匹配
- 插入图片和说明到正确位置
"""

import os
import re
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
DATA_DIR = os.path.join(BASE_DIR, "data")
ARTICLES_LIST_FILE = os.path.join(DATA_DIR, "articles_list.json")
BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")
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
            # 提取并删除图片说明
            line = re.sub(r'[（(][^）)]*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南)[^）)]*[）)]', '', line)
            # 如果删除后行为空，跳过
            if not line.strip():
                continue
        
        # 删除错误的URL片段和格式错误的行
        if 'wUPwDW5mooD9KmSpnzXp0WYF1Lia3e0UCAvZ95bWn2ONRSo9sa11ElibsT3vc7ekTb9TWVg' in line:
            continue
        if re.search(r'\]\(https?://[^\)]*\)[^\)]*\)', line):  # 错误的格式
            continue
        # 删除只包含")"或"）"的行
        if stripped in [')', '）']:
            continue
        # 删除以")"或"）"开头的行（通常是格式错误）
        if stripped.startswith(')') or stripped.startswith('）'):
            # 如果整行只有这个字符，删除；否则保留后面的内容
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


def extract_captions_with_context(original_md):
    """从原始文件中提取图片说明及其上下文"""
    lines = original_md.split('\n')
    captions = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        matches = []
        
        # 方法1: 查找行内的括号图片说明（标准格式）
        matches = list(re.finditer(r'[（(]([^）)]*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐)[^）)]*)[）)]', line))
        
        # 方法2: 如果没找到，尝试匹配斜体格式的图片说明（如 _(图片摄于2012年）_）
        if not matches:
            # 检查是否是斜体格式且包含图片说明关键词
            if re.search(r'_(.*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐).*)_', stripped):
                # 提取括号内的内容
                bracket_match = re.search(r'[（(]([^）)]*)[）)]', stripped)
                if bracket_match:
                    # 创建一个匹配对象
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
            # 单独一行，只包含括号和关键词
            if re.match(r'^[（(].*[）)]$', stripped):
                if re.search(r'(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐)', stripped):
                    class MatchObj:
                        def __init__(self, text):
                            self.text = text
                            self.start = lambda: 0
                            self.end = lambda: len(text)
                            self.group = lambda n=0: text
                    matches = [MatchObj(stripped)]
        
        for match in matches:
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


def find_insert_position(caption, imported_lines):
    """在导入后的文章中找到插入位置"""
    after_text = caption['after_text']  # 图片说明后的文本
    next_line = caption['next_line']  # 图片说明的下一行（通常更可靠）
    before_text = caption['before_text']
    prev_line = caption.get('prev_line', '')
    
    # 方法1: 如果图片说明是单独一行（after_text为空），优先使用next_line匹配
    if not after_text or len(after_text) < 5:
        if next_line and len(next_line) > 5:
            # 清理next_line，移除可能的标点符号和空白
            next_clean = re.sub(r'^[，,。.\s]+', '', next_line)
            next_clean = next_clean.strip()
            
            # 尝试多种匹配策略
            # 策略1: 精确匹配前30个字符
            search_text = next_clean[:30] if len(next_clean) > 30 else next_clean
            for i, line in enumerate(imported_lines):
                line_clean = line.strip()
                # 检查是否在当前行开头（最精确）
                if line_clean.startswith(search_text):
                    return i
                # 或者在当前行中
                if search_text in line_clean:
                    return i
            
            # 策略2: 如果精确匹配失败，尝试匹配前15个字符（更宽松）
            if len(next_clean) > 15:
                search_text_short = next_clean[:15]
                for i, line in enumerate(imported_lines):
                    line_clean = line.strip()
                    if line_clean.startswith(search_text_short):
                        return i
                    if search_text_short in line_clean:
                        return i
    
    # 方法2: 通过after_text精确匹配（如果图片说明在同一行）
    if after_text and len(after_text) > 5:
        # 清理after_text，移除可能的标点符号和空白
        after_clean = re.sub(r'^[，,。.\s]+', '', after_text)
        after_clean = after_clean.strip()
        
        # 尝试匹配前30个字符
        search_text = after_clean[:30] if len(after_clean) > 30 else after_clean
        
        for i, line in enumerate(imported_lines):
            line_clean = line.strip()
            # 检查after_text是否在当前行开头（最精确）
            if line_clean.startswith(search_text):
                return i
            # 或者after_text在当前行中
            if search_text in line_clean:
                return i
    
    # 方法3: 通过next_line模糊匹配（作为备选，使用更短的匹配文本）
    if next_line and len(next_line) > 10:
        # 尝试匹配前20个字符
        next_clean = next_line.strip()[:20]
        for i, line in enumerate(imported_lines):
            if next_clean in line:
                return i
    
    # 方法4: 通过prev_line和next_line的组合匹配
    if prev_line and next_line:
        # 查找prev_line后面的next_line
        for i in range(len(imported_lines) - 1):
            line1 = imported_lines[i].strip()
            line2 = imported_lines[i+1].strip() if i+1 < len(imported_lines) else ""
            # 如果prev_line在当前行，next_line在下一行
            if prev_line[:20] in line1 and next_line[:20] in line2:
                return i + 1  # 返回next_line的位置
    
    # 方法5: 通过before_text匹配（如果after_text和next_line都没找到）
    if before_text and len(before_text) > 10:
        before_clean = before_text.strip()[:30]
        for i, line in enumerate(imported_lines):
            if before_clean in line:
                # 返回当前行的下一行，图片说明应该在这行之后
                return i + 1 if i + 1 < len(imported_lines) else i
    
    return None


def insert_images_correctly(imported_md, images, captions):
    """将图片正确插入到文章中"""
    # 先完全清理
    cleaned_md = clean_all_images_and_captions(imported_md)
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
        # 如果图片说明是括号格式，确保保留括号
        if not (caption_text.startswith('(') or caption_text.startswith('（')):
            # 如果不是括号格式，尝试从原始文本中提取
            if '(' in caption_text or '（' in caption_text:
                # 提取括号内的内容
                bracket_match = re.search(r'[（(]([^）)]*)[）)]', caption_text)
                if bracket_match:
                    caption_text = bracket_match.group(0)  # 包含括号
        
        alt_text = caption_text.strip('（）()')
        img_url = img['url']
        
        # 检查该位置是否已经有图片（避免重复插入）
        if pos < len(lines) and re.match(r'^!\[.*\]\(https?://', lines[pos]):
            print(f"    跳过: 位置 {pos} 已有图片")
            continue
        
        # 在指定位置插入图片和说明
        lines.insert(pos, f"![{alt_text}]({img_url})")
        lines.insert(pos + 1, "")
        lines.insert(pos + 2, caption_text)
    
    return '\n'.join(lines)


def process_article(post_file):
    """处理单篇文章"""
    print(f"\n处理: {post_file.name}")
    
    # 读取文章
    md_content = post_file.read_text(encoding='utf-8')
    
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
    
    # 即使没有图片说明，也尝试从HTML获取图片（可能原始文件中没有图片说明但文章中有图片）
    if not captions:
        print(f"  未找到图片说明，但尝试从HTML获取图片")
        # 从文章列表中获取URL
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
                if images:
                    print(f"  从HTML找到 {len(images)} 张图片，插入到文章末尾")
                    # 在文章末尾（推广内容之前）插入图片
                    lines = md_content.split('\n')
                    insert_pos = len(lines)
                    # 查找推广内容的位置
                    for i in range(len(lines) - 1, max(0, len(lines) - 20), -1):
                        if any(keyword in lines[i] for keyword in ['感谢关注', '近期', '推荐', 'mp.weixin.qq.com']):
                            insert_pos = i
                            break
                    
                    # 插入图片
                    for img in images:
                        img_url = img['url']
                        alt_text = img.get('alt') or '图片'
                        lines.insert(insert_pos, f"![{alt_text}]({img_url})")
                        lines.insert(insert_pos + 1, "")
                        insert_pos += 2
                    
                    post_file.write_text('\n'.join(lines), encoding='utf-8')
                    print(f"  [OK] 已插入 {len(images)} 张图片")
                    return True
        
        return False
    
    # 从当前文章中提取图片URL
    image_urls = re.findall(r'https?://mmbiz\.qpic\.cn/[^\s\)]+', md_content)
    
    # 如果文章中没有图片URL，尝试从HTML获取
    if not image_urls:
        print(f"  未找到图片URL，尝试从HTML获取")
        # 从文章列表中获取URL
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
            # 清理URL，移除可能的尾随字符
            url_clean = url.rstrip('.,;!?）)')
            if url_clean not in seen:
                seen.add(url_clean)
                unique_urls.append(url_clean)
        
        images = [{'url': url} for url in unique_urls[:len(captions)]]
        print(f"  找到 {len(images)} 张图片（共 {len(unique_urls)} 张）")
    
    if len(images) < len(captions):
        print(f"  警告: 图片数量({len(images)})少于图片说明数量({len(captions)})")
    
    # 重新插入图片到正确位置
    new_content = insert_images_correctly(md_content, images, captions)
    
    # 保存
    post_file.write_text(new_content, encoding='utf-8')
    print(f"  [OK] 已修复，插入了 {min(len(images), len(captions))} 张图片")
    
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
