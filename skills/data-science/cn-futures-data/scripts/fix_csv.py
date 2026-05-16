"""
CSV 文件修复工具 — 多进程期货分钟数据修复
========================================
修复多进程写入导致的坏行：截断行、粘连行、编码错误
输出到 all_futures_5min_clean.csv

用法: python fix_csv.py [输入文件] [输出文件]
默认: all_futures_5min.csv → all_futures_5min_clean.csv
"""

import os
import sys
import re

SRC = sys.argv[1] if len(sys.argv) > 1 else "all_futures_5min.csv"
DST = sys.argv[2] if len(sys.argv) > 2 else "all_futures_5min_clean.csv"

EXPECTED_COLS = 11  # 合约代码,品种代码,品种名称,交易所,datetime,open,high,low,close,volume,hold


def is_valid_line(line: str) -> bool:
    """检查一行是否有效的CSV数据行"""
    parts = line.split(",")
    if len(parts) != EXPECTED_COLS:
        return False
    # 合约代码格式: 1-4个大写字母 + 4位数字, 如 CU2505
    if not re.match(r'^[A-Z]{1,4}\d{4}$', parts[0]):
        return False
    # 品种代码: 1-4个大写字母
    if not re.match(r'^[A-Z]{1,4}$', parts[1]):
        return False
    # datetime格式: YYYY-MM-DD HH:MM:SS
    if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', parts[4]):
        return False
    # 价格列是数字
    try:
        float(parts[5])
        float(parts[6])
        float(parts[7])
        float(parts[8])
    except ValueError:
        return False
    return True


def main():
    print(f"修复 {SRC} → {DST}")
    fsize = os.path.getsize(SRC)
    print(f"文件大小: {fsize / 1024 / 1024:.0f} MB")

    n_total = 0
    n_valid = 0
    n_fixed = 0
    n_skipped = 0

    with open(SRC, "rb") as fin, open(DST, "wb") as fout:
        while True:
            line = fin.readline()
            if not line:
                break
            n_total += 1

            # 表头行
            if n_total == 1:
                fout.write(line)
                continue

            # 尝试UTF-8解码
            try:
                text = line.decode("utf-8").strip("\r\n")
            except UnicodeDecodeError:
                try:
                    text = line.decode("gbk").strip("\r\n")
                except Exception:
                    n_skipped += 1
                    continue

            if is_valid_line(text):
                fout.write(line)
                n_valid += 1
            else:
                n_skipped += 1
                # 两行粘连: 超长且可拆分
                if len(text) > 200:
                    # 尝试按合约代码拆分
                    for sep in ["FB", "PP", "L(", "V(", "J(", "JM", "EG", "EB"]:
                        idx = text.find(sep, 50)
                        if 0 < idx < len(text) - 20:
                            part1, part2 = text[:idx], text[idx:]
                            if is_valid_line(part1) and is_valid_line(part2):
                                fout.write((part1 + "\n").encode("utf-8"))
                                fout.write((part2 + "\n").encode("utf-8"))
                                n_fixed += 2
                                n_valid += 2
                                break
                    else:
                        # 按列数拆分
                        parts = text.split(",")
                        if len(parts) > EXPECTED_COLS:
                            for split_at in range(EXPECTED_COLS, len(parts) - EXPECTED_COLS + 1, EXPECTED_COLS):
                                p1 = ",".join(parts[:split_at])
                                p2 = ",".join(parts[split_at:])
                                if is_valid_line(p1) and is_valid_line(p2):
                                    fout.write((p1 + "\n").encode("utf-8"))
                                    fout.write((p2 + "\n").encode("utf-8"))
                                    n_fixed += 2
                                    n_valid += 2
                                    break

            if n_total % 500000 == 0:
                pct = fin.tell() / fsize * 100
                sys.stdout.write(f"\r  进度: {pct:.0f}% | 总{n_total:,} | 有效{n_valid:,} | 修复{n_fixed} | 跳过{n_skipped}  ")
                sys.stdout.flush()

    print(f"\n\n完成!")
    print(f"  总行数: {n_total:,}")
    print(f"  有效行: {n_valid:,}")
    print(f"  修复行: {n_fixed}")
    print(f"  跳过行: {n_skipped}")
    print(f"  输出: {DST}")

    # 如果坏行率<1%，自动替换原文件
    if n_skipped <= 20 and n_valid > 0.99 * n_total:
        backup = SRC + ".bak"
        os.rename(SRC, backup)
        os.rename(DST, SRC)
        os.remove(backup)
        print(f"  已替换原文件 (备份: {backup})")
    else:
        print(f"  手动检查后决定是否替换原文件")


if __name__ == "__main__":
    main()
