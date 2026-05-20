# Python Stdlib Module Shadowing

## Symptom

When importing a library that internally does `import stdlib_module`, you get:

```
AttributeError: module 'stdlib_module' has no attribute 'some_func'
```

The error traces back through a chain like:
```
your_script.py → import akshare → import pandas → import platform
                                                    ↑ picks up your local platform.py
```

## Root Cause

A file in the project (or on `sys.path`) has the same name as a Python standard library module. Python's import system finds the local file first, shadowing the stdlib.

This is especially insidious when:
- The local file is in a package with `__init__.py` (gets added to `sys.path`)
- Scripts are run from the directory containing the conflicting file

## Diagnosis (30 seconds)

1. Read the traceback — identify which stdlib module is being imported when it fails
2. Search for a local file with that exact name:
   ```
   search_files or find . -name "platform.py"   # replace with the failing module name
   ```
3. Check if the file is in a directory that ends up on `sys.path` (has `__init__.py`, or is the script's directory)

## Permanent Fix (not workaround)

### DON'T: Pop sys.path[0] as a per-file workaround

```python
# BAD — fragile, must be added to every new script forever
_script_dir = os.path.dirname(os.path.abspath(__file__))
if sys.path and sys.path[0] == _script_dir:
    sys.path.pop(0)
```

This is a band-aid. Every new script in the same directory will hit the same bug and need the same workaround.

### DO: Rename the conflicting file

1. **Rename** the local module to a name that doesn't conflict with stdlib
2. **Search all references** across the project (not just imports — also CLI commands like `python -m core.platform`, comments, batch files)
3. **Update every reference** to use the new name
4. **Remove all workarounds** that were previously added to work around the conflict
5. **Clean up** `__pycache__/` entries for the old name and any `.bak` files

### Example from a_stock_trade

`core/platform.py` shadowed stdlib `platform` → renamed to `core/runner.py`.

Files touched:
- `core/platform.py` → `core/runner.py` (rename + docstring)
- `app.pyw` (CLI invocation: `python -m core.platform run` → `python -m core.runner run`)
- `batch_run.py` (comment)
- `run_all.py` (comment)
- `core/download_data.py` (remove workaround)
- `core/fetch_fundamentals.py` (remove workaround)
- `core/update_data.py` (remove workaround)
- `core/update_fundamentals.py` (remove workaround)
- `core/platform.py.bak` (delete)
- `core/__pycache__/platform*` (delete)

## Common Stdlib names to avoid

`platform`, `code`, `token`, `signal`, `types`, `json`, `copy`, `enum`, `html`, `text`, `test`, `tests`, `typing`, `queue`, `cmd`, `runpy`, `pprint`, `calendar`, `colorsys`, `configparser`, `csv`, `datetime`, `decimal`, `fractions`, `hashlib`, `heapq`, `inspect`, `io`, `json`, `logging`, `mailbox`, `numbers`, `pathlib`, `pickle`, `random`, `re`, `statistics`, `string`, `struct`, `tempfile`, `threading`, `time`, `traceback`, `uuid`, `warnings`, `xml`
