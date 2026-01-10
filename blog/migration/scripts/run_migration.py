#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
迁移主执行脚本
按顺序执行所有迁移步骤
"""

import os
import sys
import subprocess

# 脚本目录
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

def run_script(script_name, description):
    """运行指定的脚本"""
    print("\n" + "=" * 60)
    print(description)
    print("=" * 60)
    
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    
    if not os.path.exists(script_path):
        print(f"错误：找不到脚本 {script_name}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=os.path.dirname(SCRIPTS_DIR),
            check=False
        )
        return result.returncode == 0
    except Exception as e:
        print(f"执行脚本时出错: {str(e)}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("微信公众号文章迁移工具")
    print("=" * 60)
    print("\n本工具将按以下步骤执行迁移：")
    print("1. 抓取文章列表和内容")
    print("2. 转换文章格式为Markdown")
    print("3. 检查重复文章")
    print("4. 导入文章到博客")
    print("\n注意：由于微信公众号的反爬虫机制，")
    print("      自动抓取可能失败，您可能需要手动提供文章链接。")
    
    response = input("\n是否继续？(y/n): ")
    if response.lower() != 'y':
        print("已取消")
        return
    
    # 步骤1: 抓取文章
    if not run_script("fetch_articles.py", "步骤1: 抓取文章"):
        print("\n警告：文章抓取可能失败")
        print("如果自动抓取失败，请手动创建文章列表文件")
        print("文件路径: migration/data/articles_list.json")
        print("\n是否继续执行后续步骤？(y/n): ", end='')
        response = input()
        if response.lower() != 'y':
            return
    
    # 步骤2: 转换格式
    if not run_script("convert_format.py", "步骤2: 转换文章格式"):
        print("\n错误：格式转换失败")
        return
    
    # 步骤3: 检查重复
    if not run_script("check_duplicates.py", "步骤3: 检查重复文章"):
        print("\n错误：去重检查失败")
        return
    
    # 步骤4: 导入文章
    if not run_script("import_posts.py", "步骤4: 导入文章"):
        print("\n错误：文章导入失败")
        return
    
    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)
    print("\n下一步：")
    print("1. 检查导入的文章格式是否正确")
    print("2. 运行 'hexo server' 本地预览")
    print("3. 确认无误后运行 'hexo deploy' 部署")

if __name__ == '__main__':
    main()
