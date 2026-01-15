#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
恢复缺失的文字内容并修复分段问题
- 从原始数据源恢复缺失的文字内容
- 修复长段落的分段问题
"""

import os
import re
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
DATA_DIR = os.path.join(BASE_DIR, "data")
WECHATSYNC_MD_DIR = os.path.join(DATA_DIR, "wechatsync_md")
BLOG_DIR = os.path.dirname(BASE_DIR)  # blog/
POSTS_DIR = os.path.join(BLOG_DIR, "source", "_posts")


def restore_article_content(post_file):
    """从原始数据源恢复文章内容"""
    # 从文件名提取标题
    filename = post_file.stem
    
    # 查找对应的原始文件
    original_file = None
    for orig_file in Path(WECHATSYNC_MD_DIR).glob("*.md"):
        if filename in orig_file.stem or orig_file.stem in filename:
            original_file = orig_file
            break
    
    if not original_file:
        return None
    
    # 读取原始内容
    original_content = original_file.read_text(encoding='utf-8')
    
    # 提取正文内容（跳过front-matter和推广内容）
    lines = original_content.split('\n')
    content_lines = []
    in_frontmatter = False
    in_promo = False
    
    for line in lines:
        stripped = line.strip()
        
        if stripped == '---':
            in_frontmatter = not in_frontmatter
            continue
        
        if in_frontmatter:
            continue
        
        # 跳过推广内容
        if any(keyword in stripped for keyword in ['近期文章推荐', '点击图片直接打开', '感谢关注', 'mp.weixin.qq.com']):
            in_promo = True
            continue
        
        if in_promo:
            continue
        
        content_lines.append(line)
    
    return '\n'.join(content_lines)


def fix_long_paragraphs(md_content):
    """修复过长的段落，在句号、问号、感叹号后添加分段"""
    lines = md_content.split('\n')
    result = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 跳过空行、front-matter、图片、列表、引用等
        if not stripped:
            result.append("")
            continue
        
        if stripped.startswith('---'):
            result.append(line)
            continue
        
        if stripped.startswith(('title:', 'date:', 'tags:')):
            result.append(line)
            continue
        
        if re.match(r'^!\[.*\]\(https?://', line):
            result.append(line)
            continue
        
        if stripped.startswith(('*', '-', '+', '1.', '2.', '3.', '4.', '5.', '>', '#')):
            result.append(line)
            continue
        
        if re.match(r'^[（(].*[）)]$', stripped):
            result.append(line)
            continue
        
        if '全文完，以下图片待整理' in stripped:
            result.append(line)
            continue
        
        # 检查是否是长段落（超过200字符）
        if len(stripped) > 200:
            # 在句号、问号、感叹号、冒号后添加分段
            # 但不要破坏引号内的内容
            parts = re.split(r'([。！？：])', stripped)
            new_parts = []
            for j, part in enumerate(parts):
                new_parts.append(part)
                if j < len(parts) - 1 and part in ['。', '！', '？', '：']:
                    # 检查下一个部分是否以引号开头
                    if j + 1 < len(parts):
                        next_part = parts[j + 1].strip()
                        if not next_part.startswith(('"', "'", '"', '')):
                            # 添加分段标记
                            new_parts.append('\n\n')
            
            new_line = ''.join(new_parts)
            # 分割成多行
            for part in new_line.split('\n\n'):
                if part.strip():
                    result.append(part.strip())
                else:
                    result.append("")
        else:
            result.append(line)
    
    return '\n'.join(result)


def process_article(post_file):
    """处理单篇文章"""
    print(f"\n处理: {post_file.name}")
    
    md_content = post_file.read_text(encoding='utf-8')
    
    # 检查是否有文字内容
    text_content = re.sub(r'!\[.*\]\(https?://[^\)]+\)', '', md_content)
    text_content = re.sub(r'^[（(].*[）)]$', '', text_content, flags=re.MULTILINE)
    text_content = re.sub(r'全文完，以下图片待整理', '', text_content)
    text_content = re.sub(r'---.*?---', '', text_content, flags=re.DOTALL)
    text_content = re.sub(r'\s+', ' ', text_content)
    
    if len(text_content.strip()) < 50:
        # 缺少文字内容，尝试恢复
        print(f"  [WARN] 文章缺少文字内容，尝试从原始数据源恢复...")
        restored_content = restore_article_content(post_file)
        
        if restored_content:
            # 合并front-matter和恢复的内容
            frontmatter_match = re.search(r'(---.*?---)', md_content, re.DOTALL)
            if frontmatter_match:
                frontmatter = frontmatter_match.group(1)
                # 提取现有图片
                images = re.findall(r'!\[.*?\]\(https?://[^\)]+\)', md_content)
                # 构建新内容
                new_content = frontmatter + '\n\n' + restored_content
                # 在末尾添加图片
                if images:
                    new_content += '\n\n全文完，以下图片待整理\n'
                    for img in images:
                        new_content += '\n' + img + '\n'
                
                post_file.write_text(new_content, encoding='utf-8')
                print(f"  [OK] 已恢复文字内容")
                return True
            else:
                print(f"  [ERROR] 无法提取front-matter")
        else:
            print(f"  [ERROR] 无法找到原始数据源")
    
    # 修复长段落
    new_content = fix_long_paragraphs(md_content)
    if new_content != md_content:
        post_file.write_text(new_content, encoding='utf-8')
        print(f"  [OK] 已修复分段问题")
        return True
    
    print(f"  无需修复")
    return False


def main():
    """主函数"""
    fixed = 0
    processed = 0
    
    for post_file in Path(POSTS_DIR).glob("*.md"):
        try:
            if process_article(post_file):
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
