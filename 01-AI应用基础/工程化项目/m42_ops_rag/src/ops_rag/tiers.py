# -*- coding: utf-8 -*-
"""工单 M4.2 四档验收判定（纯函数，档位是算出来的、不是自称的）。

门槛逐条取自《M4.2工单-工业智能决策助手系统.md》验收标准：
  及格(D)：正确回答≥5个典型问题；响应清晰可用
  良好(C)：≥7个问题；Prompt对比有结论
  优秀(B)：≥10个问题；RAG链路完整且对比纯LLM有提升
  优(A)  ：达B且：Agent两步推理演示成功；含多轮对话；容错(重试/降级)实测通过
本机无外部 LLM 服务：全部功能门吃 pipeline 对"确定性兜底路径"（本地检索 +
规则/模板回答器）的实测值——"正确回答数"由真实题库跑出、"提升"由两次真实
运行的命中差、"容错通过"由真实注入的断服异常记录。数字门槛外置在
config/rules.yaml 的 tiers: 段。"清晰可用/能口述"不可机器判定 → MANUAL 清单。
"""

TIERS = [
    ("及格(D)", "题库实测正确回答数达标（真实检索命中，非自称）", "D"),
    ("良好(C)", "正确回答数达标 + Prompt 三版真实运行、实测分差有结论", "C"),
    ("优秀(B)", "正确回答数达标 + RAG 链路完整 + 对比纯 LLM 实测有提升", "B"),
    ("优(A)", "达 B 且：Agent 两步推理实测成功；多轮对话实测；容错注入实测通过", "A"),
]
KEYS = ("D", "C", "B", "A")

# 人工答辩项（教师答辩时确认，不自动判达标）——工单原文里的不可机判部分
MANUAL = [
    "响应清晰可用：回答口径经值班师傅现场抽检确认",
    "Prompt 对比结论能口述（为何结构化+引用编号更可用）",
    "Agent「判断→调用工具→汇总」两步推理思路能口述",
]

DEFAULT_GATES = {
    "style": [60.0, 70.0, 80.0, 90.0],
    "D": {"correct_min": 5},
    "C": {"correct_min": 7, "prompt_versions_min": 3},
    "B": {"correct_min": 10, "gain_min": 1},
    "A": {"tools_min": 2, "retry_min": 1},
}


def gates_from(cfg):
    """rules.yaml 的 tiers: 段 → 判定用门槛；缺失键回落 DEFAULT_GATES。"""
    raw = (cfg.raw or {}).get("tiers") or {}
    style = raw.get("style_gates") or DEFAULT_GATES["style"]
    gates = {"style": [float(x) for x in style]}
    for key in ("D", "C", "B", "A"):
        sub = dict(DEFAULT_GATES[key])
        for k, v in (raw.get(key) or {}).items():
            if isinstance(v, bool):
                sub[k] = v
                continue
            try:
                v = float(v)
            except (TypeError, ValueError):
                pass
            sub[k] = v
        gates[key] = sub
    return gates


def verdict(gates, rate, n_correct, n_refuse_ok, versions_run, prompt_gap,
            chain_ok, gain, agent_ok, multi_turn_ok, fault_ok):
    """按 pipeline 实测值给四档判定；每档 = 功能门 + 规范率门，缺一即不达标。

    n_correct: 真实题库实测命中数；n_refuse_ok: 库外问题实测正确拒答数；
    versions_run/prompt_gap: Prompt 三版真实运行数与最优-最差实测分差；
    gain: RAG 命中数 - 纯LLM（无检索上下文）命中数（两次真实运行之差）。
    """
    g = gates
    reaches = {}
    reaches["D"] = (n_correct >= g["D"]["correct_min"])
    reaches["C"] = (reaches["D"] and n_correct >= g["C"]["correct_min"]
                    and versions_run >= g["C"]["prompt_versions_min"]
                    and prompt_gap > 0)
    reaches["B"] = (reaches["C"] and n_correct >= g["B"]["correct_min"]
                    and chain_ok and gain >= g["B"]["gain_min"])
    reaches["A"] = (reaches["B"] and agent_ok and multi_turn_ok and fault_ok)
    out = []
    for i, key in enumerate(KEYS):
        name, need, _ = TIERS[i]
        gate = float(g["style"][i])
        ok = reaches[key] and rate >= gate
        out.append({"tier": name, "gate": gate, "need": need,
                    "functional": bool(reaches[key]),
                    "style_ok": rate >= gate, "pass": ok})
    claimed = next((t["tier"] for t in reversed(out) if t["pass"]),
                   "未达 D 档")
    return {"tiers": out, "claimed": claimed, "gates": g,
            "manual": list(MANUAL),
            "measured": {"n_correct": n_correct, "n_refuse_ok": n_refuse_ok,
                         "versions_run": versions_run,
                         "prompt_gap": round(float(prompt_gap), 4),
                         "chain_ok": bool(chain_ok), "gain": gain,
                         "agent_ok": bool(agent_ok),
                         "multi_turn_ok": bool(multi_turn_ok),
                         "fault_ok": bool(fault_ok)}}


def render_lines(v):
    """把判定渲染成报告行（实测 + 档位判定，进 output/report.txt）。"""
    m = v["measured"]
    head = ("实测达成档位: %s ｜ 题库实测正确回答 %d 个 ｜ 库外正确拒答 %d 个"
            " ｜ Prompt 对比 %d 版(最优分差 %.3f) ｜ RAG-纯LLM 实测提升 %+d 题"
            " ｜ Agent/多轮/容错: %s/%s/%s") % (
        v["claimed"], m["n_correct"], m["n_refuse_ok"], m["versions_run"],
        m["prompt_gap"], m["gain"],
        "OK" if m["agent_ok"] else "缺",
        "OK" if m["multi_turn_ok"] else "缺",
        "OK" if m["fault_ok"] else "缺")
    lines = [head]
    for t in v["tiers"]:
        lines.append("  %-8s 规范率门槛≥%.0f%% [%s] ｜ 功能%s ｜ %s"
                     % (t["tier"], t["gate"],
                        "达标" if t["pass"] else "未达标",
                        "OK" if t["functional"] else "缺", t["need"]))
    lines.append("  人工答辩项 %d 条（不自动判达标，教师答辩时确认）:"
                 % len(v["manual"]))
    lines.extend("    %d. %s" % (i + 1, item)
                 for i, item in enumerate(v["manual"]))
    return lines
