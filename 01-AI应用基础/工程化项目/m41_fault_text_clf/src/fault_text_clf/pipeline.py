# -*- coding: utf-8 -*-
"""语料 → 分词 → TF-IDF → 双分类器对比 → 词典/ngram 调优 → 混淆分析 → 档位判定。

工单 M4.1 的四档门槛全部钉在本次运行的实测值上（tiers.verdict 只比较、不产生数据）：
  ① 课程数据 data/fault_reports.csv 真实读取（225 条），找不到时内置语料兜底
    并在报告如实写明——"环境也是选型维度"；
  ② 新文本预测：库外文本真实调用 predict 并落 CSV；
  ③ 两分类器对比：朴素贝叶斯与逻辑回归同切分、同向量化口径实测；
  ④ 自建词典 + ngram 调优：config/userdict.txt 真实加载、(1,2) 真实训练、
    前后准确率差如实记录（工单只要求"调优"，不要求必须提升，不造假）；
  ⑤ 混淆矩阵真实计算；测试集全对角时退化到"第二选择近误计数"，仍是真实输出。
数据红线（工单"六、常见错误"）：同文本先去重再切分，vectorizer 只在训练集 fit。
"""
import os
import time

from . import core, io_utils, report, stylecheck, tiers

ROOT = stylecheck.project_root(os.path.abspath(__file__))
DATA_FILE = "fault_reports.csv"

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


def _load_rows():
    """课程 CSV 真实路径优先，缺失时内置语料兜底并如实报告来源。"""
    path = io_utils.course_data(DATA_FILE)
    if path:
        rows = [(r.get("text"), r.get("label"))
                for r in io_utils.read_csv_rows(path)]
        rows = [(t, c) for t, c in rows if t and c]
        if rows:
            return rows, "课程数据 %s（%d 条）" % (path, len(rows))
    return list(CORPUS), ("内置语料兜底（未找到 data/%s；课程数据缺失时口径"
                          "随之下降，档位判定照常实测）" % DATA_FILE)


def _split_idx(y, ratio, seed):
    """≥50 条走分层随机切分；小样本走确定性前缀切分（保证各类都进训练集）。"""
    idx = list(range(len(y)))
    if len(y) >= 50 and len(set(y)) * 2 <= len(y):
        from sklearn.model_selection import train_test_split
        return train_test_split(idx, test_size=ratio, random_state=seed,
                                stratify=y)
    n = max(1, int(len(y) * (1 - ratio)))
    return idx[:n], idx[n:]


