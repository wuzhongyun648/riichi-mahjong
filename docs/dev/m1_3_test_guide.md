# M1 + M2 + M3 验收 / 试玩指南

本文件列出当前已实现模块（M1 数据状态层 + M2 听牌与待ち + M3 役判定）可以
**手动验证**的所有功能，每条都附「**执行命令**」与「**期望输出**」。所有命令
已在 `conda activate riichi` 环境下实际跑通。

适用范围：
- 想验收 M1 / M2 / M3 是否完整？— 按顺序跑 §1 ~ §3 即可
- 想 demo 给别人看？— §4（M1）/ §5（M2）/ §5b（M3）全是可直接复制粘贴的 Python
- 想检查改了某模块后是否回归？— §1 是底线
- M3 役判定还附带一套**金标准回归集**（转写自 MahjongRepository/mahjong），见 §5b.3

---

## 0. 前置条件

```bash
cd ~/projects/riichi-mahjong/engine
conda activate riichi
```

后续所有命令均假设你在 `engine/` 目录下、`riichi` 环境已激活。

---

## 1. 一键全测试（必跑）

```bash
python -m pytest tests/ -q
```

**期望输出（末尾 1 行）**：
```
358 passed in ~2s
```

358 个用例分布：

| 模块 | 文件 | 用例数 |
|---|---|---:|
| tiles | `tests/test_tiles.py` | 42 |
| hand | `tests/test_hand.py` | 27 |
| wall | `tests/test_wall.py` | 27 |
| game_state | `tests/test_game_state.py` | 23 |
| rng | `tests/test_rng.py` | 1 |
| **M1 小计** | | **120** |
| decompose | `tests/test_decompose.py` | 32 |
| tenpai | `tests/test_tenpai.py` | 77 |
| **M2 小计** | | **109** |
| situational | `tests/test_yaku_situational.py` | 14 |
| structural | `tests/test_yaku_structural.py` | 45 |
| yakuman | `tests/test_yaku_yakuman.py` | 20 |
| judge（编排/错误） | `tests/test_yaku_judge.py` | 7 |
| property（hypothesis） | `tests/property/test_yaku_property.py` | 2 |
| golden（MahjongRepository 回归） | `tests/golden/test_yaku_golden.py` | 41 |
| **M3 小计** | | **129** |
| **总计** | | **358** |

只跑 M2 两个模块：

```bash
python -m pytest tests/test_decompose.py tests/test_tenpai.py -v
```

只跑 M3 全部：

```bash
python -m pytest tests/test_yaku_situational.py tests/test_yaku_structural.py \
  tests/test_yaku_yakuman.py tests/test_yaku_judge.py \
  tests/property/test_yaku_property.py tests/golden/ -v
```

显示 hypothesis 属性测试样本统计：

```bash
python -m pytest tests/ --hypothesis-show-statistics 2>&1 | grep -A2 "Hypothesis"
```

---

## 2. 静态检查

```bash
python -m mypy --strict src/
python -m ruff check src/ tests/
```

- **mypy** 应零错误（M1+M2 全部带类型标注）
- **ruff** 仅余 8 条 `RUF002`（中文 docstring 内的全角 `−` 等），属项目约定保留

---

## 3. 复现性自检

种子可复现是后续牌谱回放和 bug 重现的基础：

```bash
python -c "
from mahjong_engine.wall import build_wall
w1 = build_wall(mode='yonma', seed=42)
w2 = build_wall(mode='yonma', seed=42)
w3 = build_wall(mode='yonma', seed=43)
print('same seed reproduces :', w1.tiles == w2.tiles)
print('diff seed differs    :', w1.tiles != w3.tiles)
"
```

**期望**：
```
same seed reproduces : True
diff seed differs    : True
```

---

## 4. M1 模块逐项 demo

### 4.1 tiles — 牌编码 / 字符串 / 判定

