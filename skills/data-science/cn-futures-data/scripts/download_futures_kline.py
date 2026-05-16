"""
Chinese Futures K-line Download Script
Uses: AKShare -> Sina Finance (free, no account)
Output: By exchange -> by product CSV files on Desktop
"""
import os, sys, time, json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import pandas as pd

OUTPUT_DIR = Path(__file__).parent
RETRY_TIMES = 3
REQUEST_INTERVAL = 1.5

SYMBOL_DB = [
    # (symbol, chinese_name, exchange_code)
    ("CU0","沪铜","shfe"),("AL0","沪铝","shfe"),("ZN0","沪锌","shfe"),
    ("PB0","沪铅","shfe"),("NI0","沪镍","shfe"),("SN0","沪锡","shfe"),
    ("AU0","沪金","shfe"),("AG0","沪银","shfe"),("RB0","螺纹钢","shfe"),
    ("HC0","热轧卷板","shfe"),("SS0","不锈钢","shfe"),("BU0","沥青","shfe"),
    ("RU0","橡胶","shfe"),("FU0","燃料油","shfe"),("SP0","纸浆","shfe"),
    ("WR0","线材","shfe"),("NR0","20号胶","shfe"),
    ("C0","玉米","dce"),("CS0","玉米淀粉","dce"),("A0","豆一","dce"),
    ("B0","豆二","dce"),("M0","豆粕","dce"),("Y0","豆油","dce"),
    ("P0","棕榈油","dce"),("FB0","纤维板","dce"),("BB0","胶合板","dce"),
    ("JD0","鸡蛋","dce"),("L0","聚乙烯(塑料)","dce"),("PP0","聚丙烯","dce"),
    ("V0","PVC","dce"),("EG0","乙二醇","dce"),("J0","焦炭","dce"),
    ("JM0","焦煤","dce"),("I0","铁矿石","dce"),("PG0","液化石油气","dce"),
    ("EB0","苯乙烯","dce"),("RR0","粳米","dce"),("LH0","生猪","dce"),
    ("LG0","原木","dce"),("BZ0","纯苯","dce"),
    ("TA0","PTA","czce"),("OI0","菜油","czce"),("RS0","菜籽","czce"),
    ("RM0","菜粕","czce"),("WH0","强麦","czce"),("JR0","粳稻","czce"),
    ("SR0","白糖","czce"),("CF0","棉花","czce"),("ZC0","动力煤","czce"),
    ("FG0","玻璃","czce"),("MA0","甲醇","czce"),("AP0","苹果","czce"),
    ("CJ0","红枣","czce"),("UR0","尿素","czce"),("SA0","纯碱","czce"),
    ("SF0","硅铁","czce"),("SM0","锰硅","czce"),("CY0","棉纱","czce"),
    ("PF0","短纤","czce"),("PK0","花生","czce"),("LR0","晚籼稻","czce"),
    ("RI0","早籼稻","czce"),("PM0","普麦","czce"),
    ("IF0","沪深300","cffex"),("IC0","中证500","cffex"),("IH0","上证50","cffex"),
    ("IM0","中证1000","cffex"),("T0","10年期国债","cffex"),("TF0","5年期国债","cffex"),
    ("TS0","2年期国债","cffex"),("TL0","30年期国债","cffex"),
    ("SC0","原油","ine"),("LU0","低硫燃料油","ine"),("BC0","国际铜","ine"),
    ("SI0","工业硅","gfex"),("LC0","碳酸锂","gfex"),
]

EXCHANGE_NAMES = {"shfe":"上期所","dce":"大商所","czce":"郑商所","cffex":"中金所","ine":"上期能源","gfex":"广期所"}

def ensure_dir(path): os.makedirs(path, exist_ok=True); return path

def download_single(symbol, retries=RETRY_TIMES):
    import akshare as ak
    for attempt in range(retries):
        try:
            df = ak.futures_zh_daily_sina(symbol=symbol)
            if df is not None and len(df) > 0: return df, None
            return None, "empty data"
        except Exception as e:
            if attempt < retries - 1: time.sleep(2)
            else: return None, str(e)
    return None, "retries exhausted"

def save_kline(df, name, exchange):
    if df is None or len(df) == 0: return None, 0
    out = pd.DataFrame()
    out["日期"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    for k, v in [("开盘","open"),("最高","high"),("最低","low"),("收盘","close"),("成交量","volume"),("持仓量","hold")]: out[k] = df[v]
    out = out.sort_values("日期").reset_index(drop=True)
    ecn = EXCHANGE_NAMES.get(exchange, exchange)
    d = ensure_dir(os.path.join(OUTPUT_DIR, ecn, name))
    fp = os.path.join(d, f"{name}_主连日线.csv")
    out.to_csv(fp, index=False, encoding="utf-8-sig")
    return fp, len(out)

def main():
    print(f"Downloading {len(SYMBOL_DB)} futures products to {OUTPUT_DIR}...")
    by_exch = defaultdict(list); seen = set()
    for sym, name, exch in SYMBOL_DB:
        if sym not in seen: by_exch[exch].append((sym,name)); seen.add(sym)
    results, total_bars, ok, fail = [], 0, 0, 0
    t0 = time.time()
    for exch, items in by_exch.items():
        ecn = EXCHANGE_NAMES.get(exch, exch)
        print(f"\n--- {ecn} ({len(items)} products) ---")
        for sym, name in items:
            print(f"  {sym} {name} ... ", end="", flush=True)
            df, err = download_single(sym)
            if df is not None:
                fp, n = save_kline(df, name, exch)
                print(f"OK {n} bars")
                results.append({"code":sym,"name":name,"exch":ecn,"ok":True,"bars":n})
                total_bars += n; ok += 1
            else:
                print(f"FAIL {err}"); results.append({"code":sym,"name":name,"exch":ecn,"ok":False,"bars":0}); fail += 1
            time.sleep(REQUEST_INTERVAL)
    elapsed = time.time() - t0
    summary = {"time":datetime.now().isoformat(),"seconds":round(elapsed,1),"ok":ok,"fail":fail,"total_bars":total_bars,"products":results}
    with open(os.path.join(OUTPUT_DIR,"下载汇总.json"),"w",encoding="utf-8") as f: json.dump(summary,f,ensure_ascii=False,indent=2)
    print(f"\nDone: {ok}/{ok+fail} products, {total_bars} bars, {elapsed:.0f}s")

if __name__ == "__main__": main()
