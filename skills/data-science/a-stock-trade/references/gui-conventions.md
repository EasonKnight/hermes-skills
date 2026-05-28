# GUI Conventions for a_stock_trade

Complete reference for tkinter GUI patterns used in `app.pyw`.

## Color Scheme (Modern Comfort Dark)

All colors defined in `core/app_config.py`. Never hardcode.

### Backgrounds
- `BG_DEEP #0d1117` — Window base
- `BG_PRIMARY #161b22` — Main work area
- `BG_SECONDARY #21262d` — Cards/sidebar
- `BG_TERTIARY #30363d` — Inputs/headers/buttons
- `BG_ELEVATED #3c444d` — Hover/active
- `BG_CARD #1c2128` — Card dedicated

### Text
- `FG_PRIMARY #f0f6fc` — Main text
- `FG_SECONDARY #8b949e` — Labels/body
- `FG_MUTED #6e7681` — Comments/placeholders
- `FG_GHOST #484f58` — Disabled

### Accent Colors
- Blue `ACCENT_BLUE #58a6ff` — Links/primary buttons/headers
- Teal `ACCENT_TEAL #56d364` — Success/positive returns
- Amber `ACCENT_AMBER #f0883e` — Warnings
- Gold `ACCENT_GOLD #e3b341` — Amounts/highlighted data
- Red `ACCENT_RED #f85149` — Errors/negative returns
- Purple `ACCENT_PURPLE #bc8cff` — AI/R&D

Button design: `bg=BTN_*` (dark static), `activebackground=*_DIM` (hover brightening).
Never use main accent colors as button bg — text becomes unreadable.

### Button Colors (user prefers very dark)
- `BTN_TEAL #0f3a12` — Run all, Save
- `BTN_BLUE #0f2d6e` — Run selected
- `BTN_PURPLE #2e0f5c` — Auto R&D
- `BTN_RED #5a0a0a` — Stop
- NEVER set `state="disabled"` — tkinter overrides custom bg to system gray

## Font Convention: Noto Sans SC

- Titles/headers (16/13/12/11): "Noto Sans SC Medium" (no bold)
- Body/buttons/status (10/9): "Noto Sans SC Light"
- TreeView/total rows/bar labels: "Noto Sans SC Light"
- R&D area: "Consolas" (monospace)

Noto Sans SC renders via DirectWrite — much sharper than GDI-rendered Microsoft YaHei.

## High DPI (Windows)

```python
# BEFORE tkinter import (top of file)
import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI

# In App.__init__
dpi = ctypes.windll.user32.GetDpiForWindow(self.winfo_id())
scaling = dpi / 96.0 * 1.35
self.tk.call("tk", "scaling", scaling)
```

Without DPI awareness, even Noto fonts appear blurry due to bitmap stretching.

## Layout Architecture

```
Tk (self)
├── Row 0: title_lbl
├── Row 1: main_notebook (ttk.Notebook)
│   ├── Tab "📊 Strategy Backtest"
│   │   ├── Column 0: left_frame — strategy list
│   │   │   ├── header_frame
│   │   │   ├── run_bar: buttons
│   │   │   ├── tree (ttk.Treeview)
│   │   │   └── data_status (below tree)
│   │   └── Column 1: right_frame — detail panel
│   │       ├── Row 0: dev_frame (prompt, initially visible)
│   │       ├── Row 1: dev_result_frame (R&D output)
│   │       └── Row 2: notebook (chart + code, weight=1)
│   └── Tab "🔴 Live Strategies"
│       ├── Left: strat_tree + sp_tree
│       └── Right: pos_tree (combined positions)
└── Row 3: status_bar
```

## DarkScrollbar (Custom Canvas)

Replace all 6 Scrollbar instances. Implements `set(first, last)` interface compatible with Treeview/Text yscrollcommand.

States: Normal (`BG_ELEVATED`), Hover (`BORDER_LIGHT`), Drag (`ACCENT_BLUE_SOFT`).
Minimum thumb height: 20px.
Drag uses `moveto` mode (not `scroll units`) for smooth feel.

## Treeview Patterns

### Live strategy pinning (sticky to top)
```python
live_names = {s["name"] for s in load_live_strategies()}
live_entries = [e for e in strategies if e[0] in live_names]
other_entries = [e for e in strategies if e[0] not in live_names]
sorted_entries = live_entries + other_entries
```
Live strategies get `tag="live"` (dark green bg + white text). Non-live keep zebra stripes.

