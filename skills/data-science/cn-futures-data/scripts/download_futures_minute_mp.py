#!/usr/bin/env python
"""
国内期货全品种全历史分钟K线数据下载器（多进程版）
=====================================================
- 多进程并行下载 (spawn mode)
- 所有品种写入同一个 CSV 文件（带 品种代码/品种名称/交易所 列）
- 支持断点续传
- 输出到主目录下 all_futures_5min.csv

数据源: AKShare → 新浪财经 (免费，无需账号)
用法:  python download_futures_minute_mp.py
"""

import os, sys, time, datetime, multiprocessing as mp

# ── 配置 ──
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "all_futures_5min.csv")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "_progress_5min.txt")
ERROR_FILE = os.path.join(OUTPUT_DIR, "_errors_5min.txt")
PERIOD = "5"                  # 1/5/15/30/60
WORKERS = 6
FLUSH_INTERVAL = 20
BATCH_SIZE = 15
REQUEST_INTERVAL = 0.2
# ===========================================================

CONTRACT_INFO = {
    "CU":("沪铜","上期所",2005), "AL":("沪铝","上期所",2005), "ZN":("沪锌","上期所",2007),
    "PB":("沪铅","上期所",2011), "NI":("沪镍","上期所",2015), "SN":("沪锡","上期所",2015),
    "AU":("沪金","上期所",2008), "AG":("沪银","上期所",2012), "RB":("螺纹钢","上期所",2009),
    "HC":("热轧卷板","上期所",2014), "SS":("不锈钢","上期所",2019), "BU":("沥青","上期所",2013),
    "RU":("橡胶","上期所",2005), "FU":("燃料油","上期所",2005), "SP":("纸浆","上期所",2018),
    "WR":("线材","上期所",2009,[1,3,5,7,9,11]),
    "C":("玉米","大商所",2005,[1,3,5,7,9,11]), "CS":("玉米淀粉","大商所",2014,[1,3,5,7,9,11]),
    "A":("豆一","大商所",2005,[1,3,5,7,9,11]), "B":("豆二","大商所",2007,[1,3,5,7,9,11]),
    "M":("豆粕","大商所",2005,[1,3,5,7,9,11]), "Y":("豆油","大商所",2006,[1,3,5,7,9,11]),
    "P":("棕榈油","大商所",2007,[1,3,5,7,9,11]), "FB":("纤维板","大商所",2013,[1,3,5,7,9,11]),
    "BB":("胶合板","大商所",2013,[1,3,5,7,9,11]), "JD":("鸡蛋","大商所",2013),
    "L":("聚乙烯(塑料)","大商所",2007), "PP":("聚丙烯","大商所",2014), "V":("PVC","大商所",2009),
    "EG":("乙二醇","大商所",2018), "J":("焦炭","大商所",2011), "JM":("焦煤","大商所",2013),
    "I":("铁矿石","大商所",2013), "PG":("液化石油气","大商所",2020), "EB":("苯乙烯","大商所",2019),
    "RR":("粳米","大商所",2019), "LH":("生猪","大商所",2021,[1,3,5,7,9,11]),
    "LG":("原木","大商所",2024,[1,3,5,7,9,11]), "BZ":("纯苯","大商所",2025),
    "TA":("PTA","郑商所",2006), "OI":("菜油","郑商所",2007,[1,3,5,7,9,11]),
    "RS":("菜籽","郑商所",2012,[7,8,9,11]), "RM":("菜粕","郑商所",2012,[1,3,5,7,9,11]),
    "WH":("强麦","郑商所",2005,[1,3,5,7,9,11]), "JR":("粳稻","郑商所",2013,[1,3,5,7,9,11]),
    "SR":("白糖","郑商所",2006,[1,3,5,7,9,11]), "CF":("棉花","郑商所",2005,[1,3,5,7,9,11]),
    "ZC":("动力煤","郑商所",2015), "FG":("玻璃","郑商所",2012), "MA":("甲醇","郑商所",2014),
    "AP":("苹果","郑商所",2017,[1,3,4,5,10,11,12]), "CJ":("红枣","郑商所",2019,[1,3,5,7,9,12]),
    "UR":("尿素","郑商所",2019), "SA":("纯碱","郑商所",2019), "SF":("硅铁","郑商所",2014),
    "SM":("锰硅","郑商所",2014), "CY":("棉纱","郑商所",2017), "PF":("短纤","郑商所",2020),
    "PK":("花生","郑商所",2021,[1,3,4,10,11,12]), "LR":("晚籼稻","郑商所",2014,[1,3,5,7,9,11]),
    "RI":("早籼稻","郑商所",2009,[1,3,5,7,9,11]), "PM":("普麦","郑商所",2019,[1,3,5,7,9,11]),
    "IF":("沪深300","中金所",2017), "IC":("中证500","中金所",2017), "IH":("上证50","中金所",2017),
    "IM":("中证1000","中金所",2022), "T":("10年期国债","中金所",2017,[3,6,9,12]),
    "TF":("5年期国债","中金所",2017,[3,6,9,12]), "TS":("2年期国债","中金所",2018,[3,6,9,12]),
    "TL":("30年期国债","中金所",2023,[3,6,9,12]),
    "SC":("原油","上期能源",2018), "LU":("低硫燃料油","上期能源",2020),
    "BC":("国际铜","上期能源",2020), "NR":("20号胶","上期能源",2019),
    "SI":("工业硅","广期所",2022), "LC":("碳酸锂","广期所",2023),
}

