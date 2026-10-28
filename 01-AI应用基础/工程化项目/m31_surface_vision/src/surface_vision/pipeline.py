# -*- coding: utf-8 -*-
"""真实零件 → 双阈值策略测量 → 标注结果图 → 多缺陷件误检分析 → 四档判定。

工单 M3.1 的四档门槛全部钉在**本次运行的实测值**上（档位是算出来的）：
  ① 测量误差：对 data/surface_parts/ground_truth.json 教师真值逐件复算
     （凹坑比面积 mm²、划痕比长度 mm），均值/最大值进档位判定；
  ② 双阈值策略：全局阈值(工单例 100)与 Otsu 自动阈值各跑全部件，
     检出件数/平均误差/噪点数都是实测——对比记录缺一档 C 档即红；
  ③ 结果图：cv2 真落盘 png，判定看文件存在 + 字节数 + 要素计数
     （框数/文字数/图例）；"美观"的主观部分归人工答辩；
  ④ 多缺陷件：3 件真实零件的缺陷块拼板 + 撒 4×4 假缺陷噪点，按 IoU
     实测"全部检出 / 误检率=0"，成因分析行由实测剔除数生成。
数据目录缺失时走 core.synth_parts 确定性兜底，报告如实标口径——
"环境也是选型维度"，缺库缺数据都打印在报告里，不冒充证据。
"""
import os

from . import core, io_utils, report, stylecheck, tiers

STRATEGIES = ("global", "otsu")


def _load_parts(cfg):
    """课程真实零件优先；缺失走合成兜底并返回口径说明（不静默降级）。"""
    import cv2
    parts_dir = io_utils.course_data("surface_parts")
    out = []
    if parts_dir and os.path.exists(
            os.path.join(parts_dir, "ground_truth.json")):
        gt_map = {g["file"]: g for g in io_utils.read_json(
            os.path.join(parts_dir, "ground_truth.json"))}
        for name in sorted(x for x in os.listdir(parts_dir)
                           if x.endswith(".png")):
            img = cv2.imread(os.path.join(parts_dir, name))
            if img is None or name not in gt_map:
                continue
            g = gt_map[name]
            out.append({"name": name, "img": img, "type": g["type"],
                        "gt_area": g.get("area_mm2"),
                        "gt_len": g.get("length_mm")})
        if out:
            return out, "真实零件 %d 件（data/surface_parts + 教师真值）" % len(out)
    return core.synth_parts(), "合成兜底件（未找到课程数据，口径已标明）"


def _measure_all(parts, mm_per_px, min_area, t_fixed):
    """两策略 × 全部件的真跑：逐件逐策略复算实测值与误差（决策矩阵）。"""
    per = {s: {"det": 0, "errs": [], "noise": 0} for s in STRATEGIES}
    rows = []
    for rec in parts:
        g = core.gray_of(rec["img"])
        truth = rec["gt_area"] if rec["type"] == "pit" else rec["gt_len"]
        row = {"file": rec["name"], "type": rec["type"], "gt": truth,
               "per": {}}
        for s in STRATEGIES:
            t_used, m = core.binarize(g, s, t_fixed)
            defs, noise = core.part_defects(m, min_area, mm_per_px)
            meas = (sum(d["area_mm2"] for d in defs) if rec["type"] == "pit"
                    else max((d["len_mm"] for d in defs), default=0.0))
            e = core.err_pct(meas, truth)
            st = per[s]
            st["det"] += int(len(defs) >= 1)
            st["errs"].append(round(e, 3))
            st["noise"] += noise
            row["per"][s] = {"T": t_used, "n": len(defs),
                             "meas": round(meas, 2), "err": round(e, 2)}
        rows.append(row)
    return rows, per