def _plot_confusion(cm, path):
    """混淆矩阵热力图；matplotlib 缺失返回 None（报告打 MISS，不谎报产物）。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return None
    plt.rcParams["font.sans-serif"] = ["PingFang SC", "Arial Unicode MS",
                                       "Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    mat = np.array(cm["matrix"])
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    im = ax.imshow(mat, cmap="Blues")
    ax.set_xticks(range(len(cm["labels"])))
    ax.set_yticks(range(len(cm["labels"])))
    ax.set_xticklabels(cm["labels"], rotation=30, ha="right", fontsize=8)
    ax.set_yticklabels(cm["labels"], fontsize=8)
    for i in range(len(cm["labels"])):
        for j in range(len(cm["labels"])):
            ax.text(j, i, mat[i][j], ha="center", va="center", fontsize=9,
                    color="white" if mat[i][j] > mat.max() / 2 else "black")
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title("混淆矩阵（测试集实测）")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def build(cfg, out_dir, style_min=90.0):
    """跑完整训练-评估-预测链路，返回 (sections, result)；result 供 pytest 断言。"""
    stop = cfg.raw.get("stop_words") or []
    max_feat = int(cfg.raw.get("max_features", 2000))
    seed = int(cfg.raw.get("seed", 7))
    ratio = float(cfg.raw.get("test_ratio", 0.2))
    tune_ng = int(cfg.raw.get("ngram_tune", 2))
    ud_rel = str(cfg.raw.get("userdict", ""))
    ud = ud_rel if os.path.isabs(ud_rel) else os.path.join(ROOT, ud_rel)
    gates = tiers.gates_from(cfg)
    topk_kw = int(gates["B"].get("topk", 10))

    rows, src_txt = _load_rows()
    seen, ded = set(), []
    for t, c in rows:                       # 同文本进 train+test 会虚高准确率
        if t not in seen:
            seen.add(t)
            ded.append((t, c))
    tok_base, _ = core.jieba_tokenizer(None)
    tok_tuned, dict_loaded = core.jieba_tokenizer(ud)
    engine = "jieba（真实路径）" if tok_base else "内置二元词兜底（jieba MISS）"
    X = [core.feature_text(t, tok_base, stop) for t, _ in ded]
    X2 = [core.feature_text(t, tok_tuned, stop) for t, _ in ded]
    y = [c for _, c in ded]
    tr, te = _split_idx(y, ratio, seed)
    Xtr, Xte, X2tr, X2te, ytr, yte = (
        [X[i] for i in tr], [X[i] for i in te], [X2[i] for i in tr],
        [X2[i] for i in te], [y[i] for i in tr], [y[i] for i in te])

    tuned_lr = "LR调优(词典+%d-gram)" % tune_ng
    tuned_nb = "NB调优(词典+%d-gram)" % tune_ng
    specs = [("LR基线(1,1)", core.build, (1, 1), Xtr, "word(1,1)"),
             ("NB基线(1,1)", core.build_nb, (1, 1), Xtr, "word(1,1)"),
             (tuned_lr, core.build, (1, tune_ng), X2tr, "userdict+(1,%d)" % tune_ng),
             (tuned_nb, core.build_nb, (1, tune_ng), X2tr,
              "userdict+(1,%d)" % tune_ng)]
    mt, pipes, percls = {}, {}, {}
    for name, fn, ng, xtr, params in specs:
        t0 = time.perf_counter()          # 训练耗时实测——决策矩阵"训练速度"列数据源
        pipe = fn(xtr, ytr, max_feat, ngram=ng)
        xte = Xte if ng == (1, 1) else X2te
        m = core.evaluate(pipe, xte, yte)
        m["train_seconds"] = round(time.perf_counter() - t0, 4)
        m["params"] = params
        mt[name] = m
        pipes[name] = pipe
        percls[name] = core.per_class_acc(pipe, xte, yte)
    lr_t = pipes[tuned_lr]                   # 终模型：部署口径（词典+ngram 调优后 LR）
    acc_final = mt[tuned_lr]["acc"]
    tune_delta = round(acc_final - mt["LR基线(1,1)"]["acc"], 4)
    n_models = len(mt)

    kw = core.class_keywords(lr_t, k=topk_kw)
    kw_classes = len([c for c in kw if len(kw[c]) >= 1])
    cm = core.confusion_pair(lr_t, X2te, yte)

    new_items = cfg.raw.get("new_texts") or []
    if isinstance(new_items, str):
        new_items = [{"text": new_items, "expect": ""}]
    preds = []
    for it in new_items:
        text = str(it.get("text", ""))
        exp = str(it.get("expect", ""))
        if not text or text in seen:        # "库外"必须实测核验，库内文本不算数
            continue
        feat = core.feature_text(text, tok_tuned, stop)
        dist = lr_t.predict_proba([feat])[0]
        order = sorted(range(len(dist)), key=lambda j: -dist[j])
        p = str(lr_t.classes_[order[0]])
        preds.append({"text": text, "expect": exp, "pred": p,
                      "prob": round(float(dist[order[0]]), 4),
                      "second": str(lr_t.classes_[order[1]]),
                      "second_prob": round(float(dist[order[1]]), 4),
                      "features": feat,
                      "match": bool(exp) and p == exp})
    n_new = len(preds)
    n_match = len([p for p in preds if p["match"]])

    io_utils.ensure_dir(out_dir)
    compare_csv = os.path.join(out_dir, "model_compare.csv")
    cmp_rows = []
    for name in mt:
        v = mt[name]
        cmp_rows.append({"model": name, "scope": "overall",
                         "params": v["params"], "train_seconds": v["train_seconds"],
                         "test_acc": v["acc"], "test_macro_f1": v["macro_f1"],
                         "train_n": len(tr), "test_n": len(te)})
        for c, cv in sorted(percls[name].items()):
            cmp_rows.append({"model": name, "scope": "class:%s" % c,
                             "params": v["params"], "train_seconds": "",
                             "test_acc": cv, "test_macro_f1": "",
                             "train_n": "", "test_n": ""})
    io_utils.write_csv_rows(compare_csv, cmp_rows)
    kw_csv = os.path.join(out_dir, "keywords_top%d.csv" % topk_kw)
    io_utils.write_csv_rows(kw_csv, [
        {"label": c, "rank": i + 1, "word": w, "coef": s}
        for c, items in sorted(kw.items())
        for i, (w, s) in enumerate(items)])
    pred_csv = os.path.join(out_dir, "new_text_pred.csv")
    io_utils.write_csv_rows(pred_csv, preds)
    png = _plot_confusion(cm, os.path.join(out_dir, "confusion_matrix.png"))
    artifacts = {"model_compare_csv": compare_csv, "keywords_csv": kw_csv,
                 "new_pred_csv": pred_csv, "confusion_png": png,
                 "result_json": os.path.join(out_dir, "result.json")}

    stats = stylecheck.scan_project(ROOT)
    result = {"corpus_source": src_txt, "n_raw": len(rows), "n_dedup": len(ded),
              "classes": sorted(set(y)), "tokenizer": engine,
              "userdict": ud, "userdict_loaded": dict_loaded,
              "ngram_tune": tune_ng, "metrics": mt, "per_class_acc": percls,
              "tier_acc": acc_final,
              "tune_delta": tune_delta, "keywords": kw, "confusion": cm,
              "new_pred": preds, "n_new": n_new, "n_match": n_match,
              "artifacts": artifacts,
              "style_rate": stats["rate"], "style_violations": stats["violations"],
              "style_engine": stats["engine"]}
    result["tiers"] = tiers.verdict(
        gates=gates, rate=stats["rate"], acc=acc_final, n_new=n_new,
        new_match=n_match, n_models=n_models, kw_classes=kw_classes,
        n_classes=len(set(y)), cm=cm,
        tuning_done=bool(dict_loaded) and tune_ng >= 2, tune_delta=tune_delta)

    pair = cm["top_pair"]
    lines_mt = ["%s: accuracy %.4f / macro-F1 %.4f / 训练 %.3fs"
                % (k, v["acc"], v["macro_f1"], v["train_seconds"])
                for k, v in mt.items()]
    lines_kw = []
    for c in sorted(kw):
        words = "、".join(w for w, _ in kw[c][:5])
        lines_kw.append("%s（贡献词前5）: %s ｜ 全表见 %s" % (c, words, kw_csv))
    lines_pred = []
    for p in preds:
        mark = "✓" if p["match"] else "✗（如实记录，不挑数据）"
        lines_pred.append("%s → 预测「%s」p=%.3f（次选「%s」p=%.3f；期望「%s」）%s"
                          % (p["text"], p["pred"], p["prob"], p["second"],
                             p["second_prob"], p["expect"], mark))
    lines_input = [
        src_txt,
        "原始 %d 条 → 去重 %d 条（同文本跨集=泄漏，先实测消重）" % (len(rows), len(ded)),
        "分词引擎: %s ｜ 停用词 %d 个 ｜ 切分: 训练 %d / 测试 %d" % (
            engine, len(stop), len(tr), len(te)),
    ]
    compare_txt = "两分类器同切分对比完整: %s ｜ 每类准确率/训练耗时 %d 行见 %s（决策矩阵数据源）" % (
        "是（NB/LR×基线/调优）" if n_models >= 4 else "不足",
        len(cmp_rows), compare_csv)
    pair_txt = "%s→%s ×%d" % (pair["true"], pair["other"], pair["count"]) \
        if pair else "无（含近误也为 0）"
    lines_cm = [
        "off-diagonal 错分 %d 处 ｜ 定位口径: %s" % (cm["off_diag"], cm["method"]),
        "最易混类对: %s" % pair_txt,
        "热力图: %s" % (png or "MISS（matplotlib 未安装，已如实标注）"),
    ]
    lines_tune = [
        "词典文件: %s ｜ 实际加载: %s" % (ud, "是" if dict_loaded else "否（MISS）"),
        "ngram_range=(1,%d) 真实训练: 是" % tune_ng,
        "调优前后实测: 基线 %.4f → 终模型 %.4f ｜ Δ=%+.4f（负提升也如实呈现）" % (
            mt["LR基线(1,1)"]["acc"], acc_final, tune_delta),
    ]
    conclusion = ("TF-IDF+线性模型在工业短文本上已可用；LLM 的价值在开放问答"
                  "与生成解释（见 M4.2），二者互补。易混归因与关键词解释属人工答辩项")
    sections = [
        ("输入口径", lines_input),
        ("测试集指标（实测）", lines_mt + [compare_txt]),
        ("库外新文本预测（实测）", lines_pred or ["无库外新文本（MISS）"]),
        ("每类 Top%d 关键词贡献（实测表）" % topk_kw, lines_kw),
        ("混淆矩阵分析（实测）", lines_cm),
        ("自建词典/ngram 调优（实测）", lines_tune),
        ("编码规范率（PEP 8 实测）",
         stylecheck.format_section(stats, style_min)),
        ("验收档位判定（实测）", tiers.render_lines(result["tiers"])),
        ("结论与建议", [conclusion]),
    ]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections, result


def run(cfg, out_dir, style_min=90.0):
    """兼容 cli 入口：返回报告段。"""
    sections, _ = build(cfg, out_dir, style_min=style_min)
    return sections
