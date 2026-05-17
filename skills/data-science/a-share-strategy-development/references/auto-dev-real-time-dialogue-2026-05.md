# 自动研发实时对话流（2026-05-17）

## 背景

`app.pyw` 的 `auto_develop()` 方法原本只显示前 5 行 Hermes 输出，其余在完成后一次性 dump。用户要求改为"hermes 和 ai 的实时对话"。

## 改动

### 1. 移除 5 行限制

**文件**: `app.pyw` line ~1212

```python
# ❌ 旧：仅显示前5行
if len(out_lines) <= 5:
    q.put(("line", line.rstrip()))

# ✅ 新：所有行实时推送
q.put(("line", line.rstrip()))
```

### 2. 对话风格彩色标签

在 `dev_text` 创建后（line ~673）添加 tag_configure：

```python
self.dev_text.tag_configure("chat_user", foreground="#58a6ff", font=("Consolas", 13, "bold"))
self.dev_text.tag_configure("chat_ai", foreground="#56d364")
self.dev_text.tag_configure("chat_tool", foreground="#bc8cff")
self.dev_text.tag_configure("chat_code", foreground="#e3b341")
self.dev_text.tag_configure("chat_err", foreground="#f85149", font=("Consolas", 13, "bold"))
self.dev_text.tag_configure("chat_sep", foreground="#484f58")
```

### 3. 智能行配色（poll 函数）

根据内容模式自动匹配 tag：

| 模式 | 标签 | 颜色 |
|------|------|------|
| 空行 | 无 | 默认 |
| `Error`/`Traceback`/`错误` | `chat_err` | 红加粗 |
| 以 ``` 开头 | `chat_code` | 金 |
| 含 `›`/`▸`/缩进开头 | `chat_tool` | 紫 |
| 含 `%`/`年化`/`收益`/`回撤`/`夏普` | `chat_ai` | 绿 |
| 其他 | 无 | 默认 |

### 4. 对话开场框

替换旧的"已启动 Hermes 后台进程..."为带边框的对话标题 + 用户 prompt 蓝字显示：

```
┌──────────────────────────────────────────────┐
│  🤖 Hermes 自动研发 — 实时对话流            │
└──────────────────────────────────────────────┘

▸ 用户: 调用你的股票量化策略开发skill，新编写一个量化策略
```

## 相关代码位置

- `auto_develop()`: line ~1172
- `poll()`: line ~1227  
- `dev_text` 创建 + tag: line ~670
- `run_hermes()` 子线程: line ~1197