```bash
python -c "
from mahjong_engine.tiles import (
    parse_tile, parse_tiles, tile_to_str, tiles_to_str,
    is_manzu, is_honor, is_wind, is_dragon, is_terminal, is_yaochuuhai,
    tile_number, tile_suit, next_dora, make_counts, counts_to_tiles,
)

# 1. 单牌 / 多牌字符串解析
print('parse 5m         :', parse_tile('5m'))
print('parse 赤5m       :', parse_tile('赤5m'))
print('parse 东         :', parse_tile('东'))
ts = parse_tiles('1m 2m 3m 赤5p 东 东')
print('parse_tiles      :', ts)

# 2. 反向：tile → string
print('tile_to_str(4)   :', tile_to_str(4))
print('tile_to_str(4,T) :', tile_to_str(4, True))
print('tiles_to_str     :', tiles_to_str(ts))

# 3. 判定函数
for t in [0, 9, 18, 27, 31]:
    print(f'  tile {t:2d} ({tile_to_str(t):>3s}): honor={is_honor(t)} '
          f'wind={is_wind(t)} dragon={is_dragon(t)} terminal={is_terminal(t)} '
          f'yaochuu={is_yaochuuhai(t)}')

# 4. 数字 / 花色
print('number(13)       :', tile_number(13), 'suit:', tile_suit(13))

# 5. 宝牌指示推算
for ind in [0, 8, 17, 30, 33]:
    print(f'  next_dora({ind} {tile_to_str(ind):>3s}) -> {next_dora(ind)} ({tile_to_str(next_dora(ind))})')

# 6. counts 互转
counts = make_counts([0, 0, 1, 2, 27, 27])
print('counts[0..3]     :', counts[:4], '... counts[27] =', counts[27])
print('back to tiles    :', counts_to_tiles(counts))
"
```

**期望输出**：
```
parse 5m         : (4, False)
parse 赤5m       : (4, True)
parse 东         : (27, False)
parse_tiles      : [(0, False), (1, False), (2, False), (13, True), (27, False), (27, False)]
tile_to_str(4)   : 5m
tile_to_str(4,T) : 赤5m
tiles_to_str     : 1m 2m 3m 赤5p 东 东
  tile  0 ( 1m): honor=False wind=False dragon=False terminal=True yaochuu=True
  tile  9 ( 1p): honor=False wind=False dragon=False terminal=True yaochuu=True
  tile 18 ( 1s): honor=False wind=False dragon=False terminal=True yaochuu=True
  tile 27 (  东): honor=True wind=True dragon=False terminal=False yaochuu=True
  tile 31 (  白): honor=True wind=False dragon=True terminal=False yaochuu=True
number(13)       : 5 suit: p
  next_dora(0  1m) -> 1 (2m)
  next_dora(8  9m) -> 0 (1m)
  next_dora(17  9p) -> 9 (1p)
  next_dora(30   北) -> 27 (东)
  next_dora(33   中) -> 31 (白)
counts[0..3]     : [2, 1, 1, 0] ... counts[27] = 2
back to tiles    : [0, 0, 1, 2, 27, 27]
```

（输出里的对齐空格仅来自 `:>3s` 格式，留意 `dora_indicator(8m) → 9m`、`9m → 1m`、
`9p → 1p`、`北 → 东`、`中 → 白` 等绕回行为。）

---

### 4.2 hand — 手牌容器 / 副露

```bash
python -c "
from mahjong_engine.hand import Hand, Meld, MeldType
from mahjong_engine.tiles import tile_to_str

# 1. 直接从字符串构造 13 张手
h = Hand.from_str('1m 2m 3m 赤5p 7p 8p 9p 1s 2s 3s 东 东 东')
print('tile_count:', h.tile_count, 'aka_count:', h.aka_count, 'aka_5p:', h.aka_5p)
print('meld_count:', h.meld_count)

# 2. 增删（返回新 Hand，原对象不变）
h2 = h.add_tile(8)   # +9m
print('after +9m  total:', h2.tile_count)
h3 = h2.remove_tile(0)
print('after -1m  total:', h3.tile_count)

# 3. 副露
chi = Meld(type=MeldType.CHI, tiles=(0, 1, 2), called_from=3, called_tile=0)
print('chi meld:', [tile_to_str(t) for t in chi.tiles], 'type:', chi.type.value)
h_with_chi = Hand.empty().add_meld(chi)
print('hand with 1 meld:', h_with_chi.meld_count)
"
```

**期望输出**：
```
tile_count: 13 aka_count: 1 aka_5p: True
meld_count: 0
after +9m  total: 14
after -1m  total: 13
chi meld: ['1m', '2m', '3m'] type: chi
hand with 1 meld: 1
```

---

### 4.3 wall — 牌山 / 宝牌指示

