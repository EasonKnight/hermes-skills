# akshare 多进程全市场 A 股下载方案

> 来源：2026-05-15 实际运行，`a_stock_trade` 项目，5204 只股票，9 分钟完成

## 核心 API

| 用途 | API | 参数要点 |
|------|-----|--------|
| 获取全市场股票列表 | `ak.stock_info_a_code_name()` | 返回 code + name |
| 下载日K线 | `ak.stock_zh_a_daily(symbol, start_date, end_date, adjust)` | symbol = `sh600000`/`sz000001` 格式；adjust = `"qfq"`(前复权) |
| 替代 API | `ak.stock_zh_a_hist(symbol, period, start_date, end_date, adjust)` | 参数格式不同，但功能类似 |

## 股票代码 → symbol 转换规则

```python
if code.startswith("6"):
    symbol = f"sh{code}"        # 上海主板、科创板
elif code.startswith("0") or code.startswith("3"):
    symbol = f"sz{code}"        # 深圳主板、创业板
# 跳过 8xx、4xx（新三板）
```

## 多进程方案（Windows 兼容）

**关键点**：akshare 内部使用 `py_mini_racer` 解析 JavaScript（East Money 接口），多进程共用会导致崩溃。必须用 `mp.get_context("spawn")`，每个 worker 独立导入 akshare。

### 结构

```
主进程：
  - 准备股票参数列表
  - 用 Pool.imap_unordered() 提交任务
  - 收集结果，每 N 只 flush 一次 CSV
  - 维护进度文件、错误日志

Worker 进程 (spawn 模式)：
  - import akshare as ak（每个进程独立加载）
  - 下载一只股票，返回 (code, name, status, data)
  - data 可以是 dict 列表或错误消息
```

### 代码骨架

```python
def _download_one(params):
    code, name, symbol, start_date, end_date, adjust = params
    try:
        import akshare as ak
        df = ak.stock_zh_a_daily(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        if df is None or df.empty:
            return (code, name, "empty", None)
        df.insert(0, "股票代码", code)
        df.insert(1, "股票名称", name)
        records = df.to_dict("records")
        return (code, name, "ok", records)
    except Exception as e:
        err = str(e).replace("\n", " ")[:120]
        return (code, name, "error", err)

def main():
    mp.freeze_support()  # Windows 必备
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=WORKERS) as pool:
        results = pool.imap_unordered(_download_one, worker_params, chunksize=BATCH_SIZE)
        for result in results:
            # 处理 result: code, name, status, data
            ...
```

### 统计输出（背景运行时用）

Python 脚本在后台运行时 `print()` 可能被缓冲。方案：
- 实时进度写入单独日志文件 (`_log.txt`)
- 屏幕输出用 `sys.stdout.write(f"\\r  [{done}/{total}] ...")` 覆盖行
- 进度文件 (`_progress.txt`) 记录每只股票完成状态，支持断点续传

## 性能参考

| 项目 | 数值 |
|------|------|
| 股票总数 | ~5,200 |
| 下载完成 | 5,198（失败 6） |
| 数据量 | ~3.67M 行，~400MB CSV |
| 耗时 | ~9 分钟 |
| 并行数 | 5 进程 |
| 日期范围 | 近 3 年 |
