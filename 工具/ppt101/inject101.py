# -*- coding: utf-8 -*-
"""101号轮 P1-1：给 32 个精简 deck 注入 R4「知识速览卡」+ R5「下次课预告」。

R4：知识卡列表逐字摘自同周完整 deck；右栏达标线 + 动手提醒。
R5：逐字取同周完整 deck「下次课预告」页的正文行（该页预告的正是下周）。
插入点：99号轮 R3「动手前避坑清单」页之后（保持 重难点→击破→避坑→速览→预告 顺序）。
幂等：已含「知识速览」页即跳过。
"""
import glob
import os
import sys

from pptx import Presentation

ROOT = "/Users/joelgong/PycharmProjects/ai-course-teaching-resources"
sys.path.insert(0, os.path.join(ROOT, "工具", "ppt97"))
sys.path.insert(0, os.path.join(ROOT, "工具", "ppt99"))
sys.path.insert(0, os.path.join(ROOT, "03-Python程序设计-项目实战", "工具"))
from inject99 import (extract, merge_for_slim, sibling_of, slide_title,  # noqa: E402
                      find_index, clone_base, title_shape, strip_clone,
                      add_text, add_rect, fit_lines, base_color_of, font_of,
                      _reorder, LABELS, _short, INK, GRAY)
from inject97 import add_text as a97  # noqa: F401  (确保模块加载)
from ppt_enrich import _renumber_slide_num  # noqa: E402

BAK = "/tmp/backup_ppt101"
SLIM_DIRS = ["02-程序设计基础/V2授课PPT",
             "03-Python程序设计-项目实战/V2授课PPT",
             "05-AI应用基础48课时版/V2授课PPT"]


def _panel(slide, l, t, w, h, head, hcolor, font):
    add_rect(slide, l, t, w, h, "FFFFFF", line="D6DCE4")
    add_rect(slide, l, t, w, 0.4, hcolor)
    add_text(slide, l + 0.12, t + 0.04, w - 0.24, 0.32, head,
             size=11.5, bold=True, color="FFFFFF", font=font)


def build_r4(slide, mat, font, src_note):
    add_text(slide, 0.5, 1.52, 12.33, 0.3,
             "本讲是动手冲刺课：知识点在完整讲解课已细讲——这页把它们浓缩成一张速览卡，边做边对照。",
             size=10.5, color=GRAY, font=font)
    _panel(slide, 0.5, 1.95, 6.9, 4.5, "知识点速览（逐字摘自同周完整讲解课知识卡）", "2F5D8C", font)
    lines = []
    for c in mat["cards"][:6]:
        lines.append("◆ %s %s｜%s" % (c["id"], c["title"], _short(c["define"], 40)))
    if not lines:
        lines = ["◆ " + t for t in mat["topics"][:6]]
    fits, txt = fit_lines("\n".join(lines) or "见同周完整讲解课", 9.5, 6.6, 11)
    add_text(slide, 0.68, 2.48, 6.6, 3.8, txt, size=9.5, color=INK, font=font)
    _panel(slide, 7.55, 1.95, 5.28, 2.15, "本讲达标线（当堂评分同口径）", "2E7D46", font)
    qa = ["① 及格(D)：%s" % (mat["std_d"] or "对照工单及格标准"),
          "② 优秀(B+)：%s" % (mat["std_b"] or "及格基础上完成拓展项")]
    fits, txt = fit_lines("\n".join(qa), 9, 4.95, 4)
    add_text(slide, 7.73, 2.46, 4.95, 1.5, txt, size=9, color=INK, font=font)
    _panel(slide, 7.55, 4.25, 5.28, 2.2, "动手前三个提醒（踩坑点摘录）", "8A4B2D", font)
    ca = mat["cautions"][:3] or [p["fix"] for p in mat["pitfalls"][:3]]
    fits, txt = fit_lines("\n".join("⚠ " + c for c in ca) or "⚠ 见「常见错误速查」页", 9, 4.95, 5)
    add_text(slide, 7.73, 4.76, 4.95, 1.6, txt, size=9, color=INK, font=font)
    if src_note:
        add_text(slide, 0.5, 6.87, 10.5, 0.2, src_note, size=7.5, color=GRAY, font=font)


