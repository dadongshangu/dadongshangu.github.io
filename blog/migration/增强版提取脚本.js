// 增强版文章链接提取脚本
// 尝试多种方法提取文章链接

(function() {
    console.log('开始提取文章链接（增强版）...\n');
    
    let articles = [];
    let urlSet = new Set();
    
    // 方法1: 查找所有a标签
    console.log('方法1: 查找所有a标签...');
    document.querySelectorAll('a').forEach(link => {
        let href = link.href || link.getAttribute('href');
        if (href && href.includes('mp.weixin.qq.com/s')) {
            let cleanUrl = href.split('#')[0];
            if (!urlSet.has(cleanUrl)) {
                urlSet.add(cleanUrl);
                let title = link.textContent.trim() || link.innerText.trim() || '';
                articles.push({title: title || '未命名', url: cleanUrl, timestamp: null});
            }
        }
    });
    console.log(`方法1找到: ${articles.length} 篇`);
    
    // 方法2: 查找所有包含链接的元素（包括data属性）
    console.log('方法2: 查找data属性和其他属性...');
    document.querySelectorAll('[href*="mp.weixin.qq.com"], [data-url*="mp.weixin.qq.com"], [data-link*="mp.weixin.qq.com"]').forEach(elem => {
        let href = elem.href || elem.getAttribute('href') || elem.getAttribute('data-url') || elem.getAttribute('data-link');
        if (href && href.includes('mp.weixin.qq.com/s')) {
            let cleanUrl = href.split('#')[0];
            if (!urlSet.has(cleanUrl)) {
                urlSet.add(cleanUrl);
                let title = elem.textContent.trim() || elem.getAttribute('title') || '';
                articles.push({title: title || '未命名', url: cleanUrl, timestamp: null});
            }
        }
    });
    console.log(`方法2后总计: ${articles.length} 篇`);
    
    // 方法3: 从script标签中提取
    console.log('方法3: 从script标签中提取...');
    document.querySelectorAll('script').forEach(script => {
        let content = script.textContent || script.innerHTML || '';
        let matches = content.match(/https?:\/\/mp\.weixin\.qq\.com\/s\/[A-Za-z0-9_?=&-]+/g);
        if (matches) {
            matches.forEach(url => {
                let cleanUrl = url.split('#')[0];
                if (!urlSet.has(cleanUrl)) {
                    urlSet.add(cleanUrl);
                    articles.push({title: '文章' + (articles.length + 1), url: cleanUrl, timestamp: null});
                }
            });
        }
    });
    console.log(`方法3后总计: ${articles.length} 篇`);
    
    // 方法4: 查找所有文本内容中的链接
    console.log('方法4: 从页面文本中提取链接...');
    let bodyText = document.body.innerText || document.body.textContent || '';
    let textMatches = bodyText.match(/https?:\/\/mp\.weixin\.qq\.com\/s\/[A-Za-z0-9_?=&-]+/g);
    if (textMatches) {
        textMatches.forEach(url => {
            let cleanUrl = url.split('#')[0];
            if (!urlSet.has(cleanUrl)) {
                urlSet.add(cleanUrl);
                articles.push({title: '文章' + (articles.length + 1), url: cleanUrl, timestamp: null});
            }
        });
    }
    console.log(`方法4后总计: ${articles.length} 篇`);
    
    // 方法5: 查找所有可能的文章容器
    console.log('方法5: 查找文章列表容器...');
    let possibleContainers = document.querySelectorAll('[class*="article"], [class*="item"], [class*="list"], [id*="article"], [id*="item"]');
    possibleContainers.forEach(container => {
        let links = container.querySelectorAll('a[href*="mp.weixin.qq.com"]');
        links.forEach(link => {
            let href = link.href || link.getAttribute('href');
            if (href && href.includes('mp.weixin.qq.com/s')) {
                let cleanUrl = href.split('#')[0];
                if (!urlSet.has(cleanUrl)) {
                    urlSet.add(cleanUrl);
                    let title = link.textContent.trim() || container.textContent.trim().split('\n')[0] || '';
                    articles.push({title: title || '未命名', url: cleanUrl, timestamp: null});
                }
            }
        });
    });
    console.log(`方法5后总计: ${articles.length} 篇`);
    
    // 输出结果
    console.log('\n' + '='.repeat(60));
    console.log(`总共找到 ${articles.length} 篇文章`);
    console.log('='.repeat(60));
    
    if (articles.length > 0) {
        articles.forEach((article, index) => {
            console.log(`${index + 1}. ${article.title}`);
            console.log(`   ${article.url}\n`);
        });
        
        // 生成JSON
        let json = JSON.stringify(articles, null, 2);
        console.log('\nJSON格式：');
        console.log(json);
        
        // 复制到剪贴板
        if (navigator.clipboard) {
            navigator.clipboard.writeText(json).then(() => {
                console.log('\n✓ JSON已复制到剪贴板！');
                alert('成功提取 ' + articles.length + ' 篇文章！\nJSON已复制到剪贴板。');
            }).catch(() => {
                console.log('\n请手动复制上面的JSON内容');
            });
        }
    } else {
        console.log('\n未找到任何文章链接。');
        console.log('\n调试信息：');
        console.log('页面URL:', window.location.href);
        console.log('页面标题:', document.title);
        console.log('所有链接数量:', document.querySelectorAll('a').length);
        console.log('包含weixin的链接:', document.querySelectorAll('a[href*="weixin"]').length);
        console.log('包含mp.weixin的链接:', document.querySelectorAll('a[href*="mp.weixin"]').length);
        
        // 显示前10个链接供调试
        console.log('\n前10个链接：');
        document.querySelectorAll('a').forEach((link, i) => {
            if (i < 10) {
                console.log(`${i+1}. ${link.href} - ${link.textContent.trim().substring(0, 50)}`);
            }
        });
    }
    
    return articles;
})();