```bash
python -c "
from mahjong_engine.wall import build_wall
from mahjong_engine.tiles import tile_to_str

w = build_wall(mode='yonma', seed=42)
print('total tiles    :', len(w.tiles))
print('live remaining :', w.live_remaining)
print('dead wall size :', len(w.dead_wall))
print('dora_revealed  :', w.dora_revealed)
ind = w.dora_indicators[0]
print('dora indicator :', tile_to_str(ind.code, ind.is_aka))
print('active dora    :', [tile_to_str(t) for t in w.active_dora_tiles])
print('next live      :', tile_to_str(w.peek_live().code, w.peek_live().is_aka))
"
```

**期望输出**（种子 42 下确定性）：
```
total tiles    : 136
live remaining : 122
dead wall size : 14
dora_revealed  : 1
dora indicator : 8m
active dora    : ['9m']
next live      : 6m
```

> 注：换 `seed=` 会改变结果但仍满足上述结构。

---

### 4.4 rng — 种子化洗牌

```bash
python -c "
from mahjong_engine.rng import shuffled
print('seed 42 #1 :', shuffled([1,2,3,4,5], seed=42))
print('seed 42 #2 :', shuffled([1,2,3,4,5], seed=42))
print('seed 43    :', shuffled([1,2,3,4,5], seed=43))
"
```

**期望输出**：
```
seed 42 #1 : [4, 2, 3, 5, 1]
seed 42 #2 : [4, 2, 3, 5, 1]
seed 43    : [2, 5, 4, 3, 1]
```

---

### 4.5 game_state — 整局初始化

```bash
python -c "
from mahjong_engine.game_state import new_game, GameMode
from mahjong_engine.tiles import tile_to_str

gs = new_game(mode=GameMode.HALF, dealer_index=0, seed=42)
print('mode          :', gs.mode.value)
print('round         :', gs.round_wind.name, gs.round_number)
print('honba         :', gs.honba, 'sticks:', gs.riichi_sticks)
print('dealer        :', gs.dealer_index, 'active:', gs.active_player_index)
print('wall remaining:', gs.wall.live_remaining)
for i, p in enumerate(gs.players):
    print(f'  seat {i} ({p.seat_wind.name:5s}) hand={p.hand.tile_count} tiles, score={p.score}')
# 庄家手牌展开
dealer = gs.players[0].hand
tiles = []
for t, c in enumerate(dealer.counts):
    tiles.extend([tile_to_str(t)] * c)
print('dealer hand   :', ' '.join(tiles))
"
```

**期望输出**：
```
mode          : half
round         : EAST 1
honba         : 0 sticks: 0
dealer        : 0 active: 0
wall remaining: 69
  seat 0 (EAST ) hand=14 tiles, score=25000
  seat 1 (SOUTH) hand=13 tiles, score=25000
  seat 2 (WEST ) hand=13 tiles, score=25000
  seat 3 (NORTH) hand=13 tiles, score=25000
dealer hand   : 1m 3m 5m 6m 7p 1s 4s 7s 8s 9s 9s 发 中 中
```

> 庄家发 14 张（含第一张摸入），其他 3 家 13 张。牌山初始有 136 张，发完 53 张后剩 `136 − 53 − 14(王牌) = 69` 张 live。

---

## 5. M2 模块逐项 demo

### 5.1 decompose — 和牌分解

```bash
python -c "
from mahjong_engine.tiles import parse_tiles, make_counts, tile_to_str
from mahjong_engine.decompose import (
    standard_decompositions, chiitoitsu_decomposition,
    kokushi_decomposition, all_decompositions, is_complete_hand,
)

def to_counts(s):
    return make_counts([t for t,_ in parse_tiles(s)])

def show_decomp(d):
    blocks = []
    for b in d.blocks:
        blocks.append('-'.join(tile_to_str(t) for t in b.tiles))
    pair_s = '' if d.pair_tile is None else f'  pair={tile_to_str(d.pair_tile)}'
    return f'{d.form.name:9s} [{\" \".join(blocks)}]{pair_s}'

# 1. 标准型多分解
counts = to_counts('1m 1m 1m 2m 3m 4m 2m 3m 4m 2m 3m 4m 5m 5m')
decomps = standard_decompositions(counts)
print(f'== standard, multi-decomp ({len(decomps)} forms) ==')
for d in decomps:
    print(' ', show_decomp(d))

# 2. 七対子
counts = to_counts('1m 1m 3m 3m 5p 5p 7p 7p 1s 1s 3s 3s 东 东')
print('== chiitoitsu ==')
print(' ', show_decomp(chiitoitsu_decomposition(counts)))

# 3. 国士無双
counts = to_counts('1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中 中')
print('== kokushi (pair on 中) ==')
print(' ', show_decomp(kokushi_decomposition(counts)))

# 4. is_complete_hand
print('== is_complete_hand ==')
print('  14-tile standard   :', is_complete_hand(to_counts('1m 1m 1m 2m 3m 4m 5p 5p 5p 6p 7p 8p 东 东')))
print('  14-tile chiitoi    :', is_complete_hand(to_counts('1m 1m 3m 3m 5p 5p 7p 7p 1s 1s 3s 3s 东 东')))
print('  13-tile (not win)  :', is_complete_hand(to_counts('1m 2m 3m 4m 5m 6m 7m 6p 7p 8p 1s 1s 1s')))
"
```

