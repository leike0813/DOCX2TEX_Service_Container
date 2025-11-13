## docx2tex_inverse

面向开源项目 docx2tex 的深入解析与服务化封装。项目在保持上游能力的基础上，进行工程化重构与增强，提供可离线、可配置、可扩展的 DOCX → LaTeX（TeX）转换服务。

参考文档：
- 架构说明：`docs/architecture.md`
- API 文档：`docs/API_DOC.md`

---

### 核心特性
- 处理流水线：docx2hub → evolve‑hub → xml2tex；校准与扩展点完整暴露。
- 服务封装：基于 FastAPI，提供上传（/v1/task）、状态查询、结果下载与 Dry‑run 接口。
- 工程增强：
  - 缓存与并发锁：SHA‑256 缓存键 + 锁表协调；缓存自愈发布。
  - 清理策略：统一 TTL（天）控制任务与缓存过期，安全两阶段删除。
  - StyleMap：仅通过 evolve‑driver 注入（不再生成独立 custom‑xsl），自动把 Word“可见样式”规范化并按配置注入 LaTeX。
  - 后处理：矢量图（EMF/WMF/SVG）转 PDF 并改写引用；VSDX 引用删除/注释；宽度参数标准化；非调试模式自动收集图片到 image/ 并改写路径。

---

### 处理流水线（简要）
1) docx2hub：将 DOCX 解包并转换为 Hub XML（DocBook 语义）。
2) evolve‑hub：结构归一化与语义提升（列表、章节层级、图题绑定、上下标等）。
3) xml2tex：基于配置（conf）生成 XSLT，把（进化后的）Hub XML 输出为 LaTeX 文本。

自定义挂接点：
- xml2tex 配置（conf/）
- evolve‑driver（custom_evolve；StyleMap 会生成 `custom-evolve-effective.xsl`）
- evolve→xml2tex 之间的 XSL（可选；StyleMap 路线不再输出独立 custom‑xsl）
- 字体映射（fontmaps）

---

### 仓库结构（重构后）
- `app/`
  - `server.py`：应用入口，挂载路由，启动清理与锁回收
  - `api/`：对外路由（`/v1/*`、`/healthz`、`/version`）
  - `services/`：任务编排（`JobManager`）
  - `core/`：通用能力模块
    - 配置/数据：`config`、`db`、`models`、`tasks`
    - 缓存/并发：`cache`、`cleanup`
    - 工具：`storage`、`logging`、`proc`、`convert`
    - 关键增强：`postprocess`（图片收集/改写、VSDX 处理、宽度标准化、矢量转 PDF）、`stylemap`（仅 evolve‑driver 注入）
- `docs/`：`overview-zh.md`、`API_DOC.md`、`architecture.md`
- `tests/`：单元与路由测试（路由测试需 httpx）
- 其余：`conf/`（xml2tex 配置）、`catalog/`（XML catalog）、`docx2tex/`（上游源码）、`Dockerfile`、`cmd_client/docx2tex_client.ps1`

---

### 打包行为（与模式相关）
- Debug=false：
  - 仅打包 `<base>.tex` 与 `image/`；在打包前收集被引用图片到 `image/` 并改写 TeX 引用路径；删除 `.vsdx` 引用；标准化 `width=\textwidth/\linewidth`。
- Debug=true：
  - 打包 `.tex/.xml`、`<base>.debug/`、`<base>.docx.tmp/`、`logs/<task_id>.log`、`xsl/custom-evolve-effective.xsl`（若存在）、`stylemap_manifest.json`（若存在）；对 `.vsdx` 行注释并标准化宽度。

两个模式的 manifest.json 均包含 `files` 列表；debug=false 的图片清单来自 `image/`，debug=true 包含调试产物与日志/有效 XSL/manifest 等。

---

### StyleMap 注入策略
- 仅通过 evolve‑driver 注入（不生成独立 output‑layer custom‑xsl）。
- 路由层在收到 StyleMap 后，会生成 `custom-evolve-effective.xsl` 并参与后续管线；同时写入 `stylemap_manifest.json` 便于诊断。

---

### 缓存与并发
- 缓存键：`SHA256(DOCX + conf + custom_xsl + custom_evolve + MathTypeSource + TableModel + FontMapsZip)`
  - 与 `debug`、`img_post_proc` 无关（最大化复用）。
- 并发与自愈：锁表协调同键任务的构建；磁盘存在/DB 缺失会自动补发布。
- 清理：按 `TTL_DAYS` 定期清理任务与缓存（安全两阶段删除）。

---

### API 端点
- `POST /v1/task`：提交转换任务
- `GET  /v1/task/{task_id}`：查询任务状态
- `GET  /v1/task/{task_id}/result`：下载结果 ZIP
- `POST /v1/nocache`：提交任务并绕过缓存
- `POST /v1/dryrun`：生成有效 evolve driver（不跑完整流程）
- `GET  /healthz`：健康检测
- `GET  /version`：版本信息

> 服务端会对 `file`/`conf`/`custom_xsl`/`custom_evolve` 文件名做 ASCII+safe_name 规范化，避免 Calabash 报错；`debug=false` 时可通过 `image_dir` 指定图片目录，TeX 中的 `\includegraphics` 也会重写所指向的目录。

---

### 快速开始
构建镜像：
```bash
docker build -t docx2tex-svc:latest .
```

运行（建议将私有数据放入命名卷，公开结果目录 `/work` 到宿主机）：
```bash
docker volume create docx2tex_data
docker run --rm -p 8000:8000 \
  -v docx2tex_data:/data \
  -v "$(pwd)/work:/work" \
  -e TTL_DAYS=7 \
  --name docx2tex-svc \
  docx2tex-svc:latest
```

PowerShell 客户端（可选）：
```powershell
. .\test\test_docx2tex.ps1
Invoke-Docx2Tex -Server http://127.0.0.1:8000 -File .\examples\forward\example_forward.docx -IncludeDebug:$false -ImgPostProc:$true -OutFile .\result.zip
```

---

### 环境变量（常用）
- `TTL_DAYS`（默认 7）：任务与缓存的统一过期时间（天）。
- `UVICORN_WORKERS`（默认 2）：进程数。
- `MAX_UPLOAD_BYTES`：上传大小上限（字节；0 或空表示不限制）。
- `XML_CATALOG_FILES`（默认 `/opt/catalog/catalog.xml`）：XML catalog 路径。

---

### 开发与测试
- 运行单元测试：
```bash
python -m pip install pytest
pytest -q
```
- 路由测试（可选，需 httpx）：
```bash
python -m pip install httpx
pytest -q
```

---

## 感谢

伟大且专业的开源项目：[docx2tex](https://github.com/transpect/docx2tex)