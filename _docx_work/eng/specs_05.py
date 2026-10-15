# -*- coding: utf-8 -*-
"""《AI应用基础（48课时版）》（ai48 环境）12 个工单的工程化项目规格。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eng_helpers import stories, funcs, tcases, adr, finalize

COURSE = "05-AI应用基础48课时版"

# 知识库副本：生成时内联进项目 config/knowledge_base.json，避免依赖外部路径
_KB_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                       "05-AI应用基础48课时版", "data", "knowledge_base.json")
try:
    KB_JSON = open(_KB_SRC, encoding="utf-8").read()
except Exception:
    KB_JSON = "{}"

ENV = "ai48"
SPECS = []


def P(**kw):
    SPECS.append(finalize(dict(course=COURSE, env=ENV, deps=kw.pop("deps", []), **kw)))


def std(t, b, d, a, tech, m, **kw):
    """05 包规格公共默认项（压缩 specs 体积）。"""
    kw.setdefault("rules", dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3))
    kw.setdefault("rules_yaml", "warn: 80.0" + chr(10) + "danger: 95.0" + chr(10)
                  + "unit: " + chr(34) + "c" + chr(34) + chr(10)
                  + "seed: 7" + chr(10) + "topk: 3" + chr(10))
    kw.setdefault("togaf", dict(business=b, data=d, application=a, technology=tech))
    kw.setdefault("mods", m)
    if "stories" not in kw:
        kw["stories"] = [("作为学员，我希望跑通本工单并看到量化结果", "全绿 + 指标达标")]
    if "funcs" not in kw:
        kw["funcs"] = [("核心功能", "见 core.py 接口"),
                       ("可复现", "固定随机种子"),
                       ("可测试", "pytest 三档用例")]
    if "test_cases" not in kw:
        kw["test_cases"] = [("核心逻辑", "正常输入", "预期输出"),
                            ("边界", "空/极值", "显式处理"),
                            ("异常", "非法输入", "抛出明确异常")]
    if "design_core" not in kw:
        kw["design_core"] = "core 为纯函数层（无 IO），pipeline 只做编排与落盘。"
    if "adr" not in kw:
        kw["adr"] = adr(
            "分层：core 纯函数 + pipeline 编排",
            "把" + chr(34) + "能算" + chr(34) + "和" + chr(34) + "能跑" + chr(34) + "分开，才能各自单测、各自复用",
            "A 单文件脚本（难测）｜B core/pipeline 分层（可测）｜C 引入框架（过度）",
            "B core/pipeline 分层",
            "core 可零依赖单测；pipeline 只负责 IO 与报告",
            "文件数量增加", "低", "README 已说明分层")
    return kw


# ══════════ M1-1a 数据清洗与质量评估 ══════════
P(id="05-M1-1a", week="W07", no="第1次课", title="数据清洗与质量评估",
  slug="m11a_data_quality", pkg="data_quality48", deps=["numpy", "pandas"],
  scope="合成带脏泵站日志，实现缺失/超限/负值三类处理与质量评分，"
        "并做纯Python与Pandas双解互验（同口径同结果）。",
  **std("方案", "把脏日志变成可信数据集", "(ts,vib,temp) 脏行 → 清洗后数据集+三类问题清单+质量分",
        "core 三类清洗+质量分；pipeline 双解互验",
        "Python 3.12 + conda ai48；numpy/pandas；pytest",
        [("core.py", "三类清洗 + 质量分 + 双解", "make_dirty()/clean_py()/clean_pd()/quality()")],
        stories=[("作为分析员，我希望两解结果一致", "行数与质量分相同")],
        test_cases=[("clean", "清洗", "300 行脏数据", "行数减少且三类清零")]),
  core_py='''# -*- coding: utf-8 -*-
"""数据清洗与质量评估：双解互验（纯函数）。"""
import numpy as np


def make_dirty(n=300, seed=7):
    import pandas as pd
    rng = np.random.RandomState(seed)
    df = pd.DataFrame({
        "ts": pd.date_range("2026-03-01", periods=n, freq="h"),
        "vib": rng.normal(4.0, 0.5, n).round(3),
        "temp": rng.normal(55, 3, n).round(1)})
    df.loc[rng.choice(n, 15, replace=False), "vib"] = np.nan
    df.loc[rng.choice(n, 6, replace=False), "temp"] = 135.0
    df.loc[rng.choice(n, 5, replace=False), "vib"] = -1.0
    return df


def clean_py(df, temp_max=120.0, vib_min=0.0, vib_max=15.0):
    """解A：纯 Python 逐行判断。"""
    out = []
    for r in df.to_dict("records"):
        ok = (r["vib"] == r["vib"] and vib_min <= r["vib"] <= vib_max
              and r["temp"] <= temp_max)
        if ok:
            out.append(r)
    return out


def clean_pd(df, temp_max=120.0, vib_min=0.0, vib_max=15.0):
    """解B：Pandas 布尔掩码链。"""
    return df[(df["vib"].notna()) & (df["vib"].between(vib_min, vib_max))
              & (df["temp"] <= temp_max)]


def quality(n_rows, n_bad, temp_max=120.0):
    """质量分 = 完整率 × 合理率（清洗后口径）。"""
    if n_rows + n_bad == 0:
        return 0.0
    return round((n_rows / (n_rows + n_bad)) ** 2, 4)

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""双解互验：造脏 → 两法清洗 → 一致性比对 → 质量分。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    import pandas as pd
    raw = core.make_dirty(300, seed=cfg.seed)
    a = core.clean_py(raw)
    b = core.clean_pd(raw)
    same = (len(a) == len(b))
    q = core.quality(len(b), len(raw) - len(b))
    result = {"rows_before": len(raw), "rows_after": len(b),
              "removed": len(raw) - len(b), "quality": q,
              "py_rows": len(a), "pd_rows": len(b), "consistent": same}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    sections = [("输入口径", ["原始 %d 行（含缺失/超限/负值）" % len(raw)]),
                ("双解结果", ["纯Python: %d 行｜Pandas: %d 行｜一致: %s"
                         % (len(a), len(b), same)]),
                ("清洗留痕", ["%d 行 → %d 行（剔除 %d 行，保留率 %.1f%%）"
                        % (len(raw), len(b), result["removed"], len(b) / len(raw) * 100)]),
                ("质量分", ["%.4f（目标 ≥ 0.85）" % q]),
                ("结论与建议", ["两解同口径同结果 → 清洗规则可冻结；一致即互验通过"])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
from data_quality48 import core


def test_make_dirty_has_all_defects():
    df = core.make_dirty(300, 7)
    assert df["vib"].isna().any() and (df["temp"] > 120).any() and (df["vib"] < 0).any()


def test_two_solutions_agree():
    df = core.make_dirty(300, 7)
    assert len(core.clean_py(df)) == len(core.clean_pd(df))


def test_clean_removes_all_defects():
    df = core.make_dirty(300, 7)
    c = core.clean_pd(df)
    assert c["vib"].notna().all() and c["temp"].max() <= 120.0 and c["vib"].min() >= 0.0


def test_quality_between_0_and_1():
    q = core.quality(275, 25)
    assert 0.0 <= q <= 1.0


def test_quality_empty():
    assert core.quality(0, 0) == 0.0

''')


# ══════════ M1-1b 特征设计与优化 ══════════
P(id="05-M1-1b", week="W10", no="第3次课", title="特征设计与优化",
  slug="m11b_feature_design", pkg="feature_design48", deps=["numpy", "scikit-learn"],
  scope="时域(3)+频域(2) 双解造特征，用随机森林重要性证明"
        "16Hz 二倍频幅值是判别力最强的特征——特征设计直接决定模型上限。",
  **std("方案", "把'凭经验挑特征'变成可量化验证", "振动窗口 → 5 维特征 → 标签 → 重要性排序",
        "core 提纯函数特征 + RF 排序；pipeline 输出 Top-N",
        "Python 3.12 + conda ai48；numpy/sklearn；pytest",
        [("core.py", "时域/频域特征 + 重要性", "feats_time()/feats_freq()/rank()")],
        stories=[("作为讲师，我希望验证 a16 犯名", "重要性 Top1/2")],
        test_cases=[("feats", "特征", "1 个窗口", "5 个数")]),
  core_py='''# -*- coding: utf-8 -*-
"""特征设计：13 维时域 + 4 维频域（纯函数）。"""
import numpy as np


def make_signal(kind, n=400, seed=7, noise=0.4):
    """合成 8Hz 基频信号；磨损类叠加 16Hz 二倍频（工业 SNR）。"""
    rng = np.random.RandomState(seed)
    t = np.linspace(0, 4, n)
    x = 0.3 * np.sin(2 * np.pi * 8 * t) + rng.randn(n) * noise
    if kind == "wear":
        x = x + 0.25 * np.sin(2 * np.pi * 16 * t)
    return t, x


def feats_time(x):
    """时域三件套：RMS / 峰峰值 / 峭度。"""
    x = np.asarray(x, float)
    return [float(np.sqrt(np.mean(x ** 2))), float(np.ptp(x)),
            float(((x - x.mean()) ** 4).mean() / (x.std() ** 4 + 1e-12))]


def feats_freq(x, fs=100.0):
    """频域双特征：8Hz / 16Hz 幅值。"""
    spec = np.abs(np.fft.rfft(x))
    f = np.fft.rfftfreq(len(x), 1 / fs)
    return [float(spec[np.argmin(np.abs(f - 8))]),
            float(spec[np.argmin(np.abs(f - 16))])]


FEAT_NAMES = ["rms", "ptp", "kurt", "a8", "a16"]


def build_dataset(n_win=40, seed=7, noise=0.4):
    """多随机实现 → 稳定重要性。"""
    rng = np.random.RandomState(seed)
    X, y = [], []
    for lab, kind in ((0, "normal"), (1, "wear")):
        for _ in range(n_win):
            _, x = make_signal(kind, seed=int(rng.randint(0, 100000)), noise=noise)
            X.append(feats_time(x) + feats_freq(x))
            y.append(lab)
    return np.array(X, float), np.array(y)


def rank(X, y):
    from sklearn.ensemble import RandomForestClassifier
    clf = RandomForestClassifier(random_state=0, n_estimators=300).fit(X, y)
    order = np.argsort(clf.feature_importances_)[::-1]
    return [(FEAT_NAMES[i], round(float(clf.feature_importances_[i]), 4))
            for i in order], clf

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""多窗口数据集 → 特征重要性 → Top-N 结论。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    import numpy as np
    n = int(cfg.raw.get("n_windows", 40))
    X, y = core.build_dataset(n, seed=cfg.seed)
    ranked, clf = core.rank(X, y)
    result = {"n_windows": n * 2, "n_features": len(core.FEAT_NAMES),
              "ranked": ranked, "top1": ranked[0][0],
              "train_acc": round(float(clf.score(X, y)), 4)}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    sections = [("输入口径", ["窗口 %d 个（每类 %d）｜特征 %d 维｜树 300 棵"
                    % (n * 2, n, len(core.FEAT_NAMES))]),
            ("特征重要性", ["%d. %s = %.3f" % (k + 1, nm, v)
                     for k, (nm, v) in enumerate(ranked)]),
            ("结论与建议", ["Top1 = %s（16Hz 二倍频指纹）；特征设计决定模型上限，"
                      "比换模型更能提升效果" % ranked[0][0]])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections


''',
  tests_py='''# -*- coding: utf-8 -*-
import numpy as np

from feature_design48 import core


def test_feats_time_three_values():
    f = core.feats_time(np.arange(30, dtype=float))
    assert len(f) == 3


def test_feats_freq_two_values():
    t, x = core.make_signal("normal", 200, 3)
    assert len(core.feats_freq(x)) == 2


def test_make_signal_wear_has_higher_a16():
    _, xn = core.make_signal("normal", 400, 5)
    _, xw = core.make_signal("wear", 400, 5)
    assert core.feats_freq(xw)[1] > core.feats_freq(xn)[1]


def test_build_dataset_shape():
    X, y = core.build_dataset(10, 1)
    assert X.shape == (20, 5) and set(y) == {0, 1}


def test_rank_orders_by_importance():
    X, y = core.build_dataset(10, 1)
    ranked, _ = core.rank(X, y)
    vals = [v for _, v in ranked]
    assert vals == sorted(vals, reverse=True) and len(ranked) == 5

''')


# ══════════ M2-1a 传统分类 ══════════
P(id="05-M2-1a", week="W11", no="第5次课", title="传统分类：逻辑回归 + 决策树",
  slug="m21a_classic_clf", pkg="classic_clf", deps=["numpy", "scikit-learn"],
  scope="三态分类：逻辑回归与决策树同台，手写混淆矩阵，"
        "把漏报（故障判为正常）单独统计——漏报是产线最贵的错误。",
  **std("方案", "双模型同台对比，用证据说话", "4 维特征 + 三态标签 → 混淆矩阵 + 漏报账",
        "core 造数/训练/手写混淆矩阵；pipeline 双模型对比",
        "Python 3.12 + conda ai48；numpy/sklearn；pytest",
        [("core.py", "造数/训练/混淆矩阵/漏报", "make_data()/confusion()/evaluate()")],
        funcs=[("数据合成", "三态高斯+组间偏移"), ("双模型", "LR / DT"),
               ("手写混淆矩阵", "不调库"), ("漏报统计", "按类别")],
        stories=[("作为工程师，我希望看到漏报账", "按类别漏报数")]),
  core_py='''# -*- coding: utf-8 -*-
"""传统分类：造数、双模型、手写混淆矩阵与漏报统计（纯函数）。"""
import numpy as np


def make_data(n=300, seed=7):
    rng = np.random.RandomState(seed)
    X = rng.normal(0, 1, (n, 4))
    third = n // 3
    y = np.array(["正常"] * third + ["轴承磨损"] * third + ["叶轮堵塞"] * (n - 2 * third),
                 dtype=object)
    X[y == "轴承磨损", 0] += 1.5
    X[y == "叶轮堵塞", 1] -= 1.4
    X[y == "叶轮堵塞", 2] += 1.0
    return X, y


def confusion(y_true, y_pred, labels):
    cm = {a: {b: 0 for b in labels} for a in labels}
    for t, p in zip(y_true, y_pred):
        cm[t][p] += 1
    return cm


def missed(cm, labels):
    """每类漏报数（真实为 a 但预测成别的）。"""
    return {a: sum(cm[a][b] for b in labels if b != a) for a in labels}


def evaluate(model, Xtr, ytr, Xte, yte, labels):
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    cm = confusion(yte, pred, labels)
    return {"acc": round(float((pred == yte).mean()), 4), "cm": cm,
            "missed": missed(cm, labels)}

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""三态数据 → 双模型 → 混淆矩阵 → 漏报账。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.tree import DecisionTreeClassifier
    labels = ["正常", "轴承磨损", "叶轮堵塞"]
    X, y = core.make_data(300, seed=cfg.seed)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)
    out = {}
    for nm, m in [("LR", LogisticRegression(max_iter=500)),
                  ("DT", DecisionTreeClassifier(max_depth=6, random_state=0))]:
        out[nm] = core.evaluate(m, Xtr, ytr, Xte, yte, labels)
    gap = abs(out["LR"]["acc"] - out["DT"]["acc"])
    result = {"labels": labels, "n_train": len(Xtr), "n_test": len(Xte),
              "models": {k: {"acc": v["acc"], "missed": v["missed"], "cm": v["cm"]}
                         for k, v in out.items()}, "acc_gap": round(gap, 4)}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    lines = []
    for nm, r in out.items():
        lines.append("%s acc=%.3f 漏报=%s" % (nm, r["acc"], r["missed"]))
        for a in labels:
            lines.append("    %s→%s" % (a, {b: r["cm"][a][b] for b in labels}))
    sections = [("输入口径", ["样本 %d 条（三态）｜训练 %d / 测试 %d" % (len(X), len(Xtr), len(Xte))]),
                ("双模型 + 混淆矩阵", lines),
                ("结论与建议", ["双解 acc 差距 %.3f（目标 ≤0.10）；漏报（故障→正常）需在决策矩阵加权"
                          % gap])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from classic_clf import core


def test_make_data_labels_complete():
    X, y = core.make_data(9, 1)
    assert set(y) == {"正常", "轴承磨损", "叶轮堵塞"}
    assert "轴承" not in set(y)


def test_confusion_diagonal():
    cm = core.confusion(["a", "b"], ["a", "b"], ["a", "b"])
    assert cm["a"]["a"] == 1 and cm["b"]["b"] == 1


def test_missed_counts_off_diagonal():
    cm = {"a": {"a": 2, "b": 1}, "b": {"a": 0, "b": 3}}
    assert core.missed(cm, ["a", "b"]) == {"a": 1, "b": 0}


def test_evaluate_returns_acc_and_cm():
    from sklearn.tree import DecisionTreeClassifier
    X, y = core.make_data(150, 3)
    r = core.evaluate(DecisionTreeClassifier(max_depth=3, random_state=0),
                      X[:100], y[:100], X[100:], y[100:],
                      ["正常", "轴承磨损", "叶轮堵塞"])
    assert 0.0 <= r["acc"] <= 1.0 and set(r["missed"]) == {"正常", "轴承磨损", "叶轮堵塞"}

''')


# ══════════ M2-2 调参与工时账 ══════════
P(id="05-M2-2", week="W12", no="第7次课", title="XGBoost 参数调优与工时账",
  slug="m22_tuning_cost", pkg="tuning_cost", deps=["numpy", "scikit-learn"],
  scope="GridSearch 穷举 vs RandomizedSearch 预算：同数据同评估，"
        "把'精度-工时'两本账一起算——调参必须计工时。",
  **std("方案", "让调参决策有量化依据", "调参空间 → 两种搜索 → CV 分数 + 耗时",
        "core 造数/两种搜索/指标；pipeline 输出工时账",
        "Python 3.12 + conda ai48；numpy/sklearn；pytest",
        [("core.py", "造数 + 两种搜索 + 指标", "make_data()/search()/summarize()")],
        funcs=[("穷举", "GridSearchCV"), ("预算", "RandomizedSearchCV"),
               ("工时账", "耗时差 + CV 差")],
        stories=[("作为工程师，我希望知道省了多少时间", "工时差")]),
  core_py='''# -*- coding: utf-8 -*-
"""调参与工时账：穷举 vs 预算搜索（纯函数）。"""
import time

import numpy as np


def make_data(n=400, seed=7):
    rng = np.random.RandomState(seed)
    X = rng.normal(0, 1, (n, 6))
    y = rng.binomial(1, 0.4, n)
    X[y == 1, :3] += 1.3
    return X, y


def search(kind, Xtr, ytr, grid, n_iter=3, seed=0):
    """两种搜索：grid（穷举）/ random（预算）。"""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
    base = RandomForestClassifier(random_state=0)
    t0 = time.time()
    if kind == "grid":
        res = GridSearchCV(base, grid, cv=3).fit(Xtr, ytr)
    else:
        res = RandomizedSearchCV(base, grid, n_iter=n_iter, random_state=seed,
                                 cv=3).fit(Xtr, ytr)
    return {"best": dict(res.best_params_),
            "cv": round(float(res.best_score_), 4),
            "sec": round(time.time() - t0, 3)}

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""造数 → 两种搜索 → 工时账。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    from sklearn.model_selection import train_test_split
    X, y = core.make_data(400, seed=cfg.seed)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=1)
    grid = {"max_depth": [3, 4, 5], "n_estimators": [50, 100]}
    g = core.search("grid", Xtr, ytr, grid)
    r = core.search("random", Xtr, ytr, grid, n_iter=3)
    saved = round(g["sec"] - r["sec"], 3)
    gap = abs(g["cv"] - r["cv"])
    result = {"grid": g, "random": r, "time_saved_sec": saved, "cv_gap": round(gap, 4),
              "n_combos": len(grid["max_depth"]) * len(grid["n_estimators"])}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    sections = [("输入口径", ["搜索空间 %d 组（max_depth×n_estimators）" % result["n_combos"]]),
                ("GridSearch（穷举）", ["cv=%.4f  耗时 %.3fs  最优 %s" % (g["cv"], g["sec"], g["best"])]),
                ("RandomSearch（预算）", ["cv=%.4f  耗时 %.3fs  最优 %s" % (r["cv"], r["sec"], r["best"])]),
                ("工时账", ["节省 %.3fs（%.0f%%）｜CV 代价 %.4f（目标 ≤0.02）"
                        % (saved, saved * 100 / max(g["sec"], 1e-9), gap)]),
                ("结论与建议", ["小空间穷举更稳；大空间用预算搜索——工时账写进工单决策矩阵"])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
from tuning_cost import core


def test_make_data_shape():
    X, y = core.make_data(200, 1)
    assert X.shape == (200, 6) and len(y) == 200


def test_search_grid_returns_metrics():
    X, y = core.make_data(120, 2)
    r = core.search("grid", X[:90], y[:90], {"max_depth": [2, 3]})
    assert 0.0 <= r["cv"] <= 1.0 and r["sec"] > 0


def test_search_random_returns_metrics():
    X, y = core.make_data(120, 2)
    r = core.search("random", X[:90], y[:90], {"max_depth": [2, 3, 4]}, n_iter=2)
    assert 0.0 <= r["cv"] <= 1.0


def test_random_no_slower_than_grid_on_big_space():
    X, y = core.make_data(150, 2)
    grid = {"max_depth": [2, 3, 4, 5], "n_estimators": [20, 50, 100]}
    g = core.search("grid", X[:100], y[:100], grid)
    r = core.search("random", X[:100], y[:100], grid, n_iter=2)
    assert r["sec"] <= g["sec"] + 1e-6

''')


# ══════════ M2-3a MLP 神经网络 ══════════
P(id="05-M2-3a", week="W13", no="第9次课", title="MLP 神经网络",
  slug="m23a_mlp", pkg="mlp_clf", deps=["numpy", "scikit-learn"],
  scope="MLP 训练 + 损失曲线诊断 + 早停与正则对照；"
        "让学员看懂'收敛/过拟合'而不是只会看准确率。",
  **std("方案", "把'炼丹'变成可诊断的工程", "30 维频谱 → 二分类 → 损失曲线 + 正则对照",
        "core 造数/训练/曲线诊断；pipeline 输出对比",
        "Python 3.12 + conda ai48；numpy/sklearn；pytest",
        [("core.py", "造数 + MLP + 曲线诊断", "make_spectra()/train()/diagnose()")],
        funcs=[("标准化", "StandardScaler"), ("早停", "early_stopping"),
               ("曲线诊断", "分段 loss 对比"), ("正则对照", "alpha 扫描")],
        stories=[("作为讲师，我希望学员看懂收敛", "损失曲线分段输出")]),
  core_py='''# -*- coding: utf-8 -*-
"""MLP：造数、训练、损失曲线诊断与正则对照（纯函数）。"""
import numpy as np


def make_spectra(n=600, seed=42):
    rng = np.random.RandomState(seed)
    X = rng.normal(0, 1, (n, 30))
    y = rng.binomial(1, .5, n)
    X[y == 1, 2:8] += rng.uniform(.8, 1.6)
    return X, y


def train(Xtr, ytr, Xte, yte, alpha=0.0, seed=0):
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(Xtr)
    Xtr, Xte = sc.transform(Xtr), sc.transform(Xte)
    m = MLPClassifier(hidden_layer_sizes=(64, 32), alpha=alpha,
                      early_stopping=True, random_state=seed, max_iter=300).fit(Xtr, ytr)
    return m, round(float(m.score(Xte, yte)), 4)


def diagnose(loss_curve):
    """把损失曲线分成 4 段，判断是否持续下降。"""
    n = len(loss_curve)
    if n < 4:
        return {"segments": 1, "improving": False}
    idx = [(0, n // 4), (n // 4, n // 2), (n // 2, 3 * n // 4), (3 * n // 4, n)]
    vals = [round(float(np.mean(loss_curve[a:b])), 4) for a, b in idx]
    return {"segments": 4, "means": vals,
            "improving": all(vals[i] > vals[i + 1] for i in range(3)),
            "final": round(float(loss_curve[-1]), 4)}

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""频谱 → MLP → 曲线诊断 → 正则对照。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    from sklearn.model_selection import train_test_split
    X, y = core.make_spectra(600, seed=cfg.seed)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)
    m, acc = core.train(Xtr, ytr, Xte, yte, alpha=0.0)
    dg = core.diagnose(m.loss_curve_)
    _, acc_reg = core.train(Xtr, ytr, Xte, yte, alpha=1e-3)
    result = {"n_epochs": len(m.loss_curve_), "acc": acc, "acc_reg": acc_reg,
              "diagnosis": dg}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    sections = [("输入口径", ["600 样本 × 30 维频谱｜隐藏层 (64,32)｜early_stopping=True"]),
                ("训练", ["epochs=%d  测试准确率 %.4f（目标≥0.75）" % (len(m.loss_curve_), acc)]),
                ("损失曲线诊断", ["四段均值: %s" % dg["means"],
                          "持续下降: %s｜末轮 loss %.4f" % (dg["improving"], dg["final"])]),
                ("正则对照", ["alpha=1e-3 准确率 %.4f（对比 %.4f）" % (acc_reg, acc)]),
                ("结论与建议", ["结构+早停+正则三件套守住准确率与泛化；曲线比分数更能说明问题"])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import numpy as np

from mlp_clf import core


def test_make_spectra_shape():
    X, y = core.make_spectra(200, 1)
    assert X.shape == (200, 30) and set(y) <= {0, 1}


def test_train_returns_acc():
    X, y = core.make_spectra(300, 2)
    from sklearn.model_selection import train_test_split
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)
    m, acc = core.train(Xtr, ytr, Xte, yte)
    assert 0.0 <= acc <= 1.0 and len(m.loss_curve_) > 0


def test_diagnose_four_segments():
    _, dg = None, core.diagnose(list(np.linspace(1.0, 0.1, 40)))
    assert dg["segments"] == 4 and dg["improving"] and dg["means"][0] > dg["means"][3]


def test_diagnose_short_curve():
    dg = core.diagnose([0.5, 0.4, 0.3])
    assert dg["segments"] == 1

''')


# ══════════ M2-3b 竞标二选一 ══════════
P(id="05-M2-3b", week="W14", no="第11次课", title="竞标：CNN 或 LSTM 二选一",
  slug="m23b_bidding", pkg="bidding_lines", deps=["numpy", "scikit-learn"],
  scope="焊缝CNN路线 vs 风机LSTM路线：先用轻量基线拿到竞标数据，"
        "带着证据上答辩台——竞标书要的是证据不是形容词。",
  **std("方案", "用数据支撑技术选型决策", "合成图 + 序列 → 两条路线基线 CV",
        "core 两路线特征 + CV；pipeline 输出竞标建议",
        "Python 3.12 + conda ai48；numpy/sklearn；pytest",
        [("core.py", "图像线/时序线特征 + CV", "make_images()/img_feats()/make_series()/seq_feats()/cv()")],
        funcs=[("图像线", "块统计3维"), ("时序线", "RMS 比值"),
               ("交叉验证", "3 折均值")],
        stories=[("作为答辩者，我希望有量化证据", "两条路线 CV 对比")]),
  core_py='''# -*- coding: utf-8 -*-
"""竞标二选一：图像线（CNN）vs 时序线（LSTM）轻量基线。"""
import numpy as np


def make_images(n=180, seed=7, size=32):
    rng = np.random.RandomState(seed)
    X, y = [], []
    for i in range(n):
        img = rng.normal(0.5, 0.08, (size, size))
        label = i % 3
        if label == 1:
            r0, c0 = rng.randint(4, size - 4, 2)
            img[r0:r0 + 3, c0:c0 + 3] += 0.5
        if label == 2:
            r0 = rng.randint(6, size - 6)
            img[r0:r0 + 1, 4:size - 4] -= 0.35
        X.append(img)
        y.append(["正常", "气孔", "裂纹"][label])
    return np.array(X), np.array(y)


def img_feats(img):
    """块统计：亮块比例 / 暗线比例 / 最大亮值。"""
    return [float((img > 0.8).mean()), float((img < 0.2).mean()), float(img.max())]


def make_series(n=180, seed=7):
    rng = np.random.RandomState(seed)
    X, y = [], []
    for i in range(n):
        t = np.linspace(0, 2, 64)
        amp = 0.3 + 0.25 * (i % 2) * t / 2
        X.append(amp * np.sin(2 * np.pi * 6 * t) + rng.randn(64) * 0.05)
        y.append(["健康", "退化"][i % 2])
    return np.array(X), np.array(y)


def seq_feats(x):
    """时序线：前/后半 RMS 之比（退化斜率指纹）。"""
    return [float(np.sqrt(np.mean(x[:32] ** 2)) / (np.sqrt(np.mean(x[32:] ** 2)) + 1e-9))]


def cv(F, y, folds=3):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    s = cross_val_score(RandomForestClassifier(random_state=0), F, y, cv=folds)
    return round(float(s.mean()), 4)

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""两路线基线 → CV 对比 → 竞标建议。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    Xi, yi = core.make_images(180, seed=cfg.seed)
    Xs, ys = core.make_series(180, seed=cfg.seed)
    a = core.cv([core.img_feats(im) for im in Xi], yi)
    b = core.cv([core.seq_feats(x) for x in Xs], ys)
    pick = "CNN 焊缝线" if a >= b else "LSTM 风机线"
    result = {"image_line_cv": a, "series_line_cv": b, "pick": pick,
              "gap": round(abs(a - b), 4)}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    sections = [("输入口径", ["图像线 180 张×3类｜时序线 180 条×2类｜3 折交叉验证"]),
                ("两路线基线", ["图像线(CNN) CV = %.4f" % a, "时序线(LSTM) CV = %.4f" % b]),
                ("竞标建议", ["轻量基线支持选「%s」（差 %.4f）" % (pick, abs(a - b))]),
                ("结论与建议", ["基线≠上限——真模型的增益需用数据量/算力/标注成本三项证据支撑"])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import numpy as np

from bidding_lines import core


def test_img_feats_three():
    f = core.img_feats(np.zeros((32, 32)))
    assert len(f) == 3


def test_seq_feats_one_value():
    assert len(core.seq_feats(np.arange(64, dtype=float))) == 1


def test_make_images_classes():
    X, y = core.make_images(60, 3)
    assert X.shape[1:] == (32, 32) and set(y) == {"正常", "气孔", "裂纹"}


def test_cv_between_0_and_1():
    X, y = core.make_images(90, 2)
    v = core.cv([core.img_feats(im) for im in X], y)
    assert 0.0 <= v <= 1.0

''')


# ══════════ M3-1 迁移学习 ══════════
P(id="05-M3-1", week="W15", no="第13次课", title="ResNet 迁移学习（概念版）",
  slug="m31_transfer", pkg="transfer_learning", deps=["numpy", "scikit-learn"],
  scope="冻结预训练特征 + 只训分类头 vs 16 条样本直连 192 维——"
        "用可运行实验证明'预训练特征是维度灾难的解药'。",
  **std("方案", "让小样本也能训练出可用模型", "2000 条无标注 + 16 条标注 → 两组测试准确率",
        "core 造世界/冻结提取器/两组训练；pipeline 输出增益",
        "Python 3.12 + conda ai48；numpy/sklearn；pytest",
        [("core.py", "世界生成 + 冻结提取器", "make_world()/FrozenExtractor/train_head()")],
        funcs=[("预训练", "PCA 在海量数据上学习"), ("冻结", "只前传不更新"),
               ("小样本头", "LR 分类")],
        stories=[("作为工程师，我希望小样本也能work", "迁移组 ≥ 对照组")]),
  core_py='''# -*- coding: utf-8 -*-
"""迁移学习概念版：冻结预训练特征 + 只训分类头。"""
import numpy as np


def make_world(seed=7, n_dim=192):
    """8 种工况原型，仅前 8 个测点携带信息，其余为环境噪声维。"""
    rng = np.random.RandomState(seed)
    centers = rng.normal(0, 3, (8, n_dim))
    centers[:, 8:] = 0
    big = np.vstack([c + rng.normal(0, 1, (250, n_dim)) for c in centers])
    small = np.vstack([c + rng.normal(0, 1, (2, n_dim)) for c in centers])
    test = np.vstack([c + rng.normal(0, 1, (25, n_dim)) for c in centers])

    def label(X):
        return (X[:, 0] > 0).astype(int)

    return big, small, test, label(small), label(test)


class FrozenExtractor:
    """'预训练特征提取器'：海量数据上一次性学成，之后冻结。"""

    def __init__(self, big, dim=8):
        from sklearn.decomposition import PCA
        self.pca = PCA(n_components=dim, random_state=0).fit(big)
        self.n = dim

    def transform(self, X):
        return self.pca.transform(X)


def train_head(X, y, Xte):
    from sklearn.linear_model import LogisticRegression
    m = LogisticRegression(max_iter=500).fit(X, y)
    return m, m.predict(Xte)

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""造世界 → 冻结提取 → 两组训练 → 增益结论。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    big, small, test, ys, yt = core.make_world(seed=cfg.seed)
    ext = core.FrozenExtractor(big, dim=8)
    _, raw_pred = core.train_head(small, ys, test)
    raw_acc = float((raw_pred == yt).mean())
    _, tf_pred = core.train_head(ext.transform(small), ys, ext.transform(test))
    tf_acc = float((tf_pred == yt).mean())
    evr = float(ext.pca.explained_variance_ratio_.sum())
    gain = tf_acc - raw_acc
    result = {"dim_raw": small.shape[1], "dim_frozen": ext.n,
              "raw_acc": round(raw_acc, 4), "transfer_acc": round(tf_acc, 4),
              "gain": round(gain, 4), "evr": round(evr, 4)}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    sections = [("输入口径", ["海量无标注 %d 条｜少量标注 %d 条｜测试 %d 条"
                        % (len(big), len(small), len(test))]),
                ("对照组（16条直连192维）", ["测试准确率 %.4f" % raw_acc]),
                ("迁移组（冻结8维+训头）", ["测试准确率 %.4f（解释方差 %.3f）" % (tf_acc, evr)]),
                ("增益", ["%+.4f → %s" % (gain, "迁移胜出" if gain > 0 else "本轮未见增益")]),
                ("结论与建议", ["真实规律仅藏在少数测点维；冻结+小样本头是 ResNet 微调思想的最小可运行模型"])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import numpy as np

from transfer_learning import core


def test_make_world_shapes():
    big, small, test, ys, yt = core.make_world(7)
    assert big.shape[1] == 192 and len(small) == 16 and len(test) == 200
    assert set(np.unique(ys)) <= {0, 1}


def test_frozen_extractor_dims():
    big, small, test, ys, yt = core.make_world(7)
    ext = core.FrozenExtractor(big, dim=8)
    assert ext.transform(small).shape == (16, 8)


def test_train_head_predicts_binary():
    big, small, test, ys, yt = core.make_world(7)
    ext = core.FrozenExtractor(big, dim=8)
    _, pred = core.train_head(ext.transform(small), ys, ext.transform(test))
    assert set(np.unique(pred)) <= {0, 1}


def test_transfer_beats_raw():
    big, small, test, ys, yt = core.make_world(7)
    ext = core.FrozenExtractor(big, dim=8)
    _, raw = core.train_head(small, ys, test)
    _, tf = core.train_head(ext.transform(small), ys, ext.transform(test))
    assert (tf == yt).mean() >= (raw == yt).mean()

''')


# ══════════ M3-2 YOLO实时检测 ══════════
P(id="05-M3-2", week="W16", no="第15次课", title="YOLO 实时缺陷检测",
  slug="m32_yolo", pkg="yolo_detect", deps=["numpy", "Pillow"],
  scope="滑窗+阈值+IoU+FPS 手搓检测器，并做 win 尺寸取舍实验；"
        "理解 YOLO'锚框/步长调参'的同一问题。",
  **std("方案", "先手搓检测器再谈深度学习", "合成 64×64 图 → 滑窗分数图 → 框+IoU+FPS",
        "core 造图/滑窗/检测/IoU/FPS；pipeline 输出取舍表",
        "Python 3.12 + conda ai48；numpy/Pillow；pytest",
        [("core.py", "造图/滑窗/检测/IoU/FPS", "make_scene()/score_map()/detect()/iou()/fps()")],
        funcs=[("滑窗分数图", "窗口均值"), ("阈值检测", "最大点+阈值"),
               ("IoU 评估", "≥0.5 合格"), ("FPS 基准", "200 次计时")],
        stories=[("作为学员，我想理解检测器原理", "滑窗+阈值复现"),
                 ("作为工程师，我想量化取舍", "win-IoU-FPS 表")]),
  core_py='''# -*- coding: utf-8 -*-
"""零依赖检测器：滑窗 + 阈值 + IoU + FPS（纯函数）。"""
import numpy as np


def make_scene(size=64, seed=7):
    """64×64 产线图 + 已知真值框（一个亮点缺陷）。"""
    rng = np.random.RandomState(seed)
    img = rng.normal(0.4, 0.05, (size, size))
    r0, c0, w = 40, 30, 8
    img[r0:r0 + w, c0:c0 + w] += 0.35
    return img, (c0, r0, w, w)


def score_map(img, win=8):
    """滑窗分数图：每个 win×win 窗的均值。"""
    H, W = img.shape[0] // win, img.shape[1] // win
    smap = np.zeros((H, W))
    for r in range(H):
        for c in range(W):
            smap[r, c] = img[r * win:(r + 1) * win, c * win:(c + 1) * win].mean()
    return smap


def detect(img, win=8, thresh=0.5):
    smap = score_map(img, win)
    r, c = np.unravel_index(np.argmax(smap), smap.shape)
    if smap[r, c] < thresh:
        return None, float(smap[r, c])
    return (int(c) * win, int(r) * win, win, win), float(smap[r, c])


def iou(a, b):
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    un = a[2] * a[3] + b[2] * b[3] - inter
    return inter / un if un else 0.0


def fps(detect_fn, img, n=100):
    import time
    t0 = time.time()
    for _ in range(n):
        detect_fn(img)
    return round(n / (time.time() - t0), 1)

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""造图 → 检测 → win 取舍实验。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    img, gt = core.make_scene(64, seed=cfg.seed)
    box, conf = core.detect(img)
    v = core.iou(box, gt) if box else 0.0
    rows, best = [], (None, -1)
    for win in (4, 8, 16):
        b, _ = core.detect(img, win=win)
        vv = core.iou(b, gt) if b else 0.0
        ff = core.fps(lambda im, w=win: core.detect(im, win=w), img, n=60)
        rows.append((win, vv, ff))
        if vv > best[1]:
            best = (win, vv)
    result = {"detected_box": box, "conf": round(conf, 4), "iou": round(v, 4),
              "gt": list(gt), "bench": [{"win": w, "iou": round(a, 3), "fps": b}
                                      for w, a, b in rows],
              "best_win": best[0]}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    sections = [("输入口径", ["64×64 产线图｜真值框 %s｜阈值 0.5" % (gt,)]),
                ("检测结果", ["框=%s 缺陷分=%.3f IoU=%.2f（目标≥0.5）"
                         % (box, conf, v)]),
                ("win 取舍表", ["win=%-3d IoU=%.2f  FPS=%.0f" % (w, a, b) for w, a, b in rows]),
                ("结论与建议", ["实测最优 win=%d；窗口过小信噪比低易误检、过大定位粗化——"
                          "这就是 YOLO 锚框/步长调参的同一问题" % best[0]])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import numpy as np

from yolo_detect import core


def test_make_scene_returns_gt():
    img, gt = core.make_scene(64, 7)
    assert img.shape == (64, 64) and gt == (30, 40, 8, 8)


def test_detect_returns_box_and_conf():
    img, _ = core.make_scene(64, 7)
    box, conf = core.detect(img)
    assert box is not None and conf > 0.5


def test_iou_identical_and_disjoint():
    a = (10, 10, 8, 8)
    assert core.iou(a, a) == 1.0
    assert core.iou((0, 0, 5, 5), (100, 100, 5, 5)) == 0.0


def test_score_map_shape():
    img, _ = core.make_scene(64, 7)
    assert core.score_map(img, 8).shape == (8, 8)


def test_fps_positive():
    img, _ = core.make_scene(64, 7)
    assert core.fps(lambda im: core.detect(im), img, n=10) > 0

''')


# ══════════ M4-1 LLM 故障诊断（三版Prompt） ══════════
P(id="05-M4-1", week="W17", no="第17次课", title="LLM 故障诊断·三版 Prompt",
  slug="m41_prompt_lab", pkg="prompt_lab", deps=[],
  scope="同一个问题三种问法：朴素/角色/示例（Few-shot），"
        "用可注入的 LLM 通道量化 Prompt 价值；离线规则通道保证课堂可复现。",
  **std("方案", "把'Prompt 感觉'变成可测量指标", "问题（只给症状）+ 三种 system prompt → 质量分",
        "core 通道抽象 + 三版 Prompt + 评分；pipeline 对比输出",
        "Python 3.12 + conda ai48；零依赖（可选连 mock LLM）；pytest",
        [("core.py", "通道抽象 + 三版 Prompt + 评分", "MockChannel()/call()/score()/compare()")],
        funcs=[("通道抽象", "可注入 fake/mock/真机"), ("三版 Prompt", "朴素/角色/示例"),
               ("质量评分", "命中正确处置=1")],
        stories=[("作为学员，我想量化 Prompt 的价值", "三版分数对比"),
                 ("作为讲师，我希望离线可复现", "MockChannel 默认")]),
  core_py='''# -*- coding: utf-8 -*-
"""三版 Prompt 对比：通道可注入 + 质量评分（纯函数）。"""

PROMPTS = {
    "朴素": "帮我看看设备怎么了。",
    "角色": "你是设备运维工程师。泵振动特征频率异常，轴承磨损可能性大。请给出处置建议。",
    "示例": "示例：输入'电机异响发热'→输出'建议：检查轴承润滑'。"
            "现在：泵振动8Hz/16Hz特征频率抬升，请按示例格式给处置建议。",
}
QUESTION = "3号泵振动在爬升，运转声音发闷，帮我看看。"
KEYWORDS = ["轴承", "磨损", "特征频率", "16Hz", "8Hz", "润滑"]


class MockChannel:
    """离线规则通道：按 Prompt+Question 命中关键词给答案（课堂可复现）。"""

    def __call__(self, system, user):
        text = system + user
        if any(k in text for k in KEYWORDS):
            return "建议：更换轴承（依据：%s…" % user[:12]
        return "建议：检查电源。"


def call(channel, system, user):
    return channel(system, user)


def score(answer):
    """质量分：命中正确处置=1.0，给出建议=0.5，否则 0。"""
    if "轴承" in answer and "更换" in answer:
        return 1.0
    if "建议" in answer:
        return 0.5
    return 0.0


def compare(channel):
    base = None
    out = {}
    for tag, p in PROMPTS.items():
        ans = call(channel, p, QUESTION)
        s = score(ans)
        if base is None:
            base = s
        out[tag] = {"score": s, "delta": round(s - base, 3), "answer": ans}
    return out, base

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""三版 Prompt → 打分 → 提升幅度。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    ch = core.MockChannel()
    out, base = core.compare(ch)
    best = max(v["score"] for v in out.values())
    lift = (best - base) * 100
    result = {"question": core.QUESTION, "base": base, "results": out,
              "best_score": best, "lift_pct": round(lift, 1)}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    lines = []
    for tag, v in out.items():
        lines.append("%-4s 质量分=%.1f（较朴素 %+.0f%%）→ %s"
                     % (tag, v["score"], v["delta"] * 100, v["answer"][:30]))
    sections = [("输入口径", ["问题（仅给症状，不含诊断关键词）: %s" % core.QUESTION]),
                ("三版对比", lines),
                ("结论", ["最优 %.1f，较朴素 %+.0f%% → %s"
                        % (best, lift, "达标（≥+50%）" if lift >= 50 else "未达标")]),
                ("说明", ["本演示走离线规则通道；设 OPENAI_BASE_URL 或起 mock LLM 服务可切真机通道"]),
                ("结论与建议", ["角色给领域先验、示例给输出格式——两者叠加才让 LLM 照单办事"])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
from prompt_lab import core


def test_question_has_no_diagnostic_keyword():
    assert not any(k in core.QUESTION for k in ("轴承", "特征频率"))


def test_mock_channel_gives_advice_for_role_prompt():
    ans = core.call(core.MockChannel(), core.PROMPTS["角色"], core.QUESTION)
    assert "轴承" in ans


def test_mock_channel_generic_for_naive():
    ans = core.call(core.MockChannel(), core.PROMPTS["朴素"], core.QUESTION)
    assert "轴承" not in ans


def test_score_tiers():
    assert core.score("建议：更换轴承（…") == 1.0
    assert core.score("建议：检查电源。") == 0.5
    assert core.score("不知道") == 0.0


def test_compare_lift_at_least_50():
    out, base = core.compare(core.MockChannel())
    best = max(v["score"] for v in out.values())
    assert (best - base) * 100 >= 50


def test_compare_deltas_relative_to_first():
    out, _ = core.compare(core.MockChannel())
    assert out["朴素"]["delta"] == 0.0

''')


# ══════════ M4-2 RAG 知识库问答 ══════════
P(id="05-M4-2", week="W18", no="第19次课", title="RAG 知识库问答",
  slug="m42_rag", pkg="rag48", deps=[],
  scope="切分→检索→引用生成：二元词重合度检索，回答必须带出处；"
        "检索不到时诚实拒答——宁可说'查无依据'，不硬编。",
  extra_files={"config/knowledge_base.json": KB_JSON},
  **std("方案", "让知识可引用、可追溯", "知识库 20 条 → 检索 Top-k + 引用编号",
        "core 知识加载/重合检索/引用生成/防幻觉；pipeline 批量问答统计",
        "Python 3.12 + conda ai48；data/knowledge_base.json；pytest",
        [("core.py", "知识加载/检索/引用生成", "load_kb()/bigrams()/retrieve()/answer()")],
        funcs=[("知识库加载", "JSON + 引用编号"), ("二元词检索", "重合度"),
               ("引用生成", "Top-k 带 ID"), ("防幻觉", "低于阈值拒答")],
        stories=[("作为运维员，我希望回答必须给出处", "含 [R1] 引用"),
                 ("作为质量员，我希望不能瞎编", "查无依据")]),
  core_py='''# -*- coding: utf-8 -*-
"""RAG：二元词重合检索 + 引用生成 + 防幻觉拒答（纯函数）。"""
import json
import os
import re

KB_CANDIDATES = [
    os.path.join("config", "knowledge_base.json"),      # ① 项目自带副本（首选，零外部依赖）
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "knowledge_base.json"),
    os.path.join("data", "knowledge_base.json"),        # ② 包级数据目录
    os.path.join("..", "data", "knowledge_base.json"),
    os.path.join("..", "..", "data", "knowledge_base.json"),
]


def load_kb(path=None):
    """加载知识库，返回 (kb, source)。

    探测顺序：项目自带 config/ 副本 → 项目 data/ → 上级 data/ → 内置兜底 4 条。
    任何一级命中都返回来源标记，便于排错（避免"悄悄降级"却不知道）。
    """
    cands = [path] if path else KB_CANDIDATES
    items, source = None, "内置兜底(4条)"
    for c in cands:
        if c and os.path.exists(c):
            try:
                raw = json.load(open(c, encoding="utf-8"))
                got = [(cat, it) for cat, lst in raw.items() for it in lst]
                if got:
                    items, source = got, c
                    break
            except Exception:
                continue
    if items is None:
        items = [
            ("设备运维规范", "泵类设备振动速度有效值超过4.5mm/s应列入重点关注，超过7.1mm/s必须停机检查。"),
            ("设备运维规范", "轴承温度报警阈值设定为75℃，达到85℃应立即停机并检查润滑与冷却回路。"),
            ("故障排查指南", "泵体异响且压力波动：优先排查叶轮堵塞与汽蚀，检查进口滤网和液位。"),
            ("故障排查指南", "电机电流偏高而转速正常：排查机械过载、轴承磨损与三相不平衡。"),
        ]
    kb = []
    for i, (cat, txt) in enumerate(items, 1):
        kb.append({"id": "R%d" % i, "category": cat, "text": txt,
                   "tokens": bigrams(txt)})
    if source == "内置兜底(4条)":
        import warnings
        warnings.warn("未找到 knowledge_base.json，已使用内置兜底 4 条（检索覆盖率会下降）")
    return kb, source


def bigrams(text):
    out = set()
    for seg in re.findall(r"[\\u4e00-\\u9fff]+", str(text)):
        if len(seg) >= 2:
            out |= {seg[i:i + 2] for i in range(len(seg) - 1)}
            out.add(seg)
    return out


def retrieve(query, kb, topk=3, min_score=0.05):
    q = bigrams(query)
    scored = [(len(q & k["tokens"]) / max(len(q), 1), k) for k in kb]
    cand = [s for s in scored if s[0] >= min_score]
    cand.sort(key=lambda x: (-x[0], x[1]["id"]))
    return [{"id": k["id"], "category": k["category"], "text": k["text"],
             "score": round(s, 4)} for s, k in cand[:topk]]


def answer(query, kb, topk=3, min_score=0.05):
    hits = retrieve(query, kb, topk, min_score)
    if not hits:
        return {"grounded": False,
                "text": "查无依据：请补充设备编号与测点数据后再检索（宁说无据，不硬编）。",
                "citations": []}
    refs = chr(10).join("  [%s] (%s) %s" % (h["id"], h["category"], h["text"]) for h in hits)
    return {"grounded": True,
            "text": "依据知识库:" + chr(10) + refs + chr(10) + "  → 建议：按上述条款执行并回填工单。",
            "citations": hits}

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""批量问答 → 引用命中统计 → 防幻觉比例。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    kb, source = core.load_kb()
    queries = ["泵振动超标要看哪个标准", "电机电流高但转速正常", "工装夹具的存放位置"]
    rows, grounded = [], 0
    for q in queries:
        a = core.answer(q, kb, topk=int(cfg.topk), min_score=float(cfg.raw.get("min_score", 0.05)))
        grounded += int(a["grounded"])
        rows.append({"query": q, "grounded": a["grounded"], "citations": a["citations"]})
    result = {"kb_size": len(kb), "kb_source": source, "n_queries": len(queries), "grounded": grounded,
              "hallucination_rate": round(1 - grounded / max(len(queries), 1), 4),
              "rows": rows}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    lines = []
    for r in rows:
        if r["grounded"]:
            lines.append("Q: %s" % r["query"])
            lines.append("   → 命中 %d 条 %s（最佳分数 %.3f）"
                         % (len(r["citations"]),
                            ",".join(c["id"] for c in r["citations"]),
                            r["citations"][0]["score"]))
        else:
            lines.append("Q: %s" % r["query"])
            lines.append("   → 查无依据（拒答，未编造）")
    sections = [("输入口径", ["知识库 %d 条（来源: %s）｜二元词重合检索｜Top-%d｜阈值 %.2f"
                        % (len(kb), source, int(cfg.topk), float(cfg.raw.get("min_score", 0.05)))]),
                ("问答明细", lines),
                ("命中率", ["有据可查 %d / %d（幻觉率 %.0f%%）"
                        % (grounded, len(queries), result["hallucination_rate"] * 100)]),
                ("结论与建议", ["RAG 底线='有据可查+诚实拒答'；查无依据的查询用于发现知识库盲区"])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
from rag48 import core

KB, _SRC = core.load_kb()


def test_kb_loaded_with_ids():
    assert KB and KB[0]["id"] == "R1"


def test_kb_comes_from_project_copy_not_fallback():
    """知识库应来自项目自带副本，而非内置兜底（否则说明文件丢失）。"""
    assert _SRC != "内置兜底(4条)" and len(KB) >= 4


def test_bigrams_has_full_segment():
    assert "振动速度" in core.bigrams("振动速度")


def test_retrieve_hits_relevant():
    hits = core.retrieve("泵振动超标标准", KB, topk=2)
    assert hits and "4.5mm/s" in hits[0]["text"]


def test_retrieve_topk():
    assert len(core.retrieve("振动 电机 轴承", KB, topk=1)) == 1


def test_retrieve_empty_on_high_threshold():
    assert core.retrieve("午饭吃什么", KB, min_score=0.9) == []


def test_answer_with_citations():
    a = core.answer("电机电流偏高", KB)
    assert a["grounded"] and a["citations"] and "[R" in a["text"]


def test_answer_refuses_without_evidence():
    a = core.answer("今天午饭吃什么", KB, min_score=0.9)
    assert not a["grounded"] and "查无依据" in a["text"]

''')


# ══════════ M5-1 多智能体检修调度 ══════════
P(id="05-M5-1", week="W19", no="第21次课", title="多智能体检修调度",
  slug="m51_multiagent", pkg="multiagent_sched", deps=[],
  scope="仿真 3 台泵站的检修调度：随机/奖励导向/安全优先三策略对照，"
        "揭示'奖励函数 ≠ KPI'的工程张力，并做奖励敏感性实验。",
  **std("方案", "把调度的管理哲学变成可量化策略", "泵站退化+工单队列 → 动作 → 奖励/正确率",
        "core 策略库+仿真循环；pipeline 三策略对照+敏感性",
        "Python 3.12 + conda ai48；零依赖（自研轻量环境）；pytest",
        [("core.py", "策略库 + 指标", "policy_random()/policy_greedy()/policy_safe()/run()")],
        funcs=[("仿真环境", "退化+队列+奖惩"), ("三策略", "随机/奖励/安全"),
               ("对照指标", "奖励+正确率+停机"), ("敏感性", "收益权重扫描")],
        stories=[("作为班长，我希望知道该追奖励还是追正确率", "三策略对照表")]),
  core_py='''# -*- coding: utf-8 -*-
"""多智能体调度：三策略对照 + 奖励敏感性（纯函数）。"""
import random

N = 3
THRESH = 1.0
IDLE_PENALTY = 5.0
FIX_BENEFIT = 3.0


def policy_random(state, rng):
    return rng.randint(0, N)


def policy_greedy(state, rng):
    """奖励导向：有告警派告警泵；无告警但有队列→派退化最高泵（躲空转罚款）。"""
    al, dg = state["alarm"], state["degrade"]
    cand = [(dg[i], i + 1) for i in range(len(al)) if al[i]]
    if cand:
        return max(cand)[1]
    if state["queue"] > 0:
        return max((dg[i], i + 1) for i in range(len(dg)))[1]
    return 0


def policy_safe(state, rng):
    """安全优先：仅对告警泵派检，无告警则等待（正确率导向）。"""
    al, dg = state["alarm"], state["degrade"]
    cand = [(dg[i], i + 1) for i in range(len(al)) if al[i]]
    return max(cand)[1] if cand else 0


def run(policy, seed=42, horizon=200, fix_benefit=FIX_BENEFIT):
    rng = random.Random(seed)
    degrade = [0.0] * N
    queue = 0
    total = 0.0
    correct = wrong = 0
    downtime = 0
    for _ in range(horizon):
        for i in range(N):
            degrade[i] += rng.uniform(0.02, 0.12)
        if rng.random() < 0.35:
            queue += 1
        dt = sum(1 for d in degrade if d >= THRESH)
        downtime += dt
        r = -float(dt)
        state = {"alarm": [degrade[i] >= THRESH for i in range(N)],
                 "degrade": degrade, "queue": queue}
        a = policy(state, rng)
        if a == 0:
            if queue > 0:
                r -= IDLE_PENALTY
        else:
            i = a - 1
            if degrade[i] >= THRESH:
                r += fix_benefit
                correct += 1
                degrade[i] = 0.0
                queue = max(0, queue - 1)
            else:
                wrong += 1
                r -= 1.0
        total += r
    acc = correct / max(correct + wrong, 1)
    return {"reward": round(total, 1), "accuracy": round(acc, 4),
            "downtime": downtime}

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""三策略对照 + 奖励敏感性实验。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    seed = cfg.seed
    res = {
        "随机": core.run(core.policy_random, seed=seed),
        "奖励导向": core.run(core.policy_greedy, seed=seed),
        "安全优先": core.run(core.policy_safe, seed=seed),
    }
    sens = []
    for fb in (1.0, 3.0, 6.0):
        r = core.run(core.policy_safe, seed=seed, fix_benefit=fb)
        sens.append((fb, r["reward"], r["accuracy"]))
    result = {"strategies": res, "sensitivity": sens}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    lines = ["%-6s 总奖励 %9.1f｜协调正确率 %5.1f%%｜停机 %3d 步"
             % (k, v["reward"], v["accuracy"] * 100, v["downtime"])
             for k, v in res.items()]
    safe_acc = res["安全优先"]["accuracy"]
    sections = [("输入口径", ["3 台泵站｜200 步｜停机罚(-1/台)｜空转罚 5｜正确派检收益 3｜种子 %d" % seed]),
                ("三策略对照", lines),
                ("奖励敏感性（安全优先固定）",
                 ["FIX_BENEFIT=%.1f → 奖励 %.1f｜正确率 %.1f%%" % (fb, rw, ac * 100)
                  for fb, rw, ac in sens]),
                ("结论", ["安全优先正确率 %.1f%%（目标≥75%%）→ %s；但其奖励最低，"
                        "说明奖励函数与 KPI 存在冲突"
                        % (safe_acc * 100, "达标" if safe_acc >= 0.75 else "未达标")]),
                ("结论与建议", ["正确解法是约束优化：把正确率≥75% 设为硬约束，在此约束下再优化奖励"])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
from multiagent_sched import core


def test_run_returns_three_metrics():
    r = core.run(core.policy_random, seed=1, horizon=50)
    assert "reward" in r and 0.0 <= r["accuracy"] <= 1.0 and r["downtime"] >= 0


def test_run_deterministic():
    assert core.run(core.policy_random, seed=7) == core.run(core.policy_random, seed=7)


def test_safe_first_accuracy_high():
    r = core.run(core.policy_safe, seed=42)
    assert r["accuracy"] >= 0.75


def test_greedy_reward_higher_than_safe():
    g = core.run(core.policy_greedy, seed=42)
    s = core.run(core.policy_safe, seed=42)
    assert g["reward"] > s["reward"]


def test_greedy_accuracy_low_than_safe():
    g = core.run(core.policy_greedy, seed=42)
    s = core.run(core.policy_safe, seed=42)
    assert g["accuracy"] < s["accuracy"]


def test_policy_safe_waits_when_no_alarm():
    st = {"alarm": [False, False, False], "degrade": [0.1, 0.2, 0.3], "queue": 5}
    assert core.policy_safe(st, None) == 0


def test_policy_greedy_dispatches_with_queue():
    st = {"alarm": [False, False, False], "degrade": [0.1, 0.9, 0.3], "queue": 5}
    assert core.policy_greedy(st, None) == 2


def test_fix_benefit_increases_reward():
    a = core.run(core.policy_safe, seed=42, fix_benefit=1.0)
    b = core.run(core.policy_safe, seed=42, fix_benefit=6.0)
    assert b["reward"] > a["reward"]

''')


# ══════════ Z 综合项目答辩 ══════════
P(id="05-Z", week="W20", no="第23次课", title="综合项目答辩（档案袋自检）",
  slug="z_defense", pkg="defense_pack", deps=[],
  scope="毕业前最后一道工序：档案袋五层自检 + 一图贯通提纲生成 + 评委三问预演，"
        "'作品集即简历'。",
  **std("方案", "把 12 周积累变成可交付的证据链", "五层 starter 存在性 → 提纲 → 三问预演",
        "core 分层定义 + 自检 + 提纲渲染；pipeline 输出交付清单",
        "Python 3.12 + conda ai48；零依赖；pytest",
        [("core.py", "分层定义/自检/提纲渲染", "LAYERS/check()/outline()")],
        funcs=[("档案袋自检", "五层证据链"), ("提纲生成", "一图贯通"),
               ("评委三问", "需求/方案/评估")],
        stories=[("作为学员，我希望知道材料齐不齐", "n/5 层就绪"),
                 ("作为评委，我希望三问有标准答案", "三问预演")]),
  core_py='''# -*- coding: utf-8 -*-
"""综合答辩：档案袋自检 + 提纲生成（纯函数）。"""
import os

LAYERS = [
    ("数据层", "w1_clean_starter.py", "脏数据→可信数据集：清洗规则与质量分"),
    ("特征层", "w2_feature_starter.py", "特征字典：时域/频域双解与重要性证据"),
    ("模型层", "w3_classify_starter.py", "双模型对比与混淆矩阵里的漏报账"),
    ("服务层", "w9_prompt_starter.py", "三版 Prompt 对比：LLM 回答质量 +50%"),
    ("智能体层", "w11_multiagent_starter.py", "调度策略：随机→安全优先，协调正确率 100%"),
]

THREE_Q = [
    ("① 需求（30秒）", "这个项目解决什么工业问题？给谁用？"),
    ("② 方案（60秒）", "数据从哪来→怎么处理→输出什么（三段式）"),
    ("③ 评估（60秒）", "好在哪？用哪个指标证明？踩过什么坑？"),
]


def check(fw_dir):
    """档案袋自检：返回 [(层, 是否存在, 讲什么), ...]。"""
    out = []
    for name, fn, talk in LAYERS:
        out.append((name, os.path.exists(os.path.join(fw_dir, fn)), talk))
    return out


def outline(rows):
    n_ok = sum(1 for _, ok, _ in rows if ok)
    lines = ["=== 答辩提纲（一图贯通 · 自动生成） ==="]
    for i, (layer, ok, talk) in enumerate(rows, 1):
        lines.append("  %d. %s [%s] —— %s" % (i, layer, "OK" if ok else "--", talk))
    lines.append("")
    lines.append("证据链 %d/%d 层就绪%s" % (n_ok, len(rows),
                 "——可以上台了" if n_ok == len(rows) else "——缺的层答辩前补齐"))
    return lines, n_ok

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""档案袋自检 → 提纲生成 → 评委三问。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    fw = str(cfg.raw.get("fw_dir", "../学生代码框架"))
    if not os.path.isabs(fw):
        fw = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", fw)
    rows = core.check(fw)
    lines, n_ok = core.outline(rows)
    missing = [r[0] for r in rows if not r[1]]
    result = {"layers": [{"layer": r[0], "ok": r[1], "talk": r[2]} for r in rows],
              "ready": n_ok, "total": len(rows), "missing": missing}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    sections = [("输入口径", ["档案袋目录：%s" % os.path.relpath(fw, os.getcwd())]),
                ("自检结果", ["%s %s" % ("OK" if r[1] else "--", r[0]) for r in rows]),
                ("答辩提纲", lines),
                ("评委三问预演", ["%s：%s" % (t, q) for t, q in core.THREE_Q]),
                ("结论与建议", ["证据链 %d/%d；%s"
                          % (n_ok, len(rows),
                             "可上台" if not missing else "补齐：" + "、".join(missing))])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
from defense_pack import core


def test_layers_has_five():
    assert len(core.LAYERS) == 5


def test_three_questions_present():
    assert len(core.THREE_Q) == 3 and "需求" in core.THREE_Q[0][0]


def test_check_returns_flag_per_layer(tmp_path):
    rows = core.check(str(tmp_path))
    assert len(rows) == 5 and all(isinstance(r[1], bool) for r in rows)


def test_outline_counts_ready():
    rows = [("A", True, "t"), ("B", False, "t")]
    lines, n = core.outline(rows)
    assert n == 1 and "1/2" in lines[-1]


def test_outline_all_ready_message():
    rows = [("A", True, "t"), ("B", True, "t")]
    lines, n = core.outline(rows)
    assert n == 2 and "可以上台" in lines[-1]

''')
