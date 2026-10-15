# -*- coding: utf-8 -*-
"""批量问答 → 引用命中统计 → 防幻觉比例报告。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    kb = core.load_kb(list(cfg.items))
    queries = list(cfg.raw.get("queries") or ["泵振动超标要看哪个标准"])
    if isinstance(queries, str):
        queries = [queries]
    topk = int(cfg.topk)
    min_score = float(cfg.raw.get("min_score", 0.05))
    rows, grounded = [], 0
    for q in queries:
        a = core.answer(str(q), kb, topk=topk, min_score=min_score)
        grounded += int(a["grounded"])
        rows.append({"query": str(q), "grounded": a["grounded"],
                     "citations": a["citations"]})
    result = {"n_queries": len(queries), "grounded": grounded,
              "hallucination_rate": 1.0 - grounded / max(len(queries), 1),
              "rows": rows}
    lines = []
    for r in rows:
        if r["grounded"]:
            lines.append("Q: %s" % r["query"])
            lines.append("   → 命中 %d 条: %s" % (
                len(r["citations"]),
                ", ".join(c["id"] for c in r["citations"])))
            lines.append("   最佳分数 %.3f" % r["citations"][0]["score"])
        else:
            lines.append("Q: %s" % r["query"])
            lines.append("   → 查无依据（拒答，未编造）")
    sections = [("输入口径", ["知识库 %d 条｜检索: 二元词重合度(两段式重排)｜Top-%d｜阈值 %.2f"
                % (len(kb), topk, min_score)]),
                ("问答明细", lines),
                ("命中率", ["有据可查 %d / %d（幻觉率 %.0f%%）"
                 % (grounded, len(queries), result["hallucination_rate"] * 100)]),
                ("结论与建议", ["RAG 的底线是'有据可查+诚实拒答'；查无依据的查询用于发现知识库盲区，"
                 "反向驱动知识补录"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections
