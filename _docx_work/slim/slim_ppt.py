# -*- coding: utf-8 -*-
"""PPT 精简融合工具（72号轮）——去册内重复 + 去填充页 + 页脚重编号 + 关键页保护
用法: python slim_ppt.py --dry <pptx...>   |  python slim_ppt.py --apply --target 80 <pptx...>
"""
import sys, os, re, argparse
from difflib import SequenceMatcher
from pptx import Presentation
from pptx.util import Emu

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

def page_info(slide):
    txts = []
    has_pic = False
    for sh in slide.shapes:
        if sh.shape_type == 13 or sh.element.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}pic'):
            has_pic = True
        if sh.has_text_frame:
            for p in sh.text_frame.paragraphs:
                for r in p.runs:
                    if r.text: txts.append(r.text)
    return txts, has_pic

def clean(txts):
    t = "".join(txts)
    t = re.sub(r"\d+\s*/\s*\d+", "", t)
    t = re.sub(r"两江智造集团[^\s]*", "", t)
    t = re.sub(r"重庆两江智造集团[^\s]*", "", t)
    return t.strip()

def bag(s):
    return set(re.findall(r"[\u4e00-\u9fff]{2,}", s))

def is_cover(i, txts, n): return i == 0
def is_thanks(t): return ("THANKS" in t) or ("感谢聆听" in t)
def is_preview(t): return "下次课预告" in t
def is_section(t):
    """章节/过渡页：以 0X + 中文小节名 开头（课程授课PPT与说课PPT通用）"""
    return bool(re.match(r"^0[1-9][\u4e00-\u9fff]{2,8}", t))
def is_screenshot(t): return "完成后长这样" in t or "课堂实况与运行截图" in t

# 永远保护（含独有知识/设计锚点/导航），绝不删除
KEEP = [
    ("K-知识图谱回顾", lambda t: "全课知识图谱回顾" in t),
    ("K-一图流总结",   lambda t: "今日一图流总结" in t),
    ("K-决策三问",     lambda t: ("方案对比三问" in t) or ("决策怎么下" in t)),
    ("K-任务情境",     lambda t: t.startswith("任务情境")),
    ("K-场景应对",     lambda t: "常见场景应对" in t),
    ("K-关键代码",     lambda t: bool(re.match(r"^\d*\s*关键代码", t))),
    ("K-微课资源",     lambda t: "微课与自学资源" in t),
    ("K-多解法",       lambda t: bool(re.match(r"^\d*\s*多解法一瞥", t))),
    ("K-自测答案",     lambda t: bool(re.match(r"^\d*\s*自测答案", t))),
    ("K-输出对比",     lambda t: bool(re.match(r"^\d*\s*输出对比", t))),
    ("K-知识口袋书",   lambda t: bool(re.match(r"^\d*\s*知识口袋书", t))),
    ("K-答辩预演",     lambda t: "答辩预演" in t),
    ("K-课堂实录",     lambda t: "课堂实录清单" in t),
    ("K-分层卡",       lambda t: bool(re.match(r"^分层工单 · [ABCD] 层任务卡", t))),
    ("K-ABCD总览",     lambda t: bool(re.match(r"^\d*\s*ABCD四层任务总览", t))),
    ("K-实施任务",     lambda t: bool(re.match(r"^\d*\s*实施任务：工单", t))),
]

# 填充页规则（无独有知识，可删）——标题前缀匹配，避免正文含关键词被误伤
FILLER = [
    ("F1-分隔小页",  lambda t: bool(re.match(r"^基础知识\s*B\d+", t))),
    ("F2-即时练习",  lambda t: bool(re.match(r"^课堂即时练习", t))),
    ("F3-章节小结",  lambda t: bool(re.search(r"·\s*小结0\d", t)) or bool(re.match(r"^部分小结", t))),
    ("F4-工具箱",    lambda t: bool(re.match(r"^工具箱[①②③④⑤]", t))),
    ("F5-本课目录",  lambda t: bool(re.match(r"^本课目录", t))),
    ("F6-节奏自查",  lambda t: bool(re.match(r"^80分钟课堂节奏（学生自查）", t))),
    ("F7-知识快闪",  lambda t: bool(re.match(r"^知识快闪", t))),
    ("F8-虚拟产线",  lambda t: "虚拟产线月度数据" in t),
    ("F9-四步法重复", lambda t: bool(re.match(r"^课堂教法：四步法", t))),
    ("F10-时间盒重复", lambda t: bool(re.match(r"^80分钟时间盒分配", t))),
    ("F11-六步法重复", lambda t: bool(re.match(r"^六步法课堂化", t))),
    ("F12-代码走读", lambda t: bool(re.match(r"^\d*\s*代码走读：", t))),
    ("F13-详解讲重复", lambda t: bool(re.match(r"^知识详解（讲）", t))),
    ("F14-深化理解", lambda t: bool(re.match(r"^\d*\s*深化理解：", t))),
    ("F15-分层步骤页", lambda t: bool(re.match(r"^\d*[ABCD]层·", t)) and ("：步骤怎么走" in t)),
]

