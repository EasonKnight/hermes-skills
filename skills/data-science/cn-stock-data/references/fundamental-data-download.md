# A股基本面数据下载方案（akshare stock_yjbb_em）

> 来源：2026-05-17 实际运行，`a_stock_trade` 项目，41 个季度，48 秒完成

## 核心 API

`ak.stock_yjbb_em(date="20251231")` — 按季度获取全市场业绩报表。

输入：季度末日期 `YYYYMMDD`（3/31, 6/30, 9/30, 12/31）
输出：该季度所有 A 股的核心财务数据，约 5000~11000 行（年报披露最全）

## 按季度并行模式

与 K-line 不同（每只股票一个 task），基本面数据**一个 API 调用返回全市场**，因此并行粒度是**季度**。

### 季度日期生成

```python
import datetime

def generate_quarter_dates(years_back=10):
def generate_quarter_dates(years_back=10):
    """多取一个季度给前向填充缓冲（如用2015Q4覆盖2016H1）"""
    today = datetime.date.today()
    current_q_start = ((today.month - 1) // 3) * 3 + 1
    dates = []
    year, month = today.year, current_q_start
    while True:
        q_end_month = ((month - 1) // 3) * 3 + 3
        q_end = {3: (year, 3, 31), 6: (year, 6, 30), 9: (year, 9, 30),
                 12: (year, 12, 31)}[q_end_month]
        dates.append(f"{q_end[0]}{q_end[1]:02d}{q_end[2]:02d}")
        month -= 3
        if month < 1:
            month += 12; year -= 1
        if year < today.year - years_back:
            break
    # 多取一个季度（缓冲）
    last_q = dates[-1]
    y, m = int(last_q[:4]), int(last_q[4:6])
    m -= 3
    if m < 1:
        m += 12; y -= 1
    qe = ((m - 1) // 3) * 3 + 3
    end_d = {3:31, 6:30, 9:30, 12:31}[qe]
    dates.append(f"{y}{qe:02d}{end_d:02d}")
    dates.sort()
    return dates  # ~43 个季度（10年+1缓冲）
```

### 字段重命名（中文→英文）

`stock_yjbb_em` 返回中文列名，建议重命名为英文便于后续引用：

```python
rename_map = {
    "股票代码": "code", "股票简称": "name",
    "每股收益": "eps",
    "营业总收入-营业总收入": "revenue",
    "营业总收入-同比增长": "revenue_yoy",
    "营业总收入-季度环比增长": "revenue_qoq",
    "净利润-净利润": "net_profit",
    "净利润-同比增长": "net_profit_yoy",
    "净利润-季度环比增长": "net_profit_qoq",
    "每股净资产": "bps", "净资产收益率": "roe",
    "每股经营现金流量": "cf_ps", "销售毛利率": "gross_margin",
    "所处行业": "industry", "最新公告日期": "announce_date",
}
# 只重命名确实存在的列
df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
```

### 并行下载骨架

```python
import multiprocessing as mp
import pandas as pd

def _download_one_quarter(quarter_date):
    try:
        import akshare as ak
        df = ak.stock_yjbb_em(date=quarter_date)
        if df is None or df.empty:
            return (quarter_date, "empty", None)
        # 重命名、插 quarter 列、转 dict
        df = df.rename(columns={...})
        df.insert(0, "quarter", quarter_date)
        records = df.to_dict("records")
        return (quarter_date, "ok", records)
    except Exception as e:
        return (quarter_date, "error", str(e)[:200])

def main():
    mp.freeze_support()
    ctx = mp.get_context("spawn")
    todo_quarters = generate_quarter_dates(10)
    with ctx.Pool(processes=4) as pool:
        results = pool.imap_unordered(_download_one_quarter, todo_quarters, chunksize=1)
        for result in results:
            quarter_date, status, data = result
            if status == "ok":
                pd.DataFrame(data).to_csv(OUTPUT_CSV, mode="a",
                    header=first_batch, index=False, encoding="utf-8-sig")
                # 记录进度、错误日志 ...
```

### 断点续传

进度文件 `_fund_progress.txt` 记录 `quarter_date,status,rows`。重跑时跳过已完成的季度。

错误文件 `_fund_errors.txt` 记录失败季度和错误信息（主要是当前未结束的季度）。

## 🚨 关键坑: `最新公告日期` 不可信

`ak.stock_yjbb_em()` 返回的 `最新公告日期` 列是 **最后修订日期**，不是首次披露日期。

**原因**：上市公司可能后续修正/重述历史财务数据，API 返回的是最新一次数据刷新的日期，而非原始报告发布日期。

**后果**：直接用 `announce_date` 做前向填充会导致：
- 2015年财报生效日从 ~2016-04 推迟到 2017-03+（如平安银行）
- 整体数据覆盖率从约 90%+ 降到约 80%
- 回测前几年几乎无基本面数据可用

### 正确做法：法定披露时滞估算

```python
def _estimate_eff_date(quarter_date):
    \"\"\"用季度末 + 法定披露时滞估算生效日，不用不可靠的 announce_date\"\"\"
    y, m = int(quarter_date[:4]), int(quarter_date[4:6])
    end_days = {3: 31, 6: 30, 9: 30, 12: 31}
    q_end = pd.Timestamp(year=y, month=m, day=end_days[m])
    lag = 120 if m == 12 else (60 if m == 6 else 45)
    return q_end + pd.Timedelta(days=lag)
```

| 报表类型 | 季度末月 | 时滞 | 估算生效 |
|----------|---------|------|---------|
| 年报(Q4) | 12月 | 120天 | 次年4月30日 |
| 中报(H1/Q2) | 6月 | 60天 | 8月30日 |
| 一季报(Q1) | 3月 | 45天 | 5月15日 |
| 三季报(Q3) | 9月 | 45天 | 11月14日 |

### 效果对比

| 指标 | 用 `announce_date` | 用法定时滞估算 |
|------|-------------------|---------------|
| 2016年覆盖 | 约 1% | **约 76%** |
| 2017年覆盖 | 约 48% | **约 80%** |
| 总非空率 | 约 80% | **约 93%** |
| 平安银行首个EPS | 2017-04-24 | 回测第一天 |

## 与平台.py 冲突的修复

同 K-line 下载器 — 脚本在 `core/` 目录下运行时需要 `sys.path.pop(0)` 避免 `core/platform.py` 遮蔽 stdlib `platform` 模块（pandas 依赖）。详见 cn-stock-data 技能主文档的「路径冲突坑」章节。

## 实际运行结果

| 项目 | 值 |
|------|-----|
| 总季度数 | 42 |
| 成功 | 41 |
| 失败 | 1（20260630 — 当前季度未结束） |
| 总行数 | 320,929 |
| 股票数 | 11,750 |
| 耗时 | 48 秒 |
