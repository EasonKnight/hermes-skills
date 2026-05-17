# 从 Hermes 会话记录恢复丢失的策略源码

## 场景

策略 `.py` 文件被删除但 `results/` 目录和/或 `_summary.csv` 中仍有记录。需要反查原始因子公式。

## 方法

### 1. 用 session_search 定位创建会话

```python
# 搜索策略名或关键变量
session_search("A227 OR intraday_strength OR 日内强度")
```

返回包含关键词的 session ID 和时间戳。

### 2. 直接读会话 JSON 文件

会话文件存储在：`~/.hermes/sessions/session_<id>.json`（Windows: `%LOCALAPPDATA%\hermes\sessions\`）

```python
import json
with open("C:/Users/Mayn/AppData/Local/hermes/sessions/session_20260516_232223_0d0a48.json", encoding='utf-8') as f:
    data = json.load(f)
```

### 3. 提取 write_file 和策略代码

遍历 `messages` 数组，过滤：
- `role == "assistant"` 且 content 包含目标策略名 → 查看策略设计思路
- `role == "tool"` 且 content 包含 `write_file` → 查看完整源码
- `role == "tool"` 且 content 包含 `年化收益率` → 查看回测结果

```python
for msg in data['messages']:
    content = msg.get('content', '')
    if isinstance(content, str) and 'A227' in content:
        print(f"[{msg['role']}] {content[:500]}")
```

### 4. 从回测日志反推因子公式

如果源码丢失但运行日志仍在，从 `stats.csv` + 策略名反推：
- "日内强度" → 与 open/close/high/low 相关的日内位置计算
- "量价趋势一致" → volume 与 price 的协同关系
- "波动调整反转" → 反转信号除以波动率

然后用 alpha_utils 中的对应函数重建（`overnight_ret`, `correlation`, `ret_n/vol_n` 等）。

## 案例

A227/A228/A229 的源文件在修复数据 bug 后被删除，但 `_summary.csv` 中留有虚假高分记录。通过 `session_search` 找到 session `20260516_232223`，读取 JSON 完整还原了创建→运行→发现数据bug→删除的全过程，确认了原始因子公式和数据损坏事实。

## 注意事项

- 会话文件可能很大（含工具调用的完整输入输出）
- `session_search` 返回摘要而非原文，落地需读 JSON
- 会话可能已被 `/reset` 清除（默认保留 N 天）
