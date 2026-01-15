#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理文章中的重复内容和分隔符
- 删除重复的段落
- 清理分隔符（dadong*shangu等）
- 清理重复的图片说明
"""

import os
import re
from pathlib import Path
from collections import OrderedDict

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")


def clean_separators(md_content):
    """清理分隔符"""
    # 清理dadong*shangu类型的分隔符
    md_content = re.sub(r'dadong\d*shangu', '', md_content, flags=re.IGNORECASE)
    md_content = re.sub(r'dadong\s*\*\s*shangu', '', md_content, flags=re.IGNORECASE)
    md_content = re.sub(r'dadong\s*shangu', '', md_content, flags=re.IGNORECASE)
    
    return md_content


def remove_duplicate_paragraphs(md_content):
    """删除重复的段落"""
    lines = md_content.split('\n')
    result = []
    seen_paragraphs = OrderedDict()  # 使用OrderedDict保持顺序
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # 跳过空行（保留第一个空行）
        if not stripped:
            result.append("")
            i += 1
            continue
        
        # 跳过front-matter
        if stripped.startswith('---') or stripped.startswith(('title:', 'date:', 'tags:')):
            result.append(line)
            i += 1
            continue
        
        # 跳过图片、列表、引用等特殊格式
        if (re.match(r'^!\[.*\]\(https?://', line) or
            stripped.startswith(('*', '-', '+', '1.', '2.', '3.', '4.', '5.', '>', '#')) or
            re.match(r'^[（(].*[）)]$', stripped)):
            result.append(line)
            i += 1
            continue
        
        # 收集当前段落（直到下一个空行或特殊标记）
        paragraph_lines = []
        j = i
        while j < len(lines):
            current_line = lines[j]
            current_stripped = current_line.strip()
            
            # 如果遇到空行，停止收集
            if not current_stripped:
                break
            
            # 如果遇到特殊标记，停止收集
            if (re.match(r'^!\[.*\]\(https?://', current_line) or
                current_stripped.startswith(('*', '-', '+', '1.', '2.', '3.', '4.', '5.', '>', '#')) or
                re.match(r'^[（(].*[）)]$', current_stripped)):
                break
            
            paragraph_lines.append(current_line)
            j += 1
        
        # 构建段落文本
        paragraph_text = '\n'.join(paragraph_lines).strip()
        
        # 检查是否是重复段落（长度大于50字符的段落才检查）
        if len(paragraph_text) > 50:
            # 创建段落的唯一标识（去除多余空格和标点）
            paragraph_key = re.sub(r'\s+', ' ', paragraph_text)
            paragraph_key = re.sub(r'[，。！？、；：]', '', paragraph_key)
            
            # 如果这个段落已经出现过，跳过
            if paragraph_key in seen_paragraphs:
                i = j
                continue
            else:
                seen_paragraphs[paragraph_key] = True
        
        # 添加段落
        result.extend(paragraph_lines)
        i = j
    
    return '\n'.join(result)


def clean_duplicate_captions(md_content):
    """清理重复的图片说明"""
    lines = md_content.split('\n')
    result = []
    seen_captions = set()
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # 检查是否是图片说明行
        if re.match(r'^[（(].*[）)]$', stripped):
            caption_keywords = ['摄', '照', 'photo', 'image', '©', '来源', 'via', '|', '图', '大东山谷', '孟祥志', '村子', '星轨', '大东峪', '宁国', '皖南', '推荐', '假设', '价格', '我看的这个版本刚好没有这篇']
            if any(keyword in stripped for keyword in caption_keywords):
                # 检查前一行是否是图片
                if len(result) > 0 and re.match(r'^!\[.*\]\(https?://mmbiz', result[-1]):
                    # 紧跟在图片后面，保留（但只保留一次）
                    if stripped not in seen_captions:
                        result.append(line)
                        seen_captions.add(stripped)
                else:
                    # 不是紧跟在图片后面，检查是否是重复的
                    if stripped not in seen_captions:
                        # 检查后面是否有对应的图片
                        has_image_after = False
                        for j in range(i + 1, min(i + 11, len(lines))):
                            if re.match(r'^!\[.*\]\(https?://mmbiz', lines[j]):
                                has_image_after = True
                                break
                        
                        if has_image_after:
                            # 后面有图片，保留（但只保留一次）
                            result.append(line)
                            seen_captions.add(stripped)
                        # 否则删除
                i += 1
                continue
        
        result.append(line)
        i += 1
    
    return '\n'.join(result)


def fix_article(post_file):
    """修复单篇文章"""
    print(f"处理: {post_file.name}")
    
    md_content = post_file.read_text(encoding='utf-8')
    original_length = len(md_content)
    
    # 清理分隔符
    new_content = clean_separators(md_content)
    
    # 删除重复段落
    new_content = remove_duplicate_paragraphs(new_content)
    
    # 清理重复的图片说明
    new_content = clean_duplicate_captions(new_content)
    
    # 清理多余空行（连续3个以上空行压缩为2个）
    new_content = re.sub(r'\n{3,}', '\n\n', new_content)
    
    new_length = len(new_content)
    
    if new_content != md_content:
        post_file.write_text(new_content, encoding='utf-8')
        print(f"  [OK] 已清理重复内容和分隔符 (从 {original_length} 字符减少到 {new_length} 字符)")
        return True
    
    print(f"  无需修复")
    return False


def main():
    """主函数"""
    fixed = 0
    processed = 0
    
    for post_file in Path(POSTS_DIR).glob("*.md"):
        try:
            if fix_article(post_file):
                fixed += 1
            processed += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n[SUMMARY] processed={processed}, fixed={fixed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
