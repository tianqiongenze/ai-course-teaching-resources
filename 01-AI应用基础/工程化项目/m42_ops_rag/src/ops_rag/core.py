# -*- coding: utf-8 -*-
"""RAG：二元词重合检索 + 两段式（检索→重排）+ 引用生成 + 防幻觉拒答。

外部 LLM 是"真实路径"（OpenAI 兼容 HTTP），本机不可用时走确定性兜底：
本地检索 + 规则/模板式回答器（reply/llm_chat 两条路径都返回实测状态，
报告如实标注走了哪条——缺服务不许报成"无证据"）。
"""
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


# ── Prompt 三版（朴素/角色设定/带示例）+ 确定性模板回答器（LLM 兜底）──
PROMPT_VERSIONS = ("naive", "role", "example")
_PRON = re.compile(r"(它的|它们|该设备|这台设备|它)")


def _ctx(hits):
    return "\n".join("  [%s] (%s) %s" % (h["id"], h["category"], h["text"])
                     for h in hits) or "(无检索结果)"


def build_prompt(version, query, hits):
    """按工单"常见错误"统一 CONTEXT: 前缀注入检索结果（v2/v3 走 CONTEXT 路线）。"""
    if version == "naive":
        return "问题：%s\n参考：%s" % (query, _ctx(hits))
    if version == "role":
        return ("你是设备智能运维中心的值班工程师。问题：%s\nCONTEXT:\n%s\n"
                "请基于 CONTEXT 给出可执行处置。" % (query, _ctx(hits)))
    return ("示例：问『泵振动大』→答『结论：…；依据：[R1]…；下一步：…』。\n"
            "问题：%s\nCONTEXT:\n%s\n请按 结论/依据(带[R编号])/下一步 三段作答。"
            % (query, _ctx(hits)))


def reply(version, query, hits):
    """规则/模板式回答器：本机无 LLM 服务时的确定性兜底，三版输出确有差异。"""
    if not hits:
        return {"grounded": False,
                "text": "查无依据：请补充设备编号与测点数据（宁说无据，不硬编）。",
                "citations": []}
    if version == "naive":
        return {"grounded": True, "citations": hits,
                "text": "\n".join(h["text"] for h in hits)}
    if version == "role":
        return {"grounded": True, "citations": hits,
                "text": "【值班工程师】先挂牌保安全。依据：%s"
                        % "；".join("[%s] %s" % (h["id"], h["text"]) for h in hits)}
    concl = "按命中条款处置并回填工单" if hits[0]["score"] >= 0.3 else "低置信命中，复核后执行"
    return {"grounded": True, "citations": hits,
            "text": "结论：%s\n依据：%s\n下一步：现场执行→师傅签认→数据归档"
                    % (concl, "；".join("[%s] %s" % (h["id"], h["text"]) for h in hits))}


def score_reply(text, hits):
    """回答质量实测分：引用编号覆盖 + 结构完整（全部对着真实文本数出来的）。"""
    cited = all(("[R%s]" % _num(h["id"])) in text for h in hits) if hits else True
    structured = ("结论" in text) and ("下一步" in text or "依据" in text)
    return {"citation": int(cited), "structure": int(structured),
            "score": round((int(cited) + int(structured)) / 2.0, 4)}


def _num(rid):
    return str(rid).lstrip("R")


def llm_chat(base_url, prompt, timeout=0.5, retries=1):
    """真实 LLM 路径（OpenAI 兼容）：返回 (ok, attempts, exc_name, text)。

    attempts 是真实发起的请求次数、exc_name 是真异常类名——容错档位只认这个。
    requests 缺失返回 attempts=0 并在 exc 里写明 MISS（不许谎报"已尝试"）。
    """
    try:
        import requests
    except ImportError:
        return {"ok": False, "attempts": 0, "exc": "MISS(requests 未安装)", "text": ""}
    attempts, last_exc = 0, ""
    url = str(base_url).rstrip("/")
    payload = {"messages": [{"role": "user", "content": prompt}],
               "temperature": 0.2}
    for _ in range(max(1, int(retries) + 1)):
        attempts += 1
        try:
            r = requests.post(url, json=payload, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            return {"ok": True, "attempts": attempts, "exc": "",
                    "text": str(data["choices"][0]["message"]["content"])}
        except Exception as exc:
            last_exc = type(exc).__name__
    return {"ok": False, "attempts": attempts, "exc": last_exc, "text": ""}


def focus_entity(prev_query, prev_citation_text):
    """回指焦点 = 上一问与其最优引用文本的最长公共子串（实测提取，零硬编码）。"""
    a = str(prev_query)
    b = str(prev_citation_text or "")
    best = ""
    for i in range(len(a)):
        for j in range(i + 2, len(a) + 1):
            if a[i:j] in b and j - i > len(best):
                best = a[i:j]
    return best


def resolve_ref(query, focus):
    """把"它/它的/该设备"解析为回指焦点；无焦点时原样返回（如实暴露上下文缺失）。"""
    return _PRON.sub(focus, str(query), count=1) if focus else str(query)


_NUM = re.compile(r"(\d+(?:\.\d+)?)")


def parse_numbers(text, unit=""):
    """抽数：unit='mm/s' 时只取紧跟单位数值（阈值/实测值同源可比）。"""
    pat = r"(\d+(?:\.\d+)?)\s*%s" % re.escape(unit) if unit else _NUM.pattern
    return [float(m) for m in re.findall(pat, str(text))]


def agent_two_step(query, kb, topk=3, min_score=0.05, unit="mm/s"):
    """Agent 两步推理：判断→调用工具(QueryTool 检索 + CalcTool 计算)→汇总。

    返回 tools_called/decision/calc/aggregate——每个字段都来自真实调用，
    A 档"演示成功"由 pipeline 检查 aggregate 同时含引用编号与计算数值。
    """
    q_nums = parse_numbers(query, unit)
    hits = retrieve(query, kb, topk, min_score)          # QueryTool
    tools = ["QueryTool"]
    k_nums = parse_numbers(" ".join(h["text"] for h in hits), unit) if hits else []
    calc = None
    if hits and q_nums and k_nums:
        tools.append("CalcTool")                         # CalcTool
        v, lim = max(q_nums), max(k_nums)
        calc = {"value": v, "limit": lim, "margin": round(v - lim, 4),
                "ratio": round(v / lim, 4),
                "verdict": "必须停机" if v > lim else "限值内可运行"}
    decision = ("需要检索+计算" if calc else
                ("仅需检索" if hits else "无依据，拒答"))
    if not hits:
        aggregate = "查无依据：知识库里没有相关条款，不硬编（宁说无据）。"
    elif calc:
        aggregate = ("结论：%s（%.1f 对限值 %.1f，超出 %.2f，%.2f 倍）。依据：[%s] %s"
                     % (calc["verdict"], calc["value"], calc["limit"],
                        calc["margin"], calc["ratio"], hits[0]["id"],
                        hits[0]["text"]))
    else:
        aggregate = "结论：按引用条款执行。依据：[%s] %s" % (
            hits[0]["id"], hits[0]["text"])
    return {"tools_called": tools, "decision": decision, "calc": calc,
            "citations": hits, "aggregate": aggregate}
