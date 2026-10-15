# -*- coding: utf-8 -*-
"""79号轮·课程标准 PDF 周次替换

用 PyMuPDF 精确替换含周次的文本（redact + insert_text，内置中文字体）。
输出覆盖原文件（先备份）。
"""
import os
import shutil
import sys

import pymupdf

ROOT = r"D:/Python编程实战/教学实施资料"
PDF = os.path.join(ROOT, "课标PDF版", "工业互联网专业《AI应用基础（48课时版）》课程标准.pdf")
BAK = PDF + ".bak79"

# (旧文本, 新文本)  —— 按出现顺序精确匹配
RULES = [
    ("第4-15 周", "第7周、第10-20周"),
    ("自第4 周", "自第7周"),
    ("第4 周开课，学期周=教学周+3", "第7周开课（跳过第8、9周），学期周=教学周+8"),
    ("第4-5 周", "第7、10周"),
    ("第6-9 周", "第11-14周"),
    ("第10-11 周", "第15-16周"),
    ("第12-13 周", "第17-18周"),
    ("第14 周", "第19周"),
    ("第15 周（第12 教学周）", "第20周（第12教学周）"),
    ("第5 周中期诊断", "第13周中期诊断"),
]


def main():
    apply = "--apply" in sys.argv
    doc = pymupdf.open(PDF)
    hits = []
    for pno in range(doc.page_count):
        page = doc[pno]
        for old, new in RULES:
            rects = page.search_for(old)
            if rects:
                hits.append((pno + 1, old, new, len(rects)))
    for h in hits:
        print("  p%-2d %-28s → %-28s ×%d" % h)
    print("共 %d 类命中" % len(hits))
    if not apply:
        print("（空跑，未修改）")
        return
    if not os.path.exists(BAK):
        shutil.copy2(PDF, BAK)
        print("已备份 →", os.path.basename(BAK))
    # 执行替换
    for pno in range(doc.page_count):
        page = doc[pno]
        for old, new in RULES:
            rects = page.search_for(old)
            if not rects:
                continue
            # 按 y 分组（同一行合并为一个 rect），避免重复插入
            groups = []
            for r in rects:
                placed = False
                for g in groups:
                    if abs((g.y0 + g.y1) / 2 - (r.y0 + r.y1) / 2) <= 3.0:
                        g.x0 = min(g.x0, r.x0); g.y0 = min(g.y0, r.y0)
                        g.x1 = max(g.x1, r.x1); g.y1 = max(g.y1, r.y1)
                        placed = True
                        break
                if not placed:
                    groups.append(pymupdf.Rect(r))
            for g in groups:
                page.add_redact_annot(g)
            page.apply_redactions()
            for g in groups:
                page.insert_text((g.x0, g.y1 - 2.0), new, fontname="china-s",
                                 fontsize=min(11.5, g.height - 1.5), color=(0, 0, 0))
    doc.save(PDF + ".new.pdf", deflate=True)   # 先写新文件（不能覆盖原文件非增量）
    doc.close()
    os.replace(PDF + ".new.pdf", PDF)        # 原子替换
    print("已写入:", os.path.basename(PDF))


if __name__ == "__main__":
    main()