# V2「课堂投屏」档专用：自学/过程记录类页下架（既有口径"课堂投屏用V2·自学参考用旧版"）
SELFSTUDY = [
    ("S1-进阶路线图", lambda t: "进阶路线图" in t),
    ("S2-达标预期图", lambda t: "本周各层达标预期" in t),
    ("S3-预习清单",  lambda t: "课前预习清单" in t),
    ("S4-知识口袋书", lambda t: bool(re.match(r"^\d*\s*知识口袋书", t))),
    ("S5-输出对比",  lambda t: bool(re.match(r"^\d*\s*输出对比", t))),
    ("S6-课堂实录",  lambda t: "课堂实录清单" in t),
    ("S7-答辩预演",  lambda t: "答辩预演" in t),
    ("S8-微课资源",  lambda t: "微课与自学资源" in t),
    ("S9-场景应对",  lambda t: "常见场景应对" in t),
    ("S10-学习策略", lambda t: bool(re.match(r"^\d*\s*学习策略：", t))),
]
# 上述类别在 V2 档不再作为保护项
SELFSTUDY_KEEP_NAMES = {"K-微课资源", "K-知识口袋书", "K-输出对比", "K-课堂实录", "K-答辩预演", "K-场景应对"}

def analyze(path):
    prs = Presentation(path)
    n = len(prs.slides)
    infos = []
    for i, s in enumerate(prs.slides):
        txts, pic = page_info(s)
        t = clean(txts)
        infos.append(dict(idx=i, txts=txts, t=t, pic=pic, runs=len(txts),
                          cover=is_cover(i, txts, n), thanks=is_thanks(t),
                          preview=is_preview(t), section=is_section(t), shot=is_screenshot(t)))
    return prs, infos

def plan(infos, target, profile="deep"):
    n = len(infos)
    prot = set()
    for p in infos:
        if p["cover"] or p["thanks"] or p["preview"] or p["section"] or p["pic"] or p["shot"]:
            prot.add(p["idx"]); continue
        for name, fn in KEEP:
            if profile == "v2" and name in SELFSTUDY_KEEP_NAMES: continue
            if fn(p["t"]):
                prot.add(p["idx"]); break
    delete = {}   # idx -> reason
    rules = list(FILLER) + (SELFSTUDY if profile == "v2" else [])
    # 1) 填充页
    for p in infos:
        if p["idx"] in prot: continue
        for name, fn in rules:
            if fn(p["t"]):
                delete[p["idx"]] = name; break
    # 2) 结构重复 —— 并查集聚类：同类只留信息最丰富的一页，避免链式误删
    cand = [p for p in infos if p["idx"] not in prot and p["idx"] not in delete and len(p["t"]) >= 15]
    parent = {p["idx"]: p["idx"] for p in cand}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry: parent[rx] = ry
    for a in range(len(cand)):
        for b in range(a+1, len(cand)):
            pa, pb = cand[a], cand[b]
            ta, tb = pa["t"], pb["t"]
            sim = SequenceMatcher(None, ta, tb).ratio()
            ba, bb = bag(ta), bag(tb)
            jac = len(ba & bb)/max(1, len(ba | bb))
            if sim >= 0.55 or (len(ba) >= 4 and len(bb) >= 4 and jac >= 0.5):
                union(pa["idx"], pb["idx"])
    clusters = {}
    for p in cand:
        clusters.setdefault(find(p["idx"]), []).append(p)
    for root, members in clusters.items():
        if len(members) < 2: continue
        members.sort(key=lambda p: (p["runs"], len(p["t"])), reverse=True)
        keep = members[0]
        for m in members[1:]:
            delete[m["idx"]] = f"DUP->p{keep['idx']+1}"
    # 3) 若仍超目标，按信息量删最低的非保护页
    remain = n - len(delete)
    if remain > target:
        pool = [p for p in infos if p["idx"] not in prot and p["idx"] not in delete]
        pool.sort(key=lambda p: (p["runs"], len(p["t"])))
        need = remain - target
        for p in pool[:need]:
            delete[p["idx"]] = "LOW-INFO"
    return delete, prot

def renumber(slide, new_i, new_total):
    for sh in slide.shapes:
        if not sh.has_text_frame: continue
        for para in sh.text_frame.paragraphs:
            for r in para.runs:
                if re.fullmatch(r"\s*\d+\s*/\s*\d+\s*", r.text):
                    r.text = f"{new_i} / {new_total}"

def apply(path, target, out=None, dry=True, profile="deep"):
    prs, infos = analyze(path)
    delete, prot = plan(infos, target, profile)
    n = len(infos); keep = [p["idx"] for p in infos if p["idx"] not in delete]
    print(f"\n=== {os.path.basename(path)}  原{n}页 -> 删{len(delete)} -> 保留{len(keep)}页 (目标{target},档={profile})")
    for i in sorted(delete): print(f"   删 p{i+1:>3} [{delete[i]:<12}] {infos[i]['t'][:40]}")
    if dry: return None
    # 删除
    sldIdLst = prs.slides._sldIdLst
    ids = list(sldIdLst)
    for i in sorted(delete, reverse=True):
        rId = ids[i].get(f"{{{R}}}id")
        prs.part.drop_rel(rId)
        sldIdLst.remove(ids[i])
    # 重编号
    total = len(prs.slides)
    for i, s in enumerate(prs.slides, 1):
        renumber(s, i, total)
    prs.save(out or path)
    print(f"   >> 已保存 {total} 页 -> {out or path}")
    return total

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--target", type=int, default=80)
    ap.add_argument("--profile", default="deep", choices=["deep", "v2"])
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    for f in a.files:
        apply(f, a.target, dry=not a.apply, profile=a.profile)
