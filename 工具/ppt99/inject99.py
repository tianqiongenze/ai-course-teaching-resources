# -*- coding: utf-8 -*-
"""给三课 64 个 V2 授课 PPT 注入「重难点细化包」。

背景（用户要求）：把每个技术点、知识点、操作难点、课程重难点再次完善细化，
使专科大一/大二学生都能学会看懂。

每个 deck 注入：
  R1「本课重难点地图 · 老师划重点」：重点必会（知识卡全景）/ 难点易卡壳 /
     高频易错（⚠→✔）/ 达标自问四句；
  R2「难点逐个击破 · 零基础照做就能会」：每个难点 = 为什么容易栽（原文误区）→
     一招破解（知识卡定义）→ 动手验证（使用场景+示例代码）；
  精简 deck（本周第2次课/（下））额外注入：
  R3「承上启下 · 动手前避坑清单」：取同周完整 deck 的避坑清单（标注来源）。

内容纪律：所有句子逐字取自该 deck（或同周完整 deck）已有的知识卡/避坑清单/
实施步骤/达标标准，只做筛选、排序与拼版，不改写、不编造。
排版纪律：同文档克隆基准页继承页眉色带/页脚，注入后重编页码；
幂等：已含「重难点地图」页即跳过。
"""
import copy
import glob
import json
import os
import re
import shutil
import sys

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

ROOT = "/Users/joelgong/PycharmProjects/ai-course-teaching-resources"
sys.path.insert(0, os.path.join(ROOT, "工具", "ppt97"))
sys.path.insert(0, os.path.join(ROOT, "03-Python程序设计-项目实战", "工具"))
from inject97 import (slide_title, find_index, clone_base, title_shape,  # noqa: E402
                      add_text, add_rect, fit_lines, base_color_of, font_of, _reorder)
from ppt_enrich import _renumber_slide_num  # noqa: E402

BAK = "/tmp/backup_ppt99"
COURSE_DIRS = ["02-程序设计基础/V2授课PPT",
               "03-Python程序设计-项目实战/V2授课PPT",
               "05-AI应用基础48课时版/V2授课PPT"]
MARK = "重难点地图"
MAX_MIS = 3          # R2 最多拆解的难点数
LABELS = ("定义", "使用场景", "扩展与优化", "实施步骤", "⚠ 注意事项",
          "及格标准（D）", "优秀标准（B+）", "实施步骤 | ")


def _clean(t):
    return re.sub(r"\s+", " ", (t or "").strip())


def _short(t, n):
    t = _clean(t)
    return t if len(t) <= n else t[:n - 1] + "…"


