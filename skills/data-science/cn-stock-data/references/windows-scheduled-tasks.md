# Windows Scheduled Tasks (schtasks)

## 命名约定

`【地点】仓库名 功能 频率`

示例：
- `【家】a_stock_trade 数据更新 每日2358`
- `【家】a_stock_trade 数据更新 每日20点`

## 创建每日定时任务

```bash
schtasks //create \
  //tn "【家】a_stock_trade 数据更新 每日2358" \
  //tr "C:\Users\Mayn\Desktop\a_stock_trade\core\update_data.bat" \
  //sc daily \
  //st 23:58 \
  //ru Mayn \
  //f
```

## 创建一次性测试任务

```bash
schtasks //create \
  //tn "【家】a_stock_trade 更新测试" \
  //tr "C:\Users\Mayn\Desktop\a_stock_trade\core\update_data.bat" \
  //sc once \
  //st 23:15 \
  //ru Mayn \
  //f
```

## 查询已有任务

```bash
schtasks //query //fo LIST
```

## 删除任务

```bash
schtasks //delete //tn "任务名" //f
```

## 关键注意事项

1. **batch 文件必须纯 ASCII 英文** — cmd.exe 无法解析 UTF-8 中文
2. **日志路径用绝对路径写死** — 不要依赖相对路径
3. **Python 全路径写死** — 必须用 hermes venv 的 python (`...\hermes-agent\venv\Scripts\python.exe`)，系统 Python311 没有 akshare
4. **`exit /b 0` 兜底** — batch 末尾加此行，避免 Windows 任务计划程序误报退出码
5. **`//f` 静默覆盖** — 同名任务存在时直接覆盖，不弹确认
