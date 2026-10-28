# -*- coding: utf-8 -*-
"""工单 M2.1 四档验收判定（纯函数，档位是算出来的、不是自称的）。

门槛逐条取自《M2.1工单-工业焊接缺陷检测系统.md》四、验收标准：
  及格(D)：准确率≥0.80（四类均衡数据）+跑通训练-评估流程+形状表基本正确
  良好(C)：准确率≥0.85+形状表完整无误
  优秀(B)：准确率≥0.88+完成数据增强（翻转/平移）并对比效果
  优(A)：达 B 且绘制 loss 曲线与混淆矩阵+能解释 1 个典型误判样本
输入全部来自 pipeline 的实测值（真实训练指标、png 文件字节、形状钩子），
verdict 只做比较，不产生新数据——与 w06 同口径，可复核。
工单原文未逐档规定规范率门槛，故档位判定**不含**规范率门（实测规范率
仅进报告作证据）；"能解释误判样本"的口头部分归 manual 人工答辩项，
绝不自动判达标。
"""

TIERS = [
    ("及格(D)", "准确率≥0.80（四类均衡数据）+跑通训练-评估流程+形状表基本正确",
     "d", ("flow", "shape_basic")),
    ("良好(C)", "准确率≥0.85+形状表完整无误", "c", ("flow", "shape_full")),
    ("优秀(B)", "准确率≥0.88+完成数据增强（翻转/平移）并对比效果", "b",
     ("flow", "shape_full", "aug_done")),
    ("优(A)", "达 B 且绘制 loss 曲线与混淆矩阵+能解释 1 个典型误判样本", "b",
     ("flow", "shape_full", "aug_done", "plots_ok", "miss_done")),
]
KEYS = ("D", "C", "B", "A")

# 代码化不了的条目：报告里明列，教师答辩时确认，不参与自动判定
MANUAL = [
    "能解释 1 个典型误判样本的**口头**部分——代码已真实挑出误判样本并打印"
    "其真实标签/预测标签/置信度（见报告『误判样本』段），成因须答辩现场口述",
    "企业元验收：值班师傅签认（功能可用/岗位规范/数据可信，占成绩 30%）",
]


def verdict(gates, m):
    """按实测值给四档判定；每档 = 数值门（准确率）+ 功能门，缺一即不达标。

    gates: {"d":0.80,"c":0.85,"b":0.88}，数字来自 config/rules.yaml tiers 段；
    m: pipeline 实测能力字典——acc（交付臂测试准确率，缺 torch 时为 None）、
       flow/shape_basic/shape_full/aug_done/plots_ok/miss_done 均为实测布尔。
    """
    acc = m.get("acc")
    out = []
    cum = []
    for (name, need, gkey, feats), key in zip(TIERS, KEYS):
        cum = cum + [f for f in feats if f not in cum]
        functional = all(bool(m.get(f)) for f in cum)
        gate = float(gates[gkey])
        acc_ok = acc is not None and float(acc) >= gate
        out.append({"tier": name, "gate": gate, "need": need,
                    "functional": functional, "acc_ok": acc_ok,
                    "pass": bool(functional and acc_ok)})
    claimed = next((t["tier"] for t in reversed(out) if t["pass"]),
                   "未达及格(D)")
    return {"tiers": out, "claimed": claimed, "manual": list(MANUAL),
            "measured": dict(m)}


def _fmt(v, spec="%.4f"):
    """实测值渲染：None 一律显示 MISS（库缺失不许报成"无证据/达标"）。"""
    return spec % v if v is not None else "MISS"


def render_lines(v):
    """把判定渲染成报告行（实测 + 档位判定，进 output/report.txt）。"""
    m = v["measured"]
    lines = ["实测达成档位: %s ｜ 交付臂 %s 实测准确率 %s ｜ 无增强臂 %s"
             "（增强Δ=%s）｜ 形状表实测/期望一致 %s/%s 段 ｜ 误判样本挑出 %d 条"
             " ｜ loss曲线 %sB ｜ 混淆矩阵 %sB"
             % (v["claimed"], m.get("delivered", "-"), _fmt(m.get("acc")),
                _fmt(m.get("acc_noaug")), _fmt(m.get("aug_delta"), "%+.4f"),
                m.get("shape_match", 0), m.get("shape_stages", 0),
                int(m.get("n_miss", 0)), _fmt(m.get("loss_png_bytes"), "%d"),
                _fmt(m.get("cm_png_bytes"), "%d"))]
    for t in v["tiers"]:
        lines.append("  %-8s 准确率门槛≥%.2f [%s] ｜ 功能%s ｜ %s"
                     % (t["tier"], t["gate"],
                        "达标" if t["pass"] else "未达标",
                        "OK" if t["functional"] else "缺", t["need"]))
    sr = _fmt(m.get("style_rate"), "%.1f")
    lines.append("  规范率门槛: 工单 M2.1 四档未规定规范率（原文取值），"
                 "实测规范率 %s%% 仅作证据、不参与档位判定" % sr)
    if m.get("miss_note"):
        lines.append("  MISS 说明: %s" % m["miss_note"])
    lines.append("  人工答辩项 %d 条（教师答辩时口头确认，绝不自动判达标）:"
                 % len(v["manual"]))
    lines.extend("    %d) %s" % (i + 1, s)
                 for i, s in enumerate(v["manual"]))
    return lines