def extract(prs):
    """从 deck 自身逐字提取教学素材。"""
    m = {"cards": [], "pitfalls": [], "steps": [], "cautions": [],
         "std_d": "", "std_b": "", "skills": [], "topics": []}
    for sl in prs.slides:
        title = slide_title(sl)
        texts = [_clean(sh.text_frame.text) for sh in sl.shapes
                 if sh.has_text_frame and sh.text_frame.text.strip()]
        if title.startswith("知识详解："):
            card = {"id": "", "title": _short(title.split("：", 1)[1], 22),
                    "define": "", "scene": "", "code": "", "mis": ""}
            for i, t in enumerate(texts):
                nxt = texts[i + 1] if i + 1 < len(texts) else ""
                if re.match(r"^B\d{2}", t):
                    card["id"] = t.split("·")[0].strip()
                elif t == "定义" and nxt and nxt not in LABELS:
                    card["define"] = nxt
                elif t == "使用场景" and nxt and nxt not in LABELS:
                    card["scene"] = nxt
                    if i + 2 < len(texts) and texts[i + 2] not in LABELS \
                            and not texts[i + 2].startswith(("两江", "扩展")):
                        card["code"] = texts[i + 2]
                elif t == "扩展与优化" and nxt and nxt not in LABELS:
                    card["mis"] = nxt
            if card["id"] or card["title"]:
                m["cards"].append(card)
        elif "常见错误速查" in title:
            for i, t in enumerate(texts):
                if t.startswith("⚠"):
                    err = t.lstrip("⚠ ").strip()
                    cause = fix = ""
                    for j in range(i + 1, min(i + 4, len(texts))):
                        u = texts[j]
                        if u.startswith("原因"):
                            cause = u.split(":", 1)[-1].strip(" :：")
                        elif u.startswith("✔"):
                            fix = u.split("解决", 1)[-1].strip(" :：")
                    if err:
                        m["pitfalls"].append({"err": _short(err, 20),
                                              "cause": _short(cause, 26),
                                              "fix": _short(fix, 30)})
        elif title.startswith("实施步骤"):
            grab_step = grab_caution = False
            for sh in sl.shapes:
                if not sh.has_text_frame or not sh.text_frame.text.strip():
                    continue
                t = _clean(sh.text_frame.text)
                raw = sh.text_frame.text
                if t == "实施步骤":
                    grab_step, grab_caution = True, False
                    continue
                if t.startswith("⚠ 注意事项") or t == "⚠":
                    grab_step, grab_caution = False, True
                    body = t.split("注意事项", 1)[-1].strip(" :：") if "注意事项" in t else ""
                    for ln in body.split("\n"):
                        ln = _clean(ln)
                        if len(ln) >= 6 and not ln.startswith(("⚠", "两江")):
                            m["cautions"].append(
                                _short(ln.lstrip("0123456789.、 "), 42))
                    continue
                if t.startswith("两江智造"):
                    grab_step = grab_caution = False
                if grab_caution:
                    for ln in raw.split("\n"):
                        ln = _clean(ln)
                        if len(ln) >= 6 and not ln.startswith("两江"):
                            m["cautions"].append(
                                _short(ln.lstrip("0123456789.、 "), 42))
                    continue
                if grab_step and re.match(r"^\d$", t):
                    continue
                if grab_step and t and t not in LABELS:
                    m["steps"].append(_short(t, 30))
        elif title.startswith("实施任务"):
            for i, t in enumerate(texts):
                nxt = texts[i + 1] if i + 1 < len(texts) else ""
                if t.startswith("及格标准"):
                    rest = t.split("）", 1)[-1].strip(" :：")
                    m["std_d"] = _short(rest or nxt, 40)
                elif t.startswith("优秀标准"):
                    rest = t.split("）", 1)[-1].strip(" :：")
                    m["std_b"] = _short(rest or nxt, 40)
        elif title.startswith("技能点"):
            for i, t in enumerate(texts):
                if re.match(r"^S\d$", t) and i + 1 < len(texts):
                    m["skills"].append(_short(texts[i + 1].split("——")[0], 34))
    # 精简 deck 的本课主题条：任务情境页之后第一张内容页的条目
    for i, sl in enumerate(prs.slides):
        if "任务情境" in slide_title(sl):
            for j in (i + 1, i + 2):
                if j >= len(prs.slides):
                    break
                t2 = slide_title(prs.slides[j])
                if any(k in t2 for k in ("安全", "预习", "课前")):
                    continue
                bullets = [_clean(sh.text_frame.text) for sh in prs.slides[j].shapes
                           if sh.has_text_frame]
                got = []
                slide_ttl = _short(t2, 20)
                for b in bullets:
                    for ln in b.split("\n"):
                        ln = _clean(ln)
                        if len(ln) >= 8 and not ln.startswith(("两江", "工单项目")) \
                                and ln != slide_ttl and "/" not in ln[:2] \
                                and not re.search(r"（\d+）$", ln):
                            got.append(_short(ln.rstrip("；;。"), 44))
                m["topics"] = got[:6]
                break
            break
    return m


def sibling_of(path):
    """同周另一个 deck（完整版），供精简 deck 取素材。"""
    d, base = os.path.split(path)
    wk = base.split("-")[0]
    cands = [f for f in glob.glob(os.path.join(d, wk + "-*.pptx"))
             if os.path.basename(f) != base]
    return cands[0] if len(cands) == 1 else None


