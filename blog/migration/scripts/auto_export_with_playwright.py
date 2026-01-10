#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用 Playwright 自动化浏览器，批量抓取微信公众号文章并转换为 Markdown
- 自动打开每篇文章
- 提取文章内容
- 转换为 Markdown 格式
- 清理引流链接
- 保存到 wechatsync_md 目录
"""

import os
import json
import re
import time
from pathlib import Path
from datetime import datetime
from html2text import HTML2Text

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
]


def normalize_title(title: str) -> str:
    """规范化标题"""
    title = (title or "").strip()
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r"[“”\"'']", "", title)
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


def extract_article_content(page, url: str) -> dict:
    """从页面提取文章内容"""
    try:
        # 等待文章内容加载
        page.wait_for_selector("#js_content", timeout=10000)
        
        # 提取标题
        title_elem = page.query_selector("#activity-name, .rich_media_title")
        title = ""
        if title_elem:
            title = title_elem.inner_text().strip()
        
        # 提取正文 HTML
        content_elem = page.query_selector("#js_content")
        if not content_elem:
            return None
        
        html_content = content_elem.inner_html()
        
        # 提取发布日期
        date_elem = page.query_selector("#publish_time, .publish_time, #meta_content .publish_time")
        publish_date = ""
        if date_elem:
            publish_date = date_elem.inner_text().strip()
        
        return {
            "title": title,
            "html": html_content,
            "date": publish_date,
            "url": url
        }
    except Exception as e:
        print(f"    [ERROR] 提取内容失败: {str(e)}")
        return None


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
    print("微信公众号文章自动化导出工具 (Playwright)")
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
    
    # 检查是否已安装 playwright
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] 未安装 playwright")
        print("请运行: pip install playwright")
        print("然后运行: playwright install chromium")
        return 1
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    success_count = 0
    failed_count = 0
    
    with sync_playwright() as p:
        # 启动浏览器（使用已安装的 Edge，这样可以使用已登录的会话）
        print("正在启动浏览器...")
        browser = p.chromium.launch(
            headless=False,  # 显示浏览器窗口，方便调试
            channel="msedge"  # 使用 Edge 浏览器
        )
        
        # 创建新上下文，复用现有会话（如果可能）
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        )
        
        page = context.new_page()
        
        try:
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
                    # 访问文章页面
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    time.sleep(2)  # 等待页面完全加载
                    
                    # 提取文章内容
                    content_data = extract_article_content(page, url)
                    
                    if not content_data:
                        print(f"    [FAIL] 无法提取内容")
                        failed_count += 1
                        continue
                    
                    # 获取标题（优先使用提取的标题）
                    final_title = content_data.get("title") or title
                    final_title = normalize_title(final_title)
                    
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
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"    [ERROR] 处理失败: {str(e)}")
                    failed_count += 1
                    continue
        
        finally:
            browser.close()
    
    print()
    print("=" * 60)
    print(f"导出完成！成功: {success_count}, 失败: {failed_count}")
    print(f"文件保存在: {OUTPUT_DIR}")
    print("=" * 60)
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
