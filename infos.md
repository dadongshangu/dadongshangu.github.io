## 如何首页不显示全文

之后有两种方法

### 方法一：写概述

在文章的`front-matter`中添加`description`，其中description中的内容就会被显示在首页上，其余一律不显示。

```
---
title: 让首页显示部分内容
date: 2020-02-23 22:55:10
description: 这是显示在首页的概述，正文内容均会被隐藏。
---
12345
```

比较不方便的是还得写一下概述，很多时候会懒得写概述，于是就需要第二种方法了。

### 方法二：文章截断

在需要截断的地方加入：

```markdown
<!--more-->
1
```

首页就会显示这条以上的所有内容，隐藏接下来的所有内容。
例如本文会显示到`修改配置`上面。

这个明显就方便很多，但当然有利有弊，比如开头都是废话首页看着就不是很好看，因此我一般会先选择方法二，如果感觉文章前面的写的不太好再用方法一。



## **push command：**

```reStructuredText
git commit -am "Update blog"
git push origin hexo
```

需要push到hexo分支

## **public：**

```reStructuredText
hexo clean
hexo g
hexo d
```

![logo](https://cdn.jsdelivr.net/gh/dadongshangu/CDN@master/images/logo_dadongshangu.jpg)

SPEC:

https://hexo.io/zh-cn/docs/commands.html



#Branch for development

git branch hexo 



#Branch for public

git branch master



Welcome to [Hexo](https://hexo.io/)! This is your very first post. Check [documentation](https://hexo.io/docs/) for more info. If you get any problems when using Hexo, you can find the answer in [troubleshooting](https://hexo.io/docs/troubleshooting.html) or you can ask me on [GitHub](https://github.com/hexojs/hexo/issues).

## Quick Start

### Create a new post

``` bash
$ hexo new "My New Post"
```

More info: [Writing](https://hexo.io/docs/writing.html)

### Run server

``` bash
$ hexo server
```

More info: [Server](https://hexo.io/docs/server.html)

### Generate static files

``` bash
$ hexo generate
```

More info: [Generating](https://hexo.io/docs/generating.html)

### Deploy to remote sites

``` bash
$ hexo deploy
```

More info: [Deployment](https://hexo.io/docs/one-command-deployment.html)



作者：CrazyMilk
链接：https://www.zhihu.com/question/21193762/answer/79109280
一、关于搭建的流程

\1. 创建仓库，[http://CrazyMilk.github.io](https://link.zhihu.com/?target=http%3A//CrazyMilk.github.io)；
\2. 创建两个分支：master 与 hexo；
\3. 设置hexo为默认分支（因为我们只需要手动管理这个分支上的Hexo网站文件）；
\4. 使用git clone git@github.com:CrazyMilk/CrazyMilk.github.io.git拷贝仓库；
\5. 在本地[http://CrazyMilk.github.io](https://link.zhihu.com/?target=http%3A//CrazyMilk.github.io)文件夹下通过Git bash依次执行npm install hexo、hexo init、npm install 和 npm install hexo-deployer-git（此时当前分支应显示为hexo）;
\6. 修改_config.yml中的deploy参数，分支应为master；
\7. 依次执行git add .、git commit -m "..."、git push origin hexo提交网站相关的文件；
\8. 执行hexo g -d生成网站并部署到GitHub上。

这样一来，在GitHub上的[http://CrazyMilk.github.io](https://link.zhihu.com/?target=http%3A//CrazyMilk.github.io)仓库就有两个分支，一个hexo分支用来存放网站的原始文件，一个master分支用来存放生成的静态网页。完美( •̀ ω •́ )y！

二、关于日常的改动流程
在本地对博客进行修改（添加新博文、修改样式等等）后，通过下面的流程进行管理。

\1. 依次执行git add .、git commit -m "..."、git push origin hexo指令将改动推送到GitHub（此时当前分支应为hexo）；
\2. 然后才执行hexo g -d发布网站到master分支上。

虽然两个过程顺序调转一般不会有问题，不过逻辑上这样的顺序是绝对没问题的（例如突然死机要重装了，悲催....的情况，调转顺序就有问题了）。

三、本地资料丢失后的流程
当重装电脑之后，或者想在其他电脑上修改博客，可以使用下列步骤：

\1. 使用git clone git@github.com:CrazyMilk/CrazyMilk.github.io.git拷贝仓库（默认分支为hexo）；
\2. 在本地新拷贝的[http://CrazyMilk.github.io](https://link.zhihu.com/?target=http%3A//CrazyMilk.github.io)文件夹下通过Git bash依次执行下列指令：npm install hexo、npm install、npm install hexo-deployer-git（记得，不需要hexo init这条指令）。

支付宝：

![支付宝](https://cdn.jsdelivr.net/gh/dadongshangu/CDN@master/images/alipay_support.png)

微信支付：

![weixin](https://cdn.jsdelivr.net/gh/dadongshangu/CDN@master/images/wechat_support.png)

公众号：大东山谷

![大东山谷](https://cdn.jsdelivr.net/gh/dadongshangu/CDN@master/images/qr_dadongshangu.png)