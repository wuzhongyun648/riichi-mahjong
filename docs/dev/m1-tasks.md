# M1 任务进度 —— 数据与状态层

**目标**：能洗牌、发牌、构造合法初始 GameState。不做听牌、役、点数、状态转移。

**验收**：`uv run pytest` 全绿；种子可复现完整初始局面；hypothesis 属性测试覆盖牌山不变量和字符串 round-trip。

---

## 进度

| 文件 | 状态 | 说明 |
|---|---|---|
| `docs/rules.md` | ✅ 已定线 | 全部条款已审阅，`[FIX]` 标记 |
| `docs/tile-encoding.md` | ✅ 已完成 | 编码规范，可直接参考 |
| `docs/dev/m1-tasks.md` | ✅ 本文档 | |
| `engine/src/mahjong_engine/tiles.py` | ✅ 完成 | |
| `engine/src/mahjong_engine/hand.py` | ✅ 完成 | |
| `engine/src/mahjong_engine/rng.py` | ✅ 完成 | |
| `engine/src/mahjong_engine/wall.py` | ✅ 完成 | |
| `engine/src/mahjong_engine/game_state.py` | ✅ 完成 | |
| `engine/tests/test_tiles.py` | ✅ 完成 | 含 hypothesis 属性测试 |
| `engine/tests/test_hand.py` | ✅ 完成 | 含 hypothesis 属性测试 |
| `engine/tests/test_wall.py` | ✅ 完成 | 含 hypothesis 属性测试 |
| `engine/tests/test_game_state.py` | ✅ 完成 | 含 hypothesis 属性测试 |

**测试结果（2026-05-23）**：115 / 115 全绿，0 失败。

**已发现并修复的 bug**：
- `is_terminal(8)` 返回 False（9m 未被识别为老头牌）。原因：`tile % 9 == 0` 只检查了"1"牌，忘记了"9"牌（position 8）。修复：`pos == 0 or pos == 8`。

---

## 关键决策记录（rules.md 审阅时确认）

| 决策 | 值 | rules.md 章节 |
|---|---|---|
| 支持东风战 + 半庄战 | 两种均实现 | §1.1 |
| 起始分 | 25,000 | §1.2 |
| 顺位马 | +15/+5/−5/−15（两种形式一致） | §1.3 |
| 飞出条件 | 负数时（0 点可继续） | §1.5 |
| 延长战（西入） | 启用 | §1.6 |
| 赤五 | 各 1 张，共 3 张 | §2.1 |
| 王牌区 | 14 张（表宝 5 + 里宝 5 + 岭上 4） | §3.2 |
| 七对子底符 | 固定 25 符 | §9.1 |
| 切上满贯 | **不启用** | §9.2 |
| 数え役满 | 启用（13番以上） | §9.4 |
| 人和 | **无此役** | §8.5 / §10.3 |
| 双役满列表 | 国士十三面、四暗刻单骑、大四喜、純正九蓮 | §8.6 |
| 暗杠翻宝牌时机 | 暗杠：摸岭上前翻；明杠/加杠：打牌后翻 | §6.4 |
| 四杠流局 | 2+ 不同玩家开杠才触发 | §5.3 |
| 食替 | 全面禁止（直接+间接+面子） | §7.2 |

---

## 接口约定（实现时遵守）

### tiles.py
```python
# 主要导出
TILE_COUNT: int = 34
is_manzu(t) / is_pinzu(t) / is_souzu(t) / is_honor(t)
is_wind(t) / is_dragon(t) / is_terminal(t) / is_yaochuuhai(t)
tile_to_str(tile, is_aka=False) -> str
parse_tile(s) -> tuple[int, bool]   # (code, is_aka)
parse_tiles(s) -> list[tuple[int, bool]]
next_dora(indicator) -> int
make_counts(tiles) -> list[int]
```

### hand.py
```python
class MeldType(Enum): CHI, PON, KAN_OPEN, KAN_ADDED, KAN_CLOSED
@dataclass(frozen=True) class Meld: type, tiles, called_from, called_tile, aka_flags
@dataclass(frozen=True) class Hand: counts, melds, aka_5m, aka_5p, aka_5s
    .add_tile(tile, is_aka) -> Hand
    .remove_tile(tile, remove_aka=False) -> Hand
    .from_str(s) -> Hand   # classmethod
```

### rng.py
```python
shuffled(items, seed=None) -> list  # seedable shuffle
```

### wall.py
```python
@dataclass(frozen=True) class WallTile: code, is_aka
@dataclass(frozen=True) class WallState: tiles, live_pos, rinshan_drawn, dora_revealed
    .live_remaining -> int
    .dead_wall -> tuple[WallTile, ...]
    .dora_indicators -> tuple[WallTile, ...]
    .active_dora_tiles -> tuple[int, ...]
    .ura_indicators -> tuple[WallTile, ...]
    .peek_live() -> WallTile
    .peek_rinshan() -> WallTile
build_wall(mode="yonma", seed=None) -> WallState
```

### game_state.py
```python
class Wind(Enum): EAST, SOUTH, WEST, NORTH
class GameMode(Enum): EAST, HALF
@dataclass(frozen=True) class PlayerState: hand, river, score, seat_wind, in_riichi, riichi_turn, double_riichi
@dataclass(frozen=True) class GameState: mode, round_wind, round_number, honba, riichi_sticks, dealer_index, active_player_index, players, wall, turn_count
new_game(mode, dealer_index, seed) -> GameState
```
