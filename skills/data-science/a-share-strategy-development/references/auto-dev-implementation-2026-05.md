# 自动研发实现模式（2026-05）

## 架构
```
app.pyw 按钮 → auto_develop()
  ├── 创建 dev_frame（右侧面板，图表上方）
  ├── 启动后台 Hermes 进程（CREATE_NO_WINDOW）
  ├── 线程读取 stdout → Queue 传递
  ├── poll() 轮询队列 + 每秒更新计时器
  └── stop_dev() → proc.kill() 终止
```

## 关键代码模式

### 后台进程启动
```python
proc = subprocess.Popen(
    ["hermes", "-z", prompt],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL,
    creationflags=subprocess.CREATE_NO_WINDOW,  # 完全隐藏
    env=env, encoding="utf-8", errors="replace"
)
```

### 线程 + 队列通信
```python
q = queue.Queue()

def run_hermes():
    try:
        for line in proc.stdout:
            out_lines.append(line)
            if len(out_lines) <= 5:
                q.put(("line", line.rstrip()))
        q.put(("done", "".join(out_lines)))
    except (BrokenPipeError, OSError):
        pass  # 被 kill 时管道断开
```

### 主线程轮询
```python
def poll():
    try:
        while True:
            if getattr(self, "_dev_stopped", False):
                return
            typ, data = q.get_nowait()
            if typ == "line":
            elif typ == "done":
            elif typ == "error":
    except queue.Empty:
        pass
    if thread.is_alive():
        self.after(1000, poll)
```

### 停止按钮
```python
def stop_dev(self):
    if self._dev_proc and not self._dev_proc.poll():
        self._dev_proc.kill()
    self._dev_stopped = True
```

## 要点
- `CREATE_NO_WINDOW` 确保 Hermes 不在后台弹出控制台窗口
- `BrokenPipeError` 捕获避免 kill 后线程报错
- `_dev_stopped` 标志位双重防护（线程 + poll 都检查）
- 队列用 `get_nowait()` 非阻塞读取
- `self.after(1000, poll)` 替代 `time.sleep()` 实现定时器
