# Title: [bug] conda 26.5.3 `validate_subdir_config` crashes with `TypeError: expected str, bytes or os.PathLike object, not NoneType` when no env is active

## Environment
- conda: 26.5.3 (also verified the code path exists in current main)
- Python: 3.14.6 (base)
- OS: macOS 27.0 arm64
- Invocation: absolute path `/opt/anaconda3/bin/conda create -n foo python=3.12 -y` from a **non-activated** shell (no `CONDA_PREFIX`, no `CONDA_DEFAULT_ENV`)

## Traceback
```
File ".../conda/cli/main_create.py", line 209, in execute
    validate_subdir_config()
File ".../conda/cli/common.py", line 225, in validate_subdir_config
    elif not paths_equal(context.active_prefix, context.root_prefix):
File ".../conda/common/path/__init__.py", line 119, in paths_equal
    return abspath(path1) == abspath(path2)
TypeError: expected str, bytes or os.PathLike object, not NoneType
```

## Root cause
When no environment is active, `context.active_prefix` is `None`; `validate_subdir_config`
passes it straight into `paths_equal()` → `os.path.abspath(None)` → TypeError.
Note `is_active_prefix()` in the same file (line ~48) already handles
`active_prefix is None` — the guard is missing at the line above.

Related history: #15020 / #15038 (fixed in 25.9.0) handled the `str`-vs-`Path`
form of this crash but not the `None` form.

## Workarounds
1. `export CONDA_PREFIX=/opt/anaconda3` before invoking conda (active_prefix becomes non-None)
2. Local patch:
```diff
-        elif not paths_equal(context.active_prefix, context.root_prefix):
+        elif context.active_prefix is not None \
+                and not paths_equal(context.active_prefix, context.root_prefix):
```

## Suggested fix
Apply the None-guard above (semantics: no active env → treat as base/global
config case, consistent with `is_active_prefix`).