NOW, CUR_YEAR, CUR_MONTH = datetime.datetime.now(), datetime.datetime.now().year, datetime.datetime.now().month

def log(msg, f=None):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    if f: f.write(f"[{ts}] {msg}\n"); f.flush()

def generate_all_contracts():
    all_c = []
    for pc, info in CONTRACT_INFO.items():
        _, _, sy = info[0], info[1], info[2]
        ms = info[3] if len(info) > 3 else list(range(1, 13))
        for y in range(sy, CUR_YEAR + 1):
            for m in ms:
                if y == CUR_YEAR and m > CUR_MONTH + 3: continue
                all_c.append((f"{pc}{y%100:02d}{m:02d}", pc, info[0], info[1]))
    return all_c

def load_done_set():
    if not os.path.exists(PROGRESS_FILE): return set()
    done = set()
    with open(PROGRESS_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split(",")
                if len(parts) >= 1: done.add(parts[0])
    return done

def save_progress(c, pc, pn, s, r):
    with open(PROGRESS_FILE, "a") as f: f.write(f"{c},{pc},{pn},{s},{r}\n")

def save_error(c, pc, pn, e):
    with open(ERROR_FILE, "a") as f: f.write(f"{c},{pc},{pn},{e}\n")

def _download_one(params):
    contract, prod_code, prod_name, exch = params
    try:
        import akshare as ak
        time.sleep(REQUEST_INTERVAL)
        df = ak.futures_zh_minute_sina(symbol=contract, period=PERIOD)
        if df is None or len(df) == 0:
            return (contract, prod_code, prod_name, "empty", None)
        df.insert(0, "交易所", exch)
        df.insert(0, "品种名称", prod_name)
        df.insert(0, "品种代码", prod_code)
        df.insert(0, "合约代码", contract)
        return (contract, prod_code, prod_name, "ok", df.to_dict("records"))
    except Exception as e:
        err = str(e).replace("\n"," ").replace(",","，")[:120]
        if "Length mismatch" in err:
            return (contract, prod_code, prod_name, "empty", None)
        return (contract, prod_code, prod_name, "error", err)

def main():
    mp.freeze_support()
    pn = {"1":"1分钟","5":"5分钟","15":"15分钟","30":"30分钟","60":"60分钟"}.get(PERIOD,f"{PERIOD}分钟")
    print("="*60); print(f"  国内期货全品种 {pn} 数据下载 (多进程版)"); print("="*60)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_c = generate_all_contracts()
    total = len(all_c)
    print(f"总合约: {total}  WORKERS={WORKERS}")

    done_set = load_done_set()
    todo = [c for c in all_c if c[0] not in done_set]
    print(f"已有进度: {len(done_set)}  还需: {len(todo)}")
    if not todo: print("全部完成!"); return

    buffer, first_batch = [], not (os.path.exists(OUTPUT_CSV) and os.path.getsize(OUTPUT_CSV) > 0)
    csf, stats, t0 = 0, {"ok":0,"empty":0,"error":0,"rows":0,"done":0}, time.time()

    lf = open(os.path.join(OUTPUT_DIR,"_log_5min.txt"),"a"); log("下载开始",lf); log(f"{len(todo)} contracts, {WORKERS} workers",lf)
    import pandas as pd

    ctx = mp.get_context("spawn")
    with ctx.Pool(WORKERS) as pool:
        for result in pool.imap_unordered(_download_one, todo, chunksize=BATCH_SIZE):
            c, pc, pn, s, d = result
            if s == "ok": buffer.extend(d); stats["ok"]+=1; stats["rows"]+=len(d); csf+=1; save_progress(c,pc,pn,s,len(d))
            elif s == "empty": stats["empty"]+=1; csf+=1; save_progress(c,pc,pn,s,0)
            else: stats["error"]+=1; csf+=1; save_progress(c,pc,pn,s,0); save_error(c,pc,pn,d)
            stats["done"]+=1

            if csf >= FLUSH_INTERVAL and buffer:
                pd.DataFrame(buffer).to_csv(OUTPUT_CSV, mode="a", header=first_batch, index=False, encoding="utf-8-sig")
                first_batch, buffer, csf = False, [], 0

            el = time.time()-t0; rt = stats["done"]/el if el>0 else 0; rm = (len(todo)-stats["done"])/rt if rt>0 else 0
            eta = f"{rm/60:.0f}m" if rm>60 else f"{rm:.0f}s"
            sys.stdout.write(f"\r  [{stats['done']}/{len(todo)}] OK:{stats['ok']} 空:{stats['empty']} 错:{stats['error']} {stats['rows']:,}行 {rt:.1f}/s ETA:{eta}   "); sys.stdout.flush()
            if stats["done"]%200==0: log(f"[{stats['done']}/{len(todo)}] OK:{stats['ok']} 空:{stats['empty']} 错:{stats['error']} {stats['rows']:,}行 {rt:.1f}/s ETA:{eta}",lf)

    if buffer:
        pd.DataFrame(buffer).to_csv(OUTPUT_CSV, mode="a", header=first_batch, index=False, encoding="utf-8-sig")
    el = time.time()-t0
    print(); log(f"完成! {el:.0f}s ({el/60:.1f}m)",lf); log(f"OK:{stats['ok']} 空:{stats['empty']} 错:{stats['error']} 行:{stats['rows']:,}",lf)
    lf.close()

if __name__ == "__main__": main()
