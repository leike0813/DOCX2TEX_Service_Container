## docx2tex-service（容器使用说明）

一个可离线运行的 DOCX → TeX 转换服务容器。镜像内置 docx2tex、Java（Calabash）、Inkscape（矢量转 PDF）、缓存与清理逻辑，并通过 HTTP API 对外提供服务。

### 特性一览
- 可离线：依赖在镜像构建时打包，已配置 XML catalog。
- 打包可控：`debug=false` 仅输出 `.tex` + 被引用图片；`debug=true` 输出所有中间产物。
- 矢量图后处理：将 EMF/WMF/SVG 转为 PDF，并改写 TeX 引用（可选）。
- StyleMap（样式映射表）：将 Word 可见样式名映射为规范角色（`Title/Heading1..3`），并按 xml2tex 配置注入对应的 LaTeX 命令（服务端动态生成 XSL）。
- 接口完整：支持 `StyleMap`、`MathTypeSource (ole|wmf|ole+wmf)`、`TableModel (tabularx|tabular|htmltabs)`、`FontMapsZip`。
- 缓存与并发：基于输入构建 SHA-256 缓存键，具备并发锁与自愈发布能力。

### 构建镜像
```bash
docker build -t docx2tex-svc:latest .
```

镜像包含 Debian bookworm-slim、OpenJDK 17、Inkscape、sqlite3、docx2tex，以及带 FastAPI/uvicorn 的 Python venv。

### 运行容器
为服务私有状态使用命名卷，为结果输出绑定主机目录：

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
- `/data` 为服务私有工作区（上传、缓存、DB、临时文件），推荐使用命名卷。
- `/work` 仅包含结果 ZIP，由你自行管理生命周期。

### 环境变量（部分）
- `TTL_DAYS`（默认 7）：任务与缓存的过期时间。
- `LOCK_SWEEP_INTERVAL_SEC`（默认 120）、`LOCK_MAX_AGE_SEC`（默认 1800）：并发锁 GC 设置。
- `MAX_UPLOAD_BYTES`：上传大小上限（字节）；0/空表示不限。
- `UVICORN_WORKERS`（默认 2）：进程数。
- `XML_CATALOG_FILES`（默认 `/opt/catalog/catalog.xml`）。

### 快速调用示例
cURL 上传：
```bash
curl -sS -X POST http://127.0.0.1:8000/v1/task \
  -F "file=@examples/forward/example_forward.docx;type=application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
  -F "conf=@conf/conf-ctexbook-zh.xml;type=application/xml" \
  -F "debug=false" -F "img_post_proc=true"

curl -sS http://127.0.0.1:8000/v1/task/<task_id>

curl -sS -o result.zip http://127.0.0.1:8000/v1/task/<task_id>/result
```

PowerShell（内置脚本）：
```powershell
. .\test\test_docx2tex.ps1
$style = '{"Title":"主标题","Heading1":"I级标题","Heading2":"II级标题","Heading3":"III级标题"}'
$r = Invoke-Docx2Tex -Server http://127.0.0.1:8000 `
  -File .\examples\forward\example_forward.docx `
  -Conf .\conf\conf-ctexbook-zh.xml `
  -IncludeDebug:$true -ImgPostProc:$true `
  -StyleMap $style -MathTypeSource ole+wmf -TableModel tabularx
```

仅 Dry-run（只构建有效 XSL，便于调试 StyleMap）：
```bash
curl -sS -X POST http://127.0.0.1:8000/v1/dryrun \
  -F "conf=@conf/conf-ctexbook-zh.xml;type=application/xml" \
  -F "StyleMap={\"Title\":\"主标题\",\"Heading1\":\"I级标题\",\"Heading2\":\"II级标题\",\"Heading3\":\"III级标题\"}" \
  -o dryrun_xsls.zip
```

### 缓存与打包
- 缓存键：`(DOCX, conf, custom_xsl, custom_evolve, MathTypeSource, TableModel, FontMapsZip 内容)`。
- `debug=false`：ZIP 仅包含 `<basename>.tex` 与 `image/`。
- `debug=true`：ZIP 还包含 Hub XML/CSV/debug 目录/日志/manifest；若上传了 `custom_xsl`/`custom_evolve` 会打包；提供了 `fontmaps.zip` 会打包；使用了 StyleMap 会附带 `stylemap_manifest.json`。

更多 API 细节见 `docs/API_DOC.md`。
