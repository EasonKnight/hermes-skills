# APP 自动研发按钮两阶段架构

## 设计（2026-05-18 重构）

**问题**：旧版 Hermes agent 同时负责写代码 + 跑回测，8分钟内常超时（回测耗时 2-3 分钟/策略，加上思考时间经常不够）。

**方案**：两阶段拆分。

### Phase 1: Hermes 写代码

`hermes -z` prompt 要求 agent **只写策略代码到 strategies/ 目录，不跑回测**。

> ⚠️ **路径必须绝对**：`hermes -z` 将 prompt 作为纯文本参数传入，Hermes 进程不知道 CWD。不可用 `./` 或相对路径。必须在 prompt 文本中硬编码绝对路径（从 `PROJECT_ROOT` 动态生成，路径中的 `\\` 需双写为 `\\\\`）。

#### 推荐 Prompt 结构（2026-05-23 优化）

提示词是"任务书"而非"操作手册"（操作手册由 skill 提供）。高质量 prompt = 8 个板块：

```
你是 alpha 工厂，不是分析师。加载 alpha-rapid-combinatorics skill，按以下任务书执行：

【任务】生成 2~3 个 CSI1000 周频 alpha 策略，方向必须互不相同

【环境】
  项目根目录: <绝对路径>
  数据: data/a_stock_kline_3y.npz（close/open/high/low/volume，5203股×2426日）
  因子工具: core/alpha_utils.py
  策略模板: 参考 strategies/ 下已有的 a5xx_*_weekly.py 文件

【可用批处理函数】（全部 (N_stocks, N_days) 矩阵运算，零 for 循环）
  ret_n_batch / vol_n_batch / amihud_illiq_batch / amount_ratio_batch
  price_position_batch / decay_linear_batch / zscore_rank_matrix / forward_fill_alpha
  组合模式: 比率 / 加法 / 乘法 / 杠铃

【铁律】
  1. generate_alpha() 零 Python for 循环 — 全用 *_batch 函数
  2. sliding_window_view 前 pad n−1 列（非 n 列！）
  3. forward_fill_alpha 对索引做 accumulate，不对 alpha 值做 accumulate
  4. 不要重复已有策略的方向

【创意引导 — 优先探索未知领域】
  ▸ 成交额分档杠铃 / 波动率期限结构 / 反转非对称 / 量价背离 / 尾盘效应 / 缩量放量

【避坑清单 — 以下方向已验证无效，不要浪费时间】
  K线形态 / 彩票效应(MAX) / 动量加速度 / 趋势弯曲度 / 残差动量 / ...

【输出规范】
  文件名: aXXX_描述_weekly.py / 元数据紧凑一行 / 只输出文件名 / 8分钟超时即交
```

**各板块作用**：
- **角色**：防止 agent 花时间分析表现（那不是它的工作）
- **任务**：明确数量、池子、频率、多样性要求
- **环境**：路径（绝对！）、数据字段、工具路径 — 省去 agent 自己探索
- **批处理函数**：列出可用的 `*_batch` 函数名 — agent 无需猜测有哪些工具
- **铁律**：烧过的坑（padding、accumulate bug）直接写进 prompt 防复发
- **创意引导**：6 个未探索方向，每次研发都试探新领域，避免反复产出同类因子
- **避坑清单**：已知死路直接排除，8 分钟不浪费在已验证无效的方向上
- **输出规范**：命名、元数据风格、交付物格式 — 和 Phase 2 回测管线对齐

旧版简洁 fallback（文本框为空时使用）：
```python
"你是 alpha 工厂。加载 alpha-rapid-combinatorics skill，生成 2~3 个 CSI1000 周频 alpha 策略，"
"方向互不相同。全矩阵向量化（零 for 循环），8分钟即交。只输出文件名，不做表现分析。"
```

Hermes 启动前拍快照 `before_files = set(glob("strategies/*.py"))`。

### Phase 2: 子进程自动回测

Hermes 结束后，检测新文件：
```python
after_files = set(glob("strategies/*.py"))
new_files = sorted(after_files - before_files)
```

对每个新文件启动 `subprocess.Popen([sys.executable, filepath], ...)`，PIPE 捕获输出，显示最后 20 行到 `dev_text` 面板。

### 状态显示

- `dev_label` 实时显示计时（💭思考 XXs / ⏱回测 XXs / 总计 XXs）
- Phase 1 结束后自动 `self.refresh()`（刷新策略列表显示新条目）
- Phase 2 结束后自动 `self.refresh()`（更新回测结果）

### 停止按钮

`stop_dev` 同时杀死 Hermes 进程（`_dev_proc`）和回测进程（`_bt_proc`）。
