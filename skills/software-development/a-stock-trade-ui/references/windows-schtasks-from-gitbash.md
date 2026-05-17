# Windows 定时任务创建（从 git-bash 操作）

## 核心问题

git-bash (MSYS2) 会把 `/create`、`/tn` 等 schtasks 参数解释为 Unix 路径，导致 `C:/Users/.../git/create` 之类错误。

## 解决方案

### 方案A：MSYS2_ARG_CONV_EXCL 环境变量（推荐）

```bash
MSYS2_ARG_CONV_EXCL="*" schtasks /create /tn "任务名" /tr "C:\path\to\script.bat" /sc daily /st 20:00 /ru Mayn /f
```

`MSYS2_ARG_CONV_EXCL="*"` 禁止 MSYS2 对任何参数做路径转换。

### 方案B：双斜杠前缀

```bash
/c/Windows/System32/schtasks.exe //create //tn "任务名" //tr "C:\path\to\script.bat" //sc daily //st 20:00 //ru Mayn //f
```

双斜杠 `//create` 防止 MSYS2 路径展开。注意路径参数中的 `\` 无需转义。

## 命名约定

使用中文名（和 git_sync 任务风格一致）：

```
【地点】仓库名 功能 频率
```

例如：
- `【家】a_stock_trade 数据更新 每日20点`
- `【家】a_stock_trade git同步 每日8点`

中文名在 schtasks 中完全可用，配合 `//create` 或 `MSYS2_ARG_CONV_EXCL` 即可。Windows 任务计划程序 GUI 中按拼音排序显示。

## .bat 包装器路径

.bat 文件和 schtasks 的 `/tr` 路径保持一致。例如脚本在 `core/update_data.bat`，那么 `/tr` 也填完整路径 `C:\...\core\update_data.bat`。

## 常见参数

| 参数 | 说明 |
|------|------|
| `/tn` | 任务名称（英文名避免编码问题） |
| `/tr` | 执行程序路径 |
| `/sc daily` | 每日触发 |
| `/st 20:00` | 启动时间 |
| `/ru Mayn` | 运行用户（用具体用户名而非 INTERACTIVE，避免 Access denied）。中文任务名配合 `//` 前缀和 `/ru 用户名` 可正常创建 |
| `/f` | 强制覆盖已存在的任务 |
| `/delete /tn "任务名" /f` | 删除任务 |

## 配合 .bat 包装器

始终创建一个 .bat 文件作为任务入口，用 `cd /d` 设置工作目录：

```bat
@echo off
cd /d "C:\Users\Mayn\Desktop\a_stock_trade"
"C:\Users\Mayn\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" core\update_data.py
```

## 验证任务

```bash
MSYS2_ARG_CONV_EXCL="*" schtasks /query /tn "任务名" /v /fo LIST
```

关键检查项：Next Run Time、Status (Ready)、Task To Run 路径正确、Run As User 正确。
