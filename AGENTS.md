# docx2tex解析

## 项目目标

本项目用于解析开源项目[docx2tex](https://github.com/transpect/docx2tex)

doc2tex是一个将docx文档转换为tex文档的工具，特别擅长转换公式、表格等复杂对象

本项目旨在解明docx2tex的原理，并在其基础上进行二次开发，完善其功能

## docx2tex的原理

以下翻译自官方文档：

docx2tex 的处理流水线由三个宏观步骤组成：

- docx2hub：该步骤几乎不可配置。它把一个 docx 文件转换为 Hub XML 表示。

- evolve-hub：这是一组 XSLT 模式的“工具包”；其功能包括（但不限于）将带列表标记和悬挂缩进的段落转换为正确的嵌套列表、创建嵌套的章节层级、将图像与其图题分组等。docx2tex 只使用其中的部分模式，这些模式由 evolve-hub.xpl 进行编排，并由 evolve-hub-driver.xsl 做详细配置。

- xml2tex

有五个用于添加自定义处理的主要挂接点：CSV 或 xml2tex 配置；应用在 evolve-hub 与 xml2tex 之间的 XSLT；用于修改 evolve-hub 行为的 XSLT；字体映射（fontmaps）。

## docx2tex源码目录结构

docx2tex项目源码存放于项目根目录下的"docx2tex"目录下

- docx2tex/calabash: 一个前端工具，具体用途我也没搞清楚
- docx2tex/cascade: 似乎是一个用于写层级配置的库
- docx2tex/conf: 默认的配置文件
- docx2tex/docx2hub: 核心组件之一，用于将docx转为Hub XML 表示
- docx2tex/evolve-hub: 核心组件之一，用于进一步加工Hub XML 表示
- docx2tex/fontmaps: 存放了一些字体映射配置
- docx2tex/htmlreports: 似乎是用于生成HTML错误报告的组件
- docx2tex/mml-normalize: 用于处理MathML公式的组件
- docx2tex/mml2tex: 将MathML公式转化为Latex公式的组件
- docx2tex/schema: 和DocBook（？）相关，没搞清楚
- docx2tex/xml2tex: 核心组件之一，用于将XML转化为TEX
- docx2tex/xmlcatalog: 存放了一些catalog（？）
- docx2tex/xpl: 存放了一些.xpl文件，似乎也是配置相关
- docx2tex/xproc-util: 也是某个组件，用途不明
- docx2tex/xsl: 存放了一些.xsl文件，似乎也是配置相关
- docx2tex/xslt-util: 一些XSLT（？）函数

## 解析要求

- 主要以解明工作逻辑和使用方法为主，尤其是如何自定义配置
- 顺带解析一下技术栈
- 可以思考一下是否可以从中间表示（XML）转回docx