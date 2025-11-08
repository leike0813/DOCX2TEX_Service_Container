# API 参考（docx2tex-service�?
基础地址：`http://<host>:<port>`（默�?`http://127.0.0.1:8000`）�?

## 端点（Endpoints）
- `POST /v1/task`：提交转换任务（上传 DOCX 或提供 URL）
- `GET  /v1/task/{task_id}`：查询任务状态
- `GET  /v1/task/{task_id}/result`：下载结果 ZIP（任务完成后）
- `POST /v1/dryrun`：仅生成“有效 evolve driver”，不执行转换（用于调试 StyleMap 或自定义 evolve driver）
- `GET  /healthz`：健康检查
- `GET  /version`：服务版本信息


任务状态：`pending | running | converting | packaging | done | failed`�?
ZIP 内容�?- �?`debug=false`：仅�?`<basename>.tex` �?`image/`（仅拷贝被引用图片并重写路径）�?- �?`debug=true`：额外包�?`<basename>.xml`（Hub XML）、`<basename>.csv`（若有自动生成的 CSV 配置）、`<basename>.debug/`、`<basename>.docx.tmp/`、`logs/<task_id>.log`、`manifest.json`。若上传�?`custom_xsl`/`custom_evolve`、`fontmaps.zip` 会一并包含；使用�?StyleMap 时会包含 `stylemap_manifest.json`�?
缓存键：�?`(DOCX, conf(或默�?, custom_xsl(或无), custom_evolve(或无), MathTypeSource, TableModel, FontMapsZip 内容)` �?SHA-256 计算；与 `debug`、`img_post_proc` 无关�?
---

## 1）提交任�?�?`POST /v1/task`

Content-Type：`multipart/form-data`

字段（`file`/`url` 二选一，其他可选）�?- `file`：待转换�?DOCX（`application/vnd.openxmlformats-officedocument.wordprocessingml.document`）�?- `url`：远�?DOCX 下载地址（服务端下载到临时目录并参与缓存计算）�?- `debug`：`true|false`，是否包含完整中间产物（默认 `false`）�?- `img_post_proc`：`true|false`，是否对 EMF/WMF/SVG 做矢量转 PDF 并重�?TeX 引用（默�?`true`）�?- `conf`：xml2tex 配置（XML）。若缺省则使用内置默认配置。相对写�?`<import href="conf.xml"/>` 会被规范化为容器内默认配置的绝对 URI�?- `custom_xsl`：位�?evolve-hub �?xml2tex 之间的自定义 XSL（XML）�?- `custom_evolve`：自定义�?evolve-hub driver XSL（XML）�?- `StyleMap`：JSON 字符串，描述“可见样式名 �?规范角色”的映射，并驱动对应�?LaTeX 命令注入；见示例�?- `MathTypeSource`：`ole | wmf | ole+wmf`�?- `TableModel`：`tabularx | tabular | htmltabs`�?- `FontMapsZip`：自定义 fontmaps �?ZIP；服务会解压并通过 `custom-font-maps-dir` 传给管线�?
成功响应（HTTP 200）：
```json
{
  "task_id": "<uuid>",
  "cache_key": "<sha256>",
  "cache_status": "HIT|BUILDING|MISS"
}
```

错误�?00（参数错误）�?13（上传过大）�?00（服务内部错误）�?
示例（cURL）：
```bash
curl -sS -X POST http://127.0.0.1:8000/v1/task \
  -F "file=@examples/forward/example_forward.docx;type=application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
  -F "conf=@conf/conf-ctexbook-zh.xml;type=application/xml" \
  -F "debug=true" -F "img_post_proc=true" \
  -F "StyleMap={\"Title\":\"主标题\",\"Heading1\":\"I级标题\",\"Heading2\":\"II级标题\",\"Heading3\":\"III级标题\"}" \
  -F "MathTypeSource=ole+wmf" \
  -F "TableModel=tabularx"
```

