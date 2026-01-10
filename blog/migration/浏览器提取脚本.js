// 微信公众号文章批量提取脚本
// 使用方法：
// 1. 打开精选文章页面
// 2. 按F12打开开发者工具
// 3. 切换到Console标签
// 4. 滚动页面加载所有文章
// 5. 复制此脚本到控制台运行

(function() {
    console.log('开始提取文章链接...\n');
    
    let articles = [];
    let processedUrls = new Set();
    
    // 方法1: 从所有链接中提取
    document.querySelectorAll('a[href*="mp.weixin.qq.com/s"]').forEach(link => {
        let href = link.href;
        
        // 标准化URL
        if (href.includes('#')) {
            href = href.split('#')[0];
        }
        
        if (href && !processedUrls.has(href)) {
            processedUrls.add(href);
            
            // 提取标题
            let title = link.textContent.trim() || link.innerText.trim();
            
            // 如果标题为空或太短，尝试从父元素获取
            if (!title || title.length < 2) {
                let parent = link.closest('div, li, article, section');
                if (parent) {
                    let text = parent.textContent.trim();
                    // 提取第一行作为标题
                    title = text.split('\n')[0].substring(0, 100);
                }
            }
            
            // 清理标题
            title = title.replace(/^\d+\.\s*/, ''); // 移除开头的编号
            title = title.replace(/\d{10}$/, ''); // 移除末尾的时间戳
            title = title.trim();
            
            // 尝试从链接参数中提取时间戳
            let timestamp = null;
            let urlParams = new URLSearchParams(href.split('?')[1] || '');
            // 或者从页面数据中提取
            
            articles.push({
                title: title || '未命名文章',
                url: href,
                timestamp: timestamp
            });
        }
    });
    
    // 方法2: 从页面数据中提取（如果页面有数据）
    try {
        // 查找可能包含文章数据的script标签
        document.querySelectorAll('script').forEach(script => {
            let content = script.textContent || script.innerHTML;
            if (content.includes('mp.weixin.qq.com/s')) {
                let matches = content.match(/https?:\/\/mp\.weixin\.qq\.com\/s\/[A-Za-z0-9_?=&-]+/g);
                if (matches) {
                    matches.forEach(url => {
                        let cleanUrl = url.split('#')[0];
                        if (!processedUrls.has(cleanUrl)) {
                            processedUrls.add(cleanUrl);
                            articles.push({
                                title: '文章' + (articles.length + 1),
                                url: cleanUrl,
                                timestamp: null
                            });
                        }
                    });
                }
            }
        });
    } catch(e) {
        console.log('方法2提取失败:', e);
    }
    
    // 去重
    let uniqueArticles = [];
    let urlSet = new Set();
    articles.forEach(article => {
        let url = article.url.split('#')[0].split('?')[0];
        if (!urlSet.has(url)) {
            urlSet.add(url);
            uniqueArticles.push(article);
        }
    });
    
    // 输出结果
    console.log('='.repeat(60));
    console.log(`找到 ${uniqueArticles.length} 篇文章`);
    console.log('='.repeat(60));
    
    uniqueArticles.forEach((article, index) => {
        console.log(`${index + 1}. ${article.title}`);
        console.log(`   ${article.url}\n`);
    });
    
    // 生成JSON格式
    let json = JSON.stringify(uniqueArticles, null, 2);
    console.log('\nJSON格式：');
    console.log(json);
    
    // 复制到剪贴板
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(json).then(() => {
            console.log('\n✓ JSON已复制到剪贴板！');
            alert(`成功提取 ${uniqueArticles.length} 篇文章，JSON已复制到剪贴板！`);
        }).catch(err => {
            console.log('\n无法自动复制，请手动复制上面的JSON');
        });
    } else {
        console.log('\n请手动复制上面的JSON内容');
    }
    
    // 生成纯链接列表
    let links = uniqueArticles.map(a => a.url).join('\n');
    console.log('\n纯链接列表：');
    console.log(links);
    
    return uniqueArticles;
})();
