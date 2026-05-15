"""
Windows Desktop App — A股策略平台
==================================
tkinter + Pillow 策略结果查看器。
自动扫描 results/ 目录，展示策略列表、净值曲线、关键指标、源码。
"""

import os, sys, csv, subprocess
from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk

RESULTS = os.path.expanduser("~/Desktop/a_stock_trade/results")


def read_stats(csv_path):
    if not os.path.exists(csv_path):
        return {}
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            return row
    return {}


def scan_strategies():
    dirs = []
    if not os.path.isdir(RESULTS):
        return dirs
    for d in sorted(os.listdir(RESULTS)):
        full = os.path.join(RESULTS, d)
        if not os.path.isdir(full):
            continue
        stats = read_stats(os.path.join(full, "stats.csv"))
        equity = os.path.join(full, "equity_curve.png")
        if not os.path.exists(equity):
            equity = ""
        dirs.append((d, stats, equity))
    return dirs


class App(Tk):
    STAT_KEYS = ["总收益率", "年化收益率", "夏普比率", "最大回撤",
                 "日均持股", "日均换手", "总交易成本", "基准收益",
                 "超额收益", "信息比率", "交易天数", "胜率", "盈亏比"]

    def __init__(self):
        super().__init__()
        self.title("A股策略平台")
        self.geometry("1200x750")
        self.configure(bg="#0f172a")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#1e293b", foreground="#e2e8f0",
                        fieldbackground="#1e293b", rowheight=28,
                        font=("Microsoft YaHei", 10))
        style.configure("Treeview.Heading", background="#334155", foreground="#f1f5f9",
                        font=("Microsoft YaHei", 10, "bold"))
        style.map("Treeview", background=[("selected", "#3b82f6")])

        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)

        title_lbl = Label(self, text="📊  A股策略平台",
                          font=("Microsoft YaHei", 18, "bold"),
                          fg="#f1f5f9", bg="#0f172a", anchor="w", padx=16, pady=10)
        title_lbl.grid(row=0, column=0, columnspan=2, sticky="ew")

        # --- 左侧策略列表 ---
        left_frame = Frame(self, bg="#0f172a")
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=(0, 10))
        Label(left_frame, text="策略列表", font=("Microsoft YaHei", 12, "bold"),
              fg="#94a3b8", bg="#0f172a").pack(anchor="w", pady=(0, 4))

        self.tree = ttk.Treeview(left_frame, columns=("name", "ret", "sharpe", "dd"),
                                 show="headings", height=35, selectmode="browse")
        self.tree.heading("name", text="策略名称")
        self.tree.heading("ret", text="总收益")
        self.tree.heading("sharpe", text="超额夏普")
        self.tree.heading("dd", text="最大回撤")
        self.tree.column("name", width=180, minwidth=140)
        self.tree.column("ret", width=100, anchor="center")
        self.tree.column("sharpe", width=90, anchor="center")
        self.tree.column("dd", width=100, anchor="center")

        vsb = Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # --- 右侧详情面板 ---
        right_frame = Frame(self, bg="#1e293b", bd=1, relief="solid",
                            highlightbackground="#334155", highlightthickness=1)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=(0, 10))
        right_frame.rowconfigure(1, weight=1)
        right_frame.columnconfigure(0, weight=1)

        self.detail_title = Label(right_frame, text="选择左侧策略查看详情",
                                  font=("Microsoft YaHei", 13, "bold"),
                                  fg="#64748b", bg="#1e293b", pady=8)
        self.detail_title.grid(row=0, column=0, sticky="ew")

        canvas_frame = Frame(right_frame, bg="#1e293b")
        canvas_frame.grid(row=1, column=0, sticky="nsew")
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        self.img_canvas = Canvas(canvas_frame, bg="#1e293b", highlightthickness=0)
        self.img_canvas.grid(row=0, column=0, sticky="nsew")
        vsb2 = Scrollbar(canvas_frame, orient="vertical", command=self.img_canvas.yview)
        vsb2.grid(row=0, column=1, sticky="ns")
        hsb2 = Scrollbar(canvas_frame, orient="horizontal", command=self.img_canvas.xview)
        hsb2.grid(row=1, column=0, sticky="ew")
        self.img_canvas.configure(yscrollcommand=vsb2.set, xscrollcommand=hsb2.set)

        # --- 底部按钮区域 ---
        btn_frame = Frame(right_frame, bg="#1e293b")
        btn_frame.grid(row=2, column=0, sticky="ew", pady=6)

        self.stats_text = Text(btn_frame, height=4, font=("Microsoft YaHei", 9),
                               fg="#cbd5e1", bg="#0f172a", bd=0, wrap="word",
                               padx=8, pady=4, relief="flat")
        self.stats_text.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 8))

        self.open_btn = Button(btn_frame, text="📂 打开原图",
                               font=("Microsoft YaHei", 10),
                               bg="#3b82f6", fg="white", bd=0, padx=14, pady=4,
                               command=self.open_chart, cursor="hand2")
        self.open_btn.pack(side=RIGHT, padx=(4, 0))
        self.open_btn.config(state="disabled")

        self.code_btn = Button(btn_frame, text="📄 显示代码",
                               font=("Microsoft YaHei", 10),
                               bg="#8b5cf6", fg="white", bd=0, padx=14, pady=4,
                               command=self.show_code, cursor="hand2")
        self.code_btn.pack(side=RIGHT, padx=(4, 0))

        self.strategies = scan_strategies()
        self.current_equity = ""
        self._tk_img = None
        self.populate_tree()

    def populate_tree(self):
        for name, stats, _ in self.strategies:
            ret = stats.get("总收益率", "—")
            sharpe = stats.get("夏普比率", "—")
            dd = stats.get("最大回撤", "—")
            self.tree.insert("", END, values=(name, ret, sharpe, dd))

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        name = item["values"][0]
        for n, stats, equity in self.strategies:
            if n == name:
                self.show_detail(n, stats, equity)
                break

    def show_detail(self, name, stats, equity):
        self.detail_title.config(text=f"📈  {name}")
        self.current_equity = equity
        lines = [f"  {k}:  {stats.get(k, '—')}" for k in self.STAT_KEYS if k in stats]
        self.stats_text.delete("1.0", END)
        self.stats_text.insert("1.0", "\n".join(lines))
        self.img_canvas.delete("all")
        self.open_btn.config(state="normal" if equity else "disabled")
        if equity and os.path.exists(equity):
            try:
                img = Image.open(equity)
                cw = max(self.img_canvas.winfo_width() - 20, 600)
                r = cw / img.width
                nw, nh = cw, int(img.height * r)
                if nh > 800:
                    r2 = 800 / nh; nw, nh = int(nw * r2), 800
                small = img.resize((nw, nh), Image.LANCZOS)
                self._tk_img = ImageTk.PhotoImage(small)
                self.img_canvas.create_image(10, 10, anchor="nw", image=self._tk_img)
                self.img_canvas.configure(scrollregion=(0, 0, nw + 20, nh + 20))
            except Exception as e:
                self.img_canvas.create_text(100, 50, text=f"Error: {e}",
                                            fill="#ef4444", anchor="nw")

    def open_chart(self):
        if self.current_equity and os.path.exists(self.current_equity):
            subprocess.Popen(["cmd.exe", "/c", "start", "", self.current_equity],
                             shell=True)

    def show_code(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        name = item["values"][0]
        prefix = name.split("-")[0].split(" ")[0].lower()
        base = os.path.dirname(__file__)
        strategies_dir = os.path.join(base, "strategies")
        candidates = glob.glob(os.path.join(strategies_dir, f"{prefix}_*.py"))
        if not candidates:
            candidates = glob.glob(os.path.join(strategies_dir, f"{prefix}*.py"))
        if not candidates:
            self.stats_text.delete("1.0", END)
            self.stats_text.insert("1.0", f"未找到源码: {name}")
            return
        src = candidates[0]
        try:
            with open(src, encoding="utf-8") as f:
                code = f.read()
            win = Toplevel(self)
            win.title(f"源码: {os.path.basename(src)}")
            win.geometry("900x700")
            win.configure(bg="#0f172a")
            frm = Frame(win, bg="#0f172a")
            frm.pack(fill=BOTH, expand=True, padx=8, pady=8)
            txt = Text(frm, font=("Consolas", 10), fg="#e2e8f0",
                       bg="#1e293b", wrap="none", bd=0, padx=8, pady=8)
            txt.insert("1.0", code)
            txt.config(state="disabled")
            vsb = Scrollbar(frm, orient="vertical", command=txt.yview)
            hsb = Scrollbar(frm, orient="horizontal", command=txt.xview)
            txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            txt.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            frm.rowconfigure(0, weight=1)
            frm.columnconfigure(0, weight=1)
        except Exception as e:
            self.stats_text.delete("1.0", END)
            self.stats_text.insert("1.0", f"读取失败: {e}")


if __name__ == "__main__":
    App().mainloop()
