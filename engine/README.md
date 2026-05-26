# mahjong-engine

纯 Python 实现的日本麻将规则引擎。**无任何 I/O 依赖**（不读文件、不连网络、不访数据库），只接收状态、返回新状态或判定结果。

设计目标：
- 可独立发布到 PyPI
- 服务端、CLI、测试、未来的 AI 训练流程都复用同一份规则
- 完整 type hints + hypothesis 属性测试

## 安装

```bash
uv sync --dev
```

## 测试

```bash
uv run pytest
uv run mypy src
uv run ruff check src tests
```

## 当前进度

见根目录 [`docs/milestones.md`](../docs/milestones.md)。
