@echo off
chcp 65001 >nul
echo ========================================
echo Wechatsync 文章导入脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 检查导出的 Markdown 文件...
if not exist "data\wechatsync_md\*.md" (
    echo [错误] 未找到 Markdown 文件！
    echo 请先使用 Wechatsync 导出文章到: data\wechatsync_md\ 目录
    echo.
    pause
    exit /b 1
)

echo [2/3] 运行导入脚本...
py scripts\import_wechatsync_md.py
if errorlevel 1 (
    echo [错误] 导入失败！
    pause
    exit /b 1
)

echo.
echo [3/3] 导入完成！
echo.
echo 下一步：
echo 1. 运行 "cd blog && hexo server" 预览文章
echo 2. 确认无误后运行 "cd blog && hexo clean && hexo generate && hexo deploy" 部署
echo.
pause