PowerShell（内置脚本）�?```powershell
. .\test\test_docx2tex.ps1
$style = '{"Title":"主标�?,"Heading1":"I级标�?,"Heading2":"II级标�?,"Heading3":"III级标�?}'
$r = Invoke-Docx2Tex -Server http://127.0.0.1:8000 `
  -File .\examples\forward\example_forward.docx `
  -Conf .\conf\conf-ctexbook-zh.xml `
  -IncludeDebug:$true -ImgPostProc:$true `
  -StyleMap $style -MathTypeSource ole+wmf -TableModel tabularx
```

关于 StyleMap�?- 作用：将 Word 中“可见样式名”（如“主标题/I级标题”等）统一到规范角�?`Title/Heading1/Heading2/Heading3`，并根据所�?`conf` 注入对应 LaTeX 命令�?- 实现：服务端生成“有效”的 evolve-driver/XSL 片段，并通过处理指令输出原样 LaTeX，避免反斜杠转义问题�?- 范围：仅影响 `conf` 中实际出现的角色；StyleMap 中多余键会被忽略�?
---

## 2）查询任务状�?�?`GET /v1/task/{task_id}`

响应（HTTP 200）：
```json
{
  "code": 0,
  "data": {
    "task_id": "<uuid>",
    "state": "pending|running|converting|packaging|done|failed",
    "err_msg": "",
    "start_time": 1730870000.0,
    "end_time": 1730870012.0
  },
  "msg": "ok"
}
```

错误�?04（任务不存在）�?
---

## 3）下载结�?�?`GET /v1/task/{task_id}/result`

成功：HTTP 200，`application/zip`（文件名 `<basename>.zip`）�?
错误�?09（未就绪）�?04（不存在）�?
---

## 4）Dry-run – `POST /v1/dryrun`

仅构建有效的 evolve-driver 配置，不运行完整 docx2tex 流程；用于验证 StyleMap 与自定义 evolve driver 的拼装。

字段：`conf`、`custom_evolve`、`StyleMap`

返回：ZIP，包含 `xsl/custom-evolve-effective.xsl`（若生成）以及 `stylemap_manifest.json`

示例：```bash
curl -sS -X POST http://127.0.0.1:8000/v1/dryrun \
  -F "conf=@conf/conf-ctexbook-zh.xml;type=application/xml" \
  -F "StyleMap={\"Title\":\"主标题\",\"Heading1\":\"I级标题\",\"Heading2\":\"II级标题\",\"Heading3\":\"III级标题\"}" \
  -o dryrun_xsls.zip
```

---

## 打包细节
- `debug=false`：仅包含 `<basename>.tex` 与被引用图片 `image/`�?- `debug=true`：额外包�?Hub XML/CSV/debug 目录/日志/manifest；若上传�?`custom_xsl`/`custom_evolve` 会打包；提供�?`fontmaps.zip` 会打包；使用�?StyleMap 会附�?`stylemap_manifest.json`�?
## 缓存与并�?- 缓存键：`(DOCX, conf, custom_xsl, custom_evolve, MathTypeSource, TableModel, FontMapsZip 内容)` �?SHA-256�?- 命中缓存：跳过转换阶段，直接从缓存恢复，然后仍会执行图片后处理与打包�?- 并发锁：每个 `cache_key` 仅一个构建者；其他提交等待，锁过期后可接管构建�?- 自愈发布：若 DB 记录缺失但磁盘缓存存在，服务会自动补发布�?
## 环境与限�?- `TTL_DAYS`：任务与缓存过期时间（默�?7）�?- `LOCK_SWEEP_INTERVAL_SEC` / `LOCK_MAX_AGE_SEC`：并发锁 GC 设置�?- `MAX_UPLOAD_BYTES`：最大上传大小（字节）�?- `UVICORN_WORKERS`：进程数（默�?2）�?- `XML_CATALOG_FILES`：XML catalog 路径（默�?`/opt/catalog/catalog.xml`）�?
## 关于 FontMaps 的说�?- 自定�?fontmaps 对于�?Unicode 旧式字体（Symbol/Wingdings/MT Extra/MathType OLE）更容易观察到效果；对普�?Unicode 文本可能没有可见变化�?- 测试�?MathType 相关�?fontmaps 时，建议选择 `MathTypeSource=ole` �?`ole+wmf`�?