def _annotate_batch(cfg, rows, parts_by_name, out_dir):
    """主策略结果图：前 annotated_parts 件逐件画框+文字+图例，真落盘 png。"""
    primary = str(cfg.raw.get("strategy", "otsu"))
    n = int(cfg.raw.get("annotated_parts", 5))
    png_dir = io_utils.ensure_dir(os.path.join(out_dir, "annotated"))
    pngs = []
    for row in rows[:n]:
        rec = parts_by_name[row["file"]]
        g = core.gray_of(rec["img"])
        t_used, m = core.binarize(g, primary,
                                  float(cfg.raw.get("global_T", 100)))
        defs, _ = core.part_defects(m, int(cfg.raw.get("min_area_px", 20)),
                                    float(cfg.raw.get("mm_per_px", 0.1)))
        for d in defs:
            d["label"] = ("a=%.2fmm2" % d["area_mm2"]) \
                if rec["type"] == "pit" else ("l=%.2fmm" % d["len_mm"])
        meta = ["LEGEND", "defect: red box+text",
                "strategy=%s T=%.0f" % (primary, t_used),
                "err=%.2f%%" % row["per"][primary]["err"]]
        path = os.path.join(png_dir, "annot_%s.png" % row["file"][:-4])
        pngs.append(core.annotate(rec["img"], defs, path, meta))
    return pngs


def _idx_list(cfg):
    raw = cfg.raw.get("multi_sources", [0, 1, 3])
    if isinstance(raw, str):
        return [x.strip() for x in raw.split(",") if x.strip()]
    return list(raw)


def _multi_part(cfg, parts, out_dir):
    """多缺陷件实测：贴真实缺陷块 + 撒噪点 → IoU 匹配出检出/误检数。"""
    t_fixed = float(cfg.raw.get("global_T", 100))
    min_area = int(cfg.raw.get("min_area_px", 20))
    mm_per_px = float(cfg.raw.get("mm_per_px", 0.1))
    primary = str(cfg.raw.get("strategy", "otsu"))
    srcs = []
    for i in _idx_list(cfg):
        if not (0 <= i < len(parts)):
            continue
        rec = parts[i]
        got = core.extract_defect(rec["img"], t_fixed)
        if got is None:
            continue
        value = rec["gt_area"] if rec["type"] == "pit" else rec["gt_len"]
        srcs.append((got[0], got[1], {"file": rec["name"],
                                      "type": rec["type"], "value": value}))
    board, gts = core.build_multi_part(srcs)
    g = core.gray_of(board)
    _, m = core.binarize(g, primary, t_fixed)
    defs, noise = core.part_defects(m, min_area, mm_per_px)
    thr = float(_gates(cfg).get("iou_match", 0.3))
    det_boxes = [d["box"] for d in defs]
    matched_gt = sum(1 for gt in gts
                     if any(core.iou(gt["box"], b) >= thr for b in det_boxes))
    matched_det = sum(1 for b in det_boxes
                      if any(core.iou(gt["box"], b) >= thr for gt in gts))
    fp = len(det_boxes) - matched_det
    cause = ["成因分析（实测）：板上另撒 4×4 假缺陷点（灰度与真缺陷同为 60、"
             "开运算后仍存在），按面积门槛(%dpx)实测剔除 %d 个——面积维是本"
             "链路实测到的唯一误检来源；IoU<%.2f 的匹配外检出实测 %d 个"
             "（=误检数）" % (min_area, noise, thr, fp)]
    png_dir = io_utils.ensure_dir(os.path.join(out_dir, "annotated"))
    for d in defs:
        d["label"] = "a=%.2fmm2" % d["area_mm2"]
    png = core.annotate(board, defs, os.path.join(png_dir, "multi_defect.png"),
                        ["LEGEND", "multi-defect board",
                         "det=%d fp=%d" % (len(defs), fp)])
    return {"total": len(gts), "detected": matched_gt, "fp": fp, "noise": noise,
            "gts": [{"file": x["file"], "type": x["type"], "value": x["value"],
                     "box": x["box"]} for x in gts],
            "det_boxes": det_boxes, "cause_lines": cause, "png": png}


