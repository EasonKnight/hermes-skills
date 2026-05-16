# 量化策略平台可规模化管理方案 (2026-05-16)

## 问题

当前架构（每策略一个s*.py + 文件系统扫描 + 零散结果文件夹）在50个策略内运作良好，但到500/5000个策略时面临：
- `glob` 扫描5000个文件慢
- 无法按标签/类别筛选运行
- 结果分散在5000个文件夹里，无法快速排名
- 无法只跑"新策略"或"修改过的策略"

## 方案：元数据驱动 + CSV汇总（零外部依赖）

### 总览

```
a_stock_trade/
├── core/
│   ├── backtest_utils.py    # 原有引擎（不动）
│   └── platform.py          # 新：发现+运行+排名
├── strategies/
│   ├── s76_lowvol_momentum_weekly.py
│   │   └── LABEL/FOLDER/FREQ/TAGS/POOL  # 元数据变量（顶部4行）
│   └── ... (48个策略文件)
├── results/
│   ├── S76-低波动动量周频/
│   ├── ...
│   └── _summary.csv         # 汇总结果（所有策略一行一条）
└── run_platform.py          # CLI入口
```

### 核心：策略元数据

每个策略文件顶部定义4个模块级变量：

```python
LABEL = "S76 低波动动量周频"    # 人类可读的名称
FOLDER = "S76-低波动动量周频"   # results/ 下的目录名
FREQ = "weekly"                 # weekly 或 daily
TAGS = ["momentum", "lowvol"]   # 标签列表
POOL = "csi1000"                # 股票池
```

`core/platform.py` 的 `discover()` 函数用正则 `^LABEL\s*=` 读取这些变量（不import文件），无需加载全量代码即可按标签筛选。

### 统一结果汇总

```python
# 跑完后写入 _summary.csv
import pandas as pd
rows = [{"key": ..., "策略": ..., "年化收益率": ..., "夏普比率": ..., ...}]
df = pd.DataFrame(rows)
df.to_csv("results/_summary.csv", index=False, encoding="utf-8-sig")
```

**一行CSV = 一个策略结果**。读取排名只需 `pd.read_csv(...)`，秒出。

### CLI用法

```bash
# 运行
python -m core.platform run                          # 所有策略
python -m core.platform run --tags momentum lowvol   # 按标签
python -m core.platform run --names s76 s67          # 按名字
python -m core.platform run --freq weekly            # 按频率

# 查询（不跑策略，读CSV）
python -m core.platform rank                         # 排名
python -m core.platform rank --sort 信息比率          # 按信息比排
python -m core.platform compare s76 s67              # 对比
```

### 向后兼容

- 旧策略没有元数据变量时，`LABEL` 回退到文件名
- `core/platform.py` 独立于 `backtest_utils.py` 和 `run_all.py`
- 所有现有 `run_all.py`、`app.py`、`strategies/s*.py` 不受影响
- 旧策略只需加4行变量即可加入新平台

### 注意事项

1. **汇总CSV覆盖写**：每次 `run` 命令会覆盖 `_summary.csv`，要保留历史需手动备份
2. **并发冲突**：多进程同时写 `_summary.csv` 会冲突。批量运行时用单进程或子进程通信
3. **标签命名规范**：全小写、无空格、含义清晰（`momentum`, `lowvol`, `weekly`, `reverse`, `lowprice` 等）
4. **`platform` 是Python标准库名**：`core/platform.py` 没问题，但不要在 `strategies/` 下创建 `platform.py`
