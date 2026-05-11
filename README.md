# docx2tex-service

面向长期演进的文档转换平台。当前平台已经重整为“路径 × 引擎矩阵”的结构：平台正式包是 `src/document_conversion/`，引擎按后端拆分到 `src/engines/`。当前正式矩阵为：

- `docx -> latex@docx2tex`
- `docx -> latex@pandoc`
- `latex -> docx@pandoc`

`latex -> markdown@pandoc` 已作为规划中的矩阵单元预留。

上游 `docx2tex` 不再作为仓库根目录副本维护，而是作为 git submodule 固定在
`src/engines/docx2tex_engine/vendor/docx2tex`。

## 当前能力

- 平台接口
  - `GET /v1/capabilities`
  - `GET /v1/profiles`
  - `POST /v2/tasks`
  - `GET /v2/tasks/{task_id}`
  - `GET /v2/tasks/{task_id}/result`
- 基础页面
  - `GET /` 内置拖放式 WebUI
- 运维接口
  - `GET /healthz`
  - `GET /version`
  - `POST /v2/dryrun`

## 架构概览

- `src/document_conversion/`
  - 平台模型、矩阵注册、任务服务、API/CLI 入口
- `src/engines/docx2tex_engine/`
  - `docx -> latex@docx2tex` 主质量路径
  - `assets/`：本仓库维护的 conf、catalog 等运行时资产
  - `vendor/docx2tex/`：上游 submodule
- `src/engines/pandoc_engine/`
  - `docx -> latex@pandoc`
  - `latex -> docx@pandoc`
  - 未来 `latex -> markdown@pandoc`
- `src/docx2tex_service/`
  - 兼容层，只转发到新平台

详细说明见：

- [架构说明](docs/architecture.md)
- [API 参考](docs/api_reference.md)
- [本地部署](docs/local-development.md)
- [测试体系](docs/testing.md)
- [转换 Profile](docs/converter-profiles.md)

## 快速开始

### 1. 本地开发运行

初始化 submodule：

```bash
git submodule update --init --recursive
```

优先使用一键脚本：

```bash
bash scripts/local-deploy.sh check
bash scripts/local-deploy.sh serve --reload
```

浏览器打开 `http://127.0.0.1:8000/`。

脚本默认监听 `0.0.0.0`。如果你不想用脚本，也可以继续手工设置环境变量后通过 CLI 启动，见 [docs/local-development.md](docs/local-development.md)。

### 2. 使用 pyproject 安装依赖

如果不使用现成 conda 环境，推荐：

```bash
uv sync --extra dev
```

或者：

```bash
python -m pip install -e ".[dev]"
```

这两种方式都会安装 Python 侧运行时依赖，包括 `pandoc-tex-numbering`。

### 3. 容器启动

构建前先初始化 submodule：

```bash
git submodule update --init --recursive
```

```bash
docker build -t docx2tex-svc:latest .
docker run --rm -p 8000:8000 \
  -v "$(pwd)/.local/data:/data" \
  -v "$(pwd)/.local/work:/work" \
  -v "$(pwd)/.local/logs:/var/log/docx2tex" \
  docx2tex-svc:latest
```

镜像构建会检查 `docx2tex` submodule 和正式运行时依赖；容器启动前也会先执行
`check-system`，依赖缺失时直接失败。

## 测试与质量检查

```bash
python -u -m pytest -q
python -u -m mypy src
python -u -m ruff check src tests
```

真实 `docx2tex` / `pandoc` 慢测默认不跑，需要显式启用 `e2e` 标记，见 [docs/testing.md](docs/testing.md)。
