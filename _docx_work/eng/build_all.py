# -*- coding: utf-8 -*-
"""76号轮·工程化项目构建驱动：生成 → autopep8 规范化 → 语法校验

用法:
  python build_all.py            # 生成全部 + 规范化
  python build_all.py --check    # 只做语法/风格校验
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
PY = sys.executable

import eng_gen as G          # noqa: E402
import eng_specs as S        # noqa: E402

# autopep8 安全规则集（仅排版/空行/缩进类，不改语义）
# 只选「不改语义且不会过度校正」的规则（E1 类续行缩进易被过度调整，故排除）
AUTOPEP8_CODES = "E2,E3,E4,E5,E7,W2,W3"
MAXLEN = 120


def build():
    n = 0
    for spec in S.SPECS:
        G.write_project(spec)
        n += 1
    print("已生成 %d 个工程化项目" % n)
    return n


def normalize():
    """对生成的项目跑 autopep8（安全规则，批量）。返回处理文件数。"""
    files = [f for f in glob.glob(os.path.join(ROOT, "*", "工程化项目", "*", "**", "*.py"),
                                  recursive=True)
             if "__pycache__" not in f]
    if not files:
        return 0
    # 分批（每次 120 个文件）避免命令行过长
    B = 120
    for i in range(0, len(files), B):
        subprocess.run([PY, "-m", "autopep8", "--in-place", "--max-line-length",
                        str(MAXLEN), "--aggressive", "--select", AUTOPEP8_CODES] + files[i:i + B],
                       capture_output=True, text=True)
    print("autopep8 规范化 %d 个文件" % len(files))
    return len(files)


def strip_unused_imports():
    """保守清理顶层未用导入（AST 判定：绑定名在全文中除 import 行外未出现）。
    仅处理 eng/ 区域的 .py，且只删整行 import 语句，不改动其它代码。"""
    import ast as _ast
    files = [f for f in glob.glob(os.path.join(ROOT, "*", "工程化项目", "*", "**", "*.py"),
                                  recursive=True) if "__pycache__" not in f]
    removed = 0
    for f in files:
        try:
            src = open(f, encoding="utf-8").read()
            tree = _ast.parse(src)
        except Exception:
            continue
        lines = src.splitlines(keepends=True)
        drop = set()
        # 遍历全部 Import/ImportFrom（含函数级）
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                for a in node.names:
                    bound = (a.asname or a.name.split(".")[0])
                    if bound == "*":
                        continue
                    used = any(isinstance(n, _ast.Name) and n.id == bound
                               for n in _ast.walk(tree))
                    if not used:
                        drop.add(node.lineno - 1)
            elif isinstance(node, _ast.ImportFrom):
                names = [a.asname or a.name for a in node.names if a.name != "*"]
                if not names:
                    continue
                used_any = any(
                    any(isinstance(n, _ast.Name) and n.id == nm for n in _ast.walk(tree))
                    for nm in names)
                if not used_any:
                    drop.add(node.lineno - 1)
        if drop:
            new = [l for i, l in enumerate(lines) if i not in drop]
            open(f, "w", encoding="utf-8", newline="\n").write("".join(new))
            removed += len(drop)
    print("清理未用导入 %d 行" % removed)
    return removed


def _in_import(node):
    """判断节点是否位于 import 语句内（避免把 import 自身的名字算作使用）。"""
    return False   # ast.walk 从 tree 出发，Import 的 alias 不是 Name 节点，天然不计入


def check():
    """语法 + 风格校验。"""
    files = [f for f in glob.glob(os.path.join(ROOT, "*", "工程化项目", "*", "**", "*.py"),
                                  recursive=True)
             if "__pycache__" not in f]
    bad_syntax = []
    for f in files:
        try:
            compile(open(f, encoding="utf-8").read(), f, "exec")
        except SyntaxError as e:
            bad_syntax.append((os.path.relpath(f, ROOT), e.lineno, e.msg))
    r = subprocess.run([PY, "-m", "flake8", "--max-line-length=%d" % MAXLEN,
                        "--select=E1,E2,E3,E5,E7,W2,W3,F4,F8"] + files,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    style = [l for l in r.stdout.splitlines() if l.strip()]
    print("=" * 70)
    print("语法错误: %d" % len(bad_syntax))
    for b in bad_syntax[:10]:
        print("   ", b)
    print("风格问题: %d" % len(style))
    for l in style[:15]:
        print("   ", l[:110])
    print("=" * 70)
    return len(bad_syntax) == 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        ok = check()
        sys.exit(0 if ok else 1)
    build()
    normalize()
    strip_unused_imports()
    normalize()
    # 续行缩进规范化（E126/E127/E128/E131）：从 specs 生成后统一对齐到视觉缩进
    try:
        import subprocess as _sp
        _sp.run([PY, os.path.join(HERE, 'fix_continuation.py')], check=False)
    except Exception as _e:
        print('续行规范化跳过:', _e)
    check()