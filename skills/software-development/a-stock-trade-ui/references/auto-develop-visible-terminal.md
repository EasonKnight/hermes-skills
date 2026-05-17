# Auto-Develop 可见终端模式（已回退 — 历史记录）

### 状态：已回退

该方案已于 2026-05-17 回退。原因是 Windows `.pyw` 环境下 `CREATE_NEW_CONSOLE` + 文件轮询方案不稳定：
- 终端窗口出现但空白（stdout 被 PIPE 截走）
- 不 PIPE 则 GUI 无法获取输出
- 文件轮询 + tee 转发有延迟且不可靠
- **最终方案**：`CREATE_NO_WINDOW` + PIPE 直接读取，稳定可靠

### 历史：Tee 转发器方案

曾创建 `scripts/hermes_dev_runner.py` 作为中间代理，输出同时写终端和文件：

```
app.pyw ──CREATE_NEW_CONSOLE──→ runner.py ──PIPE──→ hermes -z
                                     │
                          ┌──────────┼──────────┐
                          ↓          ↓           ↓
                     终端可见   临时文件     .done标记
                                   ↓
                          app.pyw 轮询读取
```

该文件已于回退时删除。
