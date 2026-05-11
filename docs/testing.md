# Testing

## 分层

### `tests/unit/`

纯 Python 规则测试：

- 平台矩阵模型
- path-scoped profile 注册表
- 请求校验
- Pandoc 模板检测与 preprocessors

### `tests/integration/`

跨模块协作测试：

- 运行时装配
- SQLite / 任务存储
- 缓存与结果定位
- engine runtime 协作

### `tests/api/`

FastAPI 接口测试：

- 矩阵能力探测
- path-scoped Profile 返回
- 基于 profile 的平台任务提交
- 健康与版本接口
- WebUI 页面和平台 dryrun

### `tests/e2e/`

真实慢测：

- 真 `docx2tex`
- 真 `pandoc`
- WebUI 端到端

默认不跑。

## 常用命令

```bash
python -u -m pytest -q
python -u -m pytest -q -m e2e
python -u -m mypy src
python -u -m ruff check src tests
```

## 慢测策略

真实慢测通过环境变量显式启用，例如：

```bash
DOCX2TEX_E2E=1 python -u -m pytest tests/e2e -q -m e2e
```

没有该环境变量时，`tests/e2e/` 会跳过。
