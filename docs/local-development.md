# Local Development And Deployment

## 目标

本地部署优先支持 Linux。默认路径位于仓库内 `.local/`，因此不需要 root 权限即可启动和调试。

## 1. Python 依赖

推荐两种方式：

### 方式 A：`uv`

```bash
uv sync --extra dev
```

### 方式 B：`pip`

```bash
python -m pip install -e ".[dev]"
```

如果你已经激活了自己的 Python 环境，也可以只设置 `PYTHONPATH=src:.` 后从源码运行。

以上 Python 安装方式会同时安装 `pandoc-tex-numbering`，它现在属于正式运行时依赖。

## 2. 系统依赖

需要可执行文件：

- `java`
- `inkscape`
- `pandoc`

需要环境路径：

- `DOCX2TEX_HOME`
- `XML_CATALOG_FILES`

在 Debian / Ubuntu 上可参考：

```bash
sudo apt-get update
sudo apt-get install -y openjdk-17-jre-headless inkscape pandoc sqlite3
```

## 3. 环境变量

```bash
export PYTHONPATH=src:.
export DATA_ROOT="$(pwd)/.local/data"
export WORK_ROOT="$(pwd)/.local/work"
export LOG_DIR="$(pwd)/.local/logs"
export DOCX2TEX_HOME="$(pwd)/src/engines/docx2tex_engine/vendor/docx2tex"
```

## 4. 一键脚本

仓库自带一键本地部署脚本：[local-deploy.sh](/home/joshua/Workspace/Code/Python/DOCX2TEX_Service_Container/scripts/local-deploy.sh)

首次使用：

```bash
bash scripts/local-deploy.sh check
```

启动服务：

```bash
bash scripts/local-deploy.sh serve --reload
```

可选参数：

```bash
bash scripts/local-deploy.sh serve --host 0.0.0.0 --port 8000
```

脚本默认行为：

- 使用你当前已经激活的 Python 环境
- 自动设置 `PYTHONPATH`
- 自动设置并创建 `.local/data`、`.local/work`、`.local/logs`
- 自动设置 `DOCX2TEX_HOME` 和 `XML_CATALOG_FILES`
- 默认监听 `0.0.0.0`
- 启动前先执行一次系统检查

容器部署也使用同一套检查逻辑：镜像构建时验证依赖，入口脚本启动前再次执行
`check-system`，缺失依赖时直接退出。

## 5. 首次检查

```bash
python -m document_conversion.interfaces.cli check-system
```

或者在你当前已经激活的环境下：

```bash
python -u -m document_conversion.interfaces.cli check-system
```

## 6. 启动方式

### 开发模式

```bash
HOST=0.0.0.0 python -u -m document_conversion.interfaces.cli serve --reload
```

### 近生产模式

```bash
PYTHONPATH=src:. uvicorn document_conversion.interfaces.api.app:app --host 0.0.0.0 --port 8000 --workers 2
```

## 7. 目录说明

- `.local/data/`：SQLite、任务工作目录、缓存
- `.local/work/`：公开下载 ZIP
- `.local/logs/`：运行日志

## 8. 故障排查

- `Permission denied: /data`
  - 说明你把环境变量仍然指向了容器路径
- `docx2tex failed`
  - 优先检查 `DOCX2TEX_HOME`、Java 和 submodule 是否已初始化
- WebUI 能打开但任务失败
  - 先调 `/healthz`
  - 再检查任务 ZIP 同名日志与 `.local/logs/`
