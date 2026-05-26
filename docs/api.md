# API 协议 —— REST + WebSocket

**当前状态：占位文档，Stage C（M7）开始填充。**

本文档将定义：

- **REST**（鉴权 / 房间管理 / 牌谱查询）
  - `POST /auth/login`
  - `GET  /rooms` / `POST /rooms`
  - `GET  /replays/{id}`
- **WebSocket**（实时对局）
  - 客户端 → 服务端事件：`discard` / `chi` / `pon` / `kan` / `riichi` / `tsumo` / `ron` / `pass`
  - 服务端 → 客户端事件：`game_start` / `deal_tile` / `tile_discarded` / `wait_action` / `meld_made` / `game_end` / `room_state` / `error`
- **JSON schema**（与 `server/` 中 Pydantic 模型一一对应）
- **牌谱兼容**：导出格式与 Tenhou JSON 互转

设计原则（M7 前确认）：

1. **服务端权威**：所有合法性判定由服务端做，客户端事件只是"意图请求"
2. **最小公开信息**：发牌时只对单一玩家推送其手牌，他家只收到摸牌事件（不含牌型）
3. **断线重连**：服务端保留房间完整状态，客户端重连可重建 UI
4. **字符串牌型**：协议层用 `"1m"` 风格字符串（便于调试），不传 `int[34]`

字符串形式（中英文二选一）见 [`docs/tile-encoding.md`](tile-encoding.md) 第 4 节，**M7 启动前必须定线**。
