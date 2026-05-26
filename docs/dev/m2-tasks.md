# M2 任务进度 —— 听牌与待ち

**目标**：在 M1 数据层基础上实现手牌分解（standard / chiitoitsu / kokushi）、向听数计算与听牌枚举。

**验收**：`pytest engine/tests/test_decompose.py engine/tests/test_tenpai.py -v` 全绿；hypothesis 属性测试覆盖 round-trip。

---

## 进度

| 文件 | 状态 | 说明 |
|---|---|---|
| `docs/dev/m2-tasks.md` | ✅ 本文档 | |
| `engine/src/mahjong_engine/decompose.py` | ✅ 完成 | standard / chiitoi / kokushi 分解 |
| `engine/src/mahjong_engine/tenpai.py` | ✅ 完成 | shanten / is_tenpai / winning_tiles |
| `engine/tests/test_decompose.py` | ✅ 完成 | 含 hypothesis 属性测试 |
| `engine/tests/test_tenpai.py` | ✅ 完成 | 含 hypothesis 属性测试 |

---

## 接口设计（与用户对焦后确认）

### decompose.py

```python
class BlockKind(Enum):
    SHUNTSU       # 顺子
    KOUTSU        # 刻子
    PAIR          # 标准型雀头
    PAIR_CHIITOI  # 七对子的对子（区分以便 M3 走 25 符）

@dataclass(frozen=True)
class Block:
    kind: BlockKind
    tiles: tuple[int, ...]   # SHUNTSU=3 连续, KOUTSU=同×3, PAIR/PAIR_CHIITOI=同×2

class DecompForm(Enum):
    STANDARD
    CHIITOITSU
    KOKUSHI

@dataclass(frozen=True)
class Decomposition:
    form: DecompForm
    blocks: tuple[Block, ...]
    pair_tile: int | None    # 标准/国士的雀头牌；七对子为 None

# 顶层 API
standard_decompositions(counts) -> list[Decomposition]
chiitoitsu_decomposition(counts) -> Decomposition | None    # 仅 14 张
kokushi_decomposition(counts) -> Decomposition | None        # 仅 14 张
all_decompositions(counts) -> list[Decomposition]            # 完整和牌分解的合集
```

### tenpai.py

```python
shanten(counts, melds=()) -> int          # -1=和；0=听；>0=向听
is_tenpai(counts, melds=()) -> bool       # 要求 sum(counts) % 3 == 1
winning_tiles(counts, melds=()) -> list[int]  # 升序，去重；要求 sum(counts) % 3 == 1
```

---

## 关键约定（已与用户对焦）

| # | 约定 | 由来 |
|---|---|---|
| A | `is_tenpai` / `winning_tiles` 仅支持 `sum(counts) % 3 == 1` 的"听牌相位"。副露下手中张数自动是 10/7/4/1。 | 14 张切牌推荐属 M5/M10 |
| B | `Decomposition.blocks` 不包含副露 `Meld`，仅描述暗手。M3 在役判定时合并 melds。 | 分解职责单一 |
| C | `kokushi_decomposition` 仅接受 14 张完整国士；总是返回 `pair_tile`，不在 M2 区分十三面 vs 单骑（属 M3 在 `winning_tile` 上判定） | 14 张国士长得一样，区分需要"和的那张" |
| — | 七对子向听公式：`6 - pairs + max(0, 7 - unique_kinds)`（4 张同种只算 1 对，必须 7 种不同对子） | 用户修正 |
| — | 副露存在时七对子 / 国士向听 = ∞（直接失效） | 七对子要求门清；国士同样 |
| — | `Decomposition` 不显式列出国士的 12 张单张，仅保留雀头一个 `Block`。M3 通过 `form == KOKUSHI` + `pair_tile` 推断形态。 | 简化结构 |

---

## 算法路线

### standard_decompositions（完整分解）

枚举雀头位置 → 每个花色独立 DFS（顺子/刻子）→ 字牌只走刻子分支 → 卡迪卡积合并。

复杂度：每个花色最坏几十个完整分解，4 个花色相乘 + 34 个雀头候选 = 几千个 leaf，实测远低于此。

参考：
- <https://github.com/MahjongRepository/mahjong/blob/master/mahjong/agari.py>
- 经典思路：先固定 head，suit 内顺/刻 DFS

### shanten

标准型：DFS 枚举 (mentsu, taatsu, has_pair) 状态空间，应用公式

```
shanten = 8 − 2·(m_concealed + n_melds) − min(t, 4 − m_total) − (1 if has_pair else 0)
```

剪枝：`m_total + t ≥ 5` 时记录当前并停止扩展。

七对子：`6 − pairs + max(0, 7 − unique_kinds)`（n_melds == 0 才生效）。

国士：`13 − yaochuu_kinds − (1 if any_yaochuu_pair else 0)`（n_melds == 0 才生效）。

最终：三者取最小。

### winning_tiles

13 张 → 穷举加 34 种牌后是否成为完整和牌（standard / chiitoi / kokushi）。O(34 · D) 其中 D 是完整分解判定的代价。

---

## Hypothesis 属性测试

- 任意 14 张和牌（由分解构造）⇒ `shanten == -1`
- 任意听牌 13 张 ⇒ `winning_tiles` 非空且每张加上后 `shanten == -1`
- 任意 14 张分解 ⇒ 各 block tiles 数总和 == sum(counts)
- 字符串 round-trip：`Hand.from_str(...)` 的 counts 经分解后 block.tiles 还原回原 counts

---

## 验收（2026-05-23）

待执行：`cd engine && python3 -m pytest tests/ -v`
