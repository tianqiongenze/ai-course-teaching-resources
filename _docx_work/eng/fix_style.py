# -*- coding: utf-8 -*-
"""76号轮·行级排版修复器（E3xx/E7xx/E2xx/E122/E401/F541）

逐条处理 flake8 报告：
  E302/E305/E303 —— 顶层 def/class 前 2 空行、函数后 2 空行、无 3 连续空行
  E306           —— 嵌套 def 前 1 空行
  E702/E701      —— 一行多语句（分号/冒号）拆行
  E261/E262      —— 行内注释前至少两空格 / `# ` 开头
  E401           —— 一行多导入拆行
  E122           —— 续行缺缩进（对齐到上一行缩进 +4）
  F541           —— 空 f-string 去 f 前缀
只改空白与语句切分，不改语义。迭代至收敛。
"""
import glob
import os
import re
import subprocess

PY = r"C:/Users/Lenovo/AppData/Local/Temp/audit/env314/Scripts/python.exe"
ROOT = r"D:/Python编程实战/教学实施资料"
PAT = re.compile(r"^(.*?):(\d+):(\d+): ([A-Z]\d+)")
CODES = "E114,E116,E122,E131,E228,E261,E262,E302,E303,E305,E306,E401,E702,E701,F541"


def scan(files):
    rows = []
    for i in range(0, len(files), 100):
        r = subprocess.run([PY, "-m", "flake8", "--max-line-length=120",
                            "--select", CODES] + files[i:i + 100],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        for l in r.stdout.splitlines():
            m = PAT.match(l)
            if m:
                rows.append((m.group(1), int(m.group(2)), m.group(4)))
    return rows


def fix_line(lines, ln, code):
    """返回 True 若已修改（就地改 lines）。"""
    idx = ln - 1
    if idx < 0 or idx >= len(lines):
        return False
    cur = lines[idx]
    if code == "E702":                      # 一行多语句（分号）
        # 只处理顶层简单分号（不在字符串内）
        if ";" in cur and cur.count('"') % 2 == 0 and cur.count("'") % 2 == 0:
            indent = cur[:len(cur) - len(cur.lstrip())]
            parts = [p.strip() for p in cur.strip().split(";") if p.strip()]
            if len(parts) > 1:
                lines[idx:idx + 1] = [indent + p for p in parts]
                return True
    elif code == "E701":
        m = re.match(r"^(\s*)(if|elif|else|for|while|try|except|finally|with)\b(.*?):\s*(\S.*)$", cur)
        if m:
            head = "%s%s%s:" % (m.group(1), m.group(2), m.group(3))
            body = m.group(1) + "    " + m.group(4)
            lines[idx:idx + 1] = [head, body]
            return True
    elif code == "E302":
        # 顶层 def/class 前需 2 空行
        need = 2
        j = idx - 1
        blanks = 0
        while j >= 0 and not lines[j].strip():
            blanks += 1
            j -= 1
        if j >= 0 and blanks < need:
            lines[idx:idx] = [""] * (need - blanks)
            return True
    elif code == "E305":
        # 函数/类定义块结束后需 2 空行（此码由 flake8 报在后续语句行）
        j = idx - 1
        blanks = 0
        while j >= 0 and not lines[j].strip():
            blanks += 1
            j -= 1
        if j >= 0 and blanks < 2:
            lines[idx:idx] = [""] * (2 - blanks)
            return True
    elif code == "E303":
        j = idx
        cnt = 0
        while j < len(lines) and not lines[j].strip():
            cnt += 1
            j += 1
        if cnt > 2:
            del lines[idx:idx + (cnt - 2)]
            return True
    elif code == "E306":
        j = idx - 1
        blanks = 0
        while j >= 0 and not lines[j].strip():
            blanks += 1
            j -= 1
        if j >= 0 and blanks < 1:
            lines[idx:idx] = [""]
            return True
    elif code == "E261":
        if "#" in cur:
            head, _, tail = cur.partition("#")
            if not head.endswith("  ") and head.strip():
                lines[idx] = head.rstrip() + "  #" + tail
                return True
    elif code == "E262":
        if "#" in cur:
            head, _, tail = cur.partition("#")
            if tail and not tail.startswith(" "):
                lines[idx] = head + "# " + tail.lstrip()
                return True
    elif code == "E401":
        m = re.match(r"^(\s*)import\s+(.+)$", cur)
        if m and "," in m.group(2):
            mods = [x.strip() for x in m.group(2).split(",") if x.strip()]
            lines[idx:idx + 1] = ["%simport %s" % (m.group(1), x) for x in mods]
            return True
    elif code == "E122":
        indent = len(lines[idx]) - len(lines[idx].lstrip())
        want = None
        for k in range(idx - 1, -1, -1):
            if lines[k].strip():
                want = len(lines[k]) - len(lines[k].lstrip()) + 4
                break
        if want is not None and indent != want:
            lines[idx] = " " * want + lines[idx].lstrip()
            return True
    elif code == "E228":
        m = re.match(r"^(.*?)([A-Za-z0-9_)\]\"'])\s*%\s*([A-Za-z0-9_(\"'])", cur)
        if m and "%" in cur:
            head, _, tail = cur.partition("%")
            if not head.endswith(" ") and not tail.startswith(" "):
                lines[idx] = head.rstrip() + " % " + tail.lstrip()
                return True
    elif code == "E131":
        indent = len(cur) - len(cur.lstrip())
        want = None
        for k in range(idx - 1, -1, -1):
            if lines[k].strip():
                want = len(lines[k]) - len(lines[k].lstrip())
                break
        if want is not None and indent != want:
            lines[idx] = " " * want + cur.lstrip()
            return True
    elif code in ("E114", "E116"):
        if cur.strip().startswith("#"):
            want = 0
            for k in range(idx - 1, -1, -1):
                if lines[k].strip():
                    want = len(lines[k]) - len(lines[k].lstrip())
                    break
            if want % 4 != 0:
                want = (want // 4) * 4
            new = " " * want + cur.lstrip()
            if new != cur:
                lines[idx] = new
                return True
    elif code == "F541":
        if 'f"' in cur or "f'" in cur:
            new = cur.replace('f"', '"').replace("f'", "'")
            if new != cur:
                lines[idx] = new
                return True
    return False


def main():
    os.chdir(ROOT)
    files = [f for f in glob.glob("**/*.py", recursive=True)
             if "_docx_work" not in f and "__pycache__" not in f
             and "site-packages" not in f]
    total = 0
    rows = scan(files)
    bad_files = sorted({f for f, _, _ in rows})
    print("初扫：%d 处 / %d 个文件" % (len(rows), len(bad_files)))
    for rnd in range(4):
        if not bad_files:
            break
        rows = scan(bad_files)
        if not rows:
            break
        by = {}
        for f, ln, code in rows:
            by.setdefault(f, []).append((ln, code))
        prog = 0
        for f, items in by.items():
            try:
                lines = open(f, encoding="utf-8").read().splitlines()
            except Exception:
                continue
            dirty = False
            for ln, code in sorted(items, reverse=True):
                if fix_line(lines, ln, code):
                    dirty = True
                    prog += 1
            if dirty:
                open(f, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
        total += prog
        bad_files = sorted({f for f, _, _ in scan(bad_files)})
        print("第%d轮：修复 %d 处，余 %d 文件" % (rnd + 1, prog, len(bad_files)))
        if prog == 0:
            break
    left = scan(files)
    print("完成：共修复 %d 处；剩余 %d" % (total, len(left)))
    for f, ln, code in left[:12]:
        print("   %s:%d %s" % (f[:64], ln, code))


if __name__ == "__main__":
    main()