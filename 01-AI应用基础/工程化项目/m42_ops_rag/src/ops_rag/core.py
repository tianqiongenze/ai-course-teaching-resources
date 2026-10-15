# -*- coding: utf-8 -*-
"""RAG：二元词重合检索 + 两段式（检索→重排）+ 引用生成 + 防幻觉拒答。"""
import re


def bigrams(text):
    """中文二元词集合（完整传入知识库文本，非截断）。"""
    out = set()
    for seg in re.findall(r"[\u4e00-\u9fff]+", str(text)):
        if len(seg) < 2:
            continue
        out |= {seg[i:i + 2] for i in range(len(seg) - 1)}
        out.add(seg)
    return out


def load_kb(items):
    """加载知识库，生成引用编号 R1..Rn（非 dict 项自动跳过）。"""
    kb = []
    items = [d for d in items if isinstance(d, dict)]
    if not items:
        items = [{"category": "规范", "text": "泵类设备振动速度有效值超过4.5mm/s应列入重点监测"},
                 {"category": "规范", "text": "轴承温度报警阈值设定为75℃，达到85℃应立即停机检查"},
                 {"category": "排查", "text": "泵体异响且压力波动：优先排查叶轮堵塞"},
                 {"category": "排查", "text": "电机电流偏高而转速正常：排查轴承磨损"}]
    for i, d in enumerate(items, 1):
        kb.append({"id": "R%d" % i, "category": str(d["category"]),
                   "text": str(d["text"]), "tokens": bigrams(d["text"])})
    return kb


def overlap_index(q_tokens, kb):
    """重叠指数：|Q ∩ K| / |Q|（0 表示完全没有命中）。"""
    if not q_tokens:
        return 0.0
    return len(q_tokens & kb["tokens"]) / len(q_tokens)


def retrieve(query, kb, topk=3, min_score=0.05):
    """两段式：先取候选集，再用学习重叠指数重排。"""
    q = bigrams(query)
    scored = [(overlap_index(q, k), k) for k in kb]
    cand = [s for s in scored if s[0] >= min_score]
    cand.sort(key=lambda x: (-x[0], x[1]["id"]))
    reranked = sorted(cand[: max(topk, 10)], key=lambda x: -x[0])[:topk]
    return [{"id": k["id"], "category": k["category"], "text": k["text"],
             "score": round(s, 4)} for s, k in reranked]


def answer(query, kb, topk=3, min_score=0.05):
    """生成带引用的回答；无命中则拒答（防幻觉）。"""
    hits = retrieve(query, kb, topk, min_score)
    if not hits:
        return {"grounded": False,
                "text": "查无依据：请补充设备编号与测点数据后再检索（宁说无据，不硬编）。",
                "citations": []}
    refs = "\n".join("  [%s] (%s) %s" % (h["id"], h["category"], h["text"]) for h in hits)
    return {"grounded": True,
            "text": "依据知识库：\n%s\n  → 建议：按上述条款执行并回填工单。" % refs,
            "citations": hits}
