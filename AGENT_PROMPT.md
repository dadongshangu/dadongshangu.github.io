# Agent 继续项目操作提示词

## 使用说明
在新对话开始时，复制以下提示词并发送给 AI Agent，以恢复项目上下文。

---

## 提示词内容

```
我正在维护一个基于 Hexo 的静态博客项目，需要继续处理文章修复工作。

## 项目背景
- 项目路径: E:\3.github\repositories\dadongshangu.github.io
- 这是一个从微信公众号迁移文章的 Hexo 博客项目
- 文章目录: blog/source/_posts/ (共39篇文章)
- 脚本目录: blog/migration/scripts/
- 原始数据: blog/migration/data/wechatsync_md/

## 已完成的工作
1. ✅ 创建了图片插入脚本 (smart_insert_images.py) - 智能匹配图片和图片说明
2. ✅ 创建了段落修复脚本 (fix_paragraphs.py) - 修复段落分隔，识别对话行
3. ✅ 创建了重复内容清理脚本 (clean_duplicate_captions.py, fix_duplicate_content.py)
4. ✅ 创建了文章结束标记脚本 (add_end_marker.py) - 在末尾图片前添加"全文完，以下图片待整理"
5. ✅ 创建了综合修复脚本 (comprehensive_fix.py) - 检查文字内容、清理重复、修复分段
6. ✅ 创建了内容恢复脚本 (restore_missing_content.py) - 从原始数据恢复缺失内容
7. ✅ 已修复"一个异乡人眼中的宁国"文章 - 恢复了缺失的文字内容
8. ✅ 已修复"第一次摆摊，卖了39块钱"文章 - 清理了重复图片说明，修复了分段
9. ✅ 已修复"忆二十几年前的"大案""文章 - 清理了重复段落和分隔符
10. ✅ 已修复"唯有母爱不可辜负"文章 - 清理了重复的图片说明
11. ✅ 已修复"辅导班，上还是不上？"文章 - 修复了对话分段问题

## 项目规则和上下文
请参考以下文件了解详细规则：
- @CONTEXT.md - 完整的项目上下文文档
- @.cursorrules - Cursor 项目规则文件

## 重要约定
1. **文章格式**:
   - Front-matter: title, date, tags
   - 图片格式: ![图片说明](图片URL)
   - 图片说明: （图片说明）或 _（图片说明）_
   - 段落分隔: 在句号、问号、感叹号后添加空行
   - 文章结束标记: "全文完，以下图片待整理"

2. **图片处理**:
   - 过滤小图片（<200x200），可能是分隔符
   - 图片说明应紧跟在图片后面
   - 删除没有对应图片的图片说明
   - 删除重复的图片说明

3. **内容清理**:
   - 删除重复段落
   - 清理分隔符（dadong*shangu等）
   - 清理多余空行（连续3个以上压缩为2个）
   - 保留段落之间的空行

4. **段落修复**:
   - 在标点符号后添加段落分隔
   - 识别独立对话行并正确分段
   - 保留特殊格式（列表、引用、图片等）
   - 不要过度添加段落分隔

## 可用脚本
- `py blog\migration\scripts\fix_paragraphs.py` - 修复段落分隔
- `py blog\migration\scripts\clean_duplicate_captions.py` - 清理重复图片说明
- `py blog\migration\scripts\fix_duplicate_content.py` - 清理重复内容
- `py blog\migration\scripts\add_end_marker.py` - 添加文章结束标记
- `py blog\migration\scripts\comprehensive_fix.py` - 综合修复
- `py blog\migration\scripts\smart_insert_images.py` - 智能图片插入
- `py blog\migration\scripts\restore_missing_content.py` - 恢复缺失内容

## 当前状态
- 所有39篇文章已处理
- 大部分文章已修复完成
- 需要继续检查是否有遗漏的问题

## 注意事项
1. 不要破坏现有格式（front-matter、列表、引用等）
2. 不要删除文字内容，只删除重复内容和无效图片说明
3. 保持段落自然，不要过度添加段落分隔
4. 如有缺失内容，从 wechatsync_md/ 目录恢复
5. 修复后检查文章是否正常

## 响应要求
- 始终使用中文简体回复
- 使用 [OK]、[WARN]、[ERROR] 标记输出
- 最后输出 [SUMMARY] 统计信息

请帮助我继续检查和修复文章中的问题。
```

---

## 简化版提示词（快速使用）

如果对话上下文有限，可以使用这个简化版：

```
我正在维护一个 Hexo 博客项目，需要修复文章格式问题。

项目信息：
- 文章目录: blog/source/_posts/ (39篇文章)
- 脚本目录: blog/migration/scripts/
- 参考文档: @CONTEXT.md 和 @.cursorrules

已完成：图片插入、段落修复、重复内容清理、文章结束标记添加

请帮助我继续检查和修复文章问题。使用中文回复。
```

---

## 使用场景

### 场景1: 继续检查文章
```
请运行综合修复脚本检查所有文章，找出并修复问题。
```

### 场景2: 修复特定文章
```
请检查并修复文章"XXX.md"，确保：
1. 有完整的文字内容
2. 段落分隔正确
3. 没有重复的图片说明
4. 图片格式正确
```

### 场景3: 添加新功能
```
需要添加新功能：XXX
请参考现有脚本的编写风格，创建新脚本。
```

### 场景4: 批量处理
```
请对所有文章执行以下操作：
1. 检查段落分隔
2. 清理重复内容
3. 验证图片格式
```

---

## 更新记录

当项目有重大变化时，请更新此提示词：
- 添加新的已解决问题
- 更新脚本列表
- 添加新的注意事项
