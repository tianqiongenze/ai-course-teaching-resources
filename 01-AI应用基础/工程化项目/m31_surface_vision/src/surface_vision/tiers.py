# -*- coding: utf-8 -*-
"""工单 M3.1 四档验收判定（纯函数，档位是算出来的、不是自称的）。

门槛逐条取自《M3.1工单-产品表面缺陷尺寸测量系统》验收标准：
  及格(D)：正确检出并标注缺陷；测量误差<10%
  良好(C)：误差<8%；两种阈值策略对比记录完整
  优秀(B)：误差<5%；结果图美观清晰（框+文字+图例）——机检只认
           "框数/文字数/图例存在/文件字节数"，主观美观归人工答辩
  优(A)：达B且：多缺陷件全部检出；误检率=0 并分析成因
输入全部来自 pipeline 的实测值（真值复算误差、png 落盘字节、
多缺陷件 IoU 匹配计数），verdict 只做比较，不产生新数据。
误差门槛数字外置于 config/rules.yaml 的 tiers: 段（改配置不改代码）；
本工单未逐档写"代码规范率"门槛，故规范率只作实测展示、不进档位门。
"""

KEYS = ("D", "C", "B", "A")
TIERS = [
    ("及格(D)", "测量误差<%.0f%%", "正确检出并标注缺陷；测量误差<10%"),
    ("良好(C)", "测量误差<%.0f%%", "误差达标；两种阈值策略对比记录完整"),
    ("优秀(B)", "测量误差<%.0f%%", "误差达标；结果图清晰（框+文字+图例，机检要素计数）"),
    ("优(A)", "多缺陷件全检出且误检=0", "达B且：多缺陷件全部检出；误检率=0 并分析成因"),
]
DEFAULT_GATES = {"d_err_pct": 10.0, "c_err_pct": 8.0, "b_err_pct": 5.0,
                 "d_min_png": 1, "b_min_png": 3, "iou_match": 0.3,
                 # 工单只写"结果图清晰"，未给字节下限；1000B 是判"非空白图"的
                 # 兜底口径（不是工单数字），报告中已如实标注。
                 "png_min_bytes": 1000}
MANUAL = [
    "结果图整体美观度（配色/标注疏密）教师目检",
    "像素当量换算能口述：面积=px×0.1²mm²、长度=px×0.1mm",
    "误检成因分析的定性深度（答辩口头展开）",
    "企业元签认：功能可用/岗位规范/数据可信",
]


def _gates(gates):
    """rules.yaml 的 tiers: 段缺项时回落工单原文数字，不静默吞掉。"""
    g = dict(DEFAULT_GATES)
    g.update(gates or {})
    return g


def verdict(gates, m):
    """按实测值给四档判定；高档依赖低档（工单 A 档原文"达B且"）。

    m 各键均为 pipeline 本次运行真实测得：误差百分比、检出件数、
    标注图要素计数、两策略对比记录、多缺陷件匹配与误检统计。
    """
    g = _gates(gates)
    err = float(m["err_mean"])
    png_ok = int(m["png_valid"])
    func = {
        "D": (m["parts_detected"] == m["parts_total"] and err < g["d_err_pct"]
              and png_ok >= g["d_min_png"]),
        "C": err < g["c_err_pct"] and bool(m["cmp_ok"]),
        "B": err < g["b_err_pct"] and png_ok >= g["b_min_png"],
        "A": (m["multi_detected"] == m["multi_total"] and m["fp_count"] == 0
              and bool(m["cause_ok"])),
    }
    out, prev = [], True
    err_gate = {"D": g["d_err_pct"], "C": g["c_err_pct"], "B": g["b_err_pct"]}
    for (name, gate_fmt, need), key in zip(TIERS, KEYS):
        ok = prev and bool(func[key])
        prev = ok
        gate = (gate_fmt % err_gate[key]) if key in err_gate else gate_fmt
        out.append({"tier": name, "key": key, "need": need, "gate": gate,
                    "functional": bool(func[key]), "pass": ok})
    claimed = next((t["tier"] for t in reversed(out) if t["pass"]), "未达 D 档")
    meas = {k: m[k] for k in ("err_mean", "err_max", "parts_total",
                              "parts_detected", "png_valid", "png_total",
                              "multi_total", "multi_detected", "fp_count",
                              "noise_filtered", "cmp_ok", "cause_ok")}
    return {"tiers": out, "claimed": claimed, "measured": meas,
            "gates": g, "manual": list(MANUAL)}


def render_lines(v):
    """把判定渲染成报告行（实测 + 档位判定，进 output/report.txt）。"""
    m = v["measured"]
    lines = ["实测达成档位: %s ｜ 实测平均误差 %.2f%%（最大 %.2f%%）｜ "
             "检出 %d/%d 件 ｜ 合格标注图 %d/%d 张 ｜ 多缺陷件检出 %d/%d ｜ "
             "误检 %d 个 ｜ 剔除噪点 %d 个"
             % (v["claimed"], m["err_mean"], m["err_max"], m["parts_detected"],
                m["parts_total"], m["png_valid"], m["png_total"],
                m["multi_detected"], m["multi_total"], m["fp_count"],
                m["noise_filtered"])]
    for t in v["tiers"]:
        lines.append("  %-8s 门槛 %s [%s] ｜ 功能%s ｜ %s"
                     % (t["tier"], t["gate"],
                        "达标" if t["pass"] else "未达标",
                        "OK" if t["functional"] else "缺", t["need"]))
    lines.append("  注: 本工单未逐档设代码规范率门槛 → 规范率仅作实测展示，"
                 "不构成档位条件；判不到的条目一律进下方人工答辩项。")
    lines.append("  注: 「结果图清晰」的实测口径 = 框/文字/图例要素计数齐备 + "
                 "字节≥%d（工单未给字节下限，此值为『非空白图』兜底口径，"
                 "不是工单数字）；整体美观度属人工答辩项。"
                 % int(v["gates"]["png_min_bytes"]))
    return lines


def render_manual(v):
    """人工答辩项清单——绝不自动判达标，教师答辩时逐条确认。"""
    lines = ["人工答辩项 %d 条，教师答辩时确认:" % len(v["manual"])]
    lines.extend("  [%02d] %s" % (i + 1, s) for i, s in enumerate(v["manual"]))
    return lines
