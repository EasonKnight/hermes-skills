# A股代码前缀过滤

阻止 B 股（200xxx/900xxx）、债券、基金等非 A 股数据混入 NPZ 缓存或下载流程。

## 有效 A 股 3 位前缀

```python
A_SHARE_PREFIXES = {
    "000", "001", "002", "003",     # 深市主板
    "300", "301", "302", "303",     # 创业板（ChiNext）
    "600", "601", "603", "605",     # 沪市主板
    "688",                          # 科创板（STAR）
}
```

## 过滤位置

需要在3个地方同步过滤：

### 1. `update_data.py` — `get_all_stocks()`（下载时过滤）

```python
def get_all_stocks():
    import akshare as ak
    df = ak.stock_info_a_code_name()
    a_prefixes = {"000","001","002","003","300","301","302","303",
                  "600","601","603","605","688"}
    stocks = []
    for _, row in df.iterrows():
        code = str(row["code"]).strip()
        ...
        if code[:3] not in a_prefixes:
            continue
        stocks.append((code, name, symbol))
    return stocks
```

### 2. `update_data.py` — `_build_cache()`（构建 NPZ 时过滤）

过滤在 pivot 之后、ffill 之前：

```python
a_prefixes = {"000","001","002","003","300","301","302","303",
              "600","601","603","605","688"}
keep_a = [c for c in close_df.index if str(c)[:3] in a_prefixes]
close_df = close_df.loc[keep_a]
# ... 其他字段同样过滤
names = names[names.index.isin(keep_a)]
```

### 3. `update_fundamentals.py` — `get_all_stocks()`（基本面下载时过滤）

```python
a_prefixes = {"000","001","002","003","300","301","302","303",
              "600","601","603","605","688"}
if code[:3] not in a_prefixes:
    continue
```

## akshare 股票列表源

`ak.stock_info_a_code_name()` 返回包含 B 股（200xxx）、债券、基金等约 6700+ 条记录。仅约 5240 只是 A 股。必须用前缀白名单严格过滤。

## 历史数据清洗

CSV 中已混入的非 A 股数据（~1450 只，~320 万行）需要一次性移除：

```python
import pandas as pd
df = pd.read_csv(csv, dtype={'股票代码': str})
a_prefixes = ('000','001','002','003','300','301','302','303',
              '600','601','603','605','688')
mask = df['股票代码'].str[:3].isin(a_prefixes)
df[mask].to_csv(csv, index=False, encoding='utf-8-sig')
```
