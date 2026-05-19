# 基本面数据下载与更新系统

## 数据源

**使用 `akshare.stock_financial_abstract(symbol)`（通用版接口）。**

`stock_financial_abstract_ths`（同花顺专版）仅覆盖约 1200~2500 只股票，其余返回 `'NoneType' object has no attribute 'string'`。通用版 `stock_financial_abstract` 覆盖全部 5200+ A 股。

**格式差异**：通用版返回**行=指标名、列=报告期**的转置格式（124+列·80行），需要 `fetch_one` 中做去重+转置+聚合。详见 `core/update_fundamentals.py` 实现。

## 文件

| 文件 | 用途 |
|------|------|
| `core/update_fundamentals.py` | 多进程下载+NPZ缓存构建。用法：`python core/update_fundamentals.py` / `--force` 全量重下 |
| `data/a_stock_fundamentals.csv` | 原始CSV（每行=1只股票×1个报告期） |
| `data/a_stock_fundamentals.npz` | 3D缓存矩阵 (N_stocks, N_quarters, N_fields) |

## 关键字段（15个）

KEY_FIELDS 必须在 `fetch_one` 的 `stock_financial_abstract` 指标名匹配，**不同于** THS版：

```
基本每股收益, 每股净资产, 每股经营现金流,
每股未分配利润, 每股资本公积金,
营业总收入, 营业总收入增长率,              # 旧版叫 营业总收入同比增长率
净利润, 归属母公司净利润增长率,             # 旧版叫 净利润同比增长率
销售净利率, 毛利率,                        # 旧版叫 销售毛利率
净资产收益率(ROE),                         # 旧版叫 净资产收益率
流动比率, 速动比率, 资产负债率,
```

**管道陷阱**：字段名不匹配时写入 CSV 的对应列为空。切换 API 后必须 `--force` 全量重下+删除旧 CSV。

## 缓存结构

```python
d = np.load("data/a_stock_fundamentals.npz", allow_pickle=True)
d["codes"]    # (N_stocks,) 股票代码
d["dates"]    # (N_quarters,) 报告期
d["fields"]   # (N_fields,) 字段名
d["data"]     # (N_stocks, N_quarters, N_fields) float32, NaN=无数据
```

## 股票过滤

`get_all_stocks()` 使用 A股前缀白名单过滤，与 K线数据保持一致：

```python
a_prefixes = {"000","001","002","003","300","301","302","303",
              "600","601","603","605","688"}
```

两边必须同步修改。三个点都要改：
- `core/update_data.py:get_all_stocks()`
- `core/update_data.py:_build_cache()`
- `core/update_fundamentals.py:get_all_stocks()`

## 每日更新

已追加到 `core/update_data.bat`，先跑K线数据、再跑基本面数据。Windows Task Scheduler 每晚20:00自动运行。

增量更新逻辑：新/重试股票会补充到CSV并重建NPZ缓存。已成功的股票自动跳过。

## 首次下载

约8~10分钟完成约 5200 只股票（通用接口限速较慢）。失败的股票下次增量更新自动重试。`--force` 模式全量重下。
