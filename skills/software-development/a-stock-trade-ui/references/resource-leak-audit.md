# 资源泄漏审计清单 — a_stock_trade app.pyw

每次重大重构后或用户报告卡顿/残留进程时，逐项检查以下资源类别。

## 进程泄漏 (subprocess.Popen)

### 检查清单

| 创建点 | 清理机制 | 常见问题 |
|--------|---------|---------|
| `run_selected()` | `_sel_procs` 列表 + `_on_close` 杀 | ❌ 漏了 `shell=True` → cmd.exe 孤儿 |
| `run_all()` | `start cmd.exe /c` 自动退出 | 通常 OK |
| `auto_develop()` | `_dev_proc` + `stop_dev()` + `_on_close` | ❌ 漏了 `_on_close` 中清理 |
| `_run_all_live_strategies()` | `importlib` 非子进程 | OK |
| `open_chart()` | `cmd.exe /c start` 一键调用 | OK |

### 铁律

1. **`run_selected()` 永远不用 `shell=True`** — 改用 `Popen([sys.executable, src], cwd=d, creationflags=CREATE_NEW_CONSOLE)`
2. **所有子进程必须入跟踪列表** — `_sel_procs` / `_live_procs` / `_dev_proc`
3. **`_on_close` 必须清理所有进程类别**，漏一个就出一个孤儿
4. **子进程结束后从跟踪列表移除** — `self._sel_procs.remove(proc)` 防列表无限增长

## 线程泄漏 (threading.Thread)

### 检查清单

| 创建点 | daemon | cleanup | risk |
|--------|--------|---------|------|
| `run_selected` → `wait_and_refresh` | ✅ daemon=True | 结束时 proc 移除 | 低 |
| `auto_develop` → `run_hermes` | ✅ daemon=True | `stop_dev` kill proc | 低 |
| `_run_all_live_strategies` → `wait_all` | ✅ daemon=True | `pool.shutdown()` | 低 |
| `add_selected_to_live` → worker | ✅ daemon=True | 无(单次任务) | 低 |
| `BalanceWindow.refresh` → worker | ✅ daemon=True | 无(单次任务) | 低 |

铁律：**所有 `threading.Thread` 必须 `daemon=True`**，否则用户关窗口后 Python 进程不退出。

## 内存泄漏 (Python objects)

### matplotlib figures
- **风险**：`ThreadPoolExecutor` + `importlib` 多策略同进程运行时，`plt.subplots()` → 异常 → `plt.close()` 不执行 → figure 累积 OOM
- **防护**：
  - `_run_one()` 的 `finally` 块：`plt.close('all')`
  - `plot_and_save()`：`plt.close(fig)` + `plt.close('all')` 兜底

### tkinter PhotoImage
- `self._tk_img` 每次 `_render_chart()` 时重建，旧对象 GC 回收。✅

### Canvas 回调累积
- `show_detail()` 中 `img_canvas.bind("<Configure>")` 必须 `unbind` 再 `bind`，不能用 `add="+"`。

### matplotlib 异常退出保护
`plot_and_save()` 中 `plt.subplots()` 到 `plt.close()` 之间有 ~130 行绘图代码。任何异常（数据维度不符/nan/inf）都会导致 figure 泄漏。加上 `_fig = fig` 引用 + `plt.close(_fig)` 精确关闭。

## 实盘持仓计算线程 — 错误可见性

`add_selected_to_live()` 的 `poll()` 轮询函数负责把后台线程计算的持仓更新到 UI。

### 无声失败模式
```
worker → calc_strat_positions 返回 None → result["positions"] = None
poll  → pos is None → 写入 JSON → UI 显示"⏳ 持仓计算中..." 永远不变
```

### 修复
```
worker → pos 为 None 时写 result["error"] 而不是 result["positions"]
poll   → "error" 分支显示错误信息到 UI 面板
```

### 常见无声失败原因
| 现象 | root cause |
|------|-----------|
| 一直"⏳ 持仓计算中..." | `calc_strat_positions` 返回 None (NPZ 不存在或空) |
| NPZ 不存在 | 策略是在 NPZ 格式迁移前跑的，没生成 NPZ |
| NPZ 格式错误 | `pos_value` key 缺失 / `codes` 缺失 / 维度不对 |
| 股票映射为空 | `a_stock_kline_3y.npz` 被删除或路径不对 |

## 检查命令

```bash
# 检查 cmd.exe 残留
tasklist | findstr /i cmd.exe
# 检查 python 进程
tasklist | findstr /i python.exe
# 检查 conhost 残留
tasklist | findstr /i conhost.exe
```

Windows 上 conhost.exe 数量 = cmd.exe + python.exe 数量之和约为正常。cmd.exe >2 + python.exe > 预期数量 = 有孤儿进程。
