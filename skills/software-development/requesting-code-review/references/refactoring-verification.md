# Refactoring Verification — Systematic Equivalence Check

Use this when splitting, merging, or extracting code into modules. The goal is
to prove that the refactored code is **functionally identical** to the original.

## Step 1: Method Inventory

Compare ALL method definitions between old and new:

```python
# Extract method names from both files
import re

for label, fpath in [('backup', 'bak/original.pyw'), ('current', 'app.pyw')]:
    with open(fpath) as f:
        lines = f.read().split('\n')
    in_class = False
    methods = []
    for line in lines:
        if 'class App' in line and '(' in line:
            in_class = True
            continue
        if in_class:
            if line.strip().startswith('class ') and 'class App' not in line:
                break  # next class definition
            if line.strip().startswith('def ') and '(' in line:
                name = line.strip().split('(')[0].split()[-1]
                methods.append(name)
    print(f'{label}: {len(methods)} methods')
    for m in methods:
        print(f'  {m}')
```

**Check:** New count = Old count - intentionally extracted methods.
If a backup exists, double-check. Moved-to-mixin methods should be listed
there, not in the main class.

## Step 2: Attribute Cross-Reference

When extracting methods into a Mixin class, every `self.xxx` that the mixin
uses must be set up by the parent class's `__init__` or `_build_*` methods.

```bash
# Extract ALL self.xxx references from the mixin
grep -oP 'self\.\w+' core/app_mixin.py | sort -u

# Then verify each one is created in the parent's __init__ / _build methods
grep -oP 'self\.\w+\s*=' app.pyw | sort -u
```

**Check:** Every mixin attribute either appears in the parent's `self.xxx = ...`
assignments, is set dynamically (e.g. inside a method like `refresh()`),
or uses `getattr(self, ..., default)` for safe access.

Pay attention to:
- Widget references (Treeview, Label, Menu, Button)
- State flags (`_live_running`, `_dev_proc`, etc.)
- Dynamic lists (`_realtime_codes`, `_sel_procs`)

## Step 3: Verify UI Event Bindings

```bash
grep -n 'bind\|bind_all\|bind_class' app.pyw
```

Every callback bound to a UI event must exist as a method on the class or
its mixin ancestors.

Common bindings to check:
| Pattern | Expected callback |
|---------|------------------|
| `tree.bind("<<TreeviewSelect>>", ...)` | `on_select` |
| `tree.bind("<Button-3>", ...)` | `show_strat_menu` |
| `strat_tree.bind("<Double-1>", ...)` | `on_live_strat_double` |
| `pos_tree.bind("<Button-3>", ...)` | `show_pos_menu` |

## Step 4: Import Verification

```bash
# Syntax check
python -m py_compile app.pyw

# Runtime import resolution (simulate what app.pyw imports)
python -c "
import sys
sys.path.insert(0, '.')
from core.module1 import *
from core.module2 import ClassName
print('All imports resolved.')
"
```

**Check:** Both compile-time (`py_compile`) and runtime import must pass.
Pay attention to relative imports, circular imports, and renamed files.

## Step 5: Dead Code Detection

Scan for functions that are imported but never called:

```bash
# Find all imports
grep "^from\|^import" app.pyw

# Check each imported function/method
grep -c "function_name(" app.pyw  # should be > 1 (import + at least 1 usage)
```

**Check only for imports at 0 usage count.** Imports used only once (the
import statement itself) are dead. Imports used in the backup but not in
the new code are candidates for removal.

## Step 6: Config/Escape Sequence Verification

When patching files with triple-quoted docstrings or special characters,
verify patch matched correctly:

```bash
# Verify _on_close has the right number of cleanup sections
grep -c "kill\|p.kill()" app.pyw
```

## Python Script for Full Comparison

This one-shot script does Steps 1-4 in a single run:

```python
import py_compile, re, sys, os

files = {
    'current': 'app.pyw',
    'backup': 'bak/backup.pyw'
}

# Step 1: Method counts
for label, fpath in files.items():
    if not os.path.exists(fpath):
        continue
    with open(fpath) as f:
        lines = f.read().split('\n')
    # [method extraction logic]

# Step 4: Compile check
for f in ['app.pyw', 'core/*.py']:
    try:
        py_compile.compile(f, doraise=True)
        print(f'✅ {f}')
    except py_compile.PyCompileError as e:
        print(f'❌ {f}: {e}')
```

## Pitfalls

- **"self.xxx = None" in __init__ vs dynamic assignment** — Some attributes
  are set in `__init__` as `None` and later populated. Others are set
  dynamically (e.g. `self._realtime_codes` in `refresh_combined_positions`).
  Both patterns are fine as long as the mixin uses `getattr()` or
  `hasattr()` to access them gracefully.
- **Inner function methods** — Functions like `worker()`, `poll()`,
  `run_backtests()` defined inside other methods won't appear in `def`
  at class level. Account for these separately.
- **MRO (Method Resolution Order)** — `class App(Mixin, Tk)` means
  `Mixin` methods take priority. Verify the order is correct: mixin
  first, base class second.
- **Backup file reference** — Use a committed backup, not a working copy
  that may have drifted.
