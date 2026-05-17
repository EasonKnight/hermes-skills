# 基本面因子策略模式

## 数据获取

`core/fetch_fundamentals.py` — 一键下载季度财务数据 + 展开为日频 NPZ：

```bash
cd ~/Desktop/a_stock_trade
python core/fetch_fundamentals.py
```

输出 `data/a_stock_fundamentals.npz`（13MB，5203只×2426日，float32）。

## NPZ 轴序约定

**必须与 K 线一致：`(n_stocks, n_dates)`**。

| 访问方式 | 含义 | 示例 |
|----------|------|------|
| `fund["roe"][:, t]` | t 日截面所有股票的 ROE | 正确 |
| `fund["roe"][t, :]` | 第 t 只股票的所有日期 | 错误 |

## 策略中加载

```python
from core.data_loader import DataLoader, load_fundamentals
from core.alpha_utils import zscore_rank, decay_linear

ld = DataLoader().load()
fund = load_fundamentals(ld.codes)  # 按ld.codes代码顺序对齐

for t in range(n_days):
    v = close[:, t] > 0.5
    roe_z = zscore_rank(fund["roe"][:, t], v)     # 取 t 日截面
    bps_price = fund["bps"][:, t] / close[:, t]    # B/P
    bp_z = zscore_rank(bps_price, v)
    combo = (roe_z + bp_z) / 2
```

`load_fundamentals(codes)` 接受 `DataLoader.codes` 做代码顺序对齐，未覆盖的股票填 NaN。

## 已实现的基本面因子（alpha_utils.py）

### 单独因子

| 函数 | 字段 | 逻辑 |
|------|------|------|
| `alpha_fund_roe(t, fund, close_at_t)` | fund_roe | 高ROE = 盈利强 |
| `alpha_fund_eps(t, fund, close_at_t)` | fund_eps | 高EPS |
| `alpha_fund_eps_yoy(t, fund, close_at_t)` | fund_net_profit_yoy | 净利润同比增（截尾±500%） |
| `alpha_fund_revenue_yoy(t, fund, close_at_t)` | fund_revenue_yoy | 营收同比增 |
| `alpha_fund_bp(t, fund, close_at_t)` | fund_bps | B/P = bps/close（价值） |
| `alpha_fund_gross_margin(t, fund, close_at_t)` | fund_gross_margin | 高毛利率 |
| `alpha_fund_cf_quality(t, fund, close_at_t)` | fund_cf_ps / fund_eps | 经营现金流/EPS（利润含金量） |

### 复合因子

| 函数 | 组合方式 |
|------|----------|
| `alpha_fund_profit_growth(t, fund, close_at_t)` | (net_profit_yoy_z + revenue_yoy_z) / 2 |
| `alpha_fund_quality(t, fund, close_at_t)` | (roe_z + gm_z + cf_z) / 3 |
| `alpha_fund_eps_growth_price(t, fund, close)` | (eps_yoy_z + ret_20d_z) / 2 |

## 策略模板

```python
LABEL="A320 基本面因子描述"; FOLDER="A320-基本面因子描述"; FREQ="weekly"; TAGS=["alpha","fundamental"]; POOL="csi1000"
import sys,os; sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
import numpy as np
from core.backtest_utils import *
from core.alpha_utils import zscore_rank, decay_linear
from core.data_loader import load_fundamentals
DECAY=15; STOCK_POOL="csi1000"
def generate_alpha(close,dates=None,volume=None,fund=None,**kw):
    n_s,n_d=close.shape; a=np.zeros((n_s,n_d)); f=weekly_filter(dates); h=np.zeros((n_s,n_d))
    if fund is None: return a
    for t in range(n_d):
        v=close[:,t]>0.5
        # 直接取 fund[:,t] 截面数据
        r_z=zscore_rank(fund["roe"][:,t],v)
        b_z=zscore_rank(fund["bps"][:,t]/np.maximum(close[:,t],0.5),v)
        g_z=zscore_rank(np.clip(fund["net_profit_yoy"][:,t],-500,500),v)
        combo=np.full(n_s,-np.inf)
        valid=np.isfinite(r_z)&np.isfinite(b_z)&np.isfinite(g_z)
        combo[valid]=(r_z[valid]+b_z[valid]+g_z[valid])/3.0
        h[:,t]=combo
        if not f[t]:
            if t>0: a[:,t]=a[:,t-1]
            continue
        raw=decay_linear(h,t,DECAY); a[:,t]=zscore_rank(raw,v)
    return a
def main():
    l=LABEL; print("="*60); print(f"  {l}"); print("="*60)
    ld=DataLoader().load(); c=ld.close; d=ld.dates
    print("[加载基本面]..."); fund=load_fundamentals(ld.codes)
    p=stock_pool_mask(ld.codes,STOCK_POOL); v=(c>0.5)&p[:,None]
    print(f"[生成] {l}..."); al=generate_alpha(c,d,fund=fund); al[~v]=-np.inf; print(f"  日均选股: {(al>0).sum(axis=0).mean():.0f}")
    r=TradingRules(c,ld.open_price,ld.volume,ld.codes,ld.names_arr,ld.is_st,ld.exchange)
    eng=BacktestEngine(COMMISSION,SLIPPAGE,alpha_mode=True); eng.run(c,al,d,trading_rules=r,valid=v)
    print_stats(eng.stats); Visualizer.print_trades(eng); Visualizer.plot_and_save(eng,os.path.join(RESULTS_BASE,FOLDER),l); print("="*60)
if __name__=="__main__": main()
```

## 已有基本面策略表现

| 策略 | 因子 | 总收益 | 年化 | 中证IR | 换手 |
|:---|:----|:-----:|:---:|:-----:|:---:|
| A320 质量价值 | ROE+B/P+利润增长均权 | 112.32% | 7.87% | 0.63 | 2.90% ✅ |
| A322 纯成长 | 净利润同比+营收同比均权 | 104.64% | 7.50% | **0.75** ✅ | 2.98% ✅ |
| A323 纯价值 | B/P+毛利率+现金流均权 | 133.74% | 8.95% | 0.67 | 2.68% ✅ |

## 坑

1. **轴序混淆**：fund["roe"][**,t**] 取t日截面，不是fund["roe"][t,**:**]
2. **早期稀疏**：2017年4月前CSI1000成分股基本面无数据，首次有效选股约t=224
3. **增速截尾**：net_profit_yoy/revenue_yoy 可能含极端值（±1000%+），必须np.clip到±500
4. **load_fundamentals必须传codes**：不传codes返回原始NPZ轴序(n_dates,n_stocks)；传ld.codes后对齐为(n_stocks,n_dates)并过滤缺失股票
5. **跑策略前重跑fetch_fundamentals.py**：数据不自动更新，需手动重跑
