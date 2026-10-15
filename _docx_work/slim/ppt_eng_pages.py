# -*- coding: utf-8 -*-
"""74号轮·PPT 增补：① 工程化项目页 ② 效果图前置页（前后双置）

对每个含「工单完成效果图」页的课件：
  1. 在「实施任务：工单…」页之后插入**前置效果图页**（课前先看终点），
     原页标题改为「…·课末对照」——形成"课前看目标 / 课末对结果"。
  2. 紧随其后再插入**工程化项目页**（本课工单对应的第三种代码形态）。
  3. 全册页脚重编（i / N）。

幂等：已含「本工单的工程化项目」页的册自动跳过。
用法：
  python _docx_work/slim/ppt_eng_pages.py --dry     # 空跑看计划
  python _docx_work/slim/ppt_eng_pages.py           # 执行
"""
import copy
import glob
import os
import re
import sys

from pptx import Presentation
from pptx.util import Emu

ROOT = r"D:/Python编程实战/教学实施资料"
sys.path.insert(0, os.path.join(ROOT, "_docx_work", "eng"))
import eng_specs as S

RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
MAX_PAGES = 80

# 课程目录前缀 -> course
COURSE_OF = {
    "01-AI应用基础": "01-AI应用基础",
    "02-程序设计基础": "02-程序设计基础",
    "03-Python程序设计-项目实战": "03-Python程序设计-项目实战",
    "05-AI应用基础48课时版": "05-AI应用基础48课时版",
}

SPEC_BY_NO = {}
for _s in S.SPECS:
    SPEC_BY_NO[(_s["course"], _s["no"])] = _s


def slide_text(s):
    return "".join(r.text for sh in s.shapes if sh.has_text_frame
                   for pa in sh.text_frame.paragraphs for r in pa.runs)


def find_idx(prs, pred):
    for i, s in enumerate(prs.slides):
        if pred(slide_text(s)):
            return i
    return None


def clone_slide(prs, src):
    """深拷贝 src 页（传 slide 对象，避免插入后索引偏移），追加到末尾，返回新页 index。"""
    layout = src.slide_layout
    new = prs.slides.add_slide(layout)
    # 清掉 layout 自带的占位符
    for sh in list(new.shapes):
        sh._element.getparent().remove(sh._element)
    for sh in src.shapes:
        new.shapes._spTree.append(copy.deepcopy(sh._element))
    # 拷贝背景
    if src.element.find(
            "{http://schemas.openxmlformats.org/presentationml/2006/main}bg") is not None:
        pass
    return len(prs.slides) - 1


def move_slide(prs, src_idx, dst_idx):
    lst = prs.slides._sldIdLst
    items = list(lst)
    el = items[src_idx]
    lst.remove(el)
    if dst_idx >= len(items):
        lst.append(el)
    else:
        items[dst_idx].addprevious(el)


def renumber_footers(prs):
    n = len(prs.slides)
    for i, s in enumerate(prs.slides, 1):
        for sh in s.shapes:
            if not sh.has_text_frame:
                continue
            for pa in sh.text_frame.paragraphs:
                for r in pa.runs:
                    if re.fullmatch(r"\s*\d+\s*/\s*\d+\s*", r.text):
                        r.text = "%d / %d" % (i, n)


def set_box_text(sh, lines):
    """按行写入文本框：复用首段格式，逐段深拷贝。"""
    tf = sh.text_frame
    base_p = tf.paragraphs[0]
    if not base_p.runs:
        base_p.add_run()
    proto = copy.deepcopy(base_p._p)
    for p in list(tf.paragraphs)[1:]:
        p._p.getparent().remove(p._p)
    tf.paragraphs[0].runs[0].text = lines[0] if lines else ""
    for r in list(tf.paragraphs[0].runs)[1:]:
        r._r.getparent().remove(r._r)
    for i in range(1, len(lines)):
        tf._txBody.append(copy.deepcopy(proto))
    paras = list(tf.paragraphs)
    for i, ln in enumerate(lines):
        if i >= len(paras):
            break
        p = paras[i]
        for r in list(p.runs)[1:]:
            r._r.getparent().remove(r._r)
        if not p.runs:
            p.add_run()
        p.runs[0].text = ln


ENG_TITLE = "本工单的工程化项目 · 第三种代码形态"
ENG_BOXES = [
    ["① 项目位置与一键运行",
     "工程化项目/{slug}/",
     "python run.py          # 输出 output/report.txt + result.json",
     "python -m pytest -q    # 全量测试应全绿"],
    ["② 目录结构（23 个文件）",
     "config/rules.yaml      规则外置：改配置不改代码",
     "src/{pkg}/  config · core · io_utils · report · pipeline",
     "tests/      正常 / 边界 / 异常三档"],
    ["③ 国标与 TOGAF 落地",
     "GB/T 9385 需求规格 / 15532 测试 / 8567 文档 / 8566 过程组",
     "TOGAF 四域：业务 · 数据 · 应用 · 技术架构",
     "docs/07 ADR-001 架构决策记录"],
    ["④ 验收口径",
     "pytest 全绿；run.py 产出报告",
     "改配置不改代码；二次运行结果一致（种子固定）",
     "8 份过程文档齐全 → 可直接构成答辩材料链"],
]

FRONT_TITLE = "工单完成效果图 · 先看终点（本课目标预览）"
BACK_TITLE_SUFFIX = " · 课末对照"


