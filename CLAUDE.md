# Riichi Mahjong —— 项目开发规约

本文件是项目内 AI 协作者与人类工程师共同遵守的约束。**所有新会话都会自动加载本文件**，请在每次行动前对照检查。

---

## 项目目标

构建支持 **3 人日麻** 和 **4 人日麻** 的完整联机对战平台。

- 规则基准：**雀魂段位场规则**。所有规则歧义以 `docs/rules.md` 为准。
- 形态：联机对战 + 牌谱回放。
- 当前阶段：**Stage A · 4 人日麻规则引擎**。3 麻与 AI 等 M9 之后再启，本阶段**不要** 引入任何 3 麻 / AI 相关代码。
- 当前里程碑见 [`docs/milestones.md`](docs/milestones.md)。

---

## 技术栈（固定，不要替换）

| 模块 | 选型 |
|---|---|
| 规则引擎 | Python 3.11+，纯函数式，无 I/O 依赖 |
| Python 包管理 | **uv**（PEP 621 标准 `pyproject.toml`） |
| 引擎测试 | pytest + hypothesis |
| 后端服务 | FastAPI + Uvicorn + WebSocket |
| 房间状态 | Redis |
| 持久化 | PostgreSQL + SQLAlchemy 2.0 |
| 前端 | React 18 + TypeScript + Vite + Zustand |
| 牌面渲染 | SVG（开源 Riichi tiles） |
| 联机协议 | JSON over WebSocket |
| 牌谱格式 | Tenhou JSON 兼容 |

---

## 牌编码约定

```
万 1m-9m → 0-8
筒 1p-9p → 9-17
索 1s-9s → 18-26
字 东南西北白发中 → 27-33
```

- 手牌主表示统一用 `counts: int[34]`，**所有快速判定都用这个**
- 赤五用**单独 `bool` 字段**，不占编码位
- 字符串表示 `"1m 2m 3p 东"`（赤五写作 `"赤5m"`），**仅用于 IO / 牌谱 / 显示**

详细规范见 [`docs/tile-encoding.md`](docs/tile-encoding.md)。

---

## 架构纪律

1. **依赖方向单向**：`engine` ← `server` ← `web`。engine 不依赖 server/web；server 不依赖 web。
2. **engine 无 I/O**：不读文件、不连网络、不访数据库。状态进来，状态出去。
3. **服务端权威**：规则判定永远在服务端，前端不持有规则引擎，听牌/役提示由服务端下发。
4. **状态不可变**：`GameState` 用 `frozen dataclass`；所有转移函数签名 `(state, action) → (state', events)`。
5. **役判定取最高番分解**：同一手牌可能有多种合法 4 面子+雀头分解，必须枚举全部、按总番取最高。

---

## 代码风格

**Python**
- PEP 8 + 完整 type hints + Google docstring
- 不可变状态用 `@dataclass(frozen=True)`
- 算法函数附复杂度注释与参考来源（论文 / wiki 链接 / 实现出处）
- lint：ruff；类型检查：mypy（严格模式）

**TypeScript**
- 严格模式（`strict: true`）
- 所有协议类型必须与后端 Pydantic 模型一一对应
- 优先用 discriminated union 表达事件

**命名**
- 标识符英文；注释 / 文档可中文
- 文件名 snake_case，类 PascalCase，常量 UPPER_SNAKE

---

## 文档优先原则

- **规则歧义 → 先写进 `docs/rules.md` 再写代码**。M3 役判定阶段最容易翻车，规则不定死就不要动手。
- 接口设计 → 先在 `docs/api.md` 立 schema 再实现
- 牌谱兼容性问题 → 先记录到 `docs/dev/` 下的笔记

---

## 交付节奏

按 M1-M11 里程碑推进。**当前里程碑见 [`docs/milestones.md`](docs/milestones.md)。**

每个任务的交付物必须包含：
- 代码（PEP 8 + type hints + docstring）
- pytest 用例（含 hypothesis 属性测试，若涉及枚举/分解类算法）
- 若涉及规则：在 commit message 中引用 `docs/rules.md` 的具体条款编号

---

## 输出习惯（给 AI 协作者）

- **遇到规则歧义主动指出，要求人类确认**，不要自行假设
- 大块代码以**完整文件**给出，避免片段拼接（除非用户明确要求 diff）
- 中文回复，代码与文档内 docstring 用英文
- 不要主动创建未列在路线图里的模块
- 不要为"未来的 3 麻 / AI"提前抽象（参见架构纪律第 5 条之外的"先具体后抽象"原则）

---

## 历史与参考

- 初版方案设计对话：[`docs/dev/initial-design-history.md`](docs/dev/initial-design-history.md)
- Claude Code CLI 速查表（个人）：[`docs/dev/claude-code-cli-cheatsheet.md`](docs/dev/claude-code-cli-cheatsheet.md)
