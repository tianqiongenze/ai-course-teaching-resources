# -*- coding: utf-8 -*-
"""真实焊缝数据 → tiny-CNN 双臂训练（有/无增强）→ 形状钩子/loss曲线/
混淆矩阵/误判样本全实测 → 工单 M2.1 四档判定进报告。

档位门槛全部由**本次运行实测值**决定（tiers.verdict，只比较不产生数据）：
  准确率 = 交付臂在同一测试集上的真实预测；增强对比 = 双臂各真练一次取差；
  loss 曲线/混淆矩阵 = matplotlib 真实落盘 png（报告记字节数，>门槛才算绘制）；
  形状表 = forward hook 实测形状 vs 卷积算式期望逐段比对。
"环境也是选型维度"：缺 torch/matplotlib 时对应能力如实标 MISS 并降档，
兜底路径（块统计+RF）可跑但冒充不了 CNN 训练证据；数据缺失降级四类均衡
合成并在报告标注"非真实数据"。
"""
import os

from . import core, io_utils, report, stylecheck, tiers

ROOT = stylecheck.project_root(os.path.abspath(__file__))


def _load_dataset(cfg):
    """真实课程数据优先；缺失降级四类均衡合成并如实标注。"""
    loaded = core.load_weld_images()
    if loaded is not None:
        X, y = loaded
        source = "真实课程数据 data/weld_images（index.json，四类均衡）"
    else:
        X, y = core.synth_weld_images(
            n=int(cfg.raw.get("n_images", 240)), seed=cfg.seed,
            size=int(cfg.raw.get("img_size", 64)))
        source = "合成兜底数据（未找到 data/weld_images，指标不代表现场表现）"
    return X, y, source


def _train_arms(cfg, X, y, tr, te):
    """无增强/增强双臂真实训练；torch 缺失两臂皆 None（上层标 MISS）。"""
    r = cfg.raw
    kw = dict(epochs=int(r.get("epochs", 40)), lr=float(r.get("lr", 0.003)),
              batch=int(r.get("batch", 64)), seed=int(cfg.seed),
              ch1=int(r.get("ch1", 8)), ch2=int(r.get("ch2", 16)),
              img=int(X.shape[1]))
    noaug = core.train_cnn(X[tr], y[tr], X[te], y[te], **kw)
    aug = None
    if noaug is not None:
        Xa, ya = core.augment_arm(X[tr], y[tr],
                                  shift=int(r.get("aug_shift", 2)))
        aug = core.train_cnn(Xa, ya, X[te], y[te], **kw)
    return noaug, aug


