# Claude Code 使用指南


## 对话管理

### 新建对话
- `claude` — 在当前目录新建会话
- `claude -n task-name` — 新建并命名会话
- `/clear` — 清空当前上下文（历史仍保存）

### 恢复历史对话
- `claude --continue` — 恢复最近一次会话
- `claude --resume` — 打开会话选择器，浏览所有历史对话
- `claude --resume session-name` — 按名称恢复指定会话
- `/resume` — 在会话内切换到其他对话

### 上下文管理
- `/context` — 查看上下文窗口占用情况
- `/compact` — 手动压缩对话历史

### 其他常用命令
- `/rename new-name` — 重命名当前会话
- `/branch branch-name` — 分支当前会话，保留原始对话
- `/export` — 导出对话内容到文件

## 会话存储位置

```
~/.claude/projects/<project-name>/<session-id>.jsonl
```

## 最佳实践

- 将持久规则和项目背景写在 `CLAUDE.md`，每次新建会话自动加载
- 用 `-n` 给重要会话命名，便于后续用 `--resume` 快速恢复
- 对话变长时用 `/compact` 压缩，避免上下文超限
