# -*- coding: utf-8 -*-
"""输入输出工具：读 CSV/JSON、原子写文本、保证目录存在、课程数据定位。

工程要点：
  1. 原子写（先写临时文件再 os.replace）——防止中途崩溃留下半个文件；
  2. 所有路径参数为绝对/相对均可，内部统一 os.path.join；
  3. 失败时抛带文件名的异常，便于排错（对应 GB/T 15532 异常路径测试）；
  4. 课程数据集统一由 course_data() 定位（环境变量 > 课程 data/ > 内置兜底），
     换机房、换目录深度不用改代码——"环境也是选型维度"。
"""
import csv
import json
import os
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))          # .../src/<pkg>
_PROJ = os.path.normpath(os.path.join(_HERE, "..", ".."))    # .../工程化项目/<proj>
# 课程数据在 01-AI应用基础/data/（工程化项目 的上一级的上一级）；换机房可用环境变量覆盖
_CANDIDATES = [os.environ.get("AI_COURSE_DATA"),
               os.path.join(_PROJ, "..", "..", "data"),
               os.path.join(_PROJ, "..", "data"),
               os.path.join(_PROJ, "data")]


def course_data(*parts):
    """返回课程数据文件的绝对路径；找不到返回 None（调用方负责降级并如实告知）。"""
    for base in _CANDIDATES:
        if not base:
            continue
        p = os.path.join(os.path.normpath(base), *parts)
        if os.path.exists(p):
            return p
    return None


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def write_text(path, text, encoding="utf-8"):
    """原子写入：先写临时文件再替换，避免半成品文件。"""
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)),
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


def write_json(path, obj):
    return write_text(path, json.dumps(obj, ensure_ascii=False, indent=2))


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_csv_rows(path):
    """按行读 CSV，返回 list[dict]；首行视为表头。"""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def write_csv_rows(path, rows, fields=None):
    if not rows:
        return write_text(path, "")
    fields = fields or list(rows[0].keys())
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return write_text(path, buf.getvalue())


def dwidth(s):
    """显示宽度：中日韩全角字符按 2 列计（等宽表对齐用）。"""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def pad(s, width):
    """按显示宽度左对齐补空格。"""
    return s + " " * max(0, width - dwidth(s))


def fmt_table(rows, headers):
    """等宽文本表（报告用）——按显示宽度对齐中文，不依赖第三方库。"""
    cols = [list(headers)] + [[str(c) for c in r] for r in rows]
    widths = [max(dwidth(r[i]) for r in cols) for i in range(len(headers))]
    out = ["  ".join(pad(h, widths[i]) for i, h in enumerate(headers)),
           "  ".join("-" * w for w in widths)]
    for r in cols[1:]:
        out.append("  ".join(pad(c, widths[i]) for i, c in enumerate(r)))
    return "\n".join(out)
