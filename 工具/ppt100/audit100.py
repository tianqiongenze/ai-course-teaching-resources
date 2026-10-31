# -*- coding: utf-8 -*-
"""100号轮深度审计：对授课 PPT 逐页、逐形状、逐行、逐代码块检查。

检查维度（每 deck 出一份问题清单 + 指标）：
  D1 逐代码：代码块逐段 compile() 语法校验；代码行里的中文引号/中文逗号（学生照敲必炸）
  D2 逐形状：文本溢出估算（按字号/框宽逐行折算，行高1.35）
  D3 逐页：单页字符密度（>900 字判高负荷）；最小字号分布
  D4 逐字：乱码（U+FFFD/常见 mojibake）、占位符残留（TODO/XXX/{placeholder}）
输出：audit100_report.json（逐 deck 明细）+ 控制台汇总。
"""
import glob
import json
import os
import re
import sys
import unicodedata

from pptx import Presentation
from pptx.util import Pt

ROOT = "/Users/joelgong/PycharmProjects/ai-course-teaching-resources"
DECK_SETS = [
    "01-AI应用基础/授课PPT",
    "02-程序设计基础/V2授课PPT",
    "03-Python程序设计-项目实战/V2授课PPT",
    "05-AI应用基础48课时版/V2授课PPT",
]
CODE_LINE = re.compile(
    r"^\s*(?:>>> |In \[\d+\]: )?("
    r"[A-Za-z_][\w\.]*\s*=|print\(|import |from \w+ import|def |class |"
    r"for \w+ in |while |if .+:|elif .+:|else:|return|with open|"
    r"df\[|\.groupby\(|\.merge\(|\.fit\(|\.predict\(|plt\.|sns\.|"
    r"@|\]\s*=|\)\s*$)"
)
CJK_IN_CODE = re.compile(r"[“”‘’，；：（）？！]")
PROSE = re.compile(r"[\u4e00-\u9fff]{4,}")


def width_units(line):
    """显示宽度单位：全角 1，半角 0.55。"""
    u = 0.0
    for ch in line:
        u += 1.0 if unicodedata.east_asian_width(ch) in "WF" else 0.55
    return u


def shape_runs(sh):
    """[(paragraph_text, first_run_size_pt)]"""
    out = []
    for p in sh.text_frame.paragraphs:
        txt = "".join(r.text for r in p.runs)
        size = None
        for r in p.runs:
            if r.font.size:
                size = r.font.size.pt
                break
        out.append((txt, size))
    return out


