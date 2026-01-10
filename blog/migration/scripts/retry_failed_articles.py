#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重试失败的微信公众号文章抓取
- 增加重试机制
- 更长的超时时间
- 更慢的请求频率
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

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
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
    h.body_width = 0
    h.unicode_snob = True
    h.mark_code = True
    
    md = h.handle(html)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def fetch_article_with_retry(url: str, max_retries=3, timeout=60):
    """带重试机制的文章抓取"""
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
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"      尝试 {attempt}/{max_retries}...")
            response = requests.get(
                url, 
                headers=headers, 
                timeout=timeout, 
                allow_redirects=True,
                stream=True  # 使用流式下载，避免大文件超时
            )
            response.raise_for_status()
            
            # 检查是否被拦截
            content = response.text
            if "captcha" in content.lower() or "验证" in content:
                return {"error": "被反爬虫拦截"}
            
            soup = BeautifulSoup(content, "html.parser")
            
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
            
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                wait_time = attempt * 5
                print(f"      超时，等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            return {"error": "请求超时"}
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                wait_time = attempt * 5
                print(f"      连接错误: {str(e)[:50]}... 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            return {"error": f"连接错误: {str(e)}"}
            
        except Exception as e:
            if attempt < max_retries:
                wait_time = attempt * 5
                print(f"      错误: {str(e)[:50]}... 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            return {"error": str(e)}
    
    return {"error": "重试次数用尽"}


def get_existing_files():
    """获取已存在的文件列表"""
    existing = set()
    if os.path.exists(OUTPUT_DIR):
        for f in os.listdir(OUTPUT_DIR):
            if f.endswith('.md'):
                # 提取标题（去掉序号后缀）
                base = f[:-3]  # 去掉 .md
                base = re.sub(r'-\d+$', '', base)  # 去掉 -1, -2 等后缀
                existing.add(base)
    return existing


def save_markdown(title: str, content: str, date_str: str, output_dir: str):
    """保存 Markdown 文件"""
    os.makedirs(output_dir, exist_ok=True)
    
    safe_title = normalize_title(title)
    safe_title = re.sub(r"[\\/:*?\"<>|]", "_", safe_title)
    safe_title = safe_title.replace(" ", "-")[:80]
    filename = f"{safe_title}.md"
    filepath = os.path.join(output_dir, filename)
    
    if os.path.exists(filepath):
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(filepath):
            filename = f"{base}-{counter}{ext}"
            filepath = os.path.join(output_dir, filename)
            counter += 1
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    return filepath


def main():
    """主函数"""
    print("=" * 60)
    print("微信公众号文章重试抓取工具")
    print("=" * 60)
    print()
    
    if not os.path.exists(ARTICLES_LIST_FILE):
        print(f"[ERROR] 未找到文章列表文件: {ARTICLES_LIST_FILE}")
        return 1
    
    with open(ARTICLES_LIST_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)
    
    # 获取已存在的文件
    existing_files = get_existing_files()
    
    # 找出需要重试的文章（未成功抓取的）
    to_retry = []
    for article in articles:
        title = normalize_title(article.get("title", ""))
        if title and title not in existing_files:
            to_retry.append(article)
    
    if not to_retry:
        print("所有文章都已成功抓取！")
        return 0
    
    print(f"找到 {len(to_retry)} 篇需要重试的文章\n")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    success_count = 0
    failed_count = 0
    
    for i, article in enumerate(to_retry, 1):
        title = article.get("title", f"文章{i}")
        url = article.get("url", "")
        timestamp = article.get("timestamp")
        
        if not url:
            print(f"[{i}/{len(to_retry)}] [SKIP] {title} - 无URL")
            failed_count += 1
            continue
        
        print(f"[{i}/{len(to_retry)}] 重试: {title}")
        print(f"    URL: {url}")
        
        try:
            # 使用重试机制抓取
            content_data = fetch_article_with_retry(url, max_retries=3, timeout=60)
            
            if "error" in content_data:
                error_msg = content_data["error"]
                print(f"    [FAIL] {error_msg}")
                failed_count += 1
                # 延迟后继续
                time.sleep(5)
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
            time.sleep(5)
            
        except Exception as e:
            print(f"    [ERROR] 处理失败: {str(e)}")
            failed_count += 1
            time.sleep(5)
            continue
    
    print()
    print("=" * 60)
    print(f"重试完成！")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    print(f"文件保存在: {OUTPUT_DIR}")
    print("=" * 60)
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
