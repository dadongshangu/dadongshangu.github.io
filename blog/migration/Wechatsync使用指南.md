# Wechatsync 扩展安装和使用指南

## 第一步：在 Edge 浏览器中加载扩展

1. **打开 Edge 浏览器扩展管理页面**：
   - 在地址栏输入：`edge://extensions/`
   - 按回车键

2. **启用开发者模式**：
   - 在扩展管理页面的左下角，找到并开启 **"开发者模式"** 开关

3. **加载解压后的扩展程序**：
   - 点击页面左侧的 **"加载解压缩的扩展"** 按钮
   - 在弹出的文件选择窗口中，导航到：
     ```
     C:\Users\mmeng\Downloads\WechatSync-built
     ```
   - 选择该文件夹，然后点击 **"选择文件夹"** 按钮

4. **确认安装**：
   - 返回扩展管理页面，你应该能看到 **"微信公众号同步助手"** 已成功添加，并处于启用状态
   - 如果浏览器提示扩展不安全，可以暂时忽略（这是正常的，因为是从第三方下载的）

## 第二步：使用 Wechatsync 导出文章

1. **打开微信公众号文章页面**：
   - 访问你的微信公众号精选文章页面：
     ```
     https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&album_id=1417552598718332928&__biz=MzIxMjYyMDA2Nw==#wechat_redirect
     ```

2. **打开单篇文章**：
   - 点击任意一篇文章，打开文章详情页

3. **使用 Wechatsync 提取文章**：
   - 点击浏览器工具栏中的 **Wechatsync 扩展图标**
   - 在弹出窗口中，你应该能看到文章内容已经被自动提取
   - 点击 **"导出"** 或 **"保存为 Markdown"** 按钮
   - 选择保存位置为：
     ```
     E:\3.github\repositories\dadongshangu.github.io\blog\migration\data\wechatsync_md
     ```

4. **批量导出**：
   - 重复步骤 2-3，逐一打开并导出所有 36 篇文章
   - 或者，如果 Wechatsync 支持批量导出，可以使用批量功能

## 第三步：导入到 Hexo 博客

导出完成后，运行以下命令自动导入：

```bash
cd E:\3.github\repositories\dadongshangu.github.io\blog\migration
py scripts\import_wechatsync_md.py
```

脚本会自动：
- 读取 `data/wechatsync_md/` 目录下的所有 Markdown 文件
- 清理文章末尾的引流链接
- 检查重复文章（与现有 `blog/source/_posts/` 中的文章对比）
- 自动生成 Hexo 格式的 front-matter（标题、日期、标签）
- 将处理后的文章导入到 `blog/source/_posts/` 目录

## 注意事项

- **日期处理**：脚本会优先使用 `articles_list.json` 中的原始发布日期，确保文章日期准确
- **引流链接清理**：脚本会自动识别并删除文章末尾的微信公众号引流内容
- **去重检查**：如果文章标题已存在，会自动跳过，避免重复导入
- **文件命名**：导入的文件会按照 `YYYY-MM-DD-标题.md` 格式命名

## 如果遇到问题

- **扩展无法加载**：确保选择了正确的文件夹（`WechatSync-built`），而不是源代码文件夹
- **文章无法提取**：确保你已经登录了微信公众号后台，并且文章页面已完全加载
- **导出失败**：尝试刷新页面，或者关闭并重新打开文章页面
