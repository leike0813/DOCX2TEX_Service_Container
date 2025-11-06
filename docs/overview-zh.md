# docx2tex 解析总览（中文）

本文旨在从源码与配置入手，系统解析 docx2tex 的工作原理与使用方式，重点说明 xml2tex 配置与 evolve-hub 的定制方法，并给出从中间表示（Hub XML）反向生成 DOCX 的路线与可行性评估。本文不包含实际运行步骤，所有示例均基于源码分析。

---

## 1. 项目概览与技术栈

- 目标：将 DOCX 转换为 LaTeX（TeX），在公式（MathML/MathType）、表格、图片、列表、标题等复杂对象上保留语义结构。
- 三段流水线：
  - docx2hub：DOCX → Hub XML（中间表示，近 DocBook 语义）。
  - evolve-hub：基于 XSLT 的结构归一化与语义提升（列表/章节/图题等）。
  - xml2tex：依据 xml2tex 配置（CSV 或 XML DSL）生成 LaTeX 文本。
- 核心技术：
  - XProc 1.0（Calabash）：流水线编排（`docx2tex/xpl/*.xpl`）。
  - XSLT 2.0：结构变换与生成（`docx2tex/xsl/*.xsl`、`docx2tex/xml2tex/xsl/*.xsl`）。
  - Relax NG：配置校验（`docx2tex/xml2tex/schema/xml2tex.rng`）。
  - transpect 生态：`xproc-util`、`cascade`、`mml2tex`、`calstable` 等工具集。

参考文件：
- 入口总管：`docx2tex/xpl/docx2tex.xpl:1`
- evolve-hub 编排：`docx2tex/xpl/evolve-hub.xpl:1`，driver：`docx2tex/xsl/evolve-hub-driver.xsl:1`
- xml2tex 编排与生成：`docx2tex/xml2tex/xpl/xml2tex.xpl:1`，生成器：`docx2tex/xml2tex/xsl/xml2tex.xsl:1`
- 默认配置：`docx2tex/conf/conf.csv:1`、`docx2tex/conf/conf.xml:1`

---

## 2. 处理流水线与关键入口

### 2.1 数据流（不执行，仅解析）

1) docx2hub：DOCX 解包与解析 → 产出 Hub XML（DocBook 命名空间）。
2) evolve-hub：根据 driver（XSLT）在多个模式（mode）下处理 Hub XML：
   - 列表侦测/嵌套修正、章节层级归纳、图像与题注绑定、上/下标统一等。
3) xml2tex：加载 xml2tex 配置（CSV 或 XML），生成用于文本输出的 XSLT，再将（进化后的）Hub XML 转为 LaTeX 文本。

### 2.2 入口与重要选项（来自 `docx2tex/xpl/docx2tex.xpl`）

- `conf`：CSV 或 XML 配置路径，决定 xml2tex 的映射规则与 preamble 等（默认 `../conf/conf.csv`）。
- `custom-evolve-hub-driver`：自定义 evolve-hub driver 样式表入口（默认指向 `xsl/evolve-hub-driver.xsl`）。
- `custom-xsl`：在 evolve-hub 与 xml2tex 之间注入自定义 XSLT（对 Hub XML 进行项目化调整）。
- `list-mode`：列表识别策略（`indent`/`role`/`none`）。
- `table-model`：表格渲染模型（`tabular`/`tabularx`）。
- `refs`：是否转换内部引用为 LaTeX `\label`/`\ref`。
- `table-grid`：是否绘制表格边框网格。
- `mml-space-handling`：MathML 空格处理策略（`xml-space` 或 `mspace`）。
- `image-output-dir`：图片输出目录重写。
- `custom-font-maps-dir`：字体映射目录（影响 docx2hub 与 MathType 扩展）。

---

## 3. xml2tex 配置详解（核心）

xml2tex 是“把 XML（Hub XML）映射为 LaTeX 文本”的可配置引擎。它先把配置（CSV 或 XML）转换为一份“用于文本输出的 XSLT”，再对 Hub XML 应用该 XSLT 以输出 TeX。

### 3.1 配置来源与合并

- CSV 快速映射：`docx2tex/conf/conf.csv:1` 示例演示“样式名 → LaTeX 结构”的简单映射（如 `Überschrift 1 → \chapter{…}`、`Zitat → quote 环境`）。
- XML 配置 DSL：`docx2tex/conf/conf.xml:1` 使用 `<xml2tex:set>` 提供更细粒度的控制（模板、样式、前后模板块）。
- 级联加载与校验：`docx2tex/xml2tex/xpl/xml2tex.xpl:1`
  - 使用 transpect 的 `cascade` 工具递归加载配置（支持 import/组合）。
  - 使用 Relax NG（`schema/xml2tex.rng`）对最终合并后的配置进行验证。

### 3.2 XML 配置 DSL 结构要点（见 `xml2tex/xsl/xml2tex.xsl`）

