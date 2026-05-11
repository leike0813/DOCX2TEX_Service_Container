# API Reference

## 1. Platform Endpoints

### `GET /v1/capabilities`

返回平台当前可见的能力矩阵单元。

示例响应：

```json
{
  "capabilities": [
    {
      "path_id": "docx_to_latex",
      "engine_id": "docx2tex",
      "source_format": "docx",
      "target_format": "latex",
      "status": "implemented"
    },
    {
      "path_id": "latex_to_docx",
      "engine_id": "pandoc",
      "source_format": "latex",
      "target_format": "docx",
      "status": "implemented"
    }
  ],
  "matrix": {
    "paths": [
      {
        "path_id": "docx_to_latex",
        "source_format": "docx",
        "target_format": "latex"
      }
    ]
  }
}
```

### `GET /v1/profiles`

返回 path-scoped profiles 和兼容 WebUI 的 docx->latex 默认选项。

关键字段：

- `profiles`
- `profiles_by_path`
- `option_presets.custom_xsl`
- `option_presets.table_model`
- `option_presets.math_type_source`
- `defaults`

### `POST /v2/tasks`

平台化任务提交接口，当前正式支持：

- `docx -> latex@docx2tex`
- `docx -> latex@pandoc`
- `latex -> docx@pandoc`

`multipart/form-data` 字段：

- `file` 或 `url`
- `source_format`
- `target_format`
- `profile_id`
- `debug`
- `img_post_proc`
- `conf`
- `custom_xsl`
- `custom_xsl_preset`
- `custom_evolve`
- `StyleMap`
- `MathTypeSource`
- `TableModel`
- `FontMapsZip`
- `image_dir`
- `main_tex`
- `reference_doc_id`
- `numbering_metadata_id`
- `lua_filter_ids`
- `exec_filter_ids`
- `top_level_division`
- `citeproc`
- `csl_id`
- `bibliography_paths`

当前建议的首选调用方式：

```bash
curl -X POST http://127.0.0.1:8000/v2/tasks \
  -F "file=@sample.docx" \
  -F "source_format=docx" \
  -F "target_format=latex" \
  -F "profile_id=docx_to_latex/docx2tex-ctexbook" \
  -F "custom_xsl_preset=none" \
  -F "TableModel=tabularx" \
  -F "MathTypeSource=ole+wmf"
```

`latex -> docx@pandoc` 示例：

```bash
curl -X POST http://127.0.0.1:8000/v2/tasks \
  -F "file=@workspace.zip" \
  -F "source_format=latex" \
  -F "target_format=docx" \
  -F "profile_id=latex_to_docx/pandoc-auto" \
  -F "reference_doc_id=article-default" \
  -F "numbering_metadata_id=zh-default" \
  -F "exec_filter_ids=[\"pandoc-tex-numbering\"]" \
  -F "lua_filter_ids=[\"caption-colon-to-space\"]" \
  -F "top_level_division=section" \
  -F "citeproc=false"
```

### `GET /v2/tasks/{task_id}`

返回平台任务状态：

- `pending`
- `running`
- `converting`
- `packaging`
- `done`
- `failed`

### `GET /v2/tasks/{task_id}/result`

任务完成后返回 ZIP 结果。

### `POST /v2/dryrun`

生成有效的 evolve driver 诊断包，不执行完整转换。

字段：

- `conf`
- `custom_evolve`
- `StyleMap`

成功时返回 ZIP，至少包含：

- `xsl/custom-evolve-effective.xsl`
- `stylemap_manifest.json`

## 2. Utility Endpoints

### `GET /`

返回内置 WebUI。

### `GET /healthz`

健康检查。

### `GET /version`

返回服务版本与运行时路径信息。

## 3. Removed Legacy Endpoints

以下接口在第二阶段基础设施下沉后已移除：

- `POST /v1/task`
- `GET /v1/task/{task_id}`
- `GET /v1/task/{task_id}/result`
- `GET /v1/ui/presets`
- `POST /v1/dryrun`
