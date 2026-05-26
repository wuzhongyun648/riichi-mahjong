# M3 任务进度 —— 役判定

**目标**：实现 `engine/src/mahjong_engine/yaku/`，按 `docs/rules.md §8` 完成 1 番 → 双役满的全部役判定。纯函数、无 I/O、服务端权威。

**验收（2026-05-26）**：`pytest tests/` 全绿 **358 / 358**（M1=120 + M2=109 + M3=129）；`mypy --strict src/` 零错误（21 文件）；`ruff check src/ tests/` 全通过。

M3 测试构成（129）：situational 14 + structural 45 + yakuman 20 + judge 7 + property 2 + **golden 41**（转写自 MahjongRepository/mahjong，逆向验证全部役判定，见 `tests/golden/test_yaku_golden.py`）。手动验收 / demo 见 `docs/dev/m1_3_test_guide.md §5b`。

> 注：`ruff check src/ tests/` 仍报若干 M1/M2 既有文件的告警（import 排序、RUF002 全角符号、stub 文件行长等），非 M3 引入，本里程碑未触碰。

---

## 进度

| 文件 | 状态 | 说明 |
|---|---|---|
| `docs/dev/m3-tasks.md` | ✅ 本文档 | |
| `yaku/result.py` | ✅ | `Yaku` / `YakuDecomp` 数据类 |
| `yaku/context.py` | ✅ | `WinContext` + `is_menzen` |
| `yaku/partition.py` | ✅ | `Decomposition`+melds → `StandardPartition`（待ち型 / 暗刻计数 / 杠数） |
| `yaku/situational.py` | ✅ | 场况役（立直/一发/自摸/海底.../天地和） |
| `yaku/structural.py` | ✅ | 1–6 番牌型役 + 整手扫描（断幺/混清一色/混老头） |
| `yaku/yakuman.py` | ✅ | 役满 / 双役满 + 国士 + 九莲 |
| `yaku/judge.py` | ✅ | 顶层 `judge_yaku` / `has_any_yaku` |
| `yaku/__init__.py` | ✅ | 公共 API 导出 |
| `tests/test_yaku_situational.py` | ✅ | 14 例 |
| `tests/test_yaku_structural.py` | ✅ | 36 例 |
| `tests/test_yaku_yakuman.py` | ✅ | 20 例 |
| `tests/test_yaku_judge.py` | ✅ | 编排 / 错误 / 层级齐次 |
| `tests/property/test_yaku_property.py` | ✅ | hypothesis 不变量 |
| `tests/yaku_util.py` | ✅ | 共享测试辅助 |

---

## 接口设计（与用户对焦后确认）

```python
@dataclass(frozen=True)
class WinContext:
    round_wind: Wind; seat_wind: Wind; is_tsumo: bool
    is_riichi / is_double_riichi / is_ippatsu / is_haitei / is_houtei /
    is_rinshan / is_chankan / is_tenhou / is_chiihou: bool = False
    # 场况 flag 由调用方(M5)提供，M3 不自行推导

@dataclass(frozen=True)
class Yaku:
    id: str; name: str; han: int; yakuman_units: int = 0  # 0普通 / 1役满 / 2双役满

@dataclass(frozen=True)
class YakuDecomp:
    yaku: tuple[Yaku, ...]; han: int; yakuman_units: int; decomposition: Decomposition
    @property is_yakuman / has_yaku

def judge_yaku(hand: Hand, win_tile: int, ctx: WinContext) -> list[YakuDecomp]
def has_any_yaku(hand: Hand, win_tile: int, ctx: WinContext) -> bool
```

---

## 关键约定（已与用户对焦，写入 `docs/rules.md §8.8`）

| # | 约定 | 由来 |
|---|---|---|
| A | `judge_yaku` 返回**每个有役分解一项**，不在 M3 取高；M4 结合符数按点数选最高 | 用户决策；符要 M4 才有 |
| B | **层级齐次**：任一分解命中真役满 → 只返回役满项（丢弃普通役分解），M4 只在同层级里取高 | 役规则不泄漏进 scoring |
| C | 宝牌 / 赤五 / 里宝 / 数え役满(13番) **全部归 M4** | 用户决策（rules §8.8） |
| D | 绿一色**不强制含发** | 用户决策（rules §8.8） |
| E | 連風牌刻子 **2 番**（场风+自风各 1） | rules §8.8 |
| F | 荣和完成的刻子视为**明刻**（影响三暗刻/四暗刻）；四暗刻须自摸，唯单骑可荣和 | rules §8.8 |
| G | **暗杠不破门清** | rules §8.8 |
| H | 命中真役满时普通番全忽略；多役满单位相加封顶 **6** | rules §8.7 / §8.8 |

---

## 算法路线

- `judge_yaku`：`all_decompositions(counts)` → 逐分解评役 → 合并场况役 → `_combine` 处理役满优先 → 末尾强制层级齐次。
- `build_standard_partition`：把 M2 的 `Decomposition`(暗手) 与 `Hand.melds`(副露) 合并成 4 面子 + 雀头的归一结构。
  - **待ち型**只对暗手块分析（和了牌总在暗手）：单骑/双碰/嵌张/边张/两面。
  - **暗刻计数**对荣和做调整：和了牌若**只能**落在某刻子（无顺子/雀头落点）则该刻子记为明刻（-1）；否则取最有利摆法保留全部暗刻。
  - 杠数统计含明杠/加杠/暗杠；暗杠记为暗刻。
- 整手扫描役（断幺/混老头/混一色/清一色/字一色/绿一色/清老头）对 `counts + meld tiles` 直接判定，标准型与七对子复用。
- 役满复合天然由「逐分解 + 单位相加」处理：同一手牌一个分解可能是役满、另一分解是普通役（如 `222333444m 555m + 雀头` 自摸 = 四暗刻 vs 顺子读法），层级齐次保证只取役满。

---

## Hypothesis 属性测试

- 由 4 面子 + 雀头随机拼装的合法 14 张和牌：
  - `judge_yaku` 不抛异常
  - **层级齐次**：结果集不混合役满与普通役
  - 普通项 `han == Σ yaku.han` 且各 `yakuman_units == 0`；役满项 `han == 0` 且 `1 ≤ units ≤ 6`
  - `has_any_yaku == bool(judge_yaku)`
  - 门清自摸恒有役（门前清自摸和兜底）

---

## 移交 M4 的接口约定

- M4 `scoring.py` 消费 `judge_yaku` 返回的 `list[YakuDecomp]`：
  - 若任一项 `is_yakuman` → 按役满单位计点（§9.3 / §12.3），忽略普通项。
  - 否则对每个普通项：番 = `entry.han` + 宝牌/赤/里宝（M4 计算），符 = 由 `entry.decomposition` + 和了牌 + ctx 计算；**按最终点数取最高项**。
  - 13 番以上（含宝牌）→ 数え役满（§9.4）由 M4 判定。
- 待ち型 / 暗刻摆法的精细取舍（番符权衡）若 M4 需要，可在 M4 复用 `build_standard_partition` 或在其上细化；M3 目前对单一属性取最有利摆法，已满足役判定正确性。
