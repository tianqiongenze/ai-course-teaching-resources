# -*- coding: utf-8 -*-
"""工单 M4.1 四档验收判定（纯函数，档位是算出来的、不是自称的）。

门槛逐条取自《M4.1工单-工业故障报告自动分类系统.md》验收标准：
  及格(D)：准确率≥0.75；能预测新文本
  良好(C)：准确率≥0.80；两分类器对比完整
  优秀(B)：准确率≥0.85；关键词贡献解释清晰
  优(A)  ：达B且：混淆矩阵分析（哪两类易混、为何）；自建词典或ngram调优
数字（0.75/3/2 等）外置在 config/rules.yaml 的 tiers: 段，本模块只留文案
与比较逻辑；档位语义按"达B"原文取累积制——高档含低档全部功能门。
"解释清晰/为何易混/口述"无法机器判定 → 归 MANUAL 清单，绝不自动判达标。
"""

TIERS = [
    ("及格(D)", "准确率≥门槛 + 库外新文本实测预测命中", "D"),
    ("良好(C)", "准确率≥门槛 + 朴素贝叶斯/逻辑回归同切分对比完整", "C"),
    ("优秀(B)", "准确率≥门槛 + 每类 Top10 关键词表全类覆盖", "B"),
    ("优(A)", "达 B 且：混淆矩阵实测定位最易混类对；自建词典+ngram 实测调优", "A"),
]
KEYS = ("D", "C", "B", "A")

# 人工答辩项（教师答辩时确认，不自动判达标）——工单原文里的不可机判部分
MANUAL = [
    "关键词贡献解释清晰：能指出决定「电气系统」类的关键词并口述依据",
    "混淆矩阵「为何易混」归因分析（共用词/工况相似）可口述",
    "决策矩阵权衡（准确率/训练速度/可解释性）能口述",
]

DEFAULT_GATES = {
    "style": [60.0, 70.0, 80.0, 90.0],
    "D": {"acc_min": 0.75, "new_min": 3, "match_min": 2},
    "C": {"acc_min": 0.80, "models_min": 2},
    "B": {"acc_min": 0.85, "topk": 10},
    "A": {"confusion": True, "tuning": True},
}


def gates_from(cfg):
    """rules.yaml 的 tiers: 段 → 判定用门槛；缺失键回落 DEFAULT_GATES 便于离线跑。"""
    raw = (cfg.raw or {}).get("tiers") or {}
    style = raw.get("style_gates") or DEFAULT_GATES["style"]
    gates = {"style": [float(x) for x in style]}
    for key in ("D", "C", "B", "A"):
        sub = dict(DEFAULT_GATES[key])
        for k, v in (raw.get(key) or {}).items():
            if isinstance(v, bool):        # 布尔开关门（confusion/tuning）原样保留
                sub[k] = v
                continue
            try:
                v = float(v)
            except (TypeError, ValueError):
                pass
            sub[k] = v
        gates[key] = sub
    return gates


def verdict(gates, rate, acc, n_new, new_match, n_models,
            kw_classes, n_classes, cm, tuning_done, tune_delta):
    """按 pipeline 实测值给四档判定；每档 = 功能门 + 规范率门，缺一即不达标。

    acc: 终模型（含调优）测试集实测准确率；n_new/new_match: 库外新文本
    实测预测条数/命中条数；cm: confusion_pair() 的实测返回；
    tune_delta: 调优前后实测准确率差（仅报告展示，不设提升门——工单只要求"调优"）。
    """
    g = gates
    pair_ok = bool(cm and cm.get("top_pair"))
    reaches = {}
    reaches["D"] = (acc >= g["D"]["acc_min"] and n_new >= g["D"]["new_min"]
                    and new_match >= g["D"]["match_min"])
    reaches["C"] = (reaches["D"] and acc >= g["C"]["acc_min"]
                    and n_models >= g["C"]["models_min"])
    reaches["B"] = (reaches["C"] and acc >= g["B"]["acc_min"]
                    and kw_classes >= n_classes)
    reaches["A"] = (reaches["B"] and bool(g["A"].get("confusion"))
                    and pair_ok and tuning_done and bool(g["A"].get("tuning")))
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
            "measured": {"acc": acc, "n_new": n_new, "new_match": new_match,
                         "n_models": n_models, "kw_classes": kw_classes,
                         "n_classes": n_classes, "pair": (cm or {}).get("top_pair"),
                         "cm_method": (cm or {}).get("method"),
                         "tuning_done": bool(tuning_done),
                         "tune_delta": tune_delta}}


def render_lines(v):
    """把判定渲染成报告行（实测 + 档位判定，进 output/report.txt）。"""
    m = v["measured"]
    pair = m["pair"]
    if pair:
        args = (pair["true"], pair["other"], pair["count"], m["cm_method"])
        pair_txt = "%s↔%s×%d（%s）" % args
    else:
        pair_txt = "无实测混淆对"
    head = ("实测达成档位: %s ｜ 终模型准确率 %.4f ｜ 库外新文本预测 %d 条(命中 %d)"
            " ｜ 对比模型 %d 个 ｜ 关键词覆盖 %d/%d 类 ｜ 易混类对: %s"
            " ｜ 调优Δacc %+.4f") % (
        v["claimed"], m["acc"], m["n_new"], m["new_match"], m["n_models"],
        m["kw_classes"], m["n_classes"], pair_txt, m["tune_delta"])
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