### Editable cells
- Right-click menu: `add_command(label="✏️ Set XX", command=self.edit_xxx)`
- `<Double-1>` bound with column detection
- `simpledialog.askstring` → validate → save → refresh

### Click crash prevention
```python
# tree.bind("<Double-1>", ...)
def on_double(event):
    item = self.tree.identify_row(event.y)  # GUARD 1: get item
    if not item: return                      # GUARD 2: skip blank area
    values = self.tree.item(item, "values")
    if "合计" in str(values): return          # GUARD 3: skip total row
    try:
        # ... actual logic ...
    except Exception: pass                    # GUARD 4: last resort
```

### Table sorting (with live data snapshot)
1. Cache data in `self._pos_data` when refreshing
2. Sort `_pos_data` by column key
3. Snapshot live data (change_pct) from existing tree items before rebuild
4. Rebuild tree from sorted data, backfill snapshot values

## Real-time Quotes (Sina, Free)

Background daemon thread, 3-second loop:
```python
# _realtime_loop:
while True:
    codes = getattr(self, "_realtime_codes", None)
    if codes and not getattr(self, "_rt_updating", False):
        self._rt_updating = True
        self._fetch_realtime_changes(codes)
    time.sleep(3)
```

Sina API: `http://hq.sinajs.cn/list=` with GBK encoding, `Referer: https://finance.sina.com.cn` header.
Prefix mapping: `000-003,300-303` → `sz`, `600-605,688` → `sh`.

## R&D Panel (auto_develop)

Two separate Text widgets:
- `dev_text` (row 0): Prompt editor — NEVER overwritten. User edits freely.
- `dev_result` (row 1): R&D output — all Hermes output and status.

Default prompt loaded at startup. `dev_result_label` shows live timer during R&D.

### Process architecture
```python
proc = Popen(["hermes", "-z", prompt],
    stdout=PIPE, stderr=STDOUT, stdin=DEVNULL,
    creationflags=CREATE_NO_WINDOW,
    env=env, encoding="utf-8", errors="replace")
# Read lines from PIPE, display first 5 in dev_result
# Phase 1 (thinking) → Phase 2 (auto backtest)
```

## Canvas Events — Avoid Accumulation

```python
# ❌ accumulate
self.img_canvas.bind("<Configure>", self._on_canvas_resize, add="+")

# ✓ single binding
self.img_canvas.unbind("<Configure>")
self.img_canvas.bind("<Configure>", self._on_canvas_resize)
```

Any event binding inside `show_detail`/`refresh` (called repeatedly) must unbind first.

## Position Matrix (NPZ)

`position_matrix.npz` replaced CSV format. Contains: `pos_value` (float matrix), `dates`, `codes`.
Load with `np.load(npz, allow_pickle=True)`. Read last position date by scanning from last day backward.

## Startup Optimization

```python
self.after(50, self._update_data_status)    # NPZ metadata (mmap, codes only)
self.after(200, self.refresh_live)           # JSON + background NPZ IO
```

NPZ metadata reads use `mmap_mode='r'` — never load full ~100MB close matrix at startup.
Background IO (position_matrix.npz) runs in daemon thread, UI updates via `after(0)`.

## Performance Patterns

| Pattern | Fix |
|---------|-----|
| Full NPZ load for metadata | `mmap_mode='r'`, only access codes/dates |
| Syntax highlight on every keystroke | Debounce: `after_cancel` + `after(300)` |
| Canvas resize on every drag frame | Debounce + cache last dimensions |
| Real-time update queue buildup | `_updating` flag — skip if previous not done |
| 6 regex passes for highlighting | Collect all segments → sort → single tag_add pass |

## Low-level Pitfalls

- `make_label()` returns already-packed Label — cannot `.grid()` it
- `make_button()` default `pack_padx=(3,0)` — pass keyword to override
- `tab.rowconfigure()` not `self.rowconfigure()` inside tab build methods
- Never mix `place()` and `grid()` on same widget
- `_parse_label()` must read full file, not just first line
- `scan_strategies()` only scans `strategies/*.py` (top level) — subdirectories auto-excluded
