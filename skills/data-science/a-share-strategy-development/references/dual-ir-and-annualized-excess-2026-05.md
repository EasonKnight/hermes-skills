# 双超额夏普与年化超额修复记录

## 背景

2026-05-16 用户要求同时显示两个超额夏普：
1. 相对中证1000指数的信息比（中证夏普）
2. 相对等权周频基准的信息比（等权夏普）

## 实现

### 引擎改动 (`_compute_benchmark`)

在等权基准计算完成后，读取 `self.csi1000_nav`（通过 akshare 下载中证1000指数）计算第二套超额：

```python
csi_excess_ret = self.csi1000_excess_nav[-1] - 1.0
strat_ann = (strat_pct_nav[-1] / strat_pct_nav[base_idx]) ** (1.0 / years) - 1.0
csi_ann = (csi_vals[-1]) ** (1.0 / years) - 1.0
ann_csi = strat_ann - csi_ann
# 日超额、跟踪误差、IR同等方法计算
```

stats keys: `中证超额`, `中证跟踪`, `中证信息比`

### app.pyw

Treeview列改为：`("name", "ret", "csi_sharpe", "eq_sharpe", "dd", "created")`

### CSV

platform.py中增加 `中证超额`, `中证跟踪`, `中证信息比` 三列。

## 年化超额修正（重要）

**错误做法**（导致IR虚高）：
```python
ann_excess = csi_excess_ret / years  # 总点数差/年数
```

等权策略的中证IR被算出1.25，因为总点数差200%+/10年 = 20%/年，
但实际上策略年化(11.69%) - 中证年化(~6.9%) = 4.77%/年。

**正确做法**：
```python
strat_ann = (1 + strat_total_return) ** (1/years) - 1
bm_ann = (1 + bm_total_return) ** (1/years) - 1
ann_excess = strat_ann - bm_ann
```

修复后等权策略中证IR降至0.5~0.8，合理。

## 数值参考

10年数据(2016-05~2026-05):
- 等权周频基准(CSI1000池): +195.18% (~11.4%/年)
- 中证1000指数: 约+30~50% (~3~5%/年)
- TOP3策略年化: 21~22.5%
- 等权IR区间: -0.09~0.08（TOP策略）
- 中证IR区间: 0.67~0.78（TOP策略）