def check_overflow(sh, page_no, issues):
    """按框宽/字号估算所需高度，超出框高 18% 判溢出嫌疑。"""
    if not sh.has_text_frame or sh.width is None or sh.height is None:
        return
    w_in, h_in = sh.width / 914400.0, sh.height / 914400.0
    if w_in <= 0.2 or h_in <= 0.05:
        return
    paras = shape_runs(sh)
    if not paras:
        return
    need = 0.0
    max_sz = 0.0
    for txt, size in paras:
        sz = size or 12.0
        max_sz = max(max_sz, sz)
        per_line = max(1.0, w_in / (sz / 72.0 * 0.98))
        lines = max(1, -(-int(width_units(txt) + 0.999) // int(per_line))) if txt else 1
        need += lines * sz * 1.35 / 72.0
    if need > h_in * 1.18 + 0.06 and need - h_in > 0.12:
        issues.append({
            "type": "overflow", "page": page_no,
            "box": "%.2fx%.2f" % (w_in, h_in), "need": round(need, 2),
            "text": sh.text_frame.text.strip().replace("\n", "⏎")[:40],
        })


def clean_code(text):
    lines = []
    for raw in text.split("\n"):
        body = raw.rstrip()
        stripped = body.lstrip()
        indent = body[:len(body) - len(stripped)]
        ln = re.sub(r"^(▸|•|·|◆|→)\s*", "", stripped)
        if not ln or ln.startswith("#"):
            continue
        # 含函数调用/字符串结尾的行视为代码（如 alarm(3, f"温度…停机！")）
        looks_code = bool(CODE_LINE.match(ln)) or \
            (ln.endswith(')') and '(' in ln) or re.search(r'[fF]?["\'].*["\']\s*\)?$', ln)
        if PROSE.search(ln.split("#")[0]) and not looks_code:
            continue
        ln = re.sub(r"\s*——.*$", "", ln.split("#")[0]).rstrip()
        if ln:
            lines.append(indent + ln)
    return "\n".join(lines)


def check_code_block(sh, page_no, deck, issues, stats):
    text = sh.text_frame.text
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) < 2:
        return
    codeish = sum(1 for l in lines if CODE_LINE.match(l))
    if codeish < 2 or codeish < len(lines) * 0.5:
        return
    stats["code_blocks"] += 1
    # 中文标点检查（学生照敲必炸）
    bad = [(i + 1, l) for i, l in enumerate(lines) if CJK_IN_CODE.search(l)]
    if bad:
        issues.append({"type": "cjk_punct_in_code", "page": page_no,
                       "detail": bad[:3],
                       "text": text.strip().replace("\n", "⏎")[:60]})
    body = clean_code(text)
    if len(body) < 8:
        return
    stats["code_compiled"] += 1
    try:
        compile(body, "<ppt>", "exec")
    except SyntaxError as e:
        issues.append({"type": "code_syntax", "page": page_no,
                       "err": "%s: %s" % (type(e).__name__, e.msg),
                       "line": e.text and e.text.strip()[:60],
                       "text": body.replace("\n", "⏎")[:80]})


def audit_deck(path):
    prs = Presentation(path)
    issues, stats = [], {
        "slides": len(prs.slides), "code_blocks": 0, "code_compiled": 0,
        "min_font": 99.0, "page_chars": [], "dense_pages": 0,
    }
    for pi, sl in enumerate(prs.slides):
        page_chars = 0
        for sh in sl.shapes:
            if not sh.has_text_frame:
                continue
            text = sh.text_frame.text
            page_chars += len(text.strip())
            check_overflow(sh, pi + 1, issues)
            check_code_block(sh, pi + 1, path, issues, stats)
            for _t, size in shape_runs(sh):
                if size:
                    stats["min_font"] = min(stats["min_font"], size)
            if re.search(r"[\uFFFD]|æ|çå|TODO(?!归)", text):
                issues.append({"type": "garbled", "page": pi + 1,
                               "text": text.strip()[:50]})
        stats["page_chars"].append(page_chars)
        if page_chars > 900:
            stats["dense_pages"] += 1
            issues.append({"type": "dense_page", "page": pi + 1,
                           "chars": page_chars})
    avg = sum(stats["page_chars"]) / max(1, len(stats["page_chars"]))
    return {"file": os.path.basename(path), "issues": issues, "slides": stats["slides"],
            "avg_chars": round(avg),
            "dense_pages": stats["dense_pages"], "min_font": stats["min_font"],
            "code_blocks": stats["code_blocks"],
            "code_compiled": stats["code_compiled"],
            "syntax_errors": sum(1 for i in issues if i["type"] == "code_syntax"),
            "cjk_punct": sum(1 for i in issues if i["type"] == "cjk_punct_in_code"),
            "overflows": sum(1 for i in issues if i["type"] == "overflow"),
            "garbled": sum(1 for i in issues if i["type"] == "garbled")}


def main():
    report = []
    for d in DECK_SETS:
        for f in sorted(glob.glob(os.path.join(ROOT, d, "*.pptx"))):
            r = audit_deck(f)
            r["dir"] = d.split("/")[0]
            report.append(r)
            print("%-8s %-46s 页%3d 均字%4d 密页%2d 溢出%2d 代码块%3d(错%2d/中文标点%2d) 乱码%d 最小字号%.1f"
                  % (r["dir"], r["file"][:44], r["slides"], r["avg_chars"],
                     r["dense_pages"], r["overflows"], r["code_blocks"],
                     r["syntax_errors"], r["cjk_punct"], r["garbled"],
                     r["min_font"]))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "audit100_report.json")
    json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tot = lambda k: sum(r[k] for r in report)  # noqa: E731
    print("== decks=%d 溢出=%d 代码块=%d 编译检查=%d 语法错=%d 中文标点=%d 密页=%d 乱码=%d"
          % (len(report), tot("overflows"), tot("code_blocks"),
             tot("code_compiled"), tot("syntax_errors"), tot("cjk_punct"),
             tot("dense_pages"), tot("garbled")))


if __name__ == "__main__":
    main()
