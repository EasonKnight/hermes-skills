# 实盘策略「最新信号」列 — 最后持仓日期

## 功能

将实盘策略表的「最新信号」列从读取 JSON 中的原始 `signal` 字段改为读取 `position_matrix.npz`，
显示该策略最后一个有非零持仓的交易日（`MM-DD` 格式）。

## 实现（app.pyw 顶层函数）

```python
def get_last_pos_date(folder):
    """读取策略结果的 position_matrix.npz，返回最后一个有持仓的日期（MM-DD）"""
    npz_path = os.path.join(RESULTS, folder, "position_matrix.npz")
    if not os.path.exists(npz_path):
        return ""
    try:
        import numpy as np
        import pandas as pd
        d = np.load(npz_path, allow_pickle=True)
        pos = d.get("pos_value")
        dates = d.get("dates")
        if pos is None or dates is None or pos.ndim != 2:
            return ""
        for t in range(pos.shape[1] - 1, -1, -1):
            if (pos[:, t] > 0).any():
                return pd.Timestamp(dates[t]).strftime("%m-%d")
        return ""
    except Exception:
        return ""
```

## 调用位置

`refresh_live()` 中替换 `s.get("signal","")`：

```python
vals = (s.get("name",""), s.get("status",""), s.get("capital_pct",""),
        get_last_pos_date(s.get("folder","")), s.get("cum_return",""), update_time)
```

## 逻辑

1. 定位 `results/<folder>/position_matrix.npz`
2. 从最后一列（最后交易日）向前遍历
3. 找到第一个有 `pos_value > 0` 的列
4. 从 `dates` 数组中取该日，格式化为 `MM-DD`
5. 无持仓或文件不存在时返回空字符串
6. 全函数 try-except 兜底异常安全

## 注意

- 策略首次添加到实盘但尚未运行回测时，`position_matrix.npz` 不存在 → 显示空白
- 策略全仓清空后（最后一天无持仓），会向前回溯到有持仓的日期