def build_r5(slide, preview_lines, font):
    add_text(slide, 0.5, 1.52, 12.33, 0.3,
             "带着问题去下一讲——预习任务与自测问题逐字取自课程安排，课前完成。",
             size=10.5, color=GRAY, font=font)
    y = 2.1
    for head, body in preview_lines:
        h = 1.05
        add_rect(slide, 0.5, y, 12.33, h, "F7F9FC", line="D6DCE4")
        add_rect(slide, 0.5, y, 0.09, h, "2F5D8C")
        fits, txt = fit_lines(head + "：" + body, 10.5, 11.9, 3)
        add_text(slide, 0.75, y + 0.18, 11.9, 0.75, txt, size=10.5,
                 color=INK, font=font)
        y += h + 0.16


def extract_preview(path):
    """从同周完整 deck 的「下次课预告」页逐字取正文行。"""
    sib = sibling_of(path)
    if not sib:
        return []
    prs = Presentation(sib)
    for sl in prs.slides:
        if "下次课预告" in slide_title(sl):
            out = []
            for sh in sl.shapes:
                if not sh.has_text_frame:
                    continue
                for ln in sh.text_frame.text.split("\n"):
                    ln = _short(ln.strip(), 80)
                    if len(ln) >= 6 and not ln.startswith(("两江", "下次课")) \
                            and "/" not in ln[:3]:
                        out.append(ln)
            # 归并为 主题/预习快问/课前完成 三行
            groups, cur_head = [], None
            for ln in out:
                m = None
                for h in ("主题", "预习快问", "课前完成", "带着问题"):
                    if ln.startswith(h):
                        m = h
                        break
                if m:
                    groups.append([m, ln[len(m):].lstrip(" :：")])
                    cur_head = m
                elif groups and cur_head:
                    groups[-1][1] += "；" + ln
            return [(h, b) for h, b in groups[:4]]
    return []


def inject_slim(path, dry=False):
    prs = Presentation(path)
    if any("知识速览" in slide_title(sl) for sl in prs.slides):
        return "skip(已注入)"
    own = extract(prs)
    mat, src_note = merge_for_slim(path, own)
    if not mat["cards"] and not mat["topics"]:
        return "skip(无素材)"
    preview = extract_preview(path)
    base_idx = find_index(prs, "实施步骤") or 4
    base = prs.slides[base_idx]
    font = font_of(base)
    clones = []
    for _ in range(2):
        sl = clone_base(prs, base_idx)
        ts = title_shape(sl)
        strip_clone(sl, ts)
        clones.append((sl, ts))
    sl, ts = clones[0]
    if ts is not None:
        from inject99 import set_title
        set_title(ts, "本课知识速览卡 · 边做边对照", font)
    build_r4(sl, mat, font, src_note)
    sl, ts = clones[1]
    if ts is not None:
        from inject99 import set_title
        set_title(ts, "下次课预告 · 带着问题去下一讲", font)
    build_r5(sl, preview or [("主题", "见课程教学日历"), ("预习快问", "见导学单")], font)
    pos = find_index(prs, "动手前避坑清单")
    if pos is None:
        pos = find_index(prs, "实施任务")
    if pos is None:
        pos = find_index(prs, "总结评价") or len(prs.slides) - 1
    _reorder(prs, 2, pos)
    _renumber_slide_num(prs)
    if not dry:
        import shutil
        os.makedirs(BAK, exist_ok=True)
        bak = os.path.join(BAK, os.path.relpath(path, ROOT).replace(os.sep, "__"))
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
        prs.save(path)
    return "ok(+2页, 预告%d行)" % len(preview)


def main():
    for d in SLIM_DIRS:
        for f in sorted(glob.glob(os.path.join(ROOT, d, "*.pptx"))):
            prs = Presentation(f)
            if len(prs.slides) > 30:
                continue  # 只处理精简 deck
            r = inject_slim(f)
            print("%-44s %s" % (os.path.basename(f)[:42], r))


if __name__ == "__main__":
    main()