def merge_for_slim(path, own):
    """精简 deck：主题条用自身，知识卡/避坑/达标取同周完整 deck（标注来源）。"""
    sib = sibling_of(path)
    if not sib:
        return own, ""
    sm = extract(Presentation(sib))
    merged = dict(own)
    merged["cards"] = sm["cards"]
    merged["pitfalls"] = sm["pitfalls"]
    merged["skills"] = sm["skills"]
    if not merged["std_d"]:
        merged["std_d"], merged["std_b"] = sm["std_d"], sm["std_b"]
    src = "素材来源：同周《%s》知识卡与避坑清单（逐字摘录）" % _short(
        os.path.basename(sib).replace(".pptx", "").split("-", 1)[-1], 18)
    return merged, src


# ---------------- 版面 ----------------
INK, BLUE, GREEN, RED, AMBER, GRAY = "2B2F36", "35506E", "2E7D46", "B5533A", "8A6D1A", "6B7280"


def _panel(slide, l, t, w, h, head, hcolor, font):
    add_rect(slide, l, t, w, h, "FFFFFF", line="D6DCE4")
    add_rect(slide, l, t, w, 0.4, hcolor)
    add_text(slide, l + 0.12, t + 0.04, w - 0.24, 0.32, head,
             size=11.5, bold=True, color="FFFFFF", font=font)


def build_r1(slide, mat, base, font, src_note):
    add_text(slide, 0.5, 1.52, 12.33, 0.3,
             "动手前先看这页：重点要会什么、难点会卡在哪、哪里最容易错、学没学会怎么自测。",
             size=10.5, color=GRAY, font=font)
    # 左：重点必会
    _panel(slide, 0.5, 1.95, 6.05, 3.42, "重点 · 必会必考（本课知识点全景）", "2F5D8C", font)
    lines = []
    for c in mat["cards"][:6]:
        one = _short(c["define"], 34)
        lines.append("◆ %s %s｜%s" % (c["id"], c["title"], one) if c["id"]
                     else "◆ %s｜%s" % (c["title"], one))
    if not lines:
        lines = ["◆ " + t for t in mat["topics"][:6]]
    fits, txt = fit_lines("\n".join(lines) or "见知识精讲部分", 9.5, 5.75, 10)
    add_text(slide, 0.68, 2.48, 5.75, 2.8, txt, size=9.5, color=INK, font=font)
    # 右上：难点
    _panel(slide, 6.72, 1.95, 6.11, 1.62, "难点 · 易卡壳（下一页逐个击破）", "8A4B2D", font)
    miscut = [_short(c["mis"], 46) or _short(c["define"], 40)
              for c in mat["cards"] if c["mis"]][:3]
    fits, txt = fit_lines("\n".join("▲ " + x for x in miscut) or "▲ 见实施注意事项",
                          9, 5.8, 4)
    add_text(slide, 6.9, 2.44, 5.8, 1.05, txt, size=9, color=INK, font=font)
    # 右下：高频易错
    _panel(slide, 6.72, 3.72, 6.11, 1.65, "高频易错 · 动手前先记住", "9A3B3B", font)
    pl = ["%s → %s" % (p["err"], p["fix"] or p["cause"]) for p in mat["pitfalls"][:3]]
    fits, txt = fit_lines("\n".join("✗ " + x for x in pl) or "✗ 见「常见错误速查」页",
                          9, 5.8, 4)
    add_text(slide, 6.9, 4.21, 5.8, 1.05, txt, size=9, color=INK, font=font)
    # 底：达标自问
    _panel(slide, 0.5, 5.52, 12.33, 1.32, "达标自问 · 学没学会，问自己这四句（当堂评分同口径）",
           "2E7D46", font)
    qa = ["① 及格线我能过吗——%s" % (mat["std_d"] or "对照工单及格标准逐项核对"),
          "② 优秀线我够吗——%s" % (mat["std_b"] or "在及格基础上完成拓展项"),
          "③ 技能点我能独立做出来吗——%s" % ("；".join(mat["skills"][:2]) or "对照技能点页 S1–S4 逐条自测"),
          "④ 报错了先查「常见错误速查」页再举手——错误信息逐字读一遍，八成自己能修"]
    fits, txt = fit_lines("\n".join(qa), 9, 11.9, 4)
    add_text(slide, 0.68, 5.97, 12.0, 0.84, txt, size=9, color=INK, font=font)
    if src_note:
        add_text(slide, 0.5, 6.87, 10.5, 0.2, src_note, size=7.5, color=GRAY, font=font)


