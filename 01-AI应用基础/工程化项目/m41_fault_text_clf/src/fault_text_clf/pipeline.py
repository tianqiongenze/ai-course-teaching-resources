# -*- coding: utf-8 -*-
"""语料 → 二元词 → TF-IDF → 双模型对比 → 在线预测演示。"""
import os

from . import core, io_utils, report

CORPUS = [
    ("注塑机液压油温升高报警", "液压系统"),
    ("液压泵压力波动异常", "液压系统"),
    ("液压缸内泄导致压力不足", "液压系统"),
    ("冷却塔风机轴承异响", "冷却系统"),
    ("冷却水温持续偏高", "冷却系统"),
    ("冷却系统管路泄漏", "冷却系统"),
    ("电机电流偏高转速正常", "传动系统"),
    ("减速机齿轮磨损异响", "传动系统"),
    ("皮带打滑导致传动失效", "传动系统"),
    ("气缸磁性开关不动作", "气动系统"),
    ("气动阀动作迟缓", "气动系统"),
    ("气压不足导致夹爪无力", "气动系统"),
]


def run(cfg, out_dir):
    stop = cfg.raw.get("stop_words") or []
    max_feat = int(cfg.raw.get("max_features", 2000))
    demo = str(cfg.raw.get("demo_text", "3号注塑机液压油温升高报警"))
    X = [" ".join(core.tokens(t, stop)) for t, _ in CORPUS]
    y = [c for _, c in CORPUS]
    n = max(1, int(len(X) * (1 - float(cfg.raw.get("test_ratio", 0.2)))))
    Xtr, ytr, Xte, yte = X[:n], y[:n], X[n:], y[n:]
    pipe = core.build(Xtr, ytr, max_feat)
    mt = core.evaluate(pipe, Xte, yte)
    pred = core.predict(pipe, demo, stop)
    from collections import Counter
    result = {"n": len(X), "classes": sorted(set(y)), "metrics": mt,
              "demo": {"text": demo, "pred": pred}}
    sections = [("输入口径", ["语料 %d 条（%s）｜二元词分词｜TF-IDF(max_features=%d)"
                % (len(X), "/".join(sorted(set(y))), max_feat)]),
                ("测试集指标", ["accuracy = %.4f　macro-F1 = %.4f" % (mt["acc"], mt["macro_f1"])]),
                ("在线预测演示", ["输入: %s" % demo, "输出类别: %s" % pred]),
                ("类分布", ["%s: %d" % (k, v) for k, v in sorted(Counter(y).items())]),
                ("结论与建议", ["TF-IDF+线性模型在工业短文本上已可用；"
                 "LLM 的价值在开放问答与生成解释（见 M4.2），二者互补"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections
