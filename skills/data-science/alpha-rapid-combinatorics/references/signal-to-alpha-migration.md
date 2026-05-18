# s* → alpha 策略迁移模式（2026-05-18 批量转换）

## 背景

原 26 个 signal 模式策略（`generate_signal` 返回 bool 信号矩阵）全部转为 alpha 模式（`generate_alpha` 返回 float z-score 矩阵）。

## 通用迁移模式

| 旧 signal 逻辑 | 新 alpha 因子 |
|---------------|--------------|
| `price < thr_percentile`（硬阈值截断） | `zscore_rank_matrix(-close, vld)`（连续得分，低价=高分） |
| `|ret5| > 0.12`（排除极端） | `-zscore_rank_matrix(np.abs(ret_n_batch(close,5)), vld)`（极端=低分） |
| `vol < thr`（低波筛选） | `zscore_rank_matrix(-vol_n_batch(close,20), vld)`（低波=高分） |
| `ret5 > 0.12`（超涨排除） | `zscore_rank_matrix(-ret_n_batch(close,5), vld)`（超涨=低分） |
| 双条件 AND（低价 AND 低波） | `zscore(-close) + zscore(-vol_20d)`（加法等权复合） |
| 双条件 AND NOT（低价 AND NOT 极端） | `zscore(-close) - zscore(|ret5|)`（减法，极端为负） |
| 多条件 AND（低价 AND 低波 AND 正动量） | `zscore(-close) + zscore(-vol) + zscore(ret_20d)`（三因子等权） |
| 排除中间层（成交额中段） | `-np.abs(zscore(amount))`（极端=高分） |
| `ret > 0.03 AND ret < 0.20` | `np.clip(ret_n_batch, 0.03, 0.20)` + zscore |

## 模板转换

**旧模式**（signal + for t in range）：
```python
from core.backtest_utils import DataLoader, BacktestEngine, ...  # 逐个导入
STOCK_POOL = "csi1000"

def generate_signal(close, dates=None, **kw):
    signal = np.zeros(close.shape, dtype=bool)
    first = weekly_filter(dates)
    for t in range(close.shape[1]):
        if not first[t]: continue
        c = close[:, t]
        valid = c > 0.5
        thr = np.nanpercentile(c[valid], 20)
        signal[:, t] = (c <= thr) & valid
    # 手动 forward-fill
    for t in range(1, close.shape[1]):
        if not first[t]: signal[:, t] = signal[:, t-1]
    return signal
```

**新模式**（alpha + 全矩阵批处理）：
```python
from core.backtest_utils import *                      # 通配符导入
from core.alpha_utils import zscore_rank_matrix, decay_linear_batch, forward_fill_alpha
DECAY=20; STOCK_POOL="csi1000"

def generate_alpha(close, dates=None, **kw):
    n_s, n_d = close.shape
    f = weekly_filter(dates)
    vld = close > 0.5
    h = zscore_rank_matrix(-close, vld)           # 全矩阵 zscore
    a = zscore_rank_matrix(decay_linear_batch(h, DECAY), vld)  # 向量化平滑
    a = np.where(f, a, -np.inf)                   # 非调仓日置零
    a = forward_fill_alpha(a, f)                  # 向量化 forward-fill
    return a
```

## 主要改动点

1. **导入方式**：`from core.backtest_utils import *`（替代逐个导入）
2. **函数名**：`generate_signal` → `generate_alpha`
3. **返回值**：`bool` → `float z-score`（>0 选中，越大权重越高）
4. **数据流**：`for t in range` → 全矩阵 `*_batch` 函数
5. **前端处理**：手动 forward-fill → `forward_fill_alpha`
6. **引擎模式**：默认 → `alpha_mode=True`

## 验证方法

运行 `python strategies/sXXX.py` 检查回测输出。预期：
- 收益走势应与旧版相似（alpha 模式是连续版本，结果更平滑）
- 换手率应降低（decay 平滑 + 连续 z-score 替代硬阈值）