def build_eng_frames(spec):
    out = []
    for box in ENG_BOXES:
        out.append([ln.replace("{slug}", spec["slug"]).replace("{pkg}", spec["pkg"])
                    for ln in box])
    return out


def process(path, spec, dry=False):
    prs = Presentation(path)
    # 幂等
    if any(ENG_TITLE in slide_text(s) for s in prs.slides):
        return "跳过(已存在)", len(prs.slides)

    shot_idx = find_idx(prs, lambda t: "工单完成效果图" in t)
    if shot_idx is None:
        return "跳过(无效果图页)", len(prs.slides)

    anchor = find_idx(prs, lambda t: t.startswith("实施任务：工单") or t.startswith("工单实战"))
    if anchor is None:
        anchor = max(0, shot_idx - 1)

    new_total = len(prs.slides) + 2
    if new_total > MAX_PAGES:
        return "跳过(会超%d页: %d→%d)" % (MAX_PAGES, len(prs.slides), new_total), len(prs.slides)

    if dry:
        return "计划: 克隆p%d → 插入p%d/p%d (%d→%d页)" % (
            shot_idx + 1, anchor + 2, anchor + 3, len(prs.slides), new_total), new_total

    src = prs.slides[shot_idx]          # 先取对象，后续插入不会让它错位

    # ① 前置效果图页：克隆原效果图页，插入锚点之后
    ci = clone_slide(prs, src)
    front = prs.slides[ci]
    for sh in front.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip().startswith("工单完成效果图"):
            set_box_text(sh, [FRONT_TITLE])
            break
    move_slide(prs, len(prs.slides) - 1, anchor + 1)

    # ② 工程化项目页：再克隆同一源页，改标题与四个文本框
    ci2 = clone_slide(prs, src)
    eng = prs.slides[ci2]
    title_done = False
    boxes = []
    for sh in eng.shapes:
        if not sh.has_text_frame:
            continue
        txt = sh.text_frame.text.strip()
        if txt.startswith("工单完成效果图"):
            set_box_text(sh, [ENG_TITLE])
            title_done = True
        elif txt.startswith(("①", "②", "③", "④")):
            boxes.append(sh)
    if not title_done:
        # 兜底：取第一个有文本的框当标题
        for sh in eng.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip():
                set_box_text(sh, [ENG_TITLE])
                break
    boxes.sort(key=lambda sh: (round(Emu(sh.top).inches, 1), round(Emu(sh.left).inches, 1)))
    frames = build_eng_frames(spec)
    for i, sh in enumerate(boxes[:len(frames)]):
        set_box_text(sh, frames[i])
    if not boxes:
        # 该册效果图页为单文本框结构（05包 V1/V2）：把四段合并进一个框
        for sh in eng.shapes:
            if sh.has_text_frame and not sh.text_frame.text.strip().startswith(ENG_TITLE):
                flat = []
                for f in frames:
                    flat.extend(f)
                    flat.append("")
                set_box_text(sh, flat)
                break
    move_slide(prs, len(prs.slides) - 1, anchor + 2)

    # ③ 原效果图页标题改为"课末对照"
    orig = None
    for s in prs.slides:
        t = slide_text(s)
        if "工单完成效果图" in t and FRONT_TITLE not in t:
            orig = s
            break
    if orig is not None:
        for sh in orig.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip().startswith("工单完成效果图"):
                cur = sh.text_frame.text.strip().splitlines()[0]
                if BACK_TITLE_SUFFIX not in cur:
                    set_box_text(sh, [cur + BACK_TITLE_SUFFIX])
                break

    renumber_footers(prs)
    prs.save(path)
    return "已插入 2 页", len(prs.slides)


def main():
    dry = "--dry" in sys.argv
    n_done = n_skip = 0
    skipped = []
    for pkgdir, course in COURSE_OF.items():
        for p in sorted(glob.glob(os.path.join(ROOT, pkgdir, "**", "*.pptx"), recursive=True)):
            if "~$" in p or "_docx_work" in p:
                continue
            m = re.search(r"第(\d+)次课", os.path.basename(p))
            if not m:
                continue
            n = int(m.group(1))
            spec = SPEC_BY_NO.get((course, "第%d次课" % n))
            if spec is None:
                spec = SPEC_BY_NO.get((course, "第%d次课" % (n - 1)))
            if spec is None:
                skipped.append((os.path.basename(p), "无匹配工单"))
                continue
            try:
                msg, tot = process(p, spec, dry=dry)
            except Exception as e:
                skipped.append((os.path.basename(p), "%s: %s" % (type(e).__name__, e)))
                continue
            if msg.startswith("跳过"):
                n_skip += 1
                if len(skipped) < 12:
                    skipped.append((os.path.basename(p)[:40], msg))
            else:
                n_done += 1
                if dry:
                    print("  %-46s %s" % (os.path.basename(p)[:46], msg))
    print()
    print("=" * 70)
    print("%s 处理 %d 册 · 跳过 %d 册" % ("[空跑]" if dry else "[执行]", n_done, n_skip))
    if skipped:
        print("跳过明细（前 12）:")
        for a, b in skipped[:12]:
            print("  %-46s %s" % (a[:46], b))
    print("=" * 70)


if __name__ == "__main__":
    main()
