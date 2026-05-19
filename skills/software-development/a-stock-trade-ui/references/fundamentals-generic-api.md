# 基本面数据通用 API 接入笔记

## 背景

`ak.stock_financial_abstract_ths()`（同花顺版）仅覆盖约 50% A 股，其余返回 `None` 导致 `'NoneType' object has no attribute 'string'` 报错。2026-05-19 切换为 `ak.stock_financial_abstract()`（通用版），覆盖全部 A 股。

## API 签名对比

```python
# THS 版：仅部分股票有数据
ak.stock_financial_abstract_ths(symbol="000001", indicator="按报告期")

# 通用版：全部 A 股都有数据
ak.stock_financial_abstract(symbol="000001")
```

## 返回格式差异

### THS 版（行列正常）
```
行 = 报告期（如 20260331, 20251231...）
列 = 指标名（如 基本每股收益, 每股净资产...）
```

### 通用版（转置格式）
```
行 = 指标名（如 基本每股收益, 毛利率...），前两列为[选项, 指标]
列 = 报告期（如 20260331, 20251231...）
```
同一指标名可能出现在多个"选项"类别中（如"基本每股收益"同时出现在"每股指标"和"盈利能力"），需要去重。

## KEY_FIELDS 映射表

```python
# THS → 通用版
# 更新位置：core/update_fundamentals.py 顶部 KEY_FIELDS 列表
KEY_FIELDS = [
    "基本每股收益",       # 不变
    "每股净资产",         # 不变（取不带"摊薄"前缀的那个）
    "每股经营现金流",     # 不变
    "每股未分配利润",     # 不变
    "每股资本公积金",     # 不变
    "营业总收入",         # 不变
    "营业总收入增长率",   # 原 THS: "营业总收入同比增长率"
    "净利润",             # 不变
    "归属母公司净利润增长率",  # 原 THS: "净利润同比增长率"
    "销售净利率",         # 不变
    "毛利率",             # 原 THS: "销售毛利率"
    "净资产收益率(ROE)",  # 原 THS: "净资产收益率"
    "流动比率",           # 不变
    "速动比率",           # 不变
    "资产负债率",         # 不变
]
```

## 去重说明

通用版中同一指标名可能跨类别重复出现（如"基本每股收益"有2次，"毛利率"有2次），用 `drop_duplicates(subset=["指标"], keep="first")` 保留首次出现。

## ⚠️ 已知问题

### pandas 版本兼容
```python
# ❌ 旧版 pandas 支持
pivoted = pivoted.fillna(method="ffill").fillna(0.0)

# ✓ 新版 pandas（>=1.3）使用
pivoted = pivoted.ffill().fillna(0.0)
```

### 日期格式
通用版返回的日期列是 `"20260331"` 格式（无分隔符），需转为 `"2026-03-31"`：
```python
def _to_date(s):
    s = str(s).replace("-", "").strip()[:8]
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else None
```