def build_r2(slide, mat, base, font):
    add_text(slide, 0.5, 1.52, 12.33, 0.3,
             "每个难点四步走：先看「为什么容易栽」对号入座 → 记住「一招破解」→ 照「动手验证」做一遍 → 做不出回知识详解页。",
             size=10.5, color=GRAY, font=font)
    hard = [c for c in mat["cards"] if c["mis"]][:MAX_MIS]
    if not hard:
        hard = mat["cards"][:1]
    y = 1.95
    for n, c in enumerate(hard, 1):
        h = 1.62
        add_rect(slide, 0.5, y, 12.33, h, "F7F9FC", line="D6DCE4")
        add_rect(slide, 0.5, y, 0.09, h, "8A4B2D")
        add_text(slide, 0.72, y + 0.05, 12.0, 0.3,
                 "难点%d：%s %s" % (n, c["id"] or "·", c["title"]),
                 size=11, bold=True, color="8A4B2D", font=font)
        cols = [("为什么容易栽", _short(c["mis"], 80), RED),
                ("一招破解（记住这句）", _short(c["define"], 80), GREEN),
                ("动手验证（照做一遍）", _short((c["scene"] or "") +
                                        (("\n" if c["scene"] and c["code"] else "") + c["code"]), 96), BLUE)]
        x = 0.72
        for head, body, color in cols:
            add_text(slide, x, y + 0.4, 3.9, 0.24, head, size=9, bold=True,
                     color=color, font=font)
            fits, txt = fit_lines(body, 8.5, 3.9, 5)
            add_text(slide, x, y + 0.66, 3.92, 0.9, txt, size=8.5, color=INK, font=font)
            x += 4.02
        y += h + 0.13
    while y < 6.9 and len(hard) < 3:   # 难点不足 3 个时补注意事项卡
        ca = mat["cautions"][:2]
        if not ca:
            break
        add_rect(slide, 0.5, y, 12.33, 1.0, "FFF9EC", line="E3D5A8")
        add_text(slide, 0.72, y + 0.06, 12.0, 0.26, "操作提醒（实施注意事项摘录）",
                 size=10, bold=True, color=AMBER, font=font)
        fits, txt = fit_lines("\n".join("⚠ " + c for c in ca), 9, 11.9, 3)
        add_text(slide, 0.72, y + 0.36, 11.9, 0.6, txt, size=9, color=INK, font=font)
        y += 1.13


