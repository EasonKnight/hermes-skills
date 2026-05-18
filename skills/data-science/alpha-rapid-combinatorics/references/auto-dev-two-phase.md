# APP 自动研发按钮两阶段架构

## 设计（2026-05-18 重构）

**问题**：旧版 Hermes agent 同时负责写代码 + 跑回测，8分钟内常超时（回测耗时 2-3 分钟/策略，加上思考时间经常不够）。

**方案**：两阶段拆分。

### Phase 1: Hermes 写代码

`hermes -z` prompt 要求 agent **只写策略代码到 strategies/ 目录，不跑回测**。Prompt 核心约束：
```python
"不要运行回测！只写代码文件。输出创建的文件名。"
"POOL=CSI1000，元数据紧凑风格。不做任何表现分析。8分钟超时即交。"
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
