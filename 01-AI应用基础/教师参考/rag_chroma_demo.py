# -*- coding: utf-8 -*-
"""M4.2/M4-2 RAG检索·双解互验（教师演示）——AI16与AI48共用

解A（教学直观）：字符bigram重合度打分 top-k（与 mock_llm_server.retrieve 同源）
解B（工程实现）：ChromaDB向量库（哈希bigram嵌入，零下载离线）top-k

课堂三幕：
  幕1 库内题：两解Top1应一致（原理→工程的可信桥梁）
  幕2 库外题：解A正确返回"查无依据"；解B**必然**返回某个近邻——
        向量库无阈值陷阱（工单"宁说无据、不硬编"思政点的技术根源）
  幕3 升级位：换bge-small-zh真实语义嵌入只改embed()一处（A层任务）

运行: /opt/anaconda3/bin/python rag_chroma_demo.py   → 互验 PASS 才算数
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KB = os.path.join(HERE, "..", "data", "knowledge_base.json")

Q_IN = ["轴承磨损怎么判断", "冷却水温持续偏高", "泵体压力波动原因",
        "轴承温度报警值是多少"]
Q_OUT = ["钢丝绳探伤周期", "龙门吊大车啃轨"]


def tokens(text):
    toks = []
    for r in re.findall(r"[\u4e00-\u9fa5]+|[a-zA-Z0-9.]+", text):
        if re.match(r"[\u4e00-\u9fa5]", r):
            toks += [r[i:i + 2] for i in range(len(r) - 1)] + [r]
        else:
            toks.append(r.lower())
    return set(toks)


def solve_a(query, docs, k=2):
    q = tokens(query)
    scored = sorted(((len(q & tokens(d)) / (len(q) + 1e-6), i)
                     for i, d in enumerate(docs)), reverse=True)
    return [i for s, i in scored[:k] if s > 0]


DIM = 256


def embed(text):
    v = [0.0] * DIM
    for g in tokens(text):
        v[hash(g) % DIM] += 1.0
    n = sum(x * x for x in v) ** 0.5 or 1.0
    return [round(x / n, 6) for x in v]


def build_chroma(docs):
    import chromadb
    from chromadb.api.types import EmbeddingFunction

    class HashEF(EmbeddingFunction):
        def __init__(self):
            super().__init__()

        @staticmethod
        def name():
            return "hash-bigram-zh"

        def __call__(self, input):
            return [embed(t) for t in input]

    client = chromadb.PersistentClient(path=os.path.join(HERE, "_chroma_rag"))
    col = client.get_or_create_collection("kb_demo", embedding_function=HashEF())
    col.upsert(ids=[str(i) for i in range(len(docs))], documents=docs)
    return col


def solve_b(query, docs, col, k=2):
    r = col.query(query_embeddings=[embed(query)], n_results=k)
    return [int(i) for i in r["ids"][0]], r["distances"][0]


if __name__ == "__main__":
    kb = json.load(open(KB, encoding="utf8"))
    docs = [f"{c}｜{it}" for c, items in kb.items() for it in items]
    col = build_chroma(docs)

    print("== 幕1 库内题：双解Top1应一致 ==")
    same = 0
    for q in Q_IN:
        a = solve_a(q, docs)
        b, dists = solve_b(q, docs, col)
        ok = bool(a) and a[0] == b[0]
        same += ok
        print(f"  {'✓' if ok else '✗'} {q:<12} A→{(docs[a[0]][:18] if a else '∅'):<20}"
              f" B→{docs[b[0]][:18]} (d={dists[0]:.2f})")
    assert same == len(Q_IN), f"库内题一致率 {same}/{len(Q_IN)}，双解不可信"
    print(f"  库内 {len(Q_IN)}/{len(Q_IN)} 一致 ✅\n")

    print("== 幕2 库外题：向量库'必返近邻'陷阱 ==")
    for q in Q_OUT:
        a = solve_a(q, docs)
        b, dists = solve_b(q, docs, col)
        assert not a, f"解A对库外题{q}竟有命中，检查KB"
        print(f"  ⚠ {q}: A→∅(正确,宁说无据) | B→{docs[b[0]][:16]}(d={dists[0]:.2f})")
    print("  教学结论：向量库必须配相似度阈值/空结果策略，否则'一本正经胡说'——")
    print("  这正是RAG幻觉治理与工单'有据可查'思政点的技术根源。\n")

    print("== 幕3 升级位（A层） ==")
    print("  把embed()换成bge-small-zh（本地onnx约100MB）——接口不变，召回质量跃升；")
    print("  或加distance阈值（本演示哈希嵌入分辨弱，换真嵌入后阈值才有效）。")
    print("\nRAG双解互验 PASS ✅")
    sys.exit(0)
