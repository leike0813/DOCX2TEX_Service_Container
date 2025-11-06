## docx2tex-service 容器使用说明

一个可离线运行的 docx→TeX 转换服务容器，内置 docx2tex、Java（calabash）、Inkscape（将 EMF/WMF/SVG 转为 PDF）以及缓存/清理机制。对外提供 HTTP API，支持上传 DOCX、可选传入 conf/custom-xsl，返回打包好的 ZIP（仅 .tex + 引用图片 或 全量调试产物）。

关键特性
- 离线运行：构建镜像时克隆依赖，运行期无网络依赖；设置了 `XML_CATALOG_FILES`。
- 可控打包：`debug=false` 仅输出 .tex 与被引用的图片；`debug=true` 输出所有中间产物（.xml、.csv、.debug、.docx.tmp、日志、manifest）。
- 图像后处理：可选开启 Inkscape 将 EMF/WMF/SVG 转 PDF 并更新 TeX 引用。
- 去重缓存：以 (docx, conf, xsl) 内容哈希作为缓存键，自动命中复用；并发提交有锁协调，自愈逻辑保证健壮性。
- 清理策略：统一 `TTL_DAYS` 控制任务与缓存清理，以 last_access/created 判定。

### 构建镜像

```bash
docker build -t docx2tex-svc:latest .
```

镜像已内置：
- Debian bookworm-slim（APT 源、pip 源已切换至清华镜像）
- openjdk-17-jre-headless, inkscape, sqlite3
- docx2tex（构建时 `--recursive` 克隆）
- Python venv + FastAPI/uvicorn

### 运行容器

推荐：为私有数据使用“命名卷”（不可直接被主机文件系统访问）；将对外可见的结果文件夹 `/work` 绑定到宿主机目录。

```bash
docker volume create docx2tex_data
docker run --rm -p 8000:8000 \
  -v docx2tex_data:/data \
  -v "$(pwd)/work:/work" \
  -e TTL_DAYS=7 \
  --name docx2tex-svc \
  docx2tex-svc:latest
```

Windows（PowerShell）：

```powershell
docker volume create docx2tex_data
docker run --rm -p 8000:8000 `
  -v docx2tex_data:/data `
  -v "D:\\docx2tex-work:/work" `
  -e TTL_DAYS=7 `
  --name docx2tex-svc `
  docx2tex-svc:latest
```

说明：
- `/data` 为服务的私有数据卷（上传文件、缓存、SQLite 数据库、任务中间文件）；使用命名卷即避免直接文件访问。
- `/work` 为仅包含最终 ZIP 的公共目录，建议绑定宿主机目录便于取回结果；其清理由用户自管，服务不会清理。

### 环境变量（部分）

- `TTL_DAYS`（默认 7）：统一控制任务与缓存的清理 TTL；当未设置且 `/data` 是挂载点时，默认不清理。
- `LOCK_SWEEP_INTERVAL_SEC`（默认 120）：过期构建锁的清扫频率。
- `LOCK_MAX_AGE_SEC`（默认 1800）：锁的最大保留秒数。
- `MAX_UPLOAD_BYTES`：上传大小上限（字节）；0 或空表示不限制。
- `UVICORN_WORKERS`（默认 2）：服务进程数。
- `XML_CATALOG_FILES`（默认 `/opt/catalog/catalog.xml`）：XML catalog 路径。

### 健康检查

- `GET /healthz` → `{ "status": "ok" }`
- `GET /version` → 镜像信息（含 docx2tex 路径）

### 快速调用示例

cURL（上传文件）：

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/task \
  -F "file=@examples/forward/example_forward.docx;type=application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
  -F "debug=false" -F "img_post_proc=true"
# 响应: {"task_id":"...","cache_key":"...","cache_status":"HIT|BUILDING|MISS"}

curl -sS http://127.0.0.1:8000/v1/task/<task_id>
# {"code":0, "data":{"state":"pending|running|converting|packaging|done|failed", ...}}

curl -sS -o result.zip http://127.0.0.1:8000/v1/task/<task_id>/result
```

PowerShell 5.1（使用内置脚本）：

```powershell
. .\test\test_docx2tex.ps1
$r = Invoke-Docx2Tex -Server http://127.0.0.1:8000 `
  -File .\examples\forward\example_forward.docx `
  -IncludeDebug:$false -ImgPostProc:$true `
  -OutFile .\result.zip
# 输出对象包含 TaskId / CacheKey / CacheStatus / Zip
```

### 缓存与打包

- 缓存键：由 (DOCX 内容, conf 内容(或默认), custom-xsl 内容或无) 三元组计算。
- 与 `debug`、图像后处理无关；命中后仍会执行“图片后处理 + 打包”。
- `debug=false`：ZIP 包含 `<basename>.tex` + `image/`（仅被引用图片，路径已重写）。
- `debug=true`：ZIP 额外包含 `<basename>.xml`、`<basename>.csv`、`<basename>.debug/`、`<basename>.docx.tmp/`、日志、`manifest.json`。

更多 API 细节见 `docs/API_DOC.md`。

