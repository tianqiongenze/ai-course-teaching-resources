# -*- coding: utf-8 -*-
"""76号轮·starter 教学脚手架 noqa 标注（文件版，规避 heredoc 转义问题）"""
import glob
import os
import re
import subprocess

PY = r"C:/Users/Lenovo/AppData/Local/Temp/audit/env314/Scripts/python.exe"
ROOT = r"D:/Python编程实战/教学实施资料"
NOTE = "# [教学脚手架] 下列导入/变量供 TODO 完成后使用，故标注 noqa 而非删除"
PAT = re.compile(r"^(.*?):(\d+):(\d+): (F[48]\d\d)")

os.chdir(ROOT)
files = sorted(f for f in glob.glob(os.path.join("*", "学生代码框架", "**", "*.py"),
                                     recursive=True) if "__pycache__" not in f)

tg = {}
for i in range(0, len(files), 100):
    r = subprocess.run([PY, "-m", "flake8", "--max-line-length=120",
                        "--select", "F401,F841"] + files[i:i + 100],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in r.stdout.splitlines():
        m = PAT.match(line)
        if m:
            tg.setdefault(m.group(1), []).append((int(m.group(2)), m.group(4)))

print("待标注文件: %d" % len(tg))
n_line = n_file = 0
for f, items in tg.items():
    lines = open(f, encoding="utf-8").read().splitlines()
    if NOTE not in "\n".join(lines[:12]):
        ins = 0
        for i, l in enumerate(lines[:4]):
            if l.startswith("#!") or "coding" in l:
                ins = i + 1
        lines.insert(ins, NOTE)
        items = [(ln + 1 if ln > ins else ln, c) for ln, c in items]
    for ln, code in sorted(set(items)):
        idx = ln - 1
        if idx >= len(lines) or "noqa" in lines[idx] or not lines[idx].strip():
            continue
        lines[idx] = lines[idx] + "  # noqa: %s" % code
        n_line += 1
    open(f, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    n_file += 1
print("标注 %d 册 / %d 行" % (n_file, n_line))

r = subprocess.run([PY, "-m", "flake8", "--max-line-length=120",
                    "--select", "F401,F841"] + files,
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
left = [l for l in r.stdout.splitlines() if l.strip()]
print("剩余 F401/F841: %d" % len(left))
for l in left[:4]:
    print("   ", l[:100])