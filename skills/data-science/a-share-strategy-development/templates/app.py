"""A股策略平台 — Windows桌面版 (2026-05-16 最终版)

tkinter + Pillow 策略平台。自动扫描 strategies/s*.py 文件，
展示策略列表、净值曲线、关键指标、可编辑源码。
支持 Dracula 主题、运行回测(Toplevel日志窗口)、多策略筛选排序。
"""
import os, sys, csv, subprocess, re, glob, threading, queue
from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk

# ── Dracula 配色 ──
BG_PRIMARY = "#282a36"
BG_SECONDARY = "#2d2f3e"
BG_TERTIARY = "#383a4a"
FG_PRIMARY = "#f8f8f2"
FG_SECONDARY = "#6272a4"
FG_GREEN = "#50fa7b"
FG_RED = "#ff5555"
ACCENT_BLUE = "#8be9fd"
ACCENT_GREEN = "#0e639c"
ACCENT_GOLD = "#ffb86c"
BORDER = "#44475a"
TABLE_STRIPE = "#222432"
HOVER = "#44475a"

RESULTS = os.path.expanduser("~/Desktop/a_stock_trade/results")
STRATEGIES_DIR = os.path.expanduser("~/Desktop/a_stock_trade/strategies")

def read_stats(csv_path):
    if not os.path.exists(csv_path): return {}
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f): return row
    return {}

def _parse_label(src_path):
    """正则读取 LABEL/FOLDER 变量（不import文件）"""
    try:
        with open(src_path, encoding="utf-8") as f:
            c = f.read()
        m = re.search(r'LABEL\s*=\s*["\'](.+?)["\']', c)
        label = m.group(1) if m else re.search(r'label\s*=\s*["\'](.+?)["\']', c)
        label = label.group(1) if label else os.path.splitext(os.path.basename(src_path))[0]
        m2 = re.search(r'FOLDER\s*=\s*["\'](.+?)["\']', c)
        folder = m2.group(1) if m2 else re.search(r'folder\s*=\s*["\'](.+?)["\']', c)
        folder = folder.group(1) if folder else label.replace(" ", "-")
        return label, folder
    except Exception:
        name = os.path.splitext(os.path.basename(src_path))[0]
        return name, name

def scan_strategies():
    strategy_files = sorted(glob.glob(os.path.join(STRATEGIES_DIR, "s[0-9]*.py")))
    results_map = {}
    if os.path.isdir(RESULTS):
        for d in os.listdir(RESULTS):
            full = os.path.join(RESULTS, d)
            if not os.path.isdir(full): continue
            stats = read_stats(os.path.join(full, "stats.csv"))
            equity = os.path.join(full, "equity_curve.png")
            results_map[d] = (stats, equity if os.path.exists(equity) else "")
    dirs, seen = [], set()
    for sp in strategy_files:
        label, folder = _parse_label(sp)
        if not label or folder in seen: continue
        seen.add(folder)
        stats, equity = results_map.get(folder, ({}, ""))
        dirs.append((label, stats, equity, sp))
    return dirs

def _parse_pct(s):
    if not s or s == "—": return None
    try: return float(s.replace("%","").replace("+","").replace(",","").strip())
    except: return None

def _parse_num(s):
    if not s or s == "—": return None
    try: return float(s)
    except: return None

COLUMNS = [
    ("name", "策略名称", 180, None, None),
    ("ret", "总收益率", 100, _parse_pct, "总收益率"),
    ("sharpe", "超额夏普", 90, _parse_num, "夏普比率"),
    ("dd", "最大回撤", 100, _parse_pct, "最大回撤"),
]

