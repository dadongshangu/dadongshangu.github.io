# 微信公众号文章迁移工具

## 概述

此工具用于从微信公众号精选文章页面迁移文章到 Hexo 博客。

## 目录结构

```
migration/
├── scripts/
│   ├── fetch_articles.py      # 抓取文章脚本
│   ├── convert_format.py       # 格式转换脚本
│   ├── check_duplicates.py    # 去重检查脚本
│   └── import_posts.py        # 导入文章脚本
├── data/
│   ├── articles_list.json     # 文章列表
│   ├── articles_raw/          # 原始 HTML 文件
│   └── articles_markdown/     # 转换后的 Markdown
└── README.md                   # 本文件
```

## 使用方法

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 执行迁移：
```bash
python scripts/fetch_articles.py
python scripts/convert_format.py
python scripts/check_duplicates.py
python scripts/import_posts.py
```

## 注意事项

- 确保网络连接正常
- 抓取时注意控制频率，避免被封
- 迁移前建议备份现有博客
