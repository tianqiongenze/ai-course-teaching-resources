# -*- coding: utf-8 -*-
"""真实数据流水线：CSV 加载 → NumPy 分层划分 → 三分类器 → 四项指标 → 决策矩阵。

对应工单 M1.1 第三节 ①~④；输出 output/report.txt 与 result.json 为答辩过程性证据。
规范率（工单"代码规范率≥70%"）由 stylecheck 实测后并入报告，不写死数字。
"""
import os

from . import core, io_utils, report
from . import stylecheck as S

ROOT = S.project_root(os.path.abspath(__file__))


def build_models(cfg):
    """三个分类器（工单要求 LR / DT / RF 都训），参数全部来自配置。"""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.tree import DecisionTreeClassifier

    r = cfg.raw
    lr = LogisticRegression(max_iter=int(r.get("lr_max_iter", 2000)),
                            random_state=cfg.seed)
    dt = DecisionTreeClassifier(max_depth=int(r.get("dt_max_depth", 6)),
                                random_state=cfg.seed)
    rf = RandomForestClassifier(
        n_estimators=int(r.get("rf_n_estimators", 300)),
        min_samples_leaf=int(r.get("rf_min_samples_leaf", 2)),
        random_state=cfg.seed, n_jobs=1)
    return [("逻辑回归", make_pipeline(StandardScaler(), lr)),
            ("决策树", dt),
            ("随机森林", rf)]


