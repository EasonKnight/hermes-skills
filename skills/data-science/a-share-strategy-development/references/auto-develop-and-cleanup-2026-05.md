# 自动研发 + 策略清理记录 (2026-05-16)

## 自动研发按钮实现

app.py 左侧 "🤖 自动研发" 按钮的完整实现模式：

### 核心：隐藏进程 + 线程 + 队列轮询

```python
import subprocess, threading, queue

def auto_develop(self):
    q = queue.Queue()
    
    def run_hermes():
        env = os.environ.copy()
        env["USERPROFILE"] = "C:\\Users\\Mayn"
        proc = subprocess.Popen(
            ["hermes", "-z", prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            env=env, encoding="utf-8", errors="replace"
        )
        for line in proc.stdout:
            q.put(("line", line.rstrip()))
        proc.wait()
        q.put(("done", output))
    
    threading.Thread(target=run_hermes, daemon=True).start()
    
    elapsed = [0]
    def poll():
        self.after(1000, poll)
    poll()
```

### 关键设计决策
- 不弹独立终端窗口（用户明确反对）
- 采用隐藏进程 + 队列轮询模式，只在界面显示进度和最终结果
- Hermes -z (oneshot) 模式直接传入提示词，无需交互

## 策略清理方法论（69→25）

### 清理决策树

```
策略文件 → 有回测结果？
   ├── 否 → 立即删除
   └── 是 → 年化 > 15% 且 夏普 > 0.4？
       ├── 是 → 保留（核心）
       └── 否 → 年化 > 0% 且 有独特价值？
           ├── 是 → 保留做参考
           └── 否 → 删除
检查相似度 → 与已有策略重复？
   ├── 是 → 只留表现最好的
   └── 否 → 保留
检查信号量 → 日均持股 < 10只 → 删除
```

### 各策略去留原因

| 操作 | 策略 | 原因 |
|------|------|------|
| 删除 | s10/s15/s16/s19/s22/s27/s30/s36/s61/s62 | 年化<-10% |
| 删除 | s25/s59/s60/s63/s64/s65/s87 | 被s66/s67覆盖 |
| 删除 | s05/s06/s29 | 动量因子失效 |
| 删除 | s26/s68 | 高价策略无意义 |
| 删除 | s03/s08/s09/s13/s23/s32/s71/s73/s74/s75 | 年化<5% |
| 删除 | s59=s60 | 逻辑等价 |
| 保留 | 25个核心 | 见策略列表 |
