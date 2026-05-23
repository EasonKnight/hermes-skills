# 券商导出文件格式陷阱

## table.xls — 看起来是 Excel, 实际是 GBK TSV

在 `a_stock_trade/` 项目中, `table.xls` 文件虽然扩展名是 `.xls`, 但**不是** Excel 文件。
它是从券商（证券交易软件）导出的 **GBK 编码制表符分隔文本文件**。

### 检测方法

当 `pd.read_excel()` 报错 `Excel file format cannot be determined` 时,
检查文件头部原始字节:

```python
with open("table.xls", "rb") as f:
    header = f.read(200)
    # GBK 编码的汉字以 0xB0-0xF7 范围开头
    print(header[:50])  # 如: b'\xb2\xd9\xd7\xf7\t\xd0\xf2\xba\xc5\t...'
```

### 正确读取

```python
import pandas as pd
df = pd.read_csv("table.xls", sep="\t", encoding="gbk")
```

### 列名（券商标准导出格式）

| 列名 | 含义 | 类型 |
|------|------|------|
| 操作 | 操作类型 | str |
| 序号 | 行号 | int |
| 证券代码 | 6位股票代码 | str |
| 证券名称 | 中文名称 | str |
| 股票余额 | 持股数量（股） | int |
| 实际数量 | 实际持有（含冻结） | int |
| 可用余额 | 可卖出数量 | int |
| 冻结数量 | 冻结中数量 | int |
| 成本价 | 持仓成本 | float |
| 市价 | 当前市价 | float |
| 盈亏 | 浮动盈亏（元） | float |
| 盈亏比(%) | 盈亏百分比 | float |
| 市值 | 持仓市值 | float |
| 当日买入 | 当日买入量 | int |
| 当日卖出 | 当日卖出量 | int |
| 交易市场 | 深圳Ａ股/上海Ａ股 | str |
| 持股天数 | 持有天数 | int |

### 关键指标

- **股票余额** = 实际持仓股数（1 股 = 1 单位）
- 可能包含 ETF（511880 银华日利等）和非股票品种，需按需过滤
- 代码为 6 位数字字符串，无前缀（如 `300406` 而非 `sz300406`）

---

## 组合持仓 CSV — 策略生成的目标持仓

`组合持仓_YYYYMMDD.csv` 是 app.pyw 导出的目标持仓文件:

- 编码: UTF-8 with BOM (`utf-8-sig`)
- 分隔符: 逗号
- 关键列: `股票代码` (6位), `股票名称`, `总手数` (手, 1手=100股), `参考价`, `总市值`

### 手→股转换

目标持仓的 `总手数` 是 **手**（1手=100股），与券商导出的 `股票余额`（股）单位不同:

```python
target_shares = target["总手数"] * 100  # 手 → 股
diff = target_shares - current_shares   # 计算调整量
```
