# 增量数据更新方案 (core/update_data.py)

## 解决的问题

`download_data.py` 每次全量下载（近 3 年数据），对 5200 只股票耗时约 9 分钟。
日常更新只需下载最近 1~2 个交易日的增量数据，控制在 1 分钟内。

## 设计核心：按个股最新日期精确过滤

旧方案用一个全局 `update_start`（CSV 全局最大日期）过滤所有股票，存在三个问题：
1. **`--force` 模式重复写入** — 强制从更早日期重下时，已存在的数据被重复追加
2. **停牌股票漏数据** — 某股最大日期早于全局日期时，复牌那天的数据被过滤掉
3. **进度记录时机** — save_progress 在 buffer 写前就记录了，中断后丢数据

新方案用 **`{6位字符串股票代码: 最新日期}`** 做精确定位：

```
流程:
  1. 快速预检: 计算最后交易日 vs CSV 全局最大日期, 已对齐则直接退出
  2. 构建 stock_latest dict: pd.read_csv → groupby(股票代码)["date"].max()
  3. 获取全市场股票列表 → todo_stocks
  4. 多进程下载: 每个 worker 从 update_start 到今天
  5. 按返回的股票代码查 stock_latest.get(code), 只保留 date > 该股最新日期
  6. 每 10 只 flush → 先写 CSV, 再记进度
  7. 完成后删 .npz
```

## 快速预检

```python
today = datetime.date.today()
weekday = today.weekday()
if weekday == 5:      # 周六
    last_trade = today - timedelta(days=1)
elif weekday == 6:    # 周日
    last_trade = today - timedelta(days=2)
else:
    last_trade = today  # 周一到周五
```

- 正常模式：如果 CSV 最新日期 ≥ 最后交易日，直接退出（0 秒）
- `--force` 模式：跳过预检，强制下载

## 与 download_data.py 的关键区别

| 方面 | download_data.py | update_data.py |
|------|-----------------|----------------|
| 起始日期 | today - 10年 | CSV 最新日期 (或 --force 指定) |
| 过滤粒度 | 无过滤 | 按个股最新日期精确过滤 `> stock_latest[code]` |
| 快速度检察 | 无 | 最后交易日对比，已对齐即退出 |
| 断点写入时机 | save_progress 在 buffer 后 | save_batch_progress 在 flush 后 |
| 强制模式 | 无 | `--force YYYYMMDD` |
| 新股处理 | 全量写入 | dict 中查不到 → 保留全部返回数据 |

## 已知坑

### 1. stock_latest 类型一致性

CSV **股票代码** 列默认为 `int64`（如 `45`），akshare 返回 `str("000045")`。
`stock_latest.get("000045")` 永远查不到 int key `45`，导致所有股票被当成新股，
数据全部通过过滤 → **大量重复写入**。

修复：读取后立即转成 6 位字符串：
```python
df["股票代码"] = df["股票代码"].apply(lambda x: f"{int(x):06d}")
```

### 2. core/platform.py 命名冲突 [已永久修复]

~~`core/platform.py` 与 stdlib `import platform` 冲突。~~

已于 2026-05-19 永久修复：`core/platform.py` → `core/runner.py`，不再需要任何
workaround。详见 SKILL.md 的 Path Resolution & Pitfalls 章节。

### 3. CSV 编码损坏

`errors='replace'` 后，日期列可能混入数值（如 `"10.74"`），需要先过滤：
```python
df = df[df["date"].str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)]
```

### 4. akshare 多进程

必须使用 `mp.get_context("spawn")`，akshare 内部用 `py_mini_racer` 解析 JS。

### 5. _update_progress.txt 与手动删数据冲突

当手动从 CSV 删除部分交易日数据（如测试增量更新时），`update_data.py` 仍会从
`_update_progress.txt` 读取各股票的上次更新状态，认为这些股票已覆盖到最新日期，
导致 `todo_stocks` 为空，实际上不会重新下载已删除的日期数据。

**修复**：手动删 CSV 数据后，必须同时删除 `_update_progress.txt`：

```bash
rm -f data/_update_progress.txt
```

否则 `update_data.py` 会输出 `"检测到上次进度: XXXX 只已完成，跳过"` 并跳过
所有股票。此时增量更新虽完成但 `新增 0 条记录`，CSV 中仍缺失已删数据。

**注意**：`_update_progress.txt` 与 `download_data.py` 的 `_progress.txt` 是
两个不同的文件，互不影响。

运行后检查：
1. CSV 行数应增加（非周末运行，且确实有新的交易日数据）
2. `_update_log.txt` 确认无错误
3. `.npz` 文件已被删除
4. `python -c "import pandas as pd; d=pd.read_csv('data/a_stock_kline_3y.csv'); print(d.date.max())"`
5. 无重复：`python -c "import pandas as pd; d=pd.read_csv('data/a_stock_kline_3y.csv'); print(d.duplicated(subset=['股票代码','date']).sum())"`
