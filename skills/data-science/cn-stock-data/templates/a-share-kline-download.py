"""
A-Share K-Line Data Batch Downloader
Data source: baostock (free, no token)
Time range: last ~3 years
Output: a_share_kline_{start_date}_{end_date}.csv

Usage:
  python a-share-kline-download.py
  
Resume support: saves progress to .download_progress.txt
"""

import baostock as bs
import csv
import os
import sys
import time
from datetime import datetime, timedelta

# === CONFIG ===
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Default: last ~3 years. Adjust as needed.
END_DATE_DEFAULT = "2025-12-31"
START_DATE_DEFAULT = (datetime.strptime(END_DATE_DEFAULT, "%Y-%m-%d") - timedelta(days=3*365)).strftime("%Y-%m-%d")

CSV_FILE = os.path.join(OUTPUT_DIR, f"a_share_kline_{START_DATE_DEFAULT}_{END_DATE_DEFAULT}.csv")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, ".download_progress.txt")
ERROR_LOG = os.path.join(OUTPUT_DIR, ".error_log.txt")

FIELDS = ['date', 'code', 'open', 'high', 'low', 'close', 'preclose', 'volume', 'amount', 'turn']
BAOSTOCK_FIELDS = ','.join(FIELDS)


def get_all_stocks(as_of_date=END_DATE_DEFAULT):
    """Get all A-share stocks (excluding indices)."""
    lg = bs.login()
    if lg.error_code != '0':
        print(f"Login failed: {lg.error_msg}")
        sys.exit(1)

    rs = bs.query_all_stock(as_of_date)
    stocks = []
    while rs.next():
        row = rs.get_row_data()
        code, status, name = row
        if status != '1':
            continue
        prefix = code.split('.')[1][:2]
        is_stock = False
        if code.startswith('sh.') and prefix in ('60', '68'):
            is_stock = True
        elif code.startswith('sz.') and prefix in ('00', '30', '20', '01'):
            is_stock = True
        if is_stock:
            stocks.append((code, name))

    bs.logout()
    return stocks


def load_progress():
    """Load completed stock codes for resume."""
    if not os.path.exists(PROGRESS_FILE):
        return set()
    with open(PROGRESS_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())


def save_progress(code):
    with open(PROGRESS_FILE, 'a') as f:
        f.write(code + '\n')


def log_error(code, name, msg):
    with open(ERROR_LOG, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now()}] {code} {name}: {msg}\n")


def download_stock(code, name, writer):
    """Download K-line data for one stock."""
    try:
        lg = bs.login()
        if lg.error_code != '0':
            raise Exception(f"Login failed: {lg.error_msg}")

        rs = bs.query_history_k_data_plus(
            code, BAOSTOCK_FIELDS,
            start_date=START_DATE_DEFAULT,
            end_date=END_DATE_DEFAULT,
            frequency='d',
            adjustflag='3'  # 3=后复权
        )
        if rs.error_code != '0':
            raise Exception(f"Query error: {rs.error_msg}")

        count = 0
        while rs.next():
            writer.writerow(rs.get_row_data())
            count += 1

        bs.logout()
        return count
    except Exception as e:
        log_error(code, name, str(e))
        return -1


def main():
    print("=" * 60)
    print(f"A-Share K-Line Data Downloader")
    print(f"Range: {START_DATE_DEFAULT} ~ {END_DATE_DEFAULT}")
    print(f"Output: {CSV_FILE}")
    print("=" * 60)

    print("\n[1/3] Fetching stock list...")
    all_stocks = get_all_stocks()
    total = len(all_stocks)
    print(f"  Total A-share stocks: {total}")

    done_codes = load_progress()
    remaining = [(c, n) for c, n in all_stocks if c not in done_codes]
    already_done = total - len(remaining)
    print(f"  Already done: {already_done}, Remaining: {len(remaining)}")

    if not remaining:
        print("\nAll done!")
        return

    file_exists = os.path.exists(CSV_FILE)
    f_out = open(CSV_FILE, 'a', newline='', encoding='utf-8')
    writer = csv.writer(f_out)
    if not file_exists:
        writer.writerow(FIELDS)

    print(f"\n[2/3] Downloading {len(remaining)} stocks...")
    start = time.time()
    success = failed = total_records = 0

    for idx, (code, name) in enumerate(remaining):
        records = download_stock(code, name, writer)
        if records >= 0:
            success += 1
            total_records += records
            save_progress(code)
        else:
            failed += 1

        if (idx + 1) % 50 == 0 or idx == len(remaining) - 1:
            elapsed = time.time() - start
            speed = (idx + 1) / elapsed if elapsed else 0
            eta = (len(remaining) - idx - 1) / speed if speed else 0
            print(f"  {already_done + success + failed}/{total} "
                  f"({(already_done + success + failed)/total*100:.1f}%) "
                  f"| OK:{success} FAIL:{failed} | rows:{total_records} "
                  f"| {speed:.1f}/s | ETA:{eta:.0f}s")

    f_out.close()
    elapsed = time.time() - start
    print(f"\n[3/3] Complete! {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"  Success: {success}, Failed: {failed}")
    print(f"  Total records: {total_records}")
    print(f"  File: {CSV_FILE}")
    if failed:
        print(f"  Errors: {ERROR_LOG}")


if __name__ == '__main__':
    main()
