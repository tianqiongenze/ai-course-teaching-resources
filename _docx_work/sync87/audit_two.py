# -*- coding: utf-8 -*-
"""87d：《程序设计基础》《Python程序设计》九维度验收。"""
import glob
import os
import re

import docx
from pptx import Presentation
from pptx.util import Emu

ROOT = r"D:/工业互联网应用2026~2027第一学期（前八周）"

COURSES = [
    dict(name="程序设计基础", grade="2026级", weeks=list(range(1, 13)), weekday="周一",
         n_gd=12, n_ppt=24, hours=48, gd_prefix=True),
    dict(name="Python程序设计", grade="2025级", weeks=list(range(1, 9)), weekday="周三",
         n_gd=9, n_ppt=16, hours=32, gd_prefix=True),
]

issues = []


def add(lv, cat, msg):
    issues.append((lv, cat, msg))


def uniq(row):
    out, seen = [], set()
    for c in row.cells:
        k = id(c._tc)
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
    return out


def all_text(d):
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            for c in uniq(row):
                parts.append(c.text)
    return "\n".join(parts)


def check(c):
    base = os.path.join(ROOT, c["grade"], "《%s》" % c["name"])
    tag = c["name"]
    print("\n" + "=" * 60)
    print("### %s（%s）" % (tag, c["grade"]))

    # A 完整性
    dirs = ["课程标准", "授课计划", "教学设计", "任务单", "教学PPT"]
    for s in dirs:
        p = os.path.join(base, "《%s》-%s" % (tag, s))
        if not os.path.isdir(p):
            add("严重", tag, "缺目录 %s" % s)
    gd = [f for f in glob.glob(os.path.join(base, "《%s》-任务单" % tag, "*.docx"))
          if not os.path.basename(f).startswith("~$")]
    pp = [f for f in glob.glob(os.path.join(base, "《%s》-教学PPT" % tag, "*.pptx"))
          if not os.path.basename(f).startswith("~$")]
    if len(gd) != c["n_gd"]:
        add("严重", tag, "任务单应 %d，实际 %d" % (c["n_gd"], len(gd)))
    if len(pp) != c["n_ppt"]:
        add("严重", tag, "PPT 应 %d，实际 %d" % (c["n_ppt"], len(pp)))
    copy = os.path.exists(os.path.join(base, "《%s》-版权与使用说明.docx" % tag))
    print("  完整性: 工单 %d / PPT %d / 版权说明 %s" % (len(gd), len(pp), "✔" if copy else "✘"))
    if not copy:
        add("重要", tag, "缺版权与使用说明")

    # B 一致性
    texts = {}
    for key, sub in [("课标", "课程标准"), ("授课计划", "授课计划"), ("教学方案", "教学设计")]:
        f = [x for x in glob.glob(os.path.join(base, "《%s》-%s" % (tag, sub), "*.docx"))
             if not os.path.basename(x).startswith("~$")][0]
        texts[key] = all_text(docx.Document(f))
    for key, txt in texts.items():
        got = set()
        for m in re.finditer(r"第\s*(\d{1,2})(?:\s*[-–~至]\s*(\d{1,2}))?\s*周", txt):
            a = int(m.group(1))
            b = int(m.group(2)) if m.group(2) else a
            got.update(range(min(a, b), max(a, b) + 1))
        miss = [w for w in c["weeks"] if w not in got]
        if miss:
            add("重要", tag, "%s 缺周次 %s" % (key, miss))
    if "1班" not in texts["教学方案"] or "2班" not in texts["教学方案"]:
        add("重要", tag, "教学方案缺 1班/2班")
    if not any(k in texts["课标"] for k in ("工单40%", "工单任务40%", "工单任务（40%）")):
        add("重要", tag, "课标考核口径未统一（工单40%）")
    print("  一致性: 周次/双班/考核 校验完成")

    # C 教学方案
    f = [x for x in glob.glob(os.path.join(base, "《%s》-教学设计" % tag, "*.docx"))
         if not os.path.basename(x).startswith("~$")][0]
    d = docx.Document(f)
    n_tab = len(d.tables) - 1
    if n_tab > c["n_gd"]:
        add("重要", tag, "教学方案课次数 %d > 工单数 %d" % (n_tab, c["n_gd"]))
    for ti in range(1, len(d.tables)):
        t = d.tables[ti]
        u1 = uniq(t.rows[1])
        slot = u1[-1].text.strip() if u1 else ""
        wk = c["weeks"][ti - 1] if ti - 1 < len(c["weeks"]) else None
        if wk and not re.search(r"第%d周%s1~4节（1班）、5~8节（2班）" % (wk, c["weekday"]), slot):
            add("严重", tag, "表%d 时间格式: %s" % (ti, slot))
        if not any("160分钟" in x.text for x in u1):
            add("重要", tag, "表%d 课时未标 4课时（160分钟）" % ti)
        tot = 0
        for ri in (13, 14, 16, 17, 19, 20):
            u = uniq(t.rows[ri])
            m = re.match(r"(\d+)分钟", u[4].text.strip()) if len(u) > 4 else None
            if m:
                tot += int(m.group(1))
            elif len(u) > 4 and "课前" in u[4].text:
                pass
            else:
                add("提示", tag, "表%d R%d 学时格式 %s" % (ti, ri, u[4].text.strip() if len(u) > 4 else "?"))
        if tot != 160:
            add("重要", tag, "表%d 任务实施合计 %d 分钟" % (ti, tot))
    print("  教学方案: %d 个课次表 校验完成" % n_tab)

    # D PPT
    pages = 0
    for f in pp:
        b = os.path.basename(f)
        try:
            prs = Presentation(f)
        except Exception as e:
            add("严重", tag, "PPT 打开失败 %s" % b[:26])
            continue
        pages += len(prs.slides)
        if len(prs.slides) > 80:
            add("重要", tag, "%s 页数 %d > 80" % (b[:26], len(prs.slides)))
        cover = ""
        for sh in prs.slides[0].shapes:
            if sh.has_text_frame and "次课（2课时" in sh.text_frame.text:
                cover = sh.text_frame.text
                break
        # 封面课程名可能在与周次不同的文本框，取首屏全文判断
        first_all = " ".join(sh.text_frame.text for sh in prs.slides[0].shapes if sh.has_text_frame)
        if c["name"] not in first_all:
            add("重要", tag, "%s 封面课程名未统一" % b[:26])
        m = re.match(r"W(\d{2})", b)
        if m and cover:
            want = int(m.group(1))
            mm = re.search(r"第([一二三四五六七八九十]+|\d{1,2})周", cover)
            if mm:
                s = mm.group(1)
                got = int(s) if s.isdigit() else ({"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
                                                  "七": 7, "八": 8, "九": 9, "十": 10,
                                                  "十一": 11, "十二": 12}.get(s, 0))
                if got != want:
                    add("严重", tag, "%s 封面周次 %s ≠ W%d" % (b[:26], s, want))
    print("  PPT: %d 册 / %d 页" % (len(pp), pages))

    # E 工单
    for f in gd:
        b = os.path.basename(f)
        d = docx.Document(f)
        txt = all_text(d)
        if "2课时（80分钟）" in txt or "/2课时" in txt:
            add("重要", tag, "%s 仍为 2课时" % b[:30])
        if "4课时（160分钟）" not in txt:
            add("提示", tag, "%s 未标 4课时（160分钟）" % b[:30])
    print("  工单: %d 个 校验完成" % len(gd))


def main():
    for c in COURSES:
        check(c)
    print("\n" + "=" * 60)
    sev = {"严重": 0, "重要": 0, "提示": 0}
    for lv, _, _ in issues:
        sev[lv] = sev.get(lv, 0) + 1
    print("审查结果：严重 %d · 重要 %d · 提示 %d" % (sev["严重"], sev["重要"], sev["提示"]))
    for lv, tag, msg in issues[:40]:
        print("  [%s] %-8s %s" % (lv, tag, msg))
    if not issues:
        print("未发现问题 ✔")


if __name__ == "__main__":
    main()