**期望输出**：
```
== standard, multi-decomp (4 forms) ==
  STANDARD  [1m-1m-1m 2m-3m-4m 3m-4m-5m 3m-4m-5m 2m-2m]  pair=2m
  STANDARD  [1m-1m-1m 2m-2m-2m 3m-3m-3m 4m-4m-4m 5m-5m]  pair=5m
  STANDARD  [1m-1m-1m 2m-3m-4m 2m-3m-4m 2m-3m-4m 5m-5m]  pair=5m
  STANDARD  [1m-2m-3m 1m-2m-3m 1m-2m-3m 4m-4m-4m 5m-5m]  pair=5m
== chiitoitsu ==
  CHIITOITSU [1m-1m 3m-3m 5p-5p 7p-7p 1s-1s 3s-3s 东-东]
== kokushi (pair on 中) ==
  KOKUSHI   [中-中]  pair=中
== is_complete_hand ==
  14-tile standard   : True
  14-tile chiitoi    : True
  13-tile (not win)  : False
```

> 同一手牌可能有 4 种标准分解 —— M3 役判定阶段会按番取最高（CLAUDE.md §5）。

---

### 5.2 tenpai — 向听 / 听牌 / 待ち

下面 1 个脚本覆盖**所有听牌型 + 副露 + n-shanten + 14 张和牌**：

```bash
python -c "
from mahjong_engine.tiles import parse_tiles, make_counts, tile_to_str
from mahjong_engine.hand import Meld, MeldType
from mahjong_engine.tenpai import shanten, is_tenpai, winning_tiles

def to_counts(s):
    return make_counts([t for t,_ in parse_tiles(s)])

def show(label, counts, melds=()):
    sh = shanten(counts, melds)
    if sh == -1:
        print(f'{label:30s} -> COMPLETE')
        return
    if sum(counts) + 3*len(melds) == 13:
        w = winning_tiles(counts, melds)
        print(f'{label:30s} -> shanten={sh} tenpai={is_tenpai(counts, melds)} waits={[tile_to_str(t) for t in w]}')
    else:
        print(f'{label:30s} -> shanten={sh}')

print('== 标准型听法 ==')
show('三面 1m/4m/7m',  to_counts('1m 2m 3m 4m 5m 6m 7m 6p 7p 8p 1s 1s 1s'))
show('嵌张 2m',        to_counts('1m 3m 4p 5p 6p 7p 8p 9p 1s 2s 3s 东 东'))
show('边张 3m',        to_counts('1m 2m 4p 5p 6p 7p 8p 9p 1s 2s 3s 东 东'))
show('单骑 东',         to_counts('1m 2m 3m 4m 5m 6m 7m 8m 9m 6p 7p 8p 东'))
show('双碰 5m/9p',     to_counts('1m 2m 3m 4p 5p 6p 7s 8s 9s 5m 5m 9p 9p'))
show('九面 1m..9m',    to_counts('1m 1m 1m 2m 3m 4m 5m 6m 7m 8m 9m 9m 9m'))

print('== 七対子 / 国士 ==')
show('七対子単騎 东',     to_counts('1m 1m 3m 3m 5p 5p 7p 7p 1s 1s 3s 3s 东'))
show('国士単騎 中',       to_counts('1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 发'))
show('国士十三面',        to_counts('1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中'))

print('== 副露场景 ==')
chi_123m = Meld(type=MeldType.CHI, tiles=(0,1,2), called_from=3, called_tile=0)
pon_dong = Meld(type=MeldType.PON, tiles=(27,27,27), called_from=1, called_tile=27)
show('1 chi 123m, 暗 10 张',  to_counts('4m 5m 6m 7p 8p 9p 7s 8s 8s 9s'), melds=(chi_123m,))
show('2 副露, 暗 7 张',       to_counts('1m 2m 3m 6p 7p 8p 5s'),           melds=(chi_123m, pon_dong))

print('== n-shanten ==')
show('1-shanten',         to_counts('1m 2m 3m 4p 5p 6p 7s 8s 9s 5m 5m 东 南'))
show('2-shanten',         to_counts('1m 2m 3m 4p 5p 6p 7s 8s 东 东 南 西 北'))

print('== 14 张和牌检测 ==')
show('已和',              to_counts('1m 2m 3m 4m 5m 6m 7m 8m 9m 6p 7p 8p 东 东'))
"
```