def build(cfg, out_dir):
    """跑完整训练-评估流程，返回 (sections, result)；result 供 pytest 断言。"""
    r = cfg.raw
    tiers_cfg = r.get("tiers") or {}
    gates = {"d": float(tiers_cfg.get("acc_d", 0.80)),
             "c": float(tiers_cfg.get("acc_c", 0.85)),
             "b": float(tiers_cfg.get("acc_b", 0.88))}
    n_cls = len(core.WORK_CLASSES)

    X, y, source = _load_dataset(cfg)
    tr, te = core.stratified_ratio_split(y, float(r.get("test_size", 0.25)),
                                         cfg.seed)
    counts = core.class_counts(y, n_cls)

    noaug, aug = _train_arms(cfg, X, y, tr, te)
    arms = {"aug": aug, "noaug": noaug}
    deliver_name = str(r.get("deliver_arm", "aug"))
    delivered = arms.get(deliver_name) or arms.get("noaug")
    engine = "tiny-CNN(torch)"
    if delivered is None:
        delivered = core.rf_fallback(X, y, tr, te, seed=cfg.seed)
        engine = "sklearn-RF 零 torch 兜底"
    acc = delivered["acc"] if delivered else None

    # ---- 形状追踪表：forward hook 实测 vs 卷积算式期望（工单"形状追踪法"）----
    shape_rows = []
    if delivered is not None and delivered.get("model") is not None:
        import torch
        expected = core.expected_shape_chain(
            n=1, ch1=int(r.get("ch1", 8)), ch2=int(r.get("ch2", 16)),
            n_cls=n_cls, img=int(X.shape[1]))
        trace = core.trace_shapes(delivered["model"], torch,
                                  torch.tensor(X[te[0]][None, None]))
        for name, exp in expected:
            got = trace.get(name)
            shape_rows.append([name, str(got), str(tuple(exp)),
                               "一致" if got == tuple(exp) else "不一致"])
    shape_stages = len(shape_rows)
    shape_match = sum(1 for row in shape_rows if row[3] == "一致")

    # ---- 混淆矩阵 + 误判样本（从真实预测里挑，不许口头报数）----
    cm = None
    miss_rows, lowconf = [], []
    if delivered is not None and delivered.get("pred") is not None:
        cm = core.confusion_matrix(y[te], delivered["pred"], n_cls)
        miss_rows = core.find_misclassified(te, y[te], delivered["pred"],
                                            delivered["conf"], y[te])
        for a in (noaug, aug):
            if a is None or a is delivered or a.get("pred") is None:
                continue
            miss_rows.extend(core.find_misclassified(te, y[te], a["pred"],
                                                     a["conf"], y[te]))
        if not miss_rows:
            lowconf = core.low_confidence(te, delivered["conf"],
                                          k=int(r.get("lowconf_k", 2)))

    # ---- 图表真实落盘（png 存在 + 字节数是"已绘制"的物证）----
    io_utils.ensure_dir(out_dir)
    loss_path = core.plot_loss_curves(
        {("增强臂" if k == "aug" else "无增强臂"): v["losses"]
         for k, v in arms.items() if v and v.get("losses")},
        os.path.join(out_dir, "loss_curve.png"))
    cm_path = None
    if cm is not None:
        cm_path = core.plot_confusion(cm, core.WORK_CLASSES,
                                      os.path.join(out_dir,
                                                   "confusion_matrix.png"))
    loss_stat = core.artifact_stat(loss_path)
    cm_stat = core.artifact_stat(cm_path)
    min_png = int(r.get("min_png_bytes", 1000))
    plots_ok = bool(loss_stat["bytes"] > min_png and cm_stat["bytes"] > min_png)
    shape_csv = os.path.join(out_dir, "shape_trace.csv")
    if shape_rows:
        io_utils.write_csv_rows(
            shape_csv,
            [{"stage": row[0], "measured": row[1], "expected": row[2],
              "match": row[3]} for row in shape_rows],
            ["stage", "measured", "expected", "match"])

    # ---- 实测能力字典 → tiers.verdict（只比较实测值，不产生新数据）----
    aug_delta = (round(aug["acc"] - noaug["acc"], 4)
                 if aug and noaug else None)
    style = stylecheck.scan_project(ROOT)
    notes = []
    if noaug is None and aug is None:
        notes.append("torch 缺失：CNN 训练流程/逐轮 loss/形状钩子均未真实实测，"
                     "兜底 RF 指标仅作对照，档位按未达标处理（MISS）")
    if not plots_ok:
        notes.append("loss 曲线或混淆矩阵未真实落盘（matplotlib 缺失/文件不足），"
                     "A 档图表能力按 MISS 处理")
    measured = {
        "delivered": deliver_name if arms.get(deliver_name) else engine,
        "acc": acc,
        "acc_noaug": noaug["acc"] if noaug else None,
        "acc_aug": aug["acc"] if aug else None,
        "aug_delta": aug_delta,
        "flow": bool(noaug is not None and noaug.get("losses")),
        "shape_basic": shape_stages >= 4,
        "shape_full": shape_stages >= 6 and shape_match == shape_stages,
        "aug_done": bool(aug is not None and noaug is not None
                         and aug_delta is not None),
        "plots_ok": plots_ok,
        "miss_done": bool(miss_rows or lowconf),
        "n_miss": len(miss_rows),
        "n_lowconf": len(lowconf),
        "shape_stages": shape_stages,
        "shape_match": shape_match,
        "loss_png_bytes": loss_stat["bytes"],
        "cm_png_bytes": cm_stat["bytes"],
        "style_rate": style["rate"],
        "miss_note": " ｜ ".join(notes) or None,
        "classes_balance": counts,
    }
    verdict = tiers.verdict(gates, measured)

    # ---- 报告渲染 ----
    arm_lines = []
    for name, a in (("无增强臂", noaug), ("增强臂", aug)):
        if a is None:
            arm_lines.append("%s: MISS（torch 未安装，未真实训练）" % name)
        elif a.get("losses"):
            ls = a["losses"]
            arm_lines.append(
                "%s: %d 轮 loss %.4f→%.4f｜测试准确率 %.4f｜耗时 %ss"
                % (name, len(ls), ls[0], ls[-1], a["acc"], a["seconds"]))
        else:
            arm_lines.append("%s: 测试准确率 %.4f（零 torch 兜底，无逐轮 loss）"
                             % (name, a["acc"]))
    pred2 = []
    if delivered is not None and delivered.get("pred") is not None:
        for j in range(min(2, len(te))):
            pred2.append("测试图 #%d: 真实=%s 预测=%s 置信度 %.4f"
                         % (int(te[j]), core.WORK_CLASSES[int(y[te][j])],
                            core.WORK_CLASSES[int(delivered["pred"][j])],
                            float(delivered["conf"][j])))
    miss_lines = ["测试集 #%d: 真实=%s 预测=%s 置信度 %.4f"
                  % (d["test_idx"], core.WORK_CLASSES[d["true"]],
                     core.WORK_CLASSES[d["pred"]], d["conf"])
                  for d in miss_rows[:6]]
    if not miss_rows and lowconf:
        miss_lines = ["双臂零误判（模型完美），改列实测置信度最低的高危样本备解释: "
                      "测试集 #%d 置信度 %.4f" % (d["test_idx"], d["conf"])
                      for d in lowconf]
    cm_lines = []
    if cm is not None:
        cm_lines = [io_utils.fmt_table(
            [[core.WORK_CLASSES[i]] + [str(int(v)) for v in cm[i]]
             + [str(int(cm[i].sum() - cm[i, i]))] for i in range(n_cls)],
            ["真实\\预测"] + core.WORK_CLASSES + ["漏报数"])]
    shape_csv_stat = core.artifact_stat(shape_csv)
    style_viol_line = "违规条数: %d（涉及 %d 行）" % (
        style["violations"], style["violation_lines"])
    sections = [
        ("输入口径", [
            "数据来源: %s" % source,
            "图像 %d 张｜类别 %s｜单图 %d×%d｜归一化 x/255 已执行｜分层划分 "
            "训练 %d / 测试 %d（test_size=%.2f, seed=%d）" % (
                len(X), "/".join(core.WORK_CLASSES), X.shape[1], X.shape[2],
                len(tr), len(te), float(r.get("test_size", 0.25)), cfg.seed),
            "各类计数（工单'四类均衡'实测）: %s" % counts]),
        ("训练-评估流程（逐轮 loss 实测）", arm_lines),
        ("预测示例（测试集前 2 张，展示预测与置信度）", pred2 or ["-"]),
        ("形状追踪表（forward hook 实测 vs 卷积算式期望）",
         ([io_utils.fmt_table(shape_rows,
                              ["阶段", "实测形状", "期望形状", "比对"])]
          if shape_rows else ["MISS: 无 torch 模型，形状链未实测"])),
        ("数据增强效果对比（翻转/平移，双臂真实训练、同一测试集）", [
            "增强构成: 原图+水平/垂直翻转+四向平移 ±%d 像素（7 倍训练样本）"
            % int(r.get("aug_shift", 2)),
            "无增强臂 %s ｜ 增强臂 %s ｜ Δ=%s" % (
                ("%.4f" % noaug["acc"]) if noaug else "MISS",
                ("%.4f" % aug["acc"]) if aug else "MISS",
                ("%+.4f" % aug_delta) if aug_delta is not None else "MISS"),
            "口径: 两臂在同一测试集评估（工单：禁止在测试集挑图刷分）"]),
        ("混淆矩阵与误判样本（真实预测结果）",
         (cm_lines if cm_lines else ["MISS: 兜底路径未产出混淆矩阵"]) +
         (["误判样本明细（前 %d 条）:" % len(miss_lines)] + miss_lines
          if miss_lines else ["-"])),
        ("图表与落盘产物（实测文件证据）", [
            "loss 曲线: %s（%d 字节）" % (loss_stat["path"], loss_stat["bytes"]),
            "混淆矩阵: %s（%d 字节）" % (cm_stat["path"], cm_stat["bytes"]),
            "形状表 CSV: %s %d 字节" % (shape_csv_stat["path"], shape_csv_stat["bytes"]),
            "判定口径: png 存在且 >%d 字节才算已绘制（实测值进档位判定）" % min_png]),
        ("编码规范率（PEP 8 实测；工单 M2.1 未规定规范率档位门槛，仅作答辩证据）", [
            "体检引擎: %s" % style["engine"],
            style_viol_line,
            "规范率实测: %.1f%%（公式 1-违规/有效行；%d 文件 %d 行）"
            % (style["rate"], style["files"], style["lines"])]),
        ("验收档位判定（实测）", tiers.render_lines(verdict)),
        ("结论与建议", [
            "训练引擎: %s｜判档臂: %s 实测准确率 %s" % (
                engine, measured["delivered"],
                ("%.4f" % acc) if acc is not None else "MISS"),
            "档位为实测判定；误判样本的口头解释与企业元签认须答辩现场确认"
            "（见上方人工答辩项清单）"])]
    result = dict(measured)
    result.update({
        "source": source, "engine": engine, "gates": gates,
        "n_images": int(len(X)), "n_train": int(len(tr)),
        "n_test": int(len(te)), "test_size": float(r.get("test_size", 0.25)),
        "seed": int(cfg.seed), "classes": core.WORK_CLASSES,
        "losses_noaug": noaug["losses"] if noaug else None,
        "losses_aug": aug["losses"] if aug else None,
        "confusion": cm.tolist() if cm is not None else None,
        "miss_samples": miss_rows[:8], "lowconf_samples": lowconf,
        "artifacts": {"loss_curve": loss_stat,
                      "confusion_matrix": cm_stat,
                      "shape_trace": core.artifact_stat(shape_csv)},
        "shape_trace": shape_rows, "tiers": verdict,
        "style_violations": style["violations"],
        "style_engine": style["engine"],
    })
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections, result


def run(cfg, out_dir, style_min=None):
    """兼容旧入口：返回报告段（cli 用）。

    style_min 仅为兼容既有调用签名保留；工单 M2.1 未规定规范率档位门槛，
    档位判定不含规范率门，规范率实测在报告里只作证据段。
    """
    sections, _ = build(cfg, out_dir)
    return sections
