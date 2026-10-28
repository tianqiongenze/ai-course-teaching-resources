# -*- coding: utf-8 -*-
"""工单 M3.2 四档验收判定（纯函数，档位是算出来的、不是自称的）。

门槛逐条取自《M3.2工单-产线实时缺陷检测系统》验收标准：
  及格(D)：完成CPU推理与可视化（实物照+缺陷图）；阈值实验记录完整
  良好(C)：三档imgsz的FPS对比完整；选定配置有依据
  优秀(B)：自选配置较默认imgsz=640提速≥50%且检出稳定；权衡分析有条理
  优(A)：达B且：batch/多线程/输入裁剪等优化并量化提升
本机无 ultralytics：推理走"兜底口径"——cv2 基线全链路真计时为主路，
onnxruntime+离线 yolov8n.onnx 可用时同步给出真实 YOLO CPU 推理实测；
判定吃的全部是本次运行真实测出的 fps/提速比/检出数，兜底路径在报告
里标明。实物照缺失、"权衡分析有条理"等判不到的条目一律进人工答辩项。
数字外置于 config/rules.yaml 的 tiers: 段；本工单未逐档设规范率门槛，
规范率只作实测展示、不构成档位门。
"""

KEYS = ("D", "C", "B", "A")
TIERS = [
    ("及格(D)", "阈值实验≥%d档+可视化落盘", "CPU推理+可视化（实物照缺失→人工项）；阈值实验记录完整"),
    ("良好(C)", "三档imgsz实测+选定有依据", "三档imgsz的FPS对比完整；选定配置可由实测表复算"),
    ("优秀(B)", "较640提速≥%.0f%%且检出稳定", "自选配置提速≥50%（两次真实计时相除）且复跑检出恒定"),
    ("优(A)", "优化实测提速≥%.0f%%", "达B且：输入裁剪/多线程等优化落地并量化提升"),
]
DEFAULT_GATES = {"d_conf_levels": 4, "d_min_vis_png": 2, "c_imgsz_levels": 3,
                 "b_speedup_pct": 50.0, "b_stable_runs": 3,
                 "a_opt_gain_pct": 5.0, "png_min_bytes": 1000,
                 "fps_min": 0.34, "iou_match": 0.3}
MANUAL = [
    "实物照检测：学生手机拍键盘/鼠标/水杯跑通推理（本机无实物照片，"
    "实测记 MISS，教师答辩时检查提交物）",
    "预训练权重对合成工业缺陷'零检出'现象的讨论（领域不匹配→微调动机）",
    "'精度-速度'权衡分析的条理性（决策矩阵填写+口述依据）",
    "企业元签认：功能可用/岗位规范/数据可信",
]


def _gates(gates):
    """rules.yaml 的 tiers: 段缺项时回落工单原文数字，不静默吞掉。"""
    g = dict(DEFAULT_GATES)
    g.update(gates or {})
    return g


def verdict(gates, m):
    """按实测值给四档判定；高档依赖低档（工单 A 档原文"达B且"）。

    m 各键均为本次运行真实测得：推理调用数、阈值档数、标注图要素、
    三档 fps、选定配置复算一致位、提速比、复跑稳定标记、优化增益。
    """
    g = _gates(gates)
    func = {
        "D": (m["infer_calls"] >= m["imgs_total"] and m["conf_levels"] >=
              int(g["d_conf_levels"]) and m["vis_valid"] >= g["d_min_vis_png"]),
        "C": (m["fps_levels"] >= int(g["c_imgsz_levels"])
              and all(v > 0 for v in m["fps_values"].values())
              and bool(m["basis_ok"])),
        "B": (m["speedup_pct"] >= float(g["b_speedup_pct"])
              and bool(m["stable_ok"])),
        "A": (bool(m["opt_impl"])
              and m["opt_gain_pct"] >= float(g["a_opt_gain_pct"])),
    }
    fmt = {
        "D": (g["d_conf_levels"],),
        "C": (),
        "B": (g["b_speedup_pct"],),
        "A": (g["a_opt_gain_pct"],),
    }
    out, prev = [], True
    for (name, gate_fmt, need), key in zip(TIERS, KEYS):
        ok = prev and bool(func[key])
        prev = ok
        gate = (gate_fmt % fmt[key]) if "%" in gate_fmt else gate_fmt
        out.append({"tier": name, "key": key, "need": need, "gate": gate,
                    "functional": bool(func[key]), "pass": ok})
    claimed = next((t["tier"] for t in reversed(out) if t["pass"]), "未达 D 档")
    keep = ("infer_calls", "imgs_total", "conf_levels", "vis_valid",
            "fps_levels", "fps_values", "chosen", "speedup_pct",
            "stable_ok", "opt_name", "opt_gain_pct", "opt_impl",
            "onnx_status", "real_photo_status")
    return {"tiers": out, "claimed": claimed,
            "measured": {k: m[k] for k in keep if k in m},
            "gates": g, "manual": list(MANUAL)}


def render_lines(v):
    """把判定渲染成报告行（实测 + 档位判定，进 output/report.txt）。"""
    m = v["measured"]
    fps = m.get("fps_values", {})
    fps_txt = " ".join("%d:%.1f" % (k, fps[k]) for k in sorted(fps))
    lines = ["实测达成档位: %s ｜ 推理路线: cv2基线(兜底口径)实测 %d 次调用 ｜ "
             "YOLO-ONNX路线: %s ｜ 实测FPS %s ｜ 选定 imgsz=%s 较640提速 %.0f%% ｜ "
             "%s优化实测 +%.0f%% ｜ 阈值 %d 档 ｜ 合格可视化图 %d 张 ｜ 实物照: %s"
             % (v["claimed"], m.get("infer_calls", 0),
                m.get("onnx_status", "MISS"), fps_txt, m.get("chosen", "-"),
                m.get("speedup_pct", 0.0), m.get("opt_name", "无"),
                m.get("opt_gain_pct", 0.0), m.get("conf_levels", 0),
                m.get("vis_valid", 0), m.get("real_photo_status", "MISS"))]
    for t in v["tiers"]:
        lines.append("  %-8s 门槛 %s [%s] ｜ 功能%s ｜ %s"
                     % (t["tier"], t["gate"],
                        "达标" if t["pass"] else "未达标",
                        "OK" if t["functional"] else "缺", t["need"]))
    lines.append("  注: 本工单未逐档设代码规范率门槛 → 规范率仅作实测展示；"
                 "实物照/讨论/条理性等判不到的条目一律进下方人工答辩项。")
    return lines


def render_manual(v):
    """人工答辩项清单——绝不自动判达标，教师答辩时逐条确认。"""
    lines = ["人工答辩项 %d 条，教师答辩时确认:" % len(v["manual"])]
    lines.extend("  [%02d] %s" % (i + 1, s) for i, s in enumerate(v["manual"]))
    return lines
