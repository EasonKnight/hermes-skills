# app.pyw `_parse_label` 正则匹配坑

## 问题
策略文件的元数据变量名不统一：
- 旧策略（S01~S99+）：`label = "..."` / `folder = "..."`（小写，模块级）
- 新策略（S100+）：`LABEL = "..."` / `FOLDER = "..."`（大写，模块级）

platform.py 的 `_read_meta()` 只识别大写 `LABEL`/`FOLDER` key，找不到就用`setdefault("FOLDER", key)`（key = 文件名 stem）。

## 后果
- app若用文件名stem匹配→新策略显示中文名，旧策略显示文件名
- app若用小写folder匹配→旧策略读到了小写`folder`，但platform.py实际保存到文件名目录
- 结果目录名不一致，app扫不到stats.csv → 列表全空

## 修复（2026-05-16）
`_parse_label` 分两步：

```python
# 1. 先匹配大写 LABEL/FOLDER（与 platform.py _read_meta 一致）
m = re.search(r'LABEL\s*=\s*["\'](.+?)["\']', content)
label = m.group(1) if m else None
m2 = re.search(r'FOLDER\s*=\s*["\'](.+?)["\']', content)
folder = m2.group(1) if m2 else None

# 2. 无大写时回退到文件名（与 _read_meta 的 setdefault一致）
if not label:
    label = os.path.splitext(os.path.basename(src_path))[0]
if not folder:
    folder = os.path.splitext(os.path.basename(src_path))[0]
```

**关键**：不匹配小写 `label`/`folder`，因为platform.py不认它们。
