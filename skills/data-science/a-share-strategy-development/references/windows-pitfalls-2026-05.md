# Windows 平台要点速查

## 环境变量 USERPROFILE
在 git-bash 中 `os.path.expanduser('~')` 依赖 Windows 的 `USERPROFILE` 而非 bash 的 `$HOME`。被污染时：

```bash
USERPROFILE="C:\Users\Mayn" python strategies/sXX_xxx.py
```

## cmd.exe 中文编码
中文传参给 cmd 会乱码。可靠方法：
- `-z` 参数直接传给 hermes
- `.bat` 文件用 UTF-8 BOM + `chcp 65001`
- 优先用 PowerShell 脚本或 Python subprocess 直接传参

## subprocess 模式选择
| 场景 | 方法 |
|------|------|
| 隐藏后台进程 | `CREATE_NO_WINDOW` + PIPE |
| 弹出终端窗口 | `CREATE_NEW_CONSOLE` + shell=True |
| 终端自动关闭 | `/c` 参数 |
| 终端保持打开 | `/k` 参数 |
| 阻止灰色禁用文字 | `disabledforeground="white"` |

## tkinter Treeview 技巧
- 排序用 `sort_by()` + `_get_sort_key()`，永不固定解包元组
- 交替行：`tag_configure("odd"/"even", background=...)`
- 列头点击排序：`heading(col, command=lambda c=col: self.sort_by(c))`
- 新增列只需在 `COLUMNS` 加一行定义

## 后台进程 + token 保护
```python
proc.kill()                    # 立即终止 HTTP 连接
_dev_stopped = True            # 阻止线程发完成消息
while not q.empty(): q.get()   # 清空残留消息队列
```
