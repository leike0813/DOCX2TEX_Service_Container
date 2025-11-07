## docx2tex_inverse

面向 docx2tex 的深入解析与二次封装项目。
- 文档解析：梳理 docx2tex 的处理流水线（docx2hub → evolve-hub → xml2tex）、配置与定制点（conf、自定义 XSL）。
- 服务封装：提供一个可离线运行的容器化 API 服务（FastAPI），对外暴露上传/查询/下载接口，自动打包结果。
- 工程增强：内置缓存、并发锁、自愈与统一清理策略；内置 Inkscape 将 EMF/WMF/SVG 转为 PDF 并更新 TeX 引用。

### 仓库结构
- `app/`：服务端实现（FastAPI，`server.py`，`entrypoint.sh`，`requirements.txt`）。
- `app/scripts/`：
  - `convert_vector_images.py`：将 EMF/WMF/SVG 转为 PDF 并改写 TeX 引用。
  - `pack_tex_with_images.py`：在非调试模式下，仅打包被引用图片到 `image/` 并改写引用路径。
- `docx2tex/`：上游项目源码（用于本仓库的解析与封装）。
- `catalog/`：XML catalog（镜像构建时复制至 `/opt/catalog`）。
- `conf/`：默认 xml2tex 配置集（详见“默认配置”）。
- `docs/`：
  - `overview-zh.md`：docx2tex 原理与要点。
  - `API_DOC.md`：服务 API 参考。
- `test/test_docx2tex.ps1`：PowerShell 5.1 示例客户端（上传/轮询/下载）。
- `Dockerfile`：可离线的服务镜像构建文件。

### 快速开始
构建镜像：
```bash
docker build -t docx2tex-svc:latest .
```

运行（建议）：将私有数据放入命名卷（宿主不可直接访问），公开结果目录 `/work` 到宿主机。
```bash
docker volume create docx2tex_data
docker run --rm -p 8000:8000 \
  -v docx2tex_data:/data \
  -v "$(pwd)/work:/work" \
  -e TTL_DAYS=7 \
  --name docx2tex-svc \
  docx2tex-svc:latest
```

调用 API：见 `docs/API_DOC.md`；或使用 `test/test_docx2tex.ps1`。
```powershell
. .\test\test_docx2tex.ps1
Invoke-Docx2Tex -Server http://127.0.0.1:8000 -File .\examples\forward\example_forward.docx -IncludeDebug:$false -ImgPostProc:$true -OutFile .\result.zip
```

### 关键设计
- 缓存键：对 `(DOCX, conf, custom_xsl, custom_evolve, MathTypeSource, TableModel, FontMapsZip)` 进行 SHA-256 计算；与 `debug`、`img_post_proc` 无关。
- 并发锁：同键任务并发时仅一个执行构建，其他等待已发布缓存或在锁过期后接管。
- 自愈机制：若 DB 记录缺失但磁盘缓存存在，自动补发布；关键步骤均追加日志。
- 清理策略：`TTL_DAYS` 统一控制任务与缓存清理，按 `last_access/created` 判断；缓存删除采用两阶段策略避免不一致。

### 新增能力：样式映射表（StyleMap）
- 在调用接口时通过 `StyleMap`（JSON 字符串）传入 Word 中“可见样式名”到规范角色（`Title/Heading1/Heading2/Heading3`）的映射。
- 服务端根据当前使用的 xml2tex 配置自动生成“有效的 evolve-driver/XSL 片段”，实现：
  - 预处理阶段：将 `para/@role` 统一改写成规范角色名。
  - 按配置将规范角色映射为 LaTeX 命令，并以不会被转义的方式注入。
- 仅对配置中出现的角色生效；`StyleMap` 中多余键会被忽略。

### 默认配置（conf/）
- `conf-ctexart-zh.xml`：中文文章类（ctexart）。
- `conf-ctexbook-zh.xml`：中文书籍类（ctexbook）。
- `conf-elsarticle-en.xml`：英文期刊类（elsarticle）。
- `conf-book-en.xml`：英文书籍类（book）。

> 提示：还可结合 `MathTypeSource`（`ole|wmf|ole+wmf`）、`TableModel`（`tabularx|tabular|htmltabs`）、`FontMapsZip` 使用；详见 `docs/API_DOC.md`。

## 感谢

伟大且专业的开源项目：[docx2tex](https://github.com/transpect/docx2tex)