**期望输出**：
```
== 标准型听法 ==
三面 1m/4m/7m                  -> shanten=0 tenpai=True waits=['1m', '4m', '7m']
嵌张 2m                        -> shanten=0 tenpai=True waits=['2m']
边张 3m                        -> shanten=0 tenpai=True waits=['3m']
单骑 东                         -> shanten=0 tenpai=True waits=['东']
双碰 5m/9p                     -> shanten=0 tenpai=True waits=['5m', '9p']
九面 1m..9m                    -> shanten=0 tenpai=True waits=['1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m']
== 七対子 / 国士 ==
七対子単騎 东                     -> shanten=0 tenpai=True waits=['东']
国士単騎 中                       -> shanten=0 tenpai=True waits=['中']
国士十三面                        -> shanten=0 tenpai=True waits=['1m', '9m', '1p', '9p', '1s', '9s', '东', '南', '西', '北', '白', '发', '中']
== 副露场景 ==
1 chi 123m, 暗 10 张           -> shanten=0 tenpai=True waits=['8s']
2 副露, 暗 7 张                 -> shanten=0 tenpai=True waits=['5s']
== n-shanten ==
1-shanten                      -> shanten=1 tenpai=False waits=[]
2-shanten                      -> shanten=2 tenpai=False waits=[]
== 14 张和牌检测 ==
已和                            -> COMPLETE
```

---

## 5b. M3 模块逐项 demo

### 5b.1 judge_yaku — 役判定

`judge_yaku(hand, win_tile, ctx)` 返回 `list[YakuDecomp]`：每个**有役分解**
一项；命中役满时只返回役满项（层级齐次），由 M4 结合符数按点数取最高。
宝牌 / 赤 / 里宝 / 数え役満不在此计入（归 M4）。

```bash
python -c "
from mahjong_engine.hand import Hand, Meld, MeldType
from mahjong_engine.game_state import Wind
from mahjong_engine.yaku import judge_yaku, has_any_yaku, WinContext
from mahjong_engine.tiles import parse_tile

def best(res):
    if not res: return 'NO YAKU (役なし)'
    e = max(res, key=lambda x:(x.yakuman_units, x.han))
    if e.is_yakuman:
        return 'yakuman x%d :: %s' % (e.yakuman_units, sorted(y.id for y in e.yaku))
    return '%d han :: %s' % (e.han, [(y.id, y.han) for y in e.yaku])

def J(s, w, melds=(), rw=Wind.EAST, sw=Wind.SOUTH, tsumo=True, **f):
    h = Hand.from_str(s, melds=melds)
    return judge_yaku(h, parse_tile(w)[0], WinContext(round_wind=rw, seat_wind=sw, is_tsumo=tsumo, **f))

chun = Meld(type=MeldType.PON, tiles=(33,33,33), called_from=1, called_tile=33)
chi_1s = Meld(type=MeldType.CHI, tiles=(18,19,20), called_from=3, called_tile=18)

print('riichi+pinfu+tanyao tsumo :', best(J('2m 3m 4m 5m 6m 7m 3p 4p 5p 6p 7p 8p 2s 2s', '4m', is_riichi=True)))
print('open yakuhai chun ron    :', best(J('1m 2m 3m 4p 5p 6p 7s 8s 9s 5s 5s', '3m', melds=(chun,), tsumo=False)))
print('chiitoitsu ron           :', best(J('1m 1m 3m 3m 5p 5p 7p 7p 1s 1s 3s 3s 东 东', '东', tsumo=False)))
print('suuankou tanki ron       :', best(J('1m 1m 1m 5p 5p 5p 9s 9s 9s 东 东 东 2p 2p', '2p', tsumo=False)))
print('kokushi 13-men           :', best(J('1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中 中', '中')))
print('tsuuiisou+daisangen ron  :', best(J('白 白 白 发 发 发 中 中 中 东 东 东 南 南', '东', tsumo=False)))
print('open no-yaku ron         :', best(J('7m 8m 9m 1p 2p 3p 4p 5p 6p 9m 9m', '7m', melds=(chi_1s,), tsumo=False)))
"
```