def run(cfg, out_dir, style_min=None):
    r = cfg.raw
    labels = list(r.get("labels") or core.CLASSES)
    gates = {"d": float(r.get("acc_d", 0.75)), "c": float(r.get("acc_c", 0.80)),
             "b": float(r.get("acc_b", 0.85)), "a": float(r.get("acc_a", 0.85))}
    test_size = float(r.get("test_size", 0.25))

    data_path = io_utils.course_data(str(r.get("data_file", "pump_fault.csv")))
    if data_path:
        X, y, meta = core.load_labeled_csv(data_path)
        source = "真实数据 %s" % data_path
    else:                                       # 数据缺失→合成兜底，报告如实标注
        X, y = core.make_data(int(r.get("n_samples", 300)), seed=cfg.seed)
        meta = None
        source = "合成兜底数据（未找到 %s，指标不代表现场表现）" % r.get("data_file")
    if meta:
        labels = [c for c in labels if meta["class_counts"].get(c, 0) > 0] or labels

    Xtr, Xte, ytr, yte = core.stratified_split(X, y, test_size=test_size, seed=cfg.seed)
    balance = core.split_balance_report(ytr, yte, labels)

    res = {}
    for name, model in build_models(cfg):
        res[name] = core.evaluate(model, Xtr, ytr, Xte, yte, labels)

    best_name = max(res, key=lambda k: res[k]["acc"])
    best = res[best_name]
    tier = core.tier_of(best["acc"], gates)
    matrix, delivered = core.decision_matrix(
        [{"model": k, "acc": v["acc"], "f1_macro": v["f1_macro"],
          "fit_seconds": v["fit_seconds"]} for k, v in res.items()],
        {"acc": float(r.get("w_acc", 3)), "speed": float(r.get("w_speed", 1)),
         "interp": float(r.get("w_interp", 2))},
        {"acc": [(0.95, 5), (0.90, 4), (0.85, 3), (0.80, 2), (0.75, 1)],
         "fit_seconds": [(0.0, 5), (0.5, 4), (1.0, 3), (3.0, 2), (10.0, 1)]},
        {"逻辑回归": int(r.get("interp_lr", 5)), "决策树": int(r.get("interp_dt", 4)),
         "随机森林": int(r.get("interp_rf", 2))})

    # ---- 报告渲染 ----
    metric_rows = [[k, "%.4f" % v["acc"], "%.4f" % v["precision_macro"],
                    "%.4f" % v["recall_macro"], "%.4f" % v["f1_macro"],
                    "%.3fs" % v["fit_seconds"]] for k, v in res.items()]
    cm_lines = []
    for k, v in res.items():
        cm_lines.append(io_utils.fmt_table(
            [[a] + [v["confusion"][a][b] for b in labels] + [v["missed"][a]]
             for a in labels],
            ["真实\\预测"] + labels + ["漏报数"]))
    pc_rows = [[k, c, "%.4f" % d["precision"], "%.4f" % d["recall"],
                "%.4f" % d["f1"], d["support"]]
               for k, v in res.items() for c, d in v["per_class"].items()]
    matrix_rows = [[m["model"], "%.4f" % m["acc"], "%.4f" % m["f1_macro"],
                    "%.3fs" % m["fit_seconds"], m["精度预期"], m["训练速度"],
                    m["可解释性"], m["综合"], m["决策"]] for m in matrix]
    miss_cost = "%s 漏报 %d 件（漏报=故障判为正常，产线代价高于误报，交付前须与值班师傅确认容忍度）" % (
        delivered, res[delivered]["missed"].get("轴承磨损", 0)
        + res[delivered]["missed"].get("叶轮堵塞", 0))

    acc_delivered = res[delivered]["acc"]
    style_rate = float(S.scan_project(ROOT)["rate"])
    gate_lines = ["门槛 D≥%.2f C≥%.2f B≥%.2f A≥%.2f（取自 rules.yaml，非硬编码）" % (
        gates["d"], gates["c"], gates["b"], gates["a"])]
    for key, label in (("d", "及格(D)"), ("c", "良好(C)"),
                       ("b", "优秀(B)"), ("a", "优(A)")):
        gate_lines.append("  %-7s 准确率≥%.2f → %s（实测 %.4f）｜ 本行只判准确率门，"
                          "同档其余条目见下方人工答辩项" % (
                              label, gates[key],
                              "实测达标" if acc_delivered >= gates[key] else "不足",
                              acc_delivered))
    gate_lines.append("交付模型 %s → 达标档位 %s" % (delivered, tier))
    gate_lines.append("最佳模型 %s 准确率 %.4f" % (best_name, best["acc"]))
    gate_lines.append("人工答辩项 4 条（工单原文判不了机器、不计入上方档位判定，"
                      "教师答辩时逐条确认）: D·能口述四项指标含义；C·指标解读准确无误；"
                      "B·决策矩阵填写规范；A·对比分析有条理（引用指标差异解释业务影响）")
    gate_lines.append("同档可机检部分已实测: 三模型对比表 %d 行、决策矩阵 %d 行、"
                      "规范率实测 %.1f%%（工单 D 档线≥70%%）→ %s" % (
                          len(res), len(matrix), style_rate,
                          "达标" if style_rate >= 70.0 else "未达标"))

    sections = [
        ("输入口径", [
            "数据源: %s" % source,
            "样本 %d 条（可用 %d / 丢弃 %d）｜特征 %d 维: %s" % (
                meta["n_rows"] if meta else len(X), meta["n_used"] if meta else len(X),
                meta["n_dropped"] if meta else 0, X.shape[1],
                ", ".join(meta["features"] if meta else core.FEATURES[:X.shape[1]])),
            "类别分布: %s" % (meta["class_counts"] if meta else "-"),
            "划分: NumPy 分层抽样 test_size=%.2f seed=%d → 训练 %d / 测试 %d" % (
                test_size, cfg.seed, len(Xtr), len(Xte)),
            "划分后各类计数: %s" % balance]),
        ("三分类器四项指标（宏平均口径）",
         [io_utils.fmt_table(metric_rows, ["模型", "准确率", "精确率(宏)",
                                           "召回率(宏)", "F1(宏)", "训练耗时"])]),
        ("混淆矩阵与漏报账", cm_lines),
        ("各类 P/R/F1 明细", [io_utils.fmt_table(
            pc_rows, ["模型", "类别", "精确率", "召回率", "F1", "样本数"])]),
        ("决策矩阵（打分依据：精度=实测准确率、速度=实测训练耗时、可解释性=登记档位）",
         [io_utils.fmt_table(matrix_rows, ["候选模型", "精度实测", "F1实测", "训练耗时",
                                           "精度预期", "训练速度", "可解释性", "综合", "决策"]),
          "权重: 精度%.1f / 速度%.1f / 可解释性%.1f（config/rules.yaml，改配置不改代码）" % (
              float(r.get("w_acc", 3)), float(r.get("w_speed", 1)),
              float(r.get("w_interp", 2)))]),
        ("工单验收档位", gate_lines),
        ("业务解读（≤100字）", [
            "宏平均把三类看同等重：小类不缺席。%s" % miss_cost,
            "结论：以 %s 交付，准确率 %.4f、macro-F1 %.4f；训练耗时 %.3fs 满足产线日级重训。" % (
                delivered, res[delivered]["acc"], res[delivered]["f1_macro"],
                res[delivered]["fit_seconds"])]),
    ]
    result = {
        "source": source, "data_file": data_path, "labels": labels,
        "n_train": int(len(Xtr)), "n_test": int(len(Xte)),
        "balance": balance, "models": {k: {kk: vv for kk, vv in v.items() if kk != "pred"}
                                       for k, v in res.items()},
        "decision_matrix": matrix, "delivered": delivered,
        "gates": gates, "tier": tier,
        "metrics": {"acc": res[delivered]["acc"],
                    "precision_macro": res[delivered]["precision_macro"],
                    "recall_macro": res[delivered]["recall_macro"],
                    "f1_macro": res[delivered]["f1_macro"]},
    }
    os.makedirs(out_dir, exist_ok=True)
    # 规范率实测并入报告段 + result.json（阈值缺省取工单 A 档线，可用 style_min 覆盖）
    threshold = float(style_min) if style_min is not None else 90.0
    stats = S.augment(sections, result, ROOT, threshold)
    gate_lines.append("规范率门槛 D≥70%% C≥70%% B≥80%% A≥90%% → 实测 %.1f%%（引擎 %s）"
                      % (stats["rate"], stats["engine"]))
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections
