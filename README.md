# Riichi Mahjong

支持 3 人 / 4 人日本麻将的联机对战平台。规则基准：**雀魂金之间**。

当前阶段：**Stage A · 4 人日麻规则引擎**（M1 数据与状态层）。3 麻、AI 推荐打牌、人机对手在 Stage D 之后引入。

## 仓库布局

```
engine/   纯算法规则引擎（Python，无 I/O）
server/   FastAPI + WebSocket 对战服务（Stage C 开工）
web/      React 前端（Stage C 末段）
docs/     规则规约 / 牌编码 / 协议 / 里程碑
scripts/  开发辅助脚本
```

## 文档入口

- [`docs/milestones.md`](docs/milestones.md) —— 当前里程碑与路线图
- [`docs/rules.md`](docs/rules.md) —— 雀魂金之间规则规约（M1 启动前必须填完）
- [`docs/tile-encoding.md`](docs/tile-encoding.md) —— 牌编码约定
- [`docs/api.md`](docs/api.md) —— REST + WebSocket 协议（Stage C）
- [`CLAUDE.md`](CLAUDE.md) —— AI 协作者开发规约

## 本地开发

引擎包用 [uv](https://docs.astral.sh/uv/) 管理依赖：

```bash
cd engine
uv sync --dev
uv run pytest
```

服务端与前端在 Stage C 之前不需要本地启动。