class App(Tk):
    STAT_KEYS = ["总收益率","年化收益率","夏普比率","最大回撤","日均持股",
                 "日均换手","总交易成本","基准收益","超额收益","信息比率",
                 "交易天数","胜率","盈亏比"]

    def __init__(self):
        super().__init__()
        self.title("A股策略平台")
        self.state("zoomed")  # 启动最大化
        self.configure(bg=BG_PRIMARY)
        self.sort_col, self.sort_rev = "ret", True

        # ── ttk 样式 ──
        style = ttk.Style(); style.theme_use("clam")
        style.configure("Treeview", background=BG_SECONDARY, foreground=FG_PRIMARY,
                        fieldbackground=BG_SECONDARY, rowheight=30,
                        font=("Microsoft YaHei", 10))
        style.configure("Treeview.Heading", background=BG_TERTIARY, foreground=FG_PRIMARY,
                        font=("Microsoft YaHei", 10, "bold"))
        style.map("Treeview", background=[("selected", "#bd93f9")],
                  foreground=[("selected", "#1a1a2e")])
        style.map("Treeview.Heading", background=[("active", HOVER)])

        style2 = ttk.Style(); style2.theme_use("clam")
        style2.configure("TNotebook", background=BG_PRIMARY, borderwidth=0)
        style2.configure("TNotebook.Tab", background=BG_TERTIARY, foreground=FG_SECONDARY,
                         padding=[12, 4], font=("Microsoft YaHei", 10))
        style2.map("TNotebook.Tab", background=[("selected", BG_SECONDARY)],
                   foreground=[("selected", FG_PRIMARY)])

        self.rowconfigure(0, weight=0); self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=0); self.columnconfigure(1, weight=1)

        Label(self, text="📊  A股策略平台", font=("Microsoft YaHei", 18, "bold"),
              fg=FG_PRIMARY, bg=BG_PRIMARY, anchor="w", padx=16, pady=10
              ).grid(row=0, column=0, columnspan=2, sticky="ew")

        # ── 左侧：策略列表 ──
        left = Frame(self, bg=BG_PRIMARY)
        left.grid(row=1, column=0, sticky="nsew", padx=(10,5), pady=(0,10))
        hdr = Frame(left, bg=BG_PRIMARY); hdr.pack(fill=X, pady=(0,4))
        Label(hdr, text="策略列表", font=("Microsoft YaHei",12,"bold"),
              fg=FG_SECONDARY, bg=BG_PRIMARY).pack(side=LEFT)
        Button(hdr, text="↻", font=("Microsoft YaHei",11,"bold"),
               fg=FG_PRIMARY, bg=BG_TERTIARY, bd=0, padx=8, pady=0,
               activebackground=HOVER, command=self.refresh, cursor="hand2"
               ).pack(side=RIGHT, padx=(4,0))

        self.tree = ttk.Treeview(left, columns=("name","ret","sharpe","dd"),
                                 show="headings", height=35, selectmode="browse")
        self.tree.tag_configure("odd", background=TABLE_STRIPE)
        self.tree.tag_configure("even", background=BG_SECONDARY)
        for cid, txt, w, _, _ in COLUMNS:
            self.tree.heading(cid, text=txt, command=lambda c=cid: self.sort_by(c))
            self.tree.column(cid, width=w, minwidth=w)
            if cid != "name": self.tree.column(cid, anchor="center")
        vsb = Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True); vsb.pack(side=RIGHT, fill=Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # ── 右侧：详情面板 ──
        right = Frame(self, bg=BG_SECONDARY, bd=1, relief="solid",
                      highlightbackground=BORDER, highlightthickness=1)
        right.grid(row=1, column=1, sticky="nsew", padx=(5,10), pady=(0,10))
        right.rowconfigure(1, weight=1); right.columnconfigure(0, weight=1)

        self.detail_title = Label(right, text="选择左侧策略查看详情",
                                  font=("Microsoft YaHei",13,"bold"),
                                  fg=FG_SECONDARY, bg=BG_SECONDARY, pady=8)
        self.detail_title.grid(row=0, column=0, sticky="ew")

        self.notebook = ttk.Notebook(right)
        self.notebook.grid(row=1, column=0, sticky="nsew")

        # ── 标签1：图表 ──
        ct = Frame(self.notebook, bg=BG_SECONDARY)
        self.notebook.add(ct, text="📈 净值曲线")
        ct.rowconfigure(0, weight=1); ct.columnconfigure(0, weight=1)
        cf = Frame(ct, bg=BG_SECONDARY); cf.grid(sticky="nsew")
        cf.rowconfigure(0, weight=1); cf.columnconfigure(0, weight=1)
        self.img_canvas = Canvas(cf, bg=BG_SECONDARY, highlightthickness=0)
        self.img_canvas.grid(sticky="nsew")
        vsb2 = Scrollbar(cf, orient="vertical", command=self.img_canvas.yview)
        vsb2.grid(row=0, column=1, sticky="ns")
        hsb2 = Scrollbar(cf, orient="horizontal", command=self.img_canvas.xview)
        hsb2.grid(row=1, column=0, sticky="ew")
        self.img_canvas.configure(yscrollcommand=vsb2.set, xscrollcommand=hsb2.set)

        # ── 标签2：代码 ──
        cdt = Frame(self.notebook, bg=BG_SECONDARY)
        self.notebook.add(cdt, text="📄 策略代码")
        cdt.rowconfigure(1, weight=1); cdt.columnconfigure(0, weight=1)
        tb = Frame(cdt, bg=BG_SECONDARY); tb.grid(sticky="ew", pady=(4,0))
        Button(tb, text="💾 保存", font=("Microsoft YaHei",10),
               bg="#1f883d", fg="white", bd=0, padx=12, pady=2,
               command=self.save_code, cursor="hand2").pack(side=LEFT, padx=4)
        Button(tb, text="↩ 撤销", font=("Microsoft YaHei",10),
               bg=FG_SECONDARY, fg="white", bd=0, padx=12, pady=2,
               command=self.revert_code, cursor="hand2").pack(side=LEFT, padx=4)
        self.code_status = Label(tb, text="", font=("Microsoft YaHei",9),
                                 fg=FG_SECONDARY, bg=BG_SECONDARY)
        self.code_status.pack(side=RIGHT, padx=8)
        self.code_text = Text(cdt, font=("Consolas",10), fg=FG_PRIMARY,
                              bg=BG_TERTIARY, wrap="none", bd=0, padx=8, pady=8,
                              undo=True, maxundo=50, insertbackground=FG_PRIMARY)
        self.code_text.grid(sticky="nsew")
        self.code_text.bind("<Control-s>", lambda e: self.save_code())
        cv = Scrollbar(cdt, orient="vertical", command=self.code_text.yview)
        cv.grid(row=1, column=1, sticky="ns")
        ch = Scrollbar(cdt, orient="horizontal", command=self.code_text.xview)
        ch.grid(row=2, column=0, sticky="ew")
        self.code_text.configure(yscrollcommand=cv.set, xscrollcommand=ch.set)
        self.current_src_path = None

        # ── 底部：指标 + 按钮 ──
        bf = Frame(right, bg=BG_SECONDARY)
        bf.grid(row=2, column=0, sticky="ew", pady=6)
        self.stats_text = Text(bf, height=4, font=("Microsoft YaHei",9),
                               fg=FG_PRIMARY, bg=BG_TERTIARY, bd=0, wrap="word",
                               padx=8, pady=4, relief="flat")
        self.stats_text.pack(side=LEFT, fill=BOTH, expand=True, padx=(0,4))

        bgp = Frame(bf, bg=BG_SECONDARY); bgp.pack(side=RIGHT, padx=(0,4))
        self.run_sel_btn = Button(bgp, text="▶ 选中",
               font=("Microsoft YaHei",10), fg="white", bg=ACCENT_BLUE, bd=0,
               padx=10, pady=4, command=self.run_selected, cursor="hand2")
        self.run_sel_btn.pack(side=TOP, fill=X, pady=1)
        self.run_sel_btn.config(state="disabled")
        self.run_all_btn = Button(bgp, text="▶ 全量",
               font=("Microsoft YaHei",10), fg="white", bg="#1f883d", bd=0,
               padx=10, pady=4, command=self.run_all, cursor="hand2")
        self.run_all_btn.pack(side=TOP, fill=X, pady=1)
        Button(bf, text="📂 原图", font=("Microsoft YaHei",10),
               bg=ACCENT_BLUE, fg="white", bd=0, padx=14, pady=4,
               command=self.open_chart, cursor="hand2"
               ).pack(side=RIGHT, padx=4)

        self.strategies = scan_strategies()
        self.current_equity = ""
        self._tk_img = None
        self._selected_src = None
        self._selected_name = None
        self.populate_tree()

    # ── 排序 ──
    def _get_sort_key(self, cid, item):
        name, stats, _, _ = item
        for id, _, _, parser, sk in COLUMNS:
            if id == cid:
                if cid == "name": return name.lower()
                if parser and sk:
                    v = parser(stats.get(sk, "—"))
                    return v if v is not None else float("-inf")
                return ""
        return ""

    def sort_by(self, cid):
        if cid == self.sort_col: self.sort_rev = not self.sort_rev
        else: self.sort_col, self.sort_rev = cid, (cid != "name")
        self.strategies.sort(key=lambda i: self._get_sort_key(cid, i), reverse=self.sort_rev)
        self.populate_tree()
        for id, txt, _, _, _ in COLUMNS:
            a = " ▲" if id == cid and not self.sort_rev else " ▼" if id == cid else ""
            self.tree.heading(id, text=txt + a)

    def populate_tree(self):
        """填充表格，交替行颜色"""
        for r in self.tree.get_children(): self.tree.delete(r)
        for i, (n, s, _, _) in enumerate(self.strategies):
            self.tree.insert("", END, values=(n, s.get("总收益率","—"),
                s.get("夏普比率","—"), s.get("最大回撤","—")),
                tags=("odd" if i%2 else "even",))

    # ── 刷新 ──
    def refresh(self):
        self.strategies = scan_strategies()
        self.sort_by(self.sort_col)
        self.detail_title.config(text="选择左侧策略查看详情")
        self.stats_text.delete("1.0", END)
        self.img_canvas.delete("all")
        self.code_text.delete("1.0", END)
        self.current_equity = self.current_src_path = None
        self._selected_src = None; self._selected_name = None
        self.run_sel_btn.config(state="disabled")

    # ── 运行回测 ──
    def _run_cmd(self, cmd, desc):
        """启动子进程运行回测，弹出 Toplevel 实时日志窗口"""
        self.run_all_btn.config(state="disabled", text="⏳")
        self.run_sel_btn.config(state="disabled")
        if hasattr(self, "_log_win") and self._log_win.winfo_exists():
            self._log_win.destroy()
        win = Toplevel(self); win.title(f"⏳ {desc}")
        win.geometry("700x400"); win.configure(bg=BG_PRIMARY)
        win.transient(self); win.grab_set()
        self._log_win = win
        lt = Text(win, font=("Consolas",10), fg=FG_PRIMARY, bg=BG_TERTIARY,
                  wrap="word", bd=0, padx=8, pady=8)
        lt.pack(fill=BOTH, expand=True, padx=6, pady=6)
        Scrollbar(lt, orient="vertical", command=lt.yview).pack(side=RIGHT, fill=Y)
        lt.configure(yscrollcommand=lt.yview)
        lt.insert("1.0", f"▶ {desc}\n{'='*40}\n")
        q = queue.Queue()
        def task():
            try:
                env = os.environ.copy(); env["USERPROFILE"] = "C:\\Users\\Mayn"
                p = subprocess.Popen(cmd, cwd=os.path.dirname(os.path.abspath(__file__)),
                    env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1)
                for line in p.stdout: q.put(line)
                p.wait(); q.put(None)
            except Exception as e: q.put(f"错误: {e}\n"); q.put(None)
        threading.Thread(target=task, daemon=True).start()
        def poll():
            try:
                while True:
                    ln = q.get_nowait()
                    if ln is None: break
                    lt.insert(END, ln); lt.see(END)
            except queue.Empty: pass
            if hasattr(self, "_log_win") and self._log_win.winfo_exists():
                self.after(50, poll)
            else: self._on_run_done(desc, True)
        poll()

    def _on_run_done(self, desc, success):
        self.run_all_btn.config(state="normal", text="▶ 全量")
        if self._selected_src: self.run_sel_btn.config(state="normal")
        if hasattr(self, "_log_win") and self._log_win.winfo_exists():
            self._log_win.title(f"{'✅' if success else '❌'} {desc}")
            self._log_win.grab_release()
        self.refresh()

    def run_all(self):
        rp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_all.py")
        if os.path.exists(rp): self._run_cmd(["python", rp], "全量回测完成")
        else: self._run_cmd([sys.executable, "-m", "core.platform", "run"], "全量回测完成")

    def run_selected(self):
        if not self._selected_src or not os.path.exists(self._selected_src):
            self.code_status.config(text="⚠ 未找到策略文件", fg=ACCENT_GOLD); return
        self._run_cmd(["python", self._selected_src], f"{self._selected_name} 运行完成")

    # ── 选择与展示 ──
    def on_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        name = self.tree.item(sel[0])["values"][0]
        for n, stats, eq, sp in self.strategies:
            if n == name:
                self.show_detail(n, stats, eq, sp)
                self._selected_src = sp; self._selected_name = n
                self.run_sel_btn.config(state="normal"); break

    def show_detail(self, name, stats, eq, sp):
        self.detail_title.config(text=f"📈  {name}")
        self.current_equity = eq
        lines = [f"  {k}:  {stats.get(k, '—')}" for k in self.STAT_KEYS if k in stats]
        self.stats_text.delete("1.0", END); self.stats_text.insert("1.0", "\n".join(lines))
        self.img_canvas.delete("all")
        if eq and os.path.exists(eq):
            try:
                img = Image.open(eq)
                cw = max(self.img_canvas.winfo_width()-20, 600)
                r = cw / img.width; nw, nh = cw, int(img.height*r)
                if nh > 800: r2 = 800/nh; nw, nh = int(nw*r2), 800
                small = img.resize((nw, nh), Image.LANCZOS)
                self._tk_img = ImageTk.PhotoImage(small)
                self.img_canvas.create_image(10, 10, anchor="nw", image=self._tk_img)
                self.img_canvas.configure(scrollregion=(0, 0, nw+20, nh+20))
            except Exception as e:
                self.img_canvas.create_text(100, 50, text=f"Error: {e}",
                                            fill=FG_RED, anchor="nw")
        self._load_code(sp or name)

    def open_chart(self):
        if self.current_equity and os.path.exists(self.current_equity):
            subprocess.Popen(["cmd.exe", "/c", "start", "", self.current_equity], shell=True)

    # ── 代码编辑器 ──
    def _load_code(self, path_or_name):
        if os.path.isfile(path_or_name): src_path = path_or_name
        else:
            prefix = path_or_name.split("-")[0].split(" ")[0].lower()
            candidates = glob.glob(os.path.join(STRATEGIES_DIR, f"{prefix}_*.py"))
            if not candidates: candidates = glob.glob(os.path.join(STRATEGIES_DIR, f"{prefix}*.py"))
            src_path = candidates[0] if candidates else None
        self.code_text.delete("1.0", END); self.code_status.config(text="")
        if src_path and os.path.exists(src_path):
            with open(src_path, encoding="utf-8") as f: self.code_text.insert("1.0", f.read())
            self.current_src_path = src_path
        else: self.code_text.insert("1.0", f"# 未找到源码: {path_or_name}"); self.current_src_path = None
        self.code_text.edit_reset()

    def save_code(self):
        p = self.current_src_path
        if not p: self.code_status.config(text="⚠ 未关联文件", fg=ACCENT_GOLD); return
        code = self.code_text.get("1.0", "end-1c")
        try:
            compile(code, p, "exec")
            with open(p, "w", encoding="utf-8") as f: f.write(code)
            self.code_status.config(text="✅ 保存成功", fg=FG_GREEN)
            self.code_text.edit_modified(False)
        except SyntaxError as e:
            self.code_status.config(text=f"❌ 语法错误 第{e.lineno}行: {e.msg}", fg=FG_RED)
        except Exception as e:
            self.code_status.config(text=f"❌ 保存失败: {e}", fg=FG_RED)

    def revert_code(self):
        p = self.current_src_path
        if not p: return
        self._load_code(p)
        self.code_status.config(text="↩ 已还原", fg=FG_SECONDARY)

if __name__ == "__main__":
    App().mainloop()
