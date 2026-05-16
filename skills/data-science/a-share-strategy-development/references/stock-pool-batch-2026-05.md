# 股票池批量添加记录（2026-05-15）

## 背景

给全部 ~60 个策略文件（s01-s56 + tuned 版本）统一添加 `STOCK_POOL = "all"` / `"csi1000"` 切换功能。

## 核心要求

1. **零手动修改** — 用脚本一次性批量处理所有策略文件
2. **每个策略文件顶部加一行常量**：`STOCK_POOL = "all"`（全市场）或 `"csi1000"`（中证1000）
3. **main() 中注入 pool mask 代码**：`pool_1d = stock_pool_mask(loader.codes, STOCK_POOL)` + `valid = (close > 0.5) & pool_1d[:, np.newaxis]`
4. **engine.run()** 传入 `valid=valid`
5. **label** 自动追加 `（全市场）` 后缀

## 技术难点

### 1. 文件结构不统一

策略文件有三种结构：
- **简单型**（s01）：import → def → main
- **含常量型**（s31）：import → LOOKBACK=60 → def → main
- **含辅助函数型**（s07）：import → def _vol() → def generate_signal() → main

### 2. 变量名冲突

`generate_signal()` 内部也可能使用名为 `valid` 的局部变量。Python 作用域规则保证了 `main()` 中的 `valid` 与函数内的 `valid` 不冲突，但人眼检查时容易混淆。

### 3. 跨行 engine.run() 调用

有些策略的 `engine.run(close, signal, dates, trading_rules=rules,` 以 `\` 或 `(\n` 换行。正则替换 `valid=` 时需要找到右括号行。

## 两阶段批处理模式

### v1 脚本（问题版）

```python
# 问题：正则不够健壮
# 1. 注入 import stock_pool_mask 后造成双逗号: "SLIPPAGE,,"
# 2. pool_mask 代码未注入（close/dates 分两行写，regex 只匹配了分号版）
# 3. engine.run() 加了 valid=valid 但 valid 未定义
```

### v2 修复脚本

分两步：
1. `_batch_add_pool_v2.py` — 重新跑一次，处理未修改的文件
2. `_fix_v1.py` — 修复 v1 遗留问题：双逗号 + 补 pool_mask 代码

### 关键代码模式

```python
# 匹配 close/dates 行（分两行的情况）
r'^(\s*)dates\s*=\s*loader\.dates\s*$'

# 匹配分号一行的情况
r'close\s*=\s*loader\.close\s*;\s*dates\s*=\s*loader\.dates'

# 修复双逗号
text = text.replace(",,", ",")
text = text.replace("(,", "(")
```

## stock_pool_mask 函数

```python
def stock_pool_mask(codes, pool="all"):
    """返回布尔掩码 (N_stocks,)，True 表示该股票属于所选股票池。"""
    mask = np.ones(len(codes), dtype=bool)
    if pool == "csi1000":
        csi_set = load_csi1000_codes()
        if csi_set:
            mask = np.array([str(c).strip()[:6] in csi_set for c in codes], dtype=bool)
            print(f"  [股票池] 中证1000: {mask.sum()}/{len(codes)} 只成分股在数据中")
    return mask

def load_csi1000_codes():
    """自动下载/加载中证1000成分股，返回 set。"""
    path = "~/Desktop/a_stock_trade/data/csi1000_cons.csv"
    if not os.path.exists(path):
        import akshare as ak
        df = ak.index_stock_cons(symbol="000852")
        df["code"] = df["品种代码"].astype(str).str[:6]
        df.to_csv(path, index=False, encoding="utf-8-sig")
    df = pd.read_csv(path, encoding="utf-8-sig")
    return set(df["股票代码"].astype(str).str.strip().tolist())
```

## 验证结果

| 策略 | 全市场 IR | 中证1000 IR | 日均持股(全) | 日均持股(1000) |
|:----|:--------:|:----------:|:----------:|:-------------:|
| S01 等权日频 | 1.05 | **1.67** | 2,899只 | 281只 |
| S49 低价+低波 | 0.98 | 0.94 | 785只 | 72只 |

## 经验

1. 批量改 Python 文件永远用 Python 脚本，不要用 sed/awk
2. 先做 backup 或只测试一个文件再批量
3. 分两阶段：先注入 import + run，再补 pool_mask 代码（减少单次脚本复杂度）
4. `stock_pool_mask` 函数接收 `codes` array，返回 `(N_stocks,) bool`，配合 `[:, np.newaxis]` broadcast 到 2D
5. CSI1000 成分股约 284/2930 在数据中（不是全部 1000 只都在 3 年 K 线数据里）
