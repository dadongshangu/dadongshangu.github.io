#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复图片插入位置和格式 - 版本2
- 完全清理所有错误的图片和说明
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


def clean_all_images_and_captions(md_content):
    """清理所有图片链接和图片说明"""
    lines = md_content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # 删除所有图片链接
        if re.match(r'^!\[.*\]\(https?://', line):
            continue
        
        # 删除单独的图片说明行（括号格式）
        if re.match(r'^[（(].*[）)]$', stripped):
            caption_keywords = ['摄', '照', 'photo', 'image', '©', '来源', 'via', '|', '图', '大东山谷', '孟祥志', '村子', '星轨', '大东峪', '宁国', '皖南']
            if any(keyword in stripped for keyword in caption_keywords):
                continue
        
        # 删除行内的图片说明（但保留其他内容）
        if re.search(r'[（(].*[）)]', line):
            # 提取图片说明
            captions = re.findall(r'[（(]([^）)]*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪)[^）)]*)[）)]', line)
            if captions:
                # 删除图片说明，但保留其他文本
                for caption in captions:
                    line = line.replace(f"（{caption}）", "").replace(f"({caption})", "")
                # 如果删除后行为空，跳过
                if not line.strip():
                    continue
        
        # 删除错误的URL片段
        if 'wUPwDW5mooD9KmSpnzXp0WYF1Lia3e0UCAvZ95bWn2ONRSo9sa11ElibsT3vc7ekTb9TWVg' in line:
            continue
        
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def extract_captions_from_original(original_md):
    """从原始文件中提取图片说明及其完整上下文"""
    lines = original_md.split('\n')
    captions = []
    
    for i, line in enumerate(lines):
        # 查找行内的图片说明
        matches = list(re.finditer(r'[（(]([^）)]*(?:摄|照|photo|image|©|来源|via|大东山谷|孟祥志|村子|星轨|大东峪|宁国|皖南|推荐)[^）)]*)[）)]', line))
        
        for match in matches:
            caption_text = match.group(0)
            start_pos = match.start()
            end_pos = match.end()
            
            # 提取说明前后的文本
            before_text = line[:start_pos].strip()
            after_text = line[end_pos:].strip()
            
            # 获取前后行的上下文
            context_lines = []
            for j in range(max(0, i-2), i):
                if lines[j].strip():
                    context_lines.append(lines[j].strip())
            context_lines.append(before_text)  # 当前行说明前的文本
            if after_text:
                context_lines.append(after_text)  # 当前行说明后的文本
            for j in range(i+1, min(len(lines), i+3)):
                if lines[j].strip():
                    context_lines.append(lines[j].strip())
            
            captions.append({
                'text': caption_text,
                'before_text': before_text,
                'after_text': after_text,
                'context': context_lines,
                'line_index': i
            })
    
    return captions


def find_insert_position(caption, imported_lines):
    """在导入后的文章中找到插入位置"""
    before_text = caption['before_text']
    after_text = caption['after_text']
    context = caption['context']
    
    best_match = None
    best_score = 0
    
    for i in range(len(imported_lines)):
        score = 0
        line = imported_lines[i].strip()
        
        # 方法1: 检查before_text是否在当前行或前一行
        if before_text and len(before_text) > 5:
            if before_text[:30] in line:
                score += 10
            elif i > 0 and before_text[:30] in imported_lines[i-1]:
                score += 8
        
        # 方法2: 检查after_text是否在当前行或后一行
        if after_text and len(after_text) > 5:
            if after_text[:30] in line:
                score += 10
            elif i < len(imported_lines)-1 and after_text[:30] in imported_lines[i+1]:
                score += 8
        
        # 方法3: 检查上下文匹配
        for ctx_line in context:
            if ctx_line and len(ctx_line) > 10:
                # 检查前后5行内是否有匹配
                for j in range(max(0, i-5), min(len(imported_lines), i+6)):
                    if ctx_line[:40] in imported_lines[j]:
                        score += 2
                        break
        
        if score > best_score:
            best_score = score
            best_match = i
    
    # 需要较高的分数才认为匹配成功
    if best_match is not None and best_score >= 8:
        return best_match
    
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
                'image': images[i]
            })
    
    # 按位置从后往前排序
    insertions.sort(key=lambda x: x['position'], reverse=True)
    
    # 插入图片
    for item in insertions:
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
                print(f"  找到原始文件: {md_file.name}")
                break
            except:
                pass
    
    if not original_md:
        print(f"  未找到原始文件")
        return False
    
    # 从原始文件中提取图片说明
    captions = extract_captions_from_original(original_md)
    print(f"  找到 {len(captions)} 个图片说明")
    
    if not captions:
        return False
    
    # 从当前文章中提取图片URL（从HTML中获取的）
    # 我们需要重新获取，或者从之前的运行结果中提取
    # 这里我们假设图片URL已经在文章中了（即使格式错误）
    image_urls = re.findall(r'https?://mmbiz\.qpic\.cn/[^\s\)]+', md_content)
    if not image_urls:
        print(f"  未找到图片URL，需要重新获取")
        return False
    
    # 去重并排序
    image_urls = list(dict.fromkeys(image_urls))  # 保持顺序的去重
    images = [{'url': url} for url in image_urls[:len(captions)]]  # 只取前N个
    
    print(f"  找到 {len(images)} 张图片")
    
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
