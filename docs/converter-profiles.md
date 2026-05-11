# Converter Profiles

## 当前正式矩阵 Profile

### `docx_to_latex@docx2tex`

- `docx_to_latex/docx2tex-book-en`
- `docx_to_latex/docx2tex-ctexart`
- `docx_to_latex/docx2tex-ctexbook`
- `docx_to_latex/docx2tex-elsarticle`

这些 profile 映射到 `src/engines/docx2tex_engine/assets/conf/` 下的受控配置入口。

### `docx_to_latex@pandoc`

- `docx_to_latex/pandoc-default`

### `latex_to_docx@pandoc`

- `latex_to_docx/pandoc-auto`
- `latex_to_docx/pandoc-ctexart`
- `latex_to_docx/pandoc-ctexbook`
- `latex_to_docx/pandoc-elsarticle`

### `latex_to_markdown@pandoc`

- `latex_to_markdown/pandoc-default`
  - 当前只作为规划中的 profile 暴露，任务提交会返回 `501`

## 选项 Preset

### `custom_xsl`

- `none`
- `force-zh-cn-lang`

### `TableModel`

- `tabularx`
- `tabular`
- `htmltabs`

### `MathTypeSource`

- `ole`
- `wmf`
- `ole+wmf`

## 设计约束

- profile 是 path-scoped 的平台级概念
- profile 隐式绑定 engine，用户不直接提交 `engine_id`
- `pandoc` 与 `docx2tex` 使用同一平台注册表暴露 profile
- 前端应读取 `/v1/profiles`，而不是写死表单选项