**期望输出**：
```
riichi+pinfu+tanyao tsumo : 4 han :: [('tanyao', 1), ('pinfu', 1), ('riichi', 1), ('menzen_tsumo', 1)]
open yakuhai chun ron    : 1 han :: [('yakuhai_chun', 1)]
chiitoitsu ron           : 2 han :: [('chiitoitsu', 2)]
suuankou tanki ron       : yakuman x2 :: ['suuankou_tanki']
kokushi 13-men           : yakuman x2 :: ['kokushi_13']
tsuuiisou+daisangen ron  : yakuman x2 :: ['daisangen', 'tsuuiisou']
open no-yaku ron         : NO YAKU (役なし)
```

> 注意：第 1 例 `judge` 默认 `tsumo=True`，故含门前清自摸和；第 6 例改 `tsumo=False`
> 荣和点和，否则四个暗刻会再叠四暗刻（变 3 倍役満）。荣和点和的刻子视为明刻
> 是 §8.8 的关键裁定，也是第 4 例「四暗刻单骑」能成立、普通双碰荣和却降为三暗刻的原因。

### 5b.2 has_any_yaku — 是否可和（供 M5 振听/荣和合法性）

```bash
python -c "
from mahjong_engine.hand import Hand
from mahjong_engine.game_state import Wind
from mahjong_engine.yaku import has_any_yaku, WinContext
from mahjong_engine.tiles import parse_tile
h = Hand.from_str('2m 3m 4m 5m 6m 7m 3p 4p 5p 6p 7p 8p 2s 2s')
ctx = WinContext(round_wind=Wind.EAST, seat_wind=Wind.SOUTH, is_tsumo=True)
print('has_any_yaku :', has_any_yaku(h, parse_tile('4m')[0], ctx))
"
```

**期望输出**：
```
has_any_yaku : True
```

> `WinContext` 的场况 flag（`is_riichi/is_ippatsu/is_haitei/is_houtei/is_rinshan/`
> `is_chankan/is_tenhou/is_chiihou/is_double_riichi`）由调用方（M5）提供，M3 不自行推导。
> `round_wind/seat_wind/is_tsumo` 为必填。

### 5b.3 金标准回归集（MahjongRepository/mahjong）

`tests/golden/test_yaku_golden.py` 转写自开源库 MahjongRepository/mahjong 的
`tests_yaku_calculation.py` / `tests_yakuman_calculation.py`，共 41 条「手牌 → 役」
用例，覆盖全部 1~6 番役（含食断/副露降番）与全部役满（含国士十三面、纯正九莲、
四暗刻单骑、字一色+大三元双役满等）。每条逆向验证我们 `judge_yaku` 命中的役 id
与番数 / 役满倍数。规则映射说明见该文件头部 docstring（雀魂段位场 vs 该库默认配置）。

```bash
python -m pytest tests/golden/ -q
```

**期望输出**：
```
41 passed
```

---

## 6. 接口速查表

