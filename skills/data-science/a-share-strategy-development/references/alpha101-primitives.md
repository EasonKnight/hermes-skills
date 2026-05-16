# Alpha101 原语速查

## 核心公式构建模式

Alpha101 的所有公式由 5 类原语组合而成：

### 1. 截面运算
| 原语 | 含义 | 输入/输出 | 我们的函数 |
|:----|:----|:---------|:----------|
| `rank(x)` | [0,1] 百分位 | (N,) → (N,) | `rank_pct(x)` |
| `scale(x)` | 线性缩放到 [-1,1] | (N,) → (N,) | `scale(x, -1, 1)` |

### 2. 时间序列滚动运算
| 原语 | 含义 | 我们的函数 |
|:----|:----|:----------|
| `sum(x, d)` | 滚动 d 日求和 | `ts_sum(x, t, d)` |
| `product(x, d)` | 滚动 d 日求积 | `ts_product(x, t, d)` |
| `max(x, d)` / `min(x, d)` | 滚动最大/最小 | `ts_max` / `ts_min` |
| `argmax(x, d)` / `argmin(x, d)` | 极值距今天数 | `ts_argmax` / `ts_argmin` |
| `rank(x, d)` (ts_rank) | 时间序列分位 [0,1] | `ts_rank(x, t, d)` |
| `stddev(x, d)` | 滚动标准差 | `ts_std(x, t, d)` |
| `correlation(x, y, d)` | 滚动相关系数 | `correlation(x, y, t, d)` |
| `covariance(x, y, d)` | 滚动协方差 | `covariance(x, y, t, d)` |
| `decay_linear(x, d)` | 线性加权MA（权重1..d） | `decay_linear(x, t, d)` |

### 3. 延迟/差分
| 原语 | 含义 | 我们的函数 |
|:----|:----|:----------|
| `delay(x, d)` | `x[t-d]` | `delay(x, t, d)` |
| `delta(x, d)` | `x[t] - x[t-d]` | `delta(x, t, d)` |

### 4. 数学变换
| 原语 | 含义 | 我们的函数 |
|:----|:----|:----------|
| `signedpower(x, e)` | `sign(x)*\|x\|^e` | `signedpower(x, e)` |
| `sign(x)` | 符号函数 | `sign(x)` |
| `abs(x)` | 绝对值 | `np.abs` |

### 5. 条件选择
```python
# 三元运算符
a if condition else b
# 等价于 Alpha101 的 (condition ? a : b)
np.where(condition, a, b)
```

## 典型公式结构

```
rank( ts_xxx( 原始数据, N ) ) × rank( ts_yyy( 原始数据, M ) )
```

- 先做时间序列运算（差分/均值/标准差等）
- 再做截面 rank（归一化到可比尺度）
- 再相乘组合多个因子
- 最终 zscore_rank 输出到引擎

## 原始数据字段约定
| 策略参数 | 含义 |
|:--------|:----|
| `close` | 收盘价 (N_stocks, N_days) |
| `open_p` | 开盘价 |
| `volume` | 成交量 |
| `dates` | 交易日数组 |

## 快速预制因子
```python
from core.alpha_utils import (
    alpha_momentum,     # ret_20d → z-score
    alpha_reversal,     # -ret_5d → z-score
    alpha_lowvol,       # -std_60d → z-score
    alpha_lowprice,     # -close → z-score
    alpha_volume_surge, # amount_ratio → z-score
)
```
这些预制因子已经在函数内部做了 zscore_rank，返回直接可用的得分矩阵（>0 的为选中股票）。适合快速测试。
