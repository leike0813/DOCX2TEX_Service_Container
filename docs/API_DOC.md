# API 参考（docx2tex-service）

文档约定：服务根 URL 记为 `http://<host>:<port>`（默认 `http://127.0.0.1:8000`）。

## 概览

- 统一资源
  - `POST /v1/task`：提交转换任务（上传 DOCX 或提供 URL），可选 conf/custom-xsl，返回 task_id 与缓存信息
  - `GET  /v1/task/{task_id}`：查询任务状态
  - `GET  /v1/task/{task_id}/result`：下载结果 ZIP（任务完成后）
  - `GET  /healthz`：健康检查
  - `GET  /version`：镜像版本/路径信息

- 任务状态：`pending | running | converting | packaging | done | failed`
- 压缩包内容：
  - `debug=false`：`<basename>.tex` + `image/`（仅被引用图片，路径已重写）
  - `debug=true`：另含 `<basename>.xml`、`<basename>.csv`、`<basename>.debug/`、`<basename>.docx.tmp/`、日志、`manifest.json`

- 缓存键（cache_key）：由 (DOCX 内容, conf 内容(或默认), custom-xsl 内容或无) 三元组计算。与 `debug` 与 `img_post_proc` 无关。
  - `cache_status`：`HIT`（已可复用）| `BUILDING`（正在构建）| `MISS`（尚无缓存）

## 1. 提交任务

`POST /v1/task`

Content-Type：`multipart/form-data`

表单字段（二选一 + 可选项）：

- `file`（二选一）：要转换的 DOCX 文件（content-type 建议：`application/vnd.openxmlformats-officedocument.wordprocessingml.document`）
- `url`（二选一）：DOCX 下载地址（服务会下载到临时目录参与缓存计算）
- `debug`（可选，默认 `false`）：是否输出所有中间产物
- `img_post_proc`（可选，默认 `true`）：是否开启图像后处理（EMF/WMF/SVG → PDF 并更新 TeX 引用）
- `conf`（可选）：xml2tex 配置文件（将参与缓存键计算）
- `custom_xsl`（可选）：介入 evolve-hub 与 xml2tex 之间的 XSLT（将参与缓存键计算）

成功响应（HTTP 200）：

```json
{
  "task_id": "<uuid>",
  "cache_key": "<sha256>",
  "cache_status": "HIT|BUILDING|MISS"
}
```

错误响应：
- 400：参数错误（同时提供/缺失 `file` 与 `url`）
- 413：上传文件超限（若设置了 `MAX_UPLOAD_BYTES`）

示例（cURL）：

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/task \
  -F "file=@examples/forward/example_forward.docx;type=application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
  -F "debug=false" -F "img_post_proc=true"
```

## 2. 查询任务状态

`GET /v1/task/{task_id}`

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

错误响应：
- 404：任务不存在

## 3. 下载结果 ZIP

`GET /v1/task/{task_id}/result`

成功：HTTP 200，`Content-Type: application/zip`，文件名 `<basename>.zip`。

错误：
- 409：任务未完成（返回状态说明）
- 404：任务不存在或结果缺失

## 4. 健康与版本

- `GET /healthz` → `{ "status": "ok" }`
- `GET /version` → `{ "service": "docx2tex-service", "docx2tex_home": "/opt/docx2tex" }`

## 打包细节

- `debug=false`：
  - 仅包含 `<basename>.tex` 与 `image/` 目录（解析 .tex 引用，复制实际引用图片并重写路径）
- `debug=true`：
  - 额外包含：
    - `<basename>.xml`（Hub XML）
    - `<basename>.csv`（自动生成的配置）
    - `<basename>.debug/`（全量调试输出）
    - `<basename>.docx.tmp/`（从 DOCX 解压的资源）
    - `logs/<task_id>.log`（服务侧日志）
    - `manifest.json`（清单）

## 缓存与并发

- 缓存键：由 (DOCX, conf, custom-xsl) 三者内容哈希（SHA-256）计算；与 `debug`、`img_post_proc` 无关。
- 命中后：跳过 docx2tex 解析，直接从缓存恢复，再执行图片后处理与打包。
- 构建锁：同一键同时提交仅一个构建者；其他提交短时等待已发布缓存，或在锁过期后接管构建。
- 自愈：若 DB 记录缺失但磁盘缓存完整，会自动补发布；关键操作均有日志。

## 统一清理策略

- `TTL_DAYS` 控制任务与缓存的过期清理（默认 7 天）。
- 依据 `last_access`（或 `created`）判定；缓存删除采用“先标记不可用 → 删目录 → 删 DB 记录”的两阶段策略避免不一致。

## 错误码与常见问题

- 400：请求参数错误；确保 `file` 和 `url` 仅二选一
- 409：结果未就绪；继续轮询状态
- 413：上传超限；调大 `MAX_UPLOAD_BYTES` 或缩小文件
- 500：任务失败；检查 ZIP（debug 模式）或服务端日志 `/var/log/docx2tex/<task_id>.log`

