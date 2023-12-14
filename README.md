# wordcloud 词云系统

## 简介

通过关键词生成词云系统

首页功能链接：
- 1.提交关键词：获取每一课的关键词提交链接
- 2.显示词云：显示每个年级每一课的词云结果

## 一、部署环境

### Python 运行环境

```bash
# 1.pip源设置为清华源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 2.需要安装的库
pip install flask flask_sqlalchemy gevent pandas openpyxl wordcloud

```

## 二、运行

运行 app.py 后，在浏览器中打开 `http://ip:5005` 进行访问。

