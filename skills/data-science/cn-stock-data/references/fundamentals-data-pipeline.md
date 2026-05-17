# 基本面数据流水线（fundamentals-data-pipeline）

实现在 `a_stock_trade` 项目中。

## 架构

```
季度原始数据                               日频 NPZ
─────────────                             ──────────
ak.stock_yjbb_em()                         a_stock_fundamentals.npz
       │                                          │
       ▼                                          │
  _fund_raw.csv  ───→ 前向填充(announce_date+1日) ─┘
  (41个季度, 320k行)   对应5203只股票×2426交易日
```

## 一体化运行

```bash
cd ~/Desktop/a_stock_trade
python core/fetch_fundamentals.py
```

输出 `data/a_stock_fundamentals.npz`，自动清理中间文件。

## NPZ 格式约定

**必须与 K 线 NPZ 轴序一致**：`(n_stocks, n_dates)` = (5203, 2426)

| 字段 | shape | dtype | 说明 |
|------|-------|-------|------|
| `dates` | (2426,) | datetime64[us] | 与 K 线完全一致 |
| `codes` | (5203,) | object | 与 K 线完全一致 |
| `names` | (5203,) | object | 与 K 线完全一致 |
| `fund_eps` | (5203, 2426) | float32 | 每股收益 |
| `fund_roe` | (5203, 2426) | float32 | ROE(%) |
| `fund_bps` | (5203, 2426) | float32 | 每股净资产 |
| `fund_revenue` | (5203, 2426) | float32 | 营业总收入 |
| `fund_net_profit` | (5203, 2426) | float32 | 净利润 |
| `fund_revenue_yoy` | (5203, 2426) | float32 | 营收同比(%) |
| `fund_net_profit_yoy` | (5203, 2426) | float32 | 净利润同比(%) |
| `fund_gross_margin` | (5203, 2426) | float32 | 销售毛利率(%) |
| `fund_cf_ps` | (5203, 2426) | float32 | 每股经营现金流 |
| `fund_industry` | (5203, 2426) | object | 所属行业 |

所有数值字段：float32，NaN 表示无数据（未覆盖或未前向填充）。

## 填充逻辑

每一只股票独立执行：
1. 按 `eff_date`（用季度末+法定时滞估算，不用 `announce_date`）排序季度数据
2. `np.searchsorted(dates, eff_dates)` 定位每个季度在交易日轴上的位置
3. 在相邻生效日期之间填充前一个季度的值
4. 最后一个生效日期后保持最新值

**关键注意**：`announce_date` 字段不可信（是最后修订日期），必须用季度末+法定时滞估算 eff_date：
- Q1/Q3: 季度末+45天
- Q2: 季度末+60天
- Q4: 季度末+120天

**多取一个季度做缓冲**：回测从 2016-05-17 开始，需下载 2015Q4 数据才能在 2016 年前半年有足够覆盖面。`generate_quarter_dates()` 在 10 年范围外多推一个季度。

## 加载方式

```python
from core.data_loader import DataLoader, load_fundamentals

ld = DataLoader().load()
fund = load_fundamentals(ld.codes)  # 自动对齐股票顺序

# 访问：fund["roe"][stock_idx, day_idx]
# 或按天：fund["roe"][:, t]  得到所有股票在 t 日的截面
```

## 策略中使用

```python
from core.alpha_utils import zscore_rank, alpha_fund_roe, alpha_fund_bp

for t in range(n_days):
    v = close[:, t] > 0.5
    roe_z = alpha_fund_roe(t, fund, close[:, t], v)
    bp_z = alpha_fund_bp(t, fund, close[:, t], v)
    score = zscore_rank(roe_z + bp_z, v)
```

**索引约定**：fund 数组 shape 为 `(n_stocks, n_dates)`，所以 `fund["roe"][:, t]` 取 t 日所有股票的截面（与 `close[:, t]` 一致）。

## 可用基本面因子函数（alpha_utils.py）

| 函数名 | 参数 | 逻辑 |
|--------|------|------|
| `alpha_fund_roe(t, fund, close_at_t)` | t=日索引, fund=dict, close_at_t=当日收盘价数组 | ROE 截面 z-score |
| `alpha_fund_eps(t, fund, close_at_t)` | 同上 | EPS 截面 z-score |
| `alpha_fund_eps_yoy(t, fund, close_at_t)` | 同上 | 净利润同比 z-score（截尾 ±500%） |
| `alpha_fund_revenue_yoy(t, fund, close_at_t)` | 同上 | 营收同比 z-score |
| `alpha_fund_profit_growth(t, fund, close_at_t)` | 同上 | (净利同比+营收同比)/2 等权 |
| `alpha_fund_bp(t, fund, close_at_t)` | 同上 | bps/price 市净率倒数 z-score |
| `alpha_fund_gross_margin(t, fund, close_at_t)` | 同上 | 毛利率 z-score |
| `alpha_fund_cf_quality(t, fund, close_at_t)` | 同上 | 经营现金流/EPS（利润含金量） |
| `alpha_fund_quality(t, fund, close_at_t)` | 同上 | (ROE+毛利率+现金流质量)/3 综合 |
| `alpha_fund_eps_growth_price(t, fund, close)` | 多一个 close 矩阵 | EPS增长z+动量z 复合 |

所有函数返回 `(n_stocks,)` 的 z-score 数组，无效位置为 `-np.inf`。

## Pitfalls

### axis 顺序混淆

**最常见错误**：fund 数组 index 混淆。记住：
- K 线：`close[:, t]` → 所有股票在 t 日
- 基本面：`fund["roe"][:, t]` → 所有股票在 t 日
- 不要写成 `fund["roe"][t, :]`（那会取所有日期中第 t 只股票）

### core/platform.py 冲突

脚本在 `core/` 目录下运行时，`sys.path[0]` 指向 `core/`，导致 `import platform` 抓到 `core/platform.py` 而非 stdlib。修复：

```python
import os, sys
if sys.path and sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path.pop(0)
```

### fetch_fundamentals.py 清理顺序

临时 CSV 必须在 expand 完成后才删除。错误写法：

```python
temp = download_all_quarters()
os.remove(temp)          # ❌ 删了后面就读不到了
expand_to_daily(temp)
```

正确写法：

```python
temp = download_all_quarters()
expand_to_daily(temp)    # ✓ 用完再删
os.remove(temp)
```
