# 基本面数据 — API 选择

## API 对比

| API | 覆盖率 | 说明 |
|-----|--------|------|
| `ak.stock_financial_abstract_ths()` | ~50% (1200-2500只) | 同花顺源，大量股票返回 None |
| `ak.stock_financial_abstract()` | ~100% (5240只) | 通用源，覆盖全部A股 |

**始终使用 `stock_financial_abstract()`（通用版），不要用 `_ths` 版。**

## 格式差异

`stock_financial_abstract_ths()` 返回格式：行=报告期，列=字段
`stock_financial_abstract()` 返回格式：行=指标名，列=报告期（需要转置）

## 转置逻辑（fetch_one）

```python
def fetch_one(params):
    code, name = params
    df = ak.stock_financial_abstract(symbol=code)
    # 去重（同一指标名可能出现在多个类别中，取首次出现）
    df = df.drop_duplicates(subset=["指标"], keep="first")
    # 选出 KEY_FIELDS 中存在的指标
    available = [c for c in KEY_FIELDS if c in df["指标"].values]
    df_filt = df[df["指标"].isin(available)]
    # 转置：指标名→行，日期列→列
    date_cols = [c for c in df_filt.columns if c not in ("选项", "指标")]
    records = []
    for _, row in df_filt.iterrows():
        for col in date_cols:
            val = row[col]
            records.append({"报告期": col, row["指标"]: float(val) if val else None})
    records_df = pd.DataFrame(records)
    pivoted = records_df.groupby("报告期", as_index=False).first()
    pivoted = pivoted.ffill().fillna(0.0)
```

## KEY_FIELDS

转换为 `stock_financial_abstract()` 的字段名：

```python
KEY_FIELDS = [
    "基本每股收益", "每股净资产", "每股经营现金流",
    "每股未分配利润", "每股资本公积金",
    "营业总收入", "营业总收入增长率",           # 旧版："营业总收入同比增长率"
    "净利润", "归属母公司净利润增长率",        # 旧版："净利润同比增长率"
    "销售净利率", "毛利率", "净资产收益率(ROE)",  # 旧版："净资产收益率"
    "流动比率", "速动比率", "资产负债率",
]
```

## pandas 版本兼容

新版 pandas（2.2+）已弃用 `fillna(method='ffill')`，改用 `df.ffill()`：
```python
# 新版本
df = df.ffill().fillna(0.0)

# 旧版本（已弃用）
df = df.fillna(method='ffill').fillna(0.0)
```