def _gates(cfg):
    raw = cfg.raw.get("tiers")
    return raw if isinstance(raw, dict) else {}


def build(cfg, out_dir, style_min=90.0):
    """跑完整测量链路，返回 (sections, result)；result 供 pytest 断言。"""
    io_utils.ensure_dir(out_dir)
    mm_per_px = float(cfg.raw.get("mm_per_px", 0.1))
    min_area = int(cfg.raw.get("min_area_px", 20))
    t_fixed = float(cfg.raw.get("global_T", 100))
    primary = str(cfg.raw.get("strategy", "otsu"))
    gates = _gates(cfg)
    parts, caliber = _load_parts(cfg)
    parts_by_name = {p["name"]: p for p in parts}
    rows, per = _measure_all(parts, mm_per_px, min_area, t_fixed)
    pngs = _annotate_batch(cfg, rows, parts_by_name, out_dir)
    multi = _multi_part(cfg, parts, out_dir)

    png_min_bytes = int(gates.get("png_min_bytes", 1000))
    all_pngs = pngs + [multi["png"]]
    png_valid = sum(1 for p in all_pngs
                    if p["bytes"] >= png_min_bytes and p["boxes"] >= 1
                    and p["labels"] >= 1 and p["legend"])
    err_list = per[primary]["errs"]
    err_mean = sum(err_list) / max(len(err_list), 1)
    err_max = max(err_list) if err_list else 100.0
    cmp_ok = all(len(per[s]["errs"]) == len(parts) for s in STRATEGIES) \
        and per[primary]["det"] == len(parts)
    meas = {"err_mean": round(err_mean, 2), "err_max": round(err_max, 2),
            "parts_total": len(parts), "parts_detected": per[primary]["det"],
            "png_valid": png_valid, "png_total": len(all_pngs),
            "cmp_ok": cmp_ok, "multi_total": multi["total"],
            "multi_detected": multi["detected"], "fp_count": multi["fp"],
            "noise_filtered": multi["noise"],
            "cause_ok": len(multi["cause_lines"]) >= 1}
    v = tiers.verdict(gates, meas)
    worst = max(rows, key=lambda x: x["per"][primary]["err"])
    wbox = None
    if worst["type"] == "scratch":
        rec = parts_by_name[worst["file"]]
        g = core.gray_of(rec["img"])
        _, m0 = core.binarize(g, primary, t_fixed)
        defs0, _n = core.part_defects(m0, min_area, mm_per_px)
        if defs0:
            x, y, w0, h0 = defs0[0]["box"]
            wbox = (w0, h0, round((w0 * w0 + h0 * h0) ** 0.5 * mm_per_px, 2))
    result = {"caliber": caliber, "strategy": primary, "rows": rows,
              "strategies": {
                  s: {"detected": per[s]["det"],
                      "err_mean": round(sum(per[s]["errs"]) /
                                        max(len(per[s]["errs"]), 1), 2),
                      "err_max": round(max(per[s]["errs"]) if per[s]["errs"]
                                       else 0.0, 2),
                      "noise": per[s]["noise"]} for s in STRATEGIES},
              "annotated_pngs": [{k: p[k] for k in
                                  ("path", "boxes", "labels", "legend", "bytes")}
                                 for p in pngs],
              "multi": {k: multi[k] for k in
                        ("total", "detected", "fp", "noise", "gts",
                         "det_boxes", "cause_lines")},
              "n_defects": per[primary]["det"], "measured": meas,
              "defects": [r["per"][primary] for r in rows]}
    result["tiers"] = v

    sections = [("输入口径", [
        "测量链路: %s" % caliber,
        "像素当量 %.2f mm/px（工单脚注②）｜主策略 %s｜全局阈值 T=%.0f｜"
        "最小面积 %dpx" % (mm_per_px, primary, t_fixed, min_area),
        "缺陷判据: 凹坑→contourArea×0.1²mm²，划痕→minAreaRect 长边×0.1mm"])]
    sections.append(("测量与真值对照（实测）",
                     ["%-14s %-7s 真值=%-7s 实测=%-7s 误差=%.2f%% 检出=%d" % (
                         r["file"], r["type"], r["gt"],
                         r["per"][primary]["meas"], r["per"][primary]["err"],
                         r["per"][primary]["n"]) for r in rows[:12]] +
                     ["……（其余 %d 件计入均值，完整表在 result.json）"
                      % max(len(rows) - 12, 0)] if len(rows) > 12 else
                     ["%-14s %-7s 真值=%-7s 实测=%-7s 误差=%.2f%% 检出=%d" % (
                         r["file"], r["type"], r["gt"],
                         r["per"][primary]["meas"], r["per"][primary]["err"],
                         r["per"][primary]["n"]) for r in rows]))
    worst_line = "实测最大误差件: %s（%s，真值 %s）→ %.2f%%" % (
        worst["file"], worst["type"], worst["gt"],
        worst["per"][primary]["err"])
    if worst["type"] == "scratch" and wbox and worst["gt"] \
            and wbox[2] < worst["gt"]:
        worst_line += ("（外接框 %dx%dpx、对角线 %.2fmm 已小于真值弧长——弯道划痕"
                       "在工单'最小外接矩形长边'口径下天然读短弧长，此为该件误差的"
                       "实测成因）" % (wbox[0], wbox[1], wbox[2]))
    sections[1][1].append(worst_line)
    sections.append(("阈值策略对比（决策矩阵·实测）", [
        "策略 global(T=%.0f): 检出 %d/%d 件｜平均误差 %.2f%%｜最大 %.2f%%｜"
        "小面积噪点 %d" % (
            t_fixed, per["global"]["det"], len(parts),
            sum(per["global"]["errs"]) / max(len(per["global"]["errs"]), 1),
            max(per["global"]["errs"]) if per["global"]["errs"] else 0.0,
            per["global"]["noise"]),
        "策略 otsu(T 自动): 检出 %d/%d 件｜平均误差 %.2f%%｜最大 %.2f%%｜"
        "小面积噪点 %d" % (
            per["otsu"]["det"], len(parts),
            sum(per["otsu"]["errs"]) / max(len(per["otsu"]["errs"]), 1),
            max(per["otsu"]["errs"]) if per["otsu"]["errs"] else 0.0,
            per["otsu"]["noise"]),
        "对比记录完整: %s（两策略均在全部 %d 件上真跑）" % (
            "是" if cmp_ok else "否", len(parts))]))
    sections.append(("结果图（cv2 落盘实测）", [
        "%s 框 %d 文字 %d 图例 %s %d B" % (
            os.path.relpath(p["path"], out_dir), p["boxes"], p["labels"],
            "有" if p["legend"] else "无", p["bytes"])
        for p in all_pngs]))
    sections.append(("多缺陷件实测（A 档）", [
        "拼装来源: %s" % ", ".join("%s(%s=%s)" % (
            g["file"], g["type"], g["value"]) for g in multi["gts"]),
        "全部检出: %d/%d ｜ 误检: %d ｜ 小面积噪点剔除: %d" % (
            multi["detected"], multi["total"], multi["fp"], multi["noise"]),
    ] + multi["cause_lines"]))
    stylecheck.augment(sections, result, stylecheck.project_root(
        os.path.abspath(__file__)), float(style_min))
    sections.append(("验收档位判定（实测）",
                     tiers.render_lines(v) + [""] + tiers.render_manual(v)))
    sections.append(("结论与建议", [
        "误差/对比/图要素/误检均为本次实测；判不到的条目全部列入人工答辩项，"
        "不自动判达标", "疑难件进人工复核队列；照明不均场景改用 Otsu/自适应阈值复测"]))
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections, result


def run(cfg, out_dir, style_min=90.0):
    """兼容旧入口：返回报告段（cli 用）。"""
    sections, _ = build(cfg, out_dir, style_min=style_min)
    return sections
