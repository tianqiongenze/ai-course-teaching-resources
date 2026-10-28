# -*- coding: utf-8 -*-
"""工单 M2.2 四档验收判定（纯函数，档位是算出来的、不是自称的）。

门槛逐条取自《M2.2工单-轴承寿命预测系统.md》四、验收标准：
  及格(D)：MSE<0.15 + 完成预测与可视化
  良好(C)：MSE≤0.12 + 对照基线说明 LSTM 增益
  优秀(B)：MSE<0.10 + 对比≥2 种模型并解读
  优(A)：达 B 且预测曲线有拐点分析 + 对窗口长度做敏感性实验
输入全部来自 pipeline 的实测值（各模型留出集 MSE、png 字节、拐点数值、
敏感性表），verdict 只做比较，不产生新数据。D/B 用严格小于、C 用小于等
于——比较符号照抄工单原文，不做"顺手放宽"。
档位是递进制：高档累计低档功能条件（工单 A 档原文"达B且"就是这个口径），
所以删掉任一低档能力，承诺档位必然随之下降。
工单原文未逐档规定规范率门槛 → 档位判定不含规范率门（勿自创 M1.1 量表线），
实测规范率只进报告作证据；"解读/说明"的口头答辩部分归 manual，
绝不自动判达标。
"""

TIERS = [
    ("及格(D)", "MSE<0.15+完成预测与可视化", "d", "<",
     ("pred_ok", "viz_ok")),
    ("良好(C)", "MSE≤0.12+对照基线说明 LSTM 增益", "c", "<=",
     ("pred_ok", "viz_ok", "gain_ok")),
    ("优秀(B)", "MSE<0.10+对比≥2 种模型并解读", "b", "<",
     ("pred_ok", "viz_ok", "gain_ok", "multi_model")),
    ("优(A)", "达 B 且预测曲线有拐点分析+对窗口长度做敏感性实验", "b", "<",
     ("pred_ok", "viz_ok", "gain_ok", "multi_model", "knee_ok", "sens_ok")),
]
KEYS = ("D", "C", "B", "A")

# 代码化不了的条目：报告里明列，教师答辩时确认，不参与自动判定
MANUAL = [
    "『对照基线说明 LSTM 增益』『对比≥2 种模型并解读』的口头部分——"
    "代码已实测各模型 MSE/RMSE/MAE 并自动生成数字对照表与增益解读行，"
    "增益原因的现场口述须答辩确认",
    "『拐点分析』的业务含义口述（拐点位置/斜率突变数值已由代码实测并标注"
    "在预测曲线图上）与『RMSE→维护提前量』80 字业务解读的现场问答",
    "预测曲线图是否清晰可读（真值/预测两条线、拐点竖线与图例能否一眼读懂）"
    "教师目检——机检只认落盘字节数（工单未给字节下限，那个数字只是判"
    "『非空白图』的兜底口径，不是工单数字），清晰度判不了就只能目检",
    "企业元验收：值班师傅签认（功能可用/岗位规范/数据可信，占成绩 30%）",
]


def _cmp(op, mse, gate):
    """比较符号照工单原文：D/B 严格小于，C 小于等于。"""
    if op == "<=":
        return mse <= gate
    return mse < gate


def verdict(gates, m):
    """按实测值给四档判定；每档 = 数值门（MSE）+ 功能门，缺一即不达标。

    gates: {"d":0.15,"c":0.12,"b":0.10}，数字来自 config/rules.yaml tiers 段；
    m: pipeline 实测能力字典——mse（交付模型留出集实测 MSE，torch 缺失时
    用兜底交付模型并带 miss_note）、pred_ok/viz_ok/gain_ok/multi_model/
    knee_ok/sens_ok 均为实测布尔。
    """
    mse = m.get("mse")
    out = []
    cum = []
    for (name, need, gkey, op, feats), key in zip(TIERS, KEYS):
        cum = cum + [f for f in feats if f not in cum]
        functional = all(bool(m.get(f)) for f in cum)
        gate = float(gates[gkey])
        num_ok = mse is not None and _cmp(op, float(mse), gate)
        out.append({"tier": name, "key": key, "gate": gate, "op": op,
                    "need": need, "functional": functional, "num_ok": num_ok,
                    "pass": bool(functional and num_ok)})
    claimed = next((t["tier"] for t in reversed(out) if t["pass"]),
                   "未达及格(D)")
    return {"tiers": out, "claimed": claimed, "manual": list(MANUAL),
            "measured": dict(m)}


def _fmt(v, spec="%.6f"):
    """实测值渲染：None 一律显示 MISS（库缺失不许报成"无证据"）。"""
    return "MISS" if v is None else spec % v


def render_lines(v):
    """把判定渲染成报告行（实测 + 档位判定，进 output/report.txt）。"""
    m = v["measured"]
    head = "实测达成档位: %s ｜ 交付模型 %s 实测 MSE %s ｜ 线性基线 MSE %s"
    mid = "（LSTM 增益 Δ=%s）｜ 实测模型 %d 种 ｜ 拐点实测于第 %s 窗口 ｜ "
    tail = "窗口敏感性 %s 档 ｜ 预测曲线 %sB ｜ 敏感性图 %sB"
    lines = [(head + mid + tail) % (
        v["claimed"], m.get("delivered", "-"), _fmt(m.get("mse")),
        _fmt(m.get("mse_baseline")), _fmt(m.get("gain"), "%+.6f"),
        int(m.get("n_models", 0)), _fmt(m.get("knee_idx"), "%d"),
        _fmt(m.get("n_windows"), "%d"), _fmt(m.get("curve_png_bytes"), "%d"),
        _fmt(m.get("sens_png_bytes"), "%d"))]
    for t in v["tiers"]:
        lines.append("  %-8s MSE 门槛%s%.2f [%s] ｜ 功能%s ｜ %s"
                     % (t["tier"], t["op"], t["gate"],
                        "达标" if t["pass"] else "未达标",
                        "OK" if t["functional"] else "缺", t["need"]))
    sr = _fmt(m.get("style_rate"), "%.1f")
    lines.append("  规范率门槛: 工单 M2.2 四档未规定规范率（原文取值），"
                 "实测规范率 %s%% 仅作证据、不参与档位判定" % sr)
    if m.get("miss_note"):
        lines.append("  MISS 说明: %s" % m["miss_note"])
    lines.append("  人工答辩项 %d 条（教师答辩时口头确认，绝不自动判达标）:"
                 % len(v["manual"]))
    lines.extend("    %d) %s" % (i + 1, s)
                 for i, s in enumerate(v["manual"]))
    return lines
