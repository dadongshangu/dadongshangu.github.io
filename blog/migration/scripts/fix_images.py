#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复图片插入位置和格式
- 清理错误的图片插入
- 根据原始文件重新插入图片到正确位置
"""

import os
import re
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
DATA_DIR = os.path.join(BASE_DIR, "data")
BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")
WECHATSYNC_MD_DIR = os.path.join(DATA_DIR, "wechatsync_md")


def clean_broken_images(md_content):
    """清理格式错误的图片链接"""
    lines = md_content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # 删除格式错误的图片链接（包含不完整的URL或错误的格式）
        if re.search(r'!\[.*\]\(https?://[^\)]*$', line):  # 不完整的链接
            continue
        if re.search(r'wUPwDW5mooD9KmSpnzXp0WYF1Lia3e0UCAvZ95bWn2ONRSo9sa11ElibsT3vc7ekTb9TWVg', line):  # 错误的URL片段
            continue
        if re.search(r'!\[.*\]\(https?://[^\)]*\)[^\)]*\)', line):  # 重复的括号
            continue
        # 保留格式正确的图片链接
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def find_image_captions_in_original(original_md):
    """从原始文件中提取图片说明及其位置信息"""
    lines = original_md.split('\n')
    captions = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 查找行内的图片说明
        matches = re.finditer(r'[（(]([^）)]*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐)[^）)]*)[）)]', line)
        for match in matches:
            caption_text = match.group(0)
            start_pos = match.start()
            end_pos = match.end()
            
            # 获取上下文
            context_before = []
            context_after = []
            for j in range(max(0, i-3), i):
                if lines[j].strip():
                    context_before.append(lines[j].strip()[:50])  # 只取前50个字符
            for j in range(i+1, min(len(lines), i+4)):
                if lines[j].strip():
                    context_after.append(lines[j].strip()[:50])
            
            captions.append({
                'line_index': i,
                'text': caption_text,
                'start_pos': start_pos,
                'end_pos': end_pos,
                'context_before': context_before,
                'context_after': context_after,
                'full_line': line
            })
    
    return captions


def find_matching_position(caption, imported_lines):
    """在导入后的文章中找到匹配的位置"""
    context_before = caption.get('context_before', [])
    context_after = caption.get('context_after', [])
    
    best_match = None
    best_score = 0
    
    for i in range(len(imported_lines)):
        score = 0
        line = imported_lines[i].strip()
        
        # 检查前文匹配
        for ctx in context_before:
            if ctx and len(ctx) > 5:  # 只匹配有意义的上下文
                for j in range(max(0, i-3), i):
                    if ctx in imported_lines[j]:
                        score += 2
                        break
        
        # 检查后文匹配
        for ctx in context_after:
            if ctx and len(ctx) > 5:
                for j in range(i+1, min(len(imported_lines), i+4)):
                    if ctx in imported_lines[j]:
                        score += 2
                        break
        
        # 检查当前行是否包含相关关键词
        caption_keywords = caption['text'].strip('（）()').split('|')
        for keyword in caption_keywords[:2]:  # 只检查前两个关键词
            if keyword and len(keyword) > 2 and keyword in line:
                score += 1
        
        if score > best_score:
            best_score = score
            best_match = i
    
    # 如果找到了较好的匹配（至少2分），返回位置
    if best_match is not None and best_score >= 2:
        return best_match
    
    return None


def insert_images_correctly(imported_md, images, captions):
    """将图片正确插入到文章中"""
    # 先清理所有现有的图片链接
    lines = imported_md.split('\n')
    cleaned_lines = []
    for line in lines:
        if not re.match(r'^!\[.*\]\(https?://', line):
            cleaned_lines.append(line)
    
    lines = cleaned_lines
    
    # 为每个图片说明找到插入位置
    caption_positions = []
    for i, caption in enumerate(captions):
        if i >= len(images):
            break
        
        pos = find_matching_position(caption, lines)
        if pos is not None:
            caption_positions.append({
                'position': pos,
                'caption': caption,
                'image': images[i]
            })
    
    # 按位置从后往前排序
    caption_positions.sort(key=lambda x: x['position'], reverse=True)
    
    # 插入图片
    for item in caption_positions:
        pos = item['position']
        caption = item['caption']
        img = item['image']
        
        alt_text = caption['text'].strip('（）()')
        img_url = img['url']
        
        # 在指定位置插入图片和说明
        lines.insert(pos, f"![{alt_text}]({img_url})")
        lines.insert(pos + 1, "")
        lines.insert(pos + 2, caption['text'])
    
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
                break
            except:
                pass
    
    if not original_md:
        print(f"  未找到原始文件")
        return False
    
    # 从原始文件中提取图片说明
    captions = find_image_captions_in_original(original_md)
    print(f"  找到 {len(captions)} 个图片说明")
    
    if not captions:
        return False
    
    # 从当前文章中提取图片URL
    image_urls = re.findall(r'!\[.*?\]\((https?://[^\)]+)\)', md_content)
    if not image_urls:
        print(f"  未找到图片URL")
        return False
    
    images = [{'url': url} for url in image_urls]
    print(f"  找到 {len(images)} 张图片")
    
    # 清理错误的图片
    cleaned_content = clean_broken_images(md_content)
    
    # 重新插入图片到正确位置
    new_content = insert_images_correctly(cleaned_content, images, captions)
    
    # 保存
    post_file.write_text(new_content, encoding='utf-8')
    print(f"  [OK] 已修复")
    
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
