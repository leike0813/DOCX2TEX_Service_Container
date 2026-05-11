# Architecture

## Authority

本文档是当前仓库唯一的权威架构说明。平台包、引擎包、兼容层、第三方源码、运行时资产和参考资源都以本文定义为准。

## 核心原则

- 平台以 `conversion path × engine` 能力矩阵为第一公民。
- 平台包负责任务模型、profile 解析、公共状态与接口。
- 引擎包只负责引擎相关的输入准备、执行和引擎特有产物。
- 第三方源码、运行时资产、参考资源必须分层管理，禁止继续混放在仓库根目录。

## 包边界

### `src/document_conversion/`

唯一正式平台包。

- `domain/`
  - 平台核心类型：`DocumentFormat`、`ConversionPath`、`CapabilityCell`、`ConversionRequest`、`ConversionProfile`
  - 引擎接口与矩阵注册：`ConversionEngine`、`EngineRegistry`
- `application/`
  - `PlatformService`
  - 统一任务图：prepare -> resolve_profile -> resolve_engine -> execute -> package -> publish
- `infrastructure/`
  - 平台共享基础设施：配置、SQLite、缓存、任务状态、进程调用、日志、任务元数据
- `interfaces/`
  - `api/`：FastAPI 接口
  - `cli.py`：本地检查与启动入口
  - `webui/`：平台内置静态页面资源

### `src/engines/docx2tex_engine/`

`docx_to_latex@docx2tex` 的正式实现目录。

- `converter.py`：平台到引擎的提交适配
- `executor.py` / `runner.py` / `packaging.py`：`docx2tex` 执行与打包
- `postprocess.py` / `stylemap.py` / `convert.py` / `filenames.py`
- `profiles.py` / `presets.py`
- `assets/`
  - 本仓库维护的运行时资产
  - 当前包括 `conf/` 和 `xmlcatalog/`
- `vendor/`
  - 第三方源码
  - 当前包括 git submodule `vendor/docx2tex/`

### `src/engines/pandoc_engine/`

Pandoc 方向的正式实现目录。

- `converter.py`
- `config/`
- `orchestrator/`
- `preprocessors/`
- `postprocessors/`
- `runner/`
- `assets/`
  - 运行时 YAML templates 与 Lua filters

### `src/docx2tex_service/`

兼容层，不是正式实现目录。

允许保留的内容只有公开入口转发：

- `__init__.py`
- `interfaces/cli.py`
- `interfaces/api/app.py`
- `interfaces/api/router.py`

不允许在该包下继续放置 domain、application、infrastructure 业务实现。

## Engine Asset Contract

每个引擎都遵循同一套目录契约：

```text
src/engines/<engine>/
  converter.py
  profiles.py
  assets/        # 本仓库维护的运行时资产
  vendor/        # 外部源码或 submodule，可选
resources/<engine>/  # 样例、原型、研究资料，非运行时真源
```

### `assets/`

运行时真源。服务启动、profile 解析、模板检测、catalog 解析都应从这里读取。

### `vendor/`

第三方源码真源。不得在 Docker 构建时再次 clone 一份平行副本，也不得在仓库根目录保留另一份未托管源码树。

### `resources/`

非运行时真源。可用于样例、实验、文档、E2E 夹具，但不能作为平台默认路径来源。

## Third-Party Submodule Policy

- 上游 `docx2tex` 作为正式 git submodule 管理。
- submodule 固定位置：
  `src/engines/docx2tex_engine/vendor/docx2tex`
- 仓库根目录 `docx2tex/` 不再作为运行时来源。
- Docker、本地脚本、测试、平台配置默认值都必须指向 submodule 路径或由其推导。

## Runtime Path Resolution

平台保留环境变量名：

- `DOCX2TEX_HOME`
- `XML_CATALOG_FILES`

但默认来源变为 engine-local resolver：

- `DOCX2TEX_HOME`
  - 默认指向 `src/engines/docx2tex_engine/vendor/docx2tex`
- `XML_CATALOG_FILES`
  - 默认由 `src/engines/docx2tex_engine/assets/xmlcatalog/catalog.xml` 模板渲染得到
  - 渲染结果会绑定到当前有效的 `DOCX2TEX_HOME`

这条规则保证本地开发、测试和容器部署都围绕同一份 engine-local 资产布局运行，而不是回退到仓库根目录约定。

## API Ownership

正式接口由 `document_conversion.interfaces.api` 暴露：

- `GET /`
- `GET /healthz`
- `GET /version`
- `GET /v1/capabilities`
- `GET /v1/profiles`
- `POST /v2/tasks`
- `GET /v2/tasks/{task_id}`
- `GET /v2/tasks/{task_id}/result`
- `POST /v2/dryrun`

兼容层可以转发导入路径，但不应成为接口实现真源。

## Testing Layout

测试按四层组织：

- `tests/unit/`
- `tests/integration/`
- `tests/api/`
- `tests/e2e/`

测试应优先导入 `document_conversion` 与 `engines.*`。兼容层只保留少量导入级验证，不再作为主测试目标。