| 模块 | 函数 / 类 | 用途 |
|---|---|---|
| `tiles` | `parse_tile(s)` / `parse_tiles(s)` | 字符串 → `(tile_id, is_aka)` |
| `tiles` | `tile_to_str(t, is_aka=False)` | tile_id → 字符串（含赤五） |
| `tiles` | `make_counts(tiles)` / `counts_to_tiles(counts)` | counts 互转 |
| `tiles` | `is_manzu / is_pinzu / is_souzu / is_honor / is_wind / is_dragon / is_terminal / is_yaochuuhai / is_chuuchanpai / is_suited` | 牌属性判定 |
| `tiles` | `tile_number(t)` / `tile_suit(t)` | 取数字 / 花色 |
| `tiles` | `next_dora(indicator)` | 宝牌指示 → 实际宝牌 |
| `hand` | `Hand.empty()` / `Hand.from_str(s)` / `Hand.from_tile_list(...)` | 构造 |
| `hand` | `hand.add_tile / remove_tile / add_meld` | 返回新 Hand（不可变） |
| `hand` | `Meld(type, tiles, called_from, called_tile, aka_flags)` | 副露描述 |
| `wall` | `build_wall(mode='yonma', seed=None)` | 构造牌山 |
| `wall` | `WallState.live_remaining / dead_wall / dora_indicators / active_dora_tiles / ura_indicators / peek_live / peek_rinshan` | 牌山属性 |
| `rng` | `shuffled(items, seed=None)` | 可复现洗牌 |
| `game_state` | `new_game(mode, dealer_index, seed)` | 整局初始化 |
| `game_state` | `GameState` / `PlayerState` / `Wind` / `GameMode` | 状态类型 |
| `decompose` | `standard_decompositions(counts)` | 标准型全部分解 |
| `decompose` | `chiitoitsu_decomposition(counts)` | 七対子分解（成立时返回，否则 None） |
| `decompose` | `kokushi_decomposition(counts)` | 国士無双分解 |
| `decompose` | `all_decompositions(counts)` | 三种形态合并 |
| `decompose` | `is_complete_hand(counts, n_melds=0)` | 14 张是否和牌 |
| `tenpai` | `shanten(counts, melds=())` | 向听数（−1 = 和） |
| `tenpai` | `is_tenpai(counts, melds=())` | 13 张相位是否听牌 |
| `tenpai` | `winning_tiles(counts, melds=())` | 听哪几张（升序 tile_id） |
| `yaku` | `judge_yaku(hand, win_tile, ctx)` | 役判定，返回 `list[YakuDecomp]`（层级齐次，每有役分解一项） |
| `yaku` | `has_any_yaku(hand, win_tile, ctx)` | 是否存在合法役（= judge 非空） |
| `yaku` | `WinContext(round_wind, seat_wind, is_tsumo, ...)` | 场况上下文（立直/一发/海底/天地和等 flag） |
| `yaku` | `YakuDecomp(.yaku, .han, .yakuman_units, .decomposition)` | 单分解结果；`.is_yakuman` / `.has_yaku` |
| `yaku` | `Yaku(.id, .name, .han, .yakuman_units)` | 单个役（id 英文、name 中文） |

---

## 7. 故障排查

| 报错 | 原因 | 解决 |
|---|---|---|
| `ImportError: cannot import name ...` | 复制了错的 API 名 | 对照 §6 速查表 |
| `ValueError: counts must have length 34` | 传了普通 list 而不是 34 长 counts | 用 `make_counts(...)` |
| `ValueError: hand has N tiles ...` | counts 与副露加起来不是 13 / 14 | 检查 `sum(counts) + 3*len(melds)` |
| `ValueError: is_tenpai requires a post-discard hand` | 14 张相位调用了 `is_tenpai` | 改用 `shanten(...) == -1` 判和 |
| pytest 提示 `No module named mahjong_engine` | 没在 engine/ 目录跑 / 没装包 | `cd engine && pip install -e .` 或确认环境 |

---

## 8. 当前未实现 / 等 M4+

下列功能**当前阶段（M1+M2+M3）不支持**，调用会失败或返回不完整结果：

- 番符计算 / 点数结算（含宝牌/赤/里宝累加、数え役満、切上、本场/积棒）→ M4
- 振听判定 / 立直流程 / 状态机 → M5
- 牌谱解析 / 输出 → M6
- 听牌时每张听牌剩余枚数（UI 用）→ 随 M7 联机 demo 实装
- 3 麻规则 / AI → Stage D

> M3 役判定**已实现**（见 §5b）：`judge_yaku` 给出役 + 番 / 役满倍数，但**不含**
> 宝牌与最终点数——取最高分解、符算、累计役满判定都在 M4 完成。待ち型分类
> （两面/嵌张/边张/单骑/双碰）已在 `yaku/partition.py` 内部用于平和与四暗刻单骑
> 判定，M4 算符时可复用。
