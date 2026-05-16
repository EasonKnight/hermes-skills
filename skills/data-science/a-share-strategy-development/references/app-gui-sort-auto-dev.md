## 排序键未来扩展兼容

`_get_sort_key()` 用 `enumerate(COLUMNS)` + `item[idx]` 而非固定解包，加列只需在 COLUMNS 加一行。

## 创建时间排序

`_parse_time()` 将 "MM-DD HH:MM" 转分钟数。

## 自动研发按钮

临时 .ps1 脚本 + `utf-8-sig` BOM + WScript.Shell SendKeys。`AppActivate` 前等4秒，特殊字符 `{}[]()+^%~` 需转义。
