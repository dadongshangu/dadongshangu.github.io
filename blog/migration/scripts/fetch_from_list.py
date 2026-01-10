#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从 data/articles_list.json 读取文章链接，抓取每篇文章 HTML，并提取正文（js_content）
输出：
- data/articles_raw/*.html 原始HTML
- 覆盖 data/articles_list.json：写入 html_file/content
"""

import json
import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LIST_FILE = os.path.join(DATA_DIR, "articles_list.json")
RAW_DIR = os.path.join(DATA_DIR, "articles_raw")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://mp.weixin.qq.com/",
}

COOKIE_ENV = "WECHAT_COOKIE"


def safe_filename(name: str, max_len: int = 80) -> str:
    name = (name or "").strip()
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r'[\\\\/:*?"<>|]', "_", name)
    if len(name) > max_len:
        name = name[:max_len].rstrip()
    return name or "untitled"


def fetch_one(session: requests.Session, url: str):
    resp = session.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    resp.encoding = "utf-8"
    return resp


def is_blocked(html: str) -> bool:
    if not html:
        return True
    # 常见拦截/验证页面关键词
    keywords = [
        "访问过于频繁",
        "environmental",
        "verify",
        "请输入验证码",
        "为了保护你的网络安全",
    ]
    return any(k in html for k in keywords)


def main():
    if not os.path.exists(LIST_FILE):
        raise SystemExit(f"Missing {LIST_FILE}")

    os.makedirs(RAW_DIR, exist_ok=True)

    with open(LIST_FILE, "r", encoding="utf-8") as f:
        items = json.load(f)

    session = requests.Session()
    cookie = os.environ.get(COOKIE_ENV, "").strip()
    if cookie:
        # 允许用户通过环境变量注入 Cookie，绕过频控/验证
        session.headers.update({"Cookie": cookie})
        print(f"[INFO] Using Cookie from env {COOKIE_ENV} (len={len(cookie)})")
    else:
        print(f"[INFO] No Cookie found. If blocked, set env {COOKIE_ENV}.")

    updated = []
    ok = 0
    failed = 0

    for i, item in enumerate(items, 1):
        title = item.get("title", f"post-{i}")
        url = item.get("url")
        if not url:
            updated.append(item)
            failed += 1
            continue

        print(f"[{i}/{len(items)}] fetching: {title}")

        try:
            resp = fetch_one(session, url)
            if resp.status_code != 200:
                print(f"  [WARN] status={resp.status_code}")
                updated.append(item)
                failed += 1
                time.sleep(1)
                continue

            html = resp.text
            if is_blocked(html):
                print("  [ERROR] blocked by wechat (captcha/limit). Stop here.")
                # 立刻保存当前进度
                with open(LIST_FILE, "w", encoding="utf-8") as wf:
                    json.dump(updated + items[i - 1 :], wf, ensure_ascii=False, indent=2)
                raise SystemExit("Blocked. Please retry later or provide cookies.")

            filename = f"{i:02d}-{safe_filename(title)}.html"
            html_path = os.path.join(RAW_DIR, filename)
            with open(html_path, "w", encoding="utf-8") as wf:
                wf.write(html)

            soup = BeautifulSoup(html, "html.parser")
            content_div = soup.find("div", id="js_content") or soup.find("div", class_="rich_media_content")
            if not content_div:
                print("  [WARN] content div not found")
                updated.append(item)
                failed += 1
                time.sleep(1)
                continue

            new_item = dict(item)
            new_item["html_file"] = html_path
            new_item["content"] = str(content_div)
            updated.append(new_item)
            ok += 1

            # 友好一点，避免频率过高
            time.sleep(1.5)
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [ERROR] {e}")
            updated.append(item)
            failed += 1
            time.sleep(1.5)

    with open(LIST_FILE, "w", encoding="utf-8") as wf:
        json.dump(updated, wf, ensure_ascii=False, indent=2)

    print(f"[OK] fetched: {ok}, failed: {failed}, saved: {LIST_FILE}")


if __name__ == "__main__":
    main()

