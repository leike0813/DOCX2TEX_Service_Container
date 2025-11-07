# docx2tex_inverse 架构文档

本文简述服务的整体架构、关键组件职责和数据流，面向开发与维护场景。

## 总览

- 技术栈：FastAPI（HTTP API）、SQLite（状态与缓存元数据）、XProc/Calabash（docx2tex 流水线）、XSLT 2.0（evolve/xml2tex）、Inkscape（矢量转 PDF）。
- 目标：将 DOCX 转换为 LaTeX（TeX），并提供可配置、可扩展、可离线的容器化服务。
- 关键能力：
  - 可插拔配置：xml2tex 配置（conf）、evolve-driver 自定义、evolve→xml2tex 之间的自定义 XSL。
  - StyleMap：将 Word 可见样式映射到规范角色（Title/Heading1..3）并按 conf 注入 LaTeX。
  - 缓存与并发锁：基于输入计算 cache_key，支持并发构建协调与自愈发布。
  - 图片后处理：EMF/WMF/SVG → PDF 并改写 TeX 引用；非调试模式仅打包引用图片。

## 目录结构

- `app/core/` 基础设施与通用能力
  - `config.py`：集中式配置（路径、环境变量、TTL/并发等）。
  - `db.py`：SQLite 连接与 schema 初始化。
  - `models.py`：Pydantic 领域模型（JobState、CacheEntry、LockEntry）。
  - `cache.py`：`CacheStore`（缓存 DB+FS）与 `LockManager`（锁表）。
  - `storage.py`：原子写入、路径工具、哈希等。
  - `logging.py`：控制台与文件日志（轻量）。
  - `convert.py`：`compute_cache_key` 与 conf import 重写工具。
  - `proc.py`：子进程/下载封装。
  - `tasks.py`：`TaskStore`（tasks 表的 CRUD）。
  - `cleanup.py`：任务/缓存清理循环。
- `app/services/`
  - `job_manager.py`：任务编排（创建/状态、缓存命中/构建、后处理、打包、manifest）。
  - `context.py`：整合 Config/Database/Cache/Lock/Task 的上下文容器（如需）。
- `app/api/`
  - `routes.py`：对外路由（`/v1/task`、`/v1/dryrun`、`/v1/task/{id}`、`/v1/task/{id}/result`、`/healthz`、`/version`）。
- `app/server.py`：FastAPI 入口，挂载路由，启动清理与锁回收。
- `app/scripts/`：后处理脚本（仍可被服务内部调用）。
  - `convert_vector_images.py`、`pack_tex_with_images.py`、`rewrite_tex_debug.py`、`stylemap_inject.py`。
- 其余：`conf/`（默认配置）、`catalog/`（XML catalog）、`docs/`（文档）、`Dockerfile`、`tests/`。

## 数据流与执行阶段

1) 任务创建（POST /v1/task）
   - 接收 `file` 或 `url`；可选 `conf/custom_xsl/custom_evolve/StyleMap/FontMapsZip/MathTypeSource/TableModel` 等。
   - 持久化 JobState（pending），保存上传/下载的 DOCX 与相关输入至工作目录。
   - 若传入 StyleMap，生成“有效”的 evolve-driver 片段，必要时追加输出层注入（避免转义）。
   - 计算 `cache_key`（由 DOCX、配置、XSL、MathType 源、表格模型、fontmaps 内容构成）。
   - 返回 `task_id` 与 `cache_status`（HIT/BUILDING/MISS）。

2) 后台处理（JobManager.submit → _process_job）
   - 快速 HIT：从缓存恢复产物（含 `.tex/.xml`、debug 目录、解包目录），并重写 `.tex` 中的临时目录名。
   - MISS/BUILDING：通过 `locks` 表协调并发，仅一个 builder 构建；其余等待或接管。
   - 运行 Calabash（docx2tex.xpl）生成 `.tex/.xml` 等；成功后发布到缓存（DB+FS）并释放锁。
   - 可选后处理：
     - 矢量转换（EMF/WMF/SVG → PDF）并更新 `\includegraphics` 引用。
     - 非调试模式打包引用图片到 `image/` 并改写路径；调试模式注释 .vsdx 与宽度归一化。
   - 打包 ZIP（debug=false：最小化；debug=true：包含中间产物、日志、manifest、fontmaps、有效 XSL 等）。
   - 更新任务状态为 `done` 或 `failed`。

3) 查询与下载
   - GET `/v1/task/{task_id}`：返回任务状态。
   - GET `/v1/task/{task_id}/result`：返回 ZIP（仅在 `done` 时）。

4) 清理与并发
   - `cleanup.py`：周期性清理任务与缓存（基于 `TTL_DAYS`），两阶段删除避免竞态。
   - `LockManager`：定期回收超时锁；任务内恰当释放。

## 缓存键设计

`cache_key = SHA256(DOCX + conf + custom_xsl + custom_evolve + MathTypeSource + TableModel + FontMapsZip)`

- 与 `debug`、`img_post_proc` 无关；因此调试与非调试对同一输入命中相同缓存。
- 发布缓存包括 `.tex/.xml/.csv`（如有）、`<base>.debug/`、`<base>.docx.tmp/` 与 `meta.json`。

## StyleMap 有效化

- 输入：`{"Title": ["主标题", ...], "Heading1": ["I级标题", ...], ...}`。
- 处理：
  - 在 evolve-driver preprocess 模式：将匹配可见样式的段落 `@role` 归一为规范角色。
  - 在 postprocess 模式：基于 conf 中的模板为规范角色注入对应 LaTeX 命令（通过处理指令避免转义）。
  - 仅对 conf 中实际出现的角色生效；多余键被忽略。

## 端点与兼容性

- 对外端点：`/v1/task`、`/v1/dryrun`、`/v1/task/{id}`、`/v1/task/{id}/result`、`/healthz`、`/version`。
- 行为稳定：重构后外部接口与语义未变；仅内部解耦与模块化。

## 测试与验证

- `tests/` 包含：
  - 配置/存储：`test_config.py`、`test_storage.py`。
  - 缓存/锁：`test_cache.py`。
  - 任务表：`test_tasks.py`。
  - 转换工具：`test_convert.py`。
  - 子进程封装：`test_proc.py`。
  - 路由测试：`test_routes_basic.py`、`test_routes_dryrun.py`、`test_routes_task.py`（需 httpx）。

---

以上结构确保了服务的可维护性与扩展性：当要增强某个能力（如打包策略或 StyleMap），可以在对应模块内迭代，而无需影响其它层级。

