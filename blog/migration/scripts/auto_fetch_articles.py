#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动化批量抓取微信公众号文章并转换为 Markdown
使用真实的浏览器请求头，绕过基础反爬虫
"""

import os
import json
import re
import time
from pathlib import Path
from datetime import datetime
from html2text import HTML2Text
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blog/migration
DATA_DIR = os.path.join(BASE_DIR, "data")
ARTICLES_LIST_FILE = os.path.join(DATA_DIR, "articles_list.json")
OUTPUT_DIR = os.path.join(DATA_DIR, "wechatsync_md")

# 引流链接识别模式
PROMO_TAIL_PATTERNS = [
    r"感谢关注",
    r"原创推荐[：:]",
    r"关注公众号",
    r"长按.*(识别|关注)",
    r"点击.*(关注|进入)",
    r"微信公众",
    r"mp\.weixin\.qq\.com",
    r"扫码关注",
    r"识别二维码",
    r"点击上方.*关注",
    r"长按.*二维码",
]


def normalize_title(title: str) -> str:
    """规范化标题"""
    title = (title or "").strip()
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r"[""\"'']", "", title)
    title = re.sub(r"^\s*\d+\s*[\.．、]\s*", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def clean_promo_tail(md: str) -> str:
    """清理文章末尾的引流内容"""
    lines = md.split("\n")
    cut_idx = None
    for idx in range(len(lines) - 1, -1, -1):
        s = lines[idx].strip()
        if not s:
            continue
        for pat in PROMO_TAIL_PATTERNS:
            if re.search(pat, s, re.IGNORECASE):
                cut_idx = idx
                break
        if cut_idx is not None:
            break
    if cut_idx is None:
        return md.strip()
    while cut_idx > 0 and not lines[cut_idx - 1].strip():
        cut_idx -= 1
    return "\n".join(lines[:cut_idx]).rstrip()


def html_to_markdown(html: str) -> str:
    """将 HTML 转换为 Markdown"""
    h = HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0  # 不换行
    h.unicode_snob = True
    h.mark_code = True
    
    md = h.handle(html)
    # 清理多余的空白行
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def fetch_article(url: str) -> dict:
    """抓取单篇文章"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        # 检查是否被拦截
        if "captcha" in response.text.lower() or "验证" in response.text:
            return {"error": "被反爬虫拦截"}
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 提取标题
        title_elem = soup.select_one("#activity-name, .rich_media_title")
        title = ""
        if title_elem:
            title = title_elem.get_text().strip()
        
        # 提取正文
        content_elem = soup.select_one("#js_content")
        if not content_elem:
            return {"error": "未找到文章内容"}
        
        html_content = str(content_elem)
        
        # 提取发布日期
        date_elem = soup.select_one("#publish_time, .publish_time")
        publish_date = ""
        if date_elem:
            publish_date = date_elem.get_text().strip()
        
        return {
            "title": title,
            "html": html_content,
            "date": publish_date,
            "url": url
        }
    except Exception as e:
        return {"error": str(e)}


def save_markdown(title: str, content: str, date_str: str, output_dir: str):
    """保存 Markdown 文件"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成安全的文件名
    safe_title = normalize_title(title)
    safe_title = re.sub(r"[\\/:*?\"<>|]", "_", safe_title)
    safe_title = safe_title.replace(" ", "-")[:80]
    filename = f"{safe_title}.md"
    filepath = os.path.join(output_dir, filename)
    
    # 如果文件已存在，添加序号
    if os.path.exists(filepath):
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(filepath):
            filename = f"{base}-{counter}{ext}"
            filepath = os.path.join(output_dir, filename)
            counter += 1
    
    # 写入文件
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    return filepath


def main():
    """主函数"""
    print("=" * 60)
    print("微信公众号文章自动化导出工具")
    print("=" * 60)
    print()
    
    # 检查文章列表文件
    if not os.path.exists(ARTICLES_LIST_FILE):
        print(f"[ERROR] 未找到文章列表文件: {ARTICLES_LIST_FILE}")
        return 1
    
    # 读取文章列表
    with open(ARTICLES_LIST_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)
    
    print(f"找到 {len(articles)} 篇文章\n")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    success_count = 0
    failed_count = 0
    blocked_count = 0
    
    for i, article in enumerate(articles, 1):
        title = article.get("title", f"文章{i}")
        url = article.get("url", "")
        timestamp = article.get("timestamp")
        
        if not url:
            print(f"[{i}/{len(articles)}] [SKIP] {title} - 无URL")
            failed_count += 1
            continue
        
        print(f"[{i}/{len(articles)}] 处理: {title}")
        print(f"    URL: {url}")
        
        try:
            # 抓取文章
            content_data = fetch_article(url)
            
            if "error" in content_data:
                error_msg = content_data["error"]
                print(f"    [FAIL] {error_msg}")
                if "拦截" in error_msg or "captcha" in error_msg.lower():
                    blocked_count += 1
                    print(f"    [INFO] 被反爬虫拦截，建议使用浏览器扩展手动导出")
                failed_count += 1
                continue
            
            # 获取标题
            final_title = content_data.get("title") or title
            final_title = normalize_title(final_title)
            
            if not final_title:
                print(f"    [FAIL] 无法提取标题")
                failed_count += 1
                continue
            
            # 转换为 Markdown
            md_content = html_to_markdown(content_data["html"])
            
            # 清理引流链接
            md_content = clean_promo_tail(md_content)
            
            # 生成 front-matter
            if timestamp:
                date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            front_matter = f"""---
title: {final_title}
date: {date_str}
tags:
  - 大东山谷精选
---

{md_content}
"""
            
            # 保存文件
            filepath = save_markdown(final_title, front_matter, date_str, OUTPUT_DIR)
            print(f"    [OK] 已保存: {os.path.basename(filepath)}")
            success_count += 1
            
            # 延迟，避免请求过快
            time.sleep(2)
            
        except Exception as e:
            print(f"    [ERROR] 处理失败: {str(e)}")
            failed_count += 1
            continue
    
    print()
    print("=" * 60)
    print(f"导出完成！")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    if blocked_count > 0:
        print(f"  被拦截: {blocked_count} (建议使用浏览器扩展手动导出)")
    print(f"文件保存在: {OUTPUT_DIR}")
    print("=" * 60)
    
    if blocked_count > 0:
        print("\n提示：如果有多篇文章被拦截，建议：")
        print("1. 使用已安装的'文章同步助手'扩展手动导出")
        print("2. 或者提供浏览器 Cookie 来绕过反爬虫")
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
