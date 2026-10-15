# -*- coding: utf-8 -*-
"""76号轮·starter 教学脚手架标注

学生代码框架（starter）中的 F401/F841 是**有意设计**：
  导入与预置变量供 TODO 完成后使用，若删除会破坏脚手架完整性。
处理：在对应行尾追加 `# noqa: F401/F841`，并在文件头（若无）加一行说明。
仅作用于 `学生代码框架/` 目录，幂等。
"""
import glob
import os
import re
import subprocess
import sys

ROOT = r"D:/Python编程实战/教学实施资料"
PY = sys.executable
NOTE = "# [教学脚手架] 下列导入/变量供 TODO 完成后使用，故标注 noqa 而非删除"


def flake(files):
    out = {}
    for i in range(0, len(files), 100):
        r = subprocess.run([PY, "-m", "flake8", "--max-line-length=120",
                            "--select", "F401,F841"] + files[i:i + 100],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        for l in r.stdout.splitlines():
            m = re.match(r"^(.*?):(\d+):(\d+): (F4\d\d)", l)
            if m:
                out.setdefault(os.path.normpath(m.group(1)), []).append((int(m.group(2)), m.group(4)))
    return out


def main():
    # 用相对路径调用 flake8（绝对路径的盘符冒号会破坏行号正则）
    os.chdir(ROOT)
    files = sorted(f for f in glob.glob(os.path.join("*", "学生代码框架", "**", "*.py"),
                                         recursive=True) if "__pycache__" not in f)
    tg = flake(files)
    n_line = n_file = 0
    for f, items in tg.items():
        try:
            lines = open(f, encoding="utf-8").read().splitlines()
        except Exception:
            continue
        # 文件头说明（在 shebang/coding 之后插入一次）
        if NOTE not in "\n".join(lines[:12]):
            ins = 0
            for i, l in enumerate(lines[:4]):
                if l.startswith("#!") or "coding" in l:
                    ins = i + 1
            lines.insert(ins, NOTE)
            items = [(ln + 1 if ln > ins else ln, c) for ln, c in items]
        for ln, code in sorted(set(items)):
            idx = ln - 1
            if idx >= len(lines):
                continue
            cur = lines[idx]
            if "noqa" in cur:
                continue
            # 多行 import 的行尾不适合加 noqa：改在上一行或跳过
            lines[idx] = cur + ("  # noqa: %s" % code if cur.strip() else cur)
            n_line += 1
        open(f, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
        n_file += 1
    print("starter 标注：%d 册 / %d 行" % (n_file, n_line))
    # 复检
    left = flake(files)
    tot = sum(len(v) for v in left.values())
    print("剩余 F401/F841：%d" % tot)
    for f, items in list(left.items())[:5]:
        print("   ", os.path.relpath(f, ROOT)[:60], items[:3])


if __name__ == "__main__":
    main()