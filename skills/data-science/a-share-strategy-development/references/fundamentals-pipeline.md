# 基本面数据流水线（2026-05-17 建立）

## 架构

```
core/fetch_fundamentals.py     ← 一体化：下载 → 展开 → 保存 NPZ + CSV
data/a_stock_fundamentals.npz  ← 日频基本面 (n_stocks, n_dates) float32
data/a_stock_fundamentals.csv  ← 季度末抽样 CSV（42个交易日 x 5203只 ≈ 22万行）
```

## 数据源

`ak.stock_yjbb_em(date="YYYYMMDD")` — 按季度末日期获取全市场业绩报表。
一次性返回该季度所有股票的财务数据，无需逐股遍历。

## 季度范围

从当前季度往前推 10 年，**多取一个季度**作为前向填充缓冲（如用 2015Q4 覆盖 2016 年上半年的空白）。

## ⚠️ 核心坑：announce_date 是最后修订日，不是首次披露日

`stock_yjbb_em` 返回的 `最新公告日期` 字段是**数据最后修订日期**，不是财务报告的实际首次披露日。

- 平安银行 2015 年报原在 2016 年 2-4 月披露，但 API 显示的公告日是 **2017-03-17**（后续修订）
- 直接用 announce_date 做生效日会导致数据可用时间滞后 1-2 年

**修复**：不用 announce_date，改用**季度末 + 法定披露时滞**估算生效日期：

| 报表类型 | 时滞 | 估算生效日 |
|---------|------|-----------|
| 一季报/三季报 (Q1/Q3) | 45天 | 季度末 + 45天 |
| 中报/半年报 (Q2) | 60天 | 季度末 + 60天 |
| 年报 (Q4) | 120天 | 季度末 + 120天 |

实现见 `fetch_fundamentals.py` 的 `_estimate_eff_date()`。

## 前向填充逻辑

按 stock 分组 → eff_date 排序 → np.searchsorted 定位每日历日在 K 线时间轴的位置 → 逐段填充重复值 → 覆盖到下一季报生效。

## NPZ 轴序约定

所有基本面 NPZ 统一 `(n_stocks, n_dates)`，与 K 线 NPZ 一致。因子函数用 `[:, t]` 索引。

## 覆盖效果（修复后）

| 年度 | 覆盖率 |
|:---:|:-----:|
| 2016 | 76% |
| 2017 | 80% |
| 2018+ | 85-100% |
| 总 | 92.9% |

## 因子函数

全部在 `core/alpha_utils.py` 中，函数名以 `alpha_fund_` 开头，返回 z-score：

| 函数 | 逻辑 |
|------|------|
| `alpha_fund_roe(t, fund)` | 高 ROE → 高分 |
| `alpha_fund_eps(t, fund)` | 高 EPS → 高分 |
| `alpha_fund_eps_yoy(t, fund)` | 净利润同比增速（成长因子） |
| `alpha_fund_revenue_yoy(t, fund)` | 营收同比增速 |
| `alpha_fund_profit_growth(t, fund)` | 净利+营收双增长 |
| `alpha_fund_bp(t, fund, close_at_t)` | B/P = bps/price（价值因子） |
| `alpha_fund_gross_margin(t, fund)` | 高毛利率 → 护城河 |
| `alpha_fund_cf_quality(t, fund)` | 经营现金流/EPS（利润含金量） |
| `alpha_fund_quality(t, fund)` | 质量综合：(ROE+毛利率+现金流)/3 |
| `alpha_fund_eps_growth_price(t, fund, close)` | EPS增长+动量复合 |

## 策略中使用

```python
from core.data_loader import load_fundamentals
from core.alpha_utils import alpha_fund_roe, alpha_fund_bp

fund = load_fundamentals(ld.codes)  # 自动对齐到 DataLoader 的股票顺序
# 在 generate_alpha 循环中：
score = alpha_fund_roe(t, fund, close[:, t])
score += alpha_fund_bp(t, fund, close[:, t])
```

## 重新生成

```bash
cd ~/Desktop/a_stock_trade
PYTHONIOENCODING=utf-8 python core/fetch_fundamentals.py
# ~60秒完成，自动清理临时 CSV
```

## 性能

- 43个季度 x 4进程并行下载 ≈ 40-50秒
- 前向填充 5203 只股票 ≈ 20-25秒
- NPZ 10MB（63x压缩比，因前向填充产生大量重复值）
- CSV 29MB（季度末抽样，42个交易日）