- 根元素：`<xml2tex:set>`，可包含：
  - `<xsl:import/>`、`<xsl:param/>`、`<xsl:key/>` 等 XSLT 声明（可扩展算法）。
  - `<xml2tex:preamble/>`：文档导言区；用于 `\documentclass`、`\usepackage` 等（默认导言见 `conf.xml`）。
  - `<xml2tex:front/>`、`<xml2tex:back/>`：可在正文前后拼接固定内容。
  - `<xml2tex:style name start end>`：基于“样式属性”的简单包裹映射（如 `Heading1 → \chapter{…}`）。
  - `<xml2tex:template context [name|priority]> … </xml2tex:template>`：基于 XPath 的上下文匹配，生成任意 LaTeX 文本或调用子模板；用于复杂结构（表格、图片、注释等）。
  - `<xml2tex:file href method encoding>`：将内容输出到独立文件（如生成 `*.tex` 的分片）。
  - `<xml2tex:regex>`：正则替换声明（由 XSLT 消化，参与生成器行为）。
- 模板优先级：
  - 如果存在多条匹配规则，按文档顺序后者覆盖前者（优先级更高）。
  - `<template @priority>` 可显式控制；`@name` 同名模板仅保留最后一个。
- 风格属性绑定：通过 `style-attribute`（在生成器中由 `@style-attribute` 读取）把 Hub XML 的样式属性（譬如 `@role`）与 `<style name>` 对齐。

### 3.3 关键参数与行为（`xml2tex.xpl` → `xml2tex.xsl`）

- `only-tex-body`：仅输出正文（不含 preamble / `\begin{document}`/`\end{document}`）。
- `table-model`：`tabular`（默认）/`tabularx`/`htmltabs`（通过 calstable 工具转换）。
- `table-grid` 与 `no-table-grid-*`：控制表格边框栅格输出与禁用条件（样式/role）。
- `nested-tables`：是否消解嵌套表格。
- `texmap-uri`：mml2tex 的 texmap 选择（影响数学符号映射）。
- `collect-all-xsl`：将所有匹配模板收集入生成样式表（便于调试）。
- `xslt-version`：生成器产出的 XSLT 版本（默认 2.0）。

### 3.4 字符映射与转义

- `conf.charmap.xml`：控制字符替换（特殊符号到 TeX 安全写法）。
- 生成器内置“坏字符”转义模板，确保输出中的 `\`, `_`, `%` 等敏感字符被正确处理。

### 3.5 示例（基于 DSL，非运行）

将段落样式 `Heading1` 映射为章节命令，普通段落为 `\par`：

```xml
<xml2tex:set xmlns="http://transpect.io/xml2tex">
  <preamble>
    \documentclass{scrbook}
    \usepackage[utf8]{inputenc}
  </preamble>
  <!-- 基于样式属性（如 Hub XML 的 @role） -->
  <style name="Heading1" start="\chapter{" end="}"/>
  <!-- 基于上下文匹配（XPath），更灵活 -->
  <template context="dbk:para[not(@role)]">
    <tex>\par </tex>
    <apply-templates/>
  </template>
</xml2tex:set>
```

> 提示：真实 Hub XML 的命名空间为 DocBook（`http://docbook.org/ns/docbook`，常前缀 `dbk`）。

---

## 4. evolve-hub 定制（核心）

evolve-hub 的作用是“让 Hub XML 更接近目标语义”，为 xml2tex 生成阶段提供更规整的数据结构。

### 4.1 driver 与模式（mode）

- 标准 driver：`docx2tex/xsl/evolve-hub-driver.xsl:1`（导入 transpect 官方 evolve-hub 规则，并追加 docx2tex 的预/后处理）。
- 常见模式（可在 `docx2tex/xpl/evolve-hub.xpl:1` 看到多次 `tr:xslt-mode` 调用）：
  - `hub:twipsify-lengths`：单位/长度归一化；
  - `hub:split-at-tab`：按制表符分割；
  - `hub:identifiers`：标识归一化、相邻同类分组；
  - 其他与标题、列表、注脚、链接、图表相关的模式（详见 driver 与 evolve-hub 上游文档）。

### 4.2 如何提供自定义 driver

- `custom-evolve-hub-driver` 端口（`docx2tex.xpl`）可传入你自己的 XSLT；推荐在自定义 XSLT 中 `xsl:import` 标准 driver 并在其之上覆写模板（保持升级兼容）。
- 官方示例：`docx2tex/xsl/custom-evolve-hub-driver-example.xsl:1`

```xml
<xsl:stylesheet version="3.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xpath-default-namespace="http://docbook.org/ns/docbook">
  <xsl:import href="http://transpect.io/docx2tex/xsl/evolve-hub-driver.xsl"/>
  <!-- 将空段落标记为 Heading1（示例用法） -->
  <xsl:template match="para[empty(node())]" mode="docx2tex-preprocess">
    <xsl:copy>
      <xsl:apply-templates select="@*"/>
      <xsl:attribute name="role" select="'Heading1'"/>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
```

