# -*- coding: utf-8 -*-
"""双模型对比：数据 → 训练 → 手写混淆矩阵 → 漏报统计。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.tree import DecisionTreeClassifier

    labels = ["正常", "轴承磨损", "叶轮堵塞"]
    X, y = core.make_data(int(cfg.raw.get("n_samples", 300)), seed=cfg.seed)
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=float(cfg.raw.get("test_size", 0.25)),
        stratify=y, random_state=int(cfg.raw.get("random_state", 42)))
    res = {}
    for name, m in [("逻辑回归", LogisticRegression(max_iter=500)),
                    ("决策树", DecisionTreeClassifier(max_depth=6, random_state=0))]:
        res[name] = core.evaluate(m, Xtr, ytr, Xte, yte, labels)
    lines = []
    for name, r in res.items():
        lines.append("%s acc=%.3f 漏报=%s" % (name, r["acc"], r["missed"]))
        lines.append("   混淆矩阵（行=真实 列=预测）: " + " ; ".join(
            "%s→%s" % (a, {b: r["confusion"][a][b] for b in labels}) for a in labels))
    result = {"labels": labels, "n_train": len(Xtr), "n_test": len(Xte),
              "models": {k: {"acc": v["acc"], "missed": v["missed"],
                             "confusion": v["confusion"]} for k, v in res.items()}}
    sections = [("输入口径", ["样本 %d 条（%s）｜训练 %d / 测试 %d｜分层划分固定种子"
                % (len(X), "/".join(labels), len(Xtr), len(Xte))]),
                ("双模型对比", lines),
                ("漏报账", ["%s: %s" % (k, v["missed"]) for k, v in res.items()]),
                ("结论与建议", ["双解 acc 达标（≥0.85）即可交付；漏报（故障→正常）需在决策矩阵中加权，"
                 "因为产线上漏报比误报更贵"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections
