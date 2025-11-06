## docx2tex_inverse

面向 docx2tex 的深入解析与二次封装项目：

- 文档解析：梳理 docx2tex 的处理流水线（docx2hub → evolve-hub → xml2tex）、配置与定制点（conf、自定义 XSL）。
- 服务封装：提供一个可离线运行的容器化 API 服务（FastAPI），对外暴露上传/查询/下载接口，自动打包结果。
- 工程增强：内置缓存、并发锁、自愈与统一清理策略；内置 Inkscape 将 EMF/WMF/SVG 转 PDF 并更新 TeX 引用。

### 仓库结构

- `app/`：服务端实现（FastAPI，`server.py`，`entrypoint.sh`，`requirements.txt`）
- `scripts/`：
  - `convert_vector_images.py`：将 EMF/WMF/SVG → PDF 并改写 TeX 引用
  - `pack_tex_with_images.py`：在非调试模式下，仅打包被引用图片到 `image/` 并改写引用路径
- `docx2tex/`：上游项目（参考/分析）
- `catalog/`：XML catalog（镜像构建时复制到 `/opt/catalog`）
- `docs/`：
  - `overview-zh.md`：docx2tex 原理与要点
  - `API_DOC.md`：服务 API 参考
- `test/test_docx2tex.ps1`：PowerShell 5.1 示例客户端（上传/轮询/下载）
- `Dockerfile`：可离线的服务镜像构建文件

### 快速开始

构建：

```bash
docker build -t docx2tex-svc:latest .
```

运行（建议）：将私有数据放入命名卷（宿主不可直接访问），公开结果目录 `/work` 到宿主机：

```bash
docker volume create docx2tex_data
docker run --rm -p 8000:8000 \
  -v docx2tex_data:/data \
  -v "$(pwd)/work:/work" \
  -e TTL_DAYS=7 \
  --name docx2tex-svc \
  docx2tex-svc:latest
```

调用 API：见 `docs/API_DOC.md`；或使用 `test/test_docx2tex.ps1`：

```powershell
. .\test\test_docx2tex.ps1
Invoke-Docx2Tex -Server http://127.0.0.1:8000 -File .\examples\forward\example_forward.docx -IncludeDebug:$false -ImgPostProc:$true -OutFile .\result.zip
```

### 关键设计

- 缓存键：由 (DOCX 内容, conf 内容(或默认), custom-xsl 内容或无) 三元组计算（SHA-256）；与 `debug`、`img_post_proc` 无关。
- 并发锁：同键任务并发时仅一个执行构建，其他等待已发布缓存或在锁过期后接管。
- 自愈机制：若 DB 记录缺失但磁盘缓存存在，自动补发布；所有关键步骤均追加日志。
- 清理策略：`TTL_DAYS` 统一控制任务与缓存清理，按 `last_access/created` 判断；缓存删除采用两阶段策略避免不一致。

### 相关文档

- docx2tex 总览与定制：`docs/overview-zh.md`
- 容器使用说明：`README-container.md`
- API 参考：`docs/API_DOC.md`

## 感谢

伟大且专业的开源项目：[docx2tex](https://github.com/transpect/docx2tex)