### 4.3 在 evolve-hub 与 xml2tex 之间插入自定义 XSLT

- 使用 `docx2tex.xpl` 的 `custom-xsl` 选项，为进化后的 Hub XML 做项目化定制（如章节层级重排、列表修正规则、图片路径规范化等）。

### 4.4 常见定制点

- 列表识别与嵌套修正（`list-mode`）
- 标题层级与编号策略
- 图像与题注绑定/重命名路径（配合 `image-output-dir`）
- 脚注/交叉引用统一到便于 LaTeX 消化的结构
- 表格：选定 `table-model` 并在 Hub 层面清洗结构（合并/拆分单元格）

---

## 5. 可扩展挂接点（总结）

1) xml2tex 配置：CSV 映射或 XML DSL（`<style>`、`<template>`、`<preamble>` 等）。
2) evolve-hub 与 xml2tex 之间的 XSLT：`custom-xsl` 注入。
3) evolve-hub driver 定制：基于标准 driver 进行 import + 覆写。
4) 字体映射（fontmaps）：影响 docx2hub 与 MathType，目录由 `custom-font-maps-dir` 指定。
5) 数学：`mml2tex`（`xml2tex/conf.xml` 已 `xsl:import`），可通过 `texmap-uri` 选择映射表。

---

## 6. 反向生成 DOCX：路线与可行性评估

目标：从 Hub XML（或 xml2tex 的输入）生成 DOCX。这里给出方案比较与建议，不实现 PoC。

- 路线 A：Hub XML → WordprocessingML（XSLT 直接生成）→ 打包为 `.docx`
  - 优点：全链路可控；可做高保真元素级映射（段落 `w:p`、运行 `w:r`、样式 `w:style`、公式 `m:oMath`）。
  - 难点：WordprocessingML 结构复杂，对表格/样式/编号/分页/图像锚定等要求高；打包关系（`_rels`）与部件（`document.xml` 等）需完整生成。

- 路线 B：Hub XML → DocBook/HTML → Pandoc → DOCX
  - 优点：工程成本最低，生态成熟；适合快速验证往返的大致可行性。
  - 难点：细粒度样式与复杂表格/公式的忠实度依赖 Pandoc 的映射；需要对 Pandoc 的过滤器/模板二次定制。

- 路线 C：程序化构建（docx4j/POI XWPF 等）
  - 优点：调试友好，易于根据业务拆分模块；
  - 难点：开发量较大，需维护 Java/Kotlin 等代码与样式模板。

建议：以路线 B 做快速验证（建立“可出文档”的闭环）；如需高保真与可控性，再推进路线 A 或 C（A 偏声明式、C 偏命令式）。

---

## 7. 调试与排错建议（不运行，供参考）

- 打开调试：`debug`/`debug-dir-uri`，借助 `xproc-util/store-debug` 落盘每步产物与进度（`status`）。
- 读取与定位：对照 `docx2tex.xpl` 的每个 `tr:xslt-mode`/步骤名，逐步审阅 Hub XML 的演变。
- 校验配置：`xml2tex` 在加载合并配置后会用 Relax NG 校验，优先修正 schema 不满足项。
- 离线依赖：通过 `xmlcatalog` 配置将 `http://transpect.io/...` 的 XSL/XPL 映射到本地，避免网络波动。
- 字符与编码：优先 UTF-8；在 preamble 集中声明包与宏，保持输出一致性。

---

## 8. 参考文件索引（便于查阅源码）

- `docx2tex/xpl/docx2tex.xpl:1`（主入口，所有关键选项与挂接点）
- `docx2tex/xpl/evolve-hub.xpl:1`（evolve-hub 编排，remove-indents、各模式调用）
- `docx2tex/xsl/evolve-hub-driver.xsl:1`（标准 driver，含预/后处理导入）
- `docx2tex/xsl/custom-evolve-hub-driver-example.xsl:1`（自定义 driver 示例）
- `docx2tex/conf/conf.csv:1`、`docx2tex/conf/conf.xml:1`（默认 xml2tex 配置示例）
- `docx2tex/xml2tex/xpl/xml2tex.xpl:1`（配置加载/验证、生成与输出编排）
- `docx2tex/xml2tex/xsl/xml2tex.xsl:1`（将 XML 配置转为 XSLT 生成器）
- `docx2tex/xml2tex/xsl/mml2tex.xsl:1`（MathML → TeX 转换）

---

## 9. 后续工作建议

- 将 CSV 过渡到 XML DSL：在保证映射粒度的同时，集中管理 preamble 与复杂结构模板。
- 建立项目级自定义 driver：import 标准 driver，仅在需要的模式/模板上做精细覆写，降低升级成本。
- 分层管理挂接点：`custom-evolve-hub-driver`、`custom-xsl`、`xml2tex` 配置分别承载“结构归一化”、“项目特定变换”、“输出映射”。
- 若未来需要往返转换（DOCX ↔ Hub ↔ TeX），优先以路线 B 验证可行性，再根据精度要求选择 A/C。