def build_r3(slide, mat, base, font, src_note):
    add_text(slide, 0.5, 1.52, 12.33, 0.3,
             "本讲是动手冲刺课：先把上周完整讲解里的高频翻车点过一遍，再开工——每条都是历届学生真实踩过的坑。",
             size=10.5, color=GRAY, font=font)
    ps = mat["pitfalls"][:6]
    rows_n = max(1, (len(ps) + 1) // 2)
    colw = 6.05
    rowh = min(2.3, 4.75 / rows_n - 0.12)
    for k, p in enumerate(ps):
        r, c = divmod(k, 2)
        l, t = 0.5 + c * (colw + 0.23), 1.95 + r * (rowh + 0.14)
        add_rect(slide, l, t, colw, rowh, "FFFFFF", line="D6DCE4")
        add_rect(slide, l, t, 0.09, rowh, "9A3B3B")
        add_text(slide, l + 0.22, t + 0.07, colw - 0.4, 0.3, "✗ " + p["err"],
                 size=10.5, bold=True, color=RED, font=font)
        fits, txt = fit_lines("原因：%s\n✔ 解决：%s" % (p["cause"] or "见错误信息", p["fix"]),
                              9, colw - 0.4, 3)
        add_text(slide, l + 0.22, t + 0.42, colw - 0.4, 0.95, txt, size=9,
                 color=INK, font=font)
    if src_note:
        add_text(slide, 0.5, 6.87, 10.5, 0.2, src_note, size=7.5, color=GRAY, font=font)


def strip_clone(slide, keep_title):
    """只保留页眉色带(top<=0.02)、装饰条(1.2-1.4/h<0.15)、标题、页脚(top>=7.0)，
    其余基准页正文残影全部删除。"""
    for sh in list(slide.shapes):
        top = (sh.top or 0) / 914400.0
        h = (sh.height or 0) / 914400.0
        if top <= 0.02 or top >= 7.0:
            continue
        if 1.2 <= top <= 1.4 and h < 0.15:
            continue
        if keep_title is not None and sh._element is keep_title._element:
            continue
        sh._element.getparent().remove(sh._element)


def inject_deck(path, dry=False):
    prs = Presentation(path)
    if any(MARK in slide_title(sl) for sl in prs.slides):
        return {"file": path, "status": "skip(已注入)"}
    slim = len(prs.slides) <= 30
    mat = extract(prs)
    src_note = ""
    if slim:
        mat, src_note = merge_for_slim(path, mat)
        if not mat["cards"] and not mat["pitfalls"]:
            return {"file": path, "status": "skip(无素材)"}
    # 克隆 3 页基准（取「实施步骤」页做母版；找不到就用第 5 页）
    base_idx = find_index(prs, "实施步骤") or 4
    base = prs.slides[base_idx]
    base_color, font = base_color_of(base), font_of(base)
    n_pages = 3 if slim else 2
    clones = []
    for _ in range(n_pages):
        sl = clone_base(prs, base_idx)
        ts = title_shape(sl)
        strip_clone(sl, ts)
        clones.append((sl, ts))
    # 填内容
    sl, ts = clones[0]
    if ts is not None:
        set_title(ts, "本课重难点地图 · 老师划重点（动手前必看）", font)
    build_r1(sl, mat, base_color, font, src_note)
    sl, ts = clones[1]
    if ts is not None:
        set_title(ts, "难点逐个击破 · 零基础照做就能会", font)
    build_r2(sl, mat, base_color, font)
    if slim:
        sl, ts = clones[2]
        if ts is not None:
            set_title(ts, "承上启下 · 动手前避坑清单", font)
        build_r3(sl, mat, base_color, font, src_note)
    # 定位插入点：实施任务 → 总结评价 → THANKS
    pos = find_index(prs, "实施任务")
    if pos is None:
        pos = find_index(prs, "总结评价")
    if pos is None:
        pos = find_index(prs, "THANKS") or len(prs.slides) - 1
    _reorder(prs, n_pages, pos - 1 if pos > 0 else 0)
    _renumber_slide_num(prs)
    if not dry:
        rel = os.path.relpath(path, ROOT)
        bak = os.path.join(BAK, rel.replace(os.sep, "__"))
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
        prs.save(path)
    return {"file": path, "status": "ok", "slim": slim, "insert_before": pos + 1,
            "pages": n_pages, "cards": len(mat["cards"]),
            "pitfalls": len(mat["pitfalls"]), "std_d": mat["std_d"][:24]}


def set_title(ts, text, font):
    """复用克隆来的标题框样式，只换文字。"""
    tf = ts.text_frame
    # 保留第一 run 的字号/加粗/颜色，重写文本
    first = None
    for p in tf.paragraphs:
        for r in p.runs:
            if first is None:
                col = None
                try:
                    if r.font.color and r.font.color.type is not None:
                        col = r.font.color.rgb
                except Exception:  # noqa: BLE001
                    col = None
                first = (r.font.size, r.font.bold, col)
    lines = text.split("\n")
    tf.clear()
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = ln
        if first:
            if first[0]:
                r.font.size = first[0]
            if first[1] is not None:
                r.font.bold = first[1]
            try:
                if first[2]:
                    r.font.color.rgb = first[2]
            except Exception:  # noqa: BLE001
                pass
        if font:
            r.font.name = font


def main():
    dry = "--dry" in sys.argv
    report = []
    for d in COURSE_DIRS:
        for f in sorted(glob.glob(os.path.join(ROOT, d, "*.pptx"))):
            try:
                r = inject_deck(f, dry=dry)
            except Exception as e:  # noqa: BLE001
                r = {"file": f, "status": "ERROR: %s" % e}
            r["file"] = os.path.basename(r["file"])
            report.append(r)
            print(r)
    ok = sum(1 for r in report if r["status"] == "ok")
    print("== ok=%d / total=%d" % (ok, len(report)))
    if not dry:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "inject99_manifest.json")
        json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
