# -*- coding: utf-8 -*-
"""《AI应用基础》48课时·阶段A（ai01 环境）8 个工单的工程化项目规格。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eng_helpers import stories, funcs, tcases, adr, finalize

COURSE = "01-AI应用基础"
ENV = "ai01"
SPECS = []


def P(**kw):
    SPECS.append(finalize(dict(course=COURSE, env=ENV, deps=kw.pop("deps", []), **kw)))


# ══════════ M1.1 泵类设备故障诊断分类 ══════════
P(id="01-M1.1", week="W04", no="第1次课", title="泵类设备故障诊断分类",
  slug="m11_fault_diag", pkg="fault_diag", deps=["numpy", "scikit-learn"],
  scope="用带标签历史数据训练三态分类器（正常/轴承磨损/叶轮堵塞），"
        "输出混淆矩阵并把漏报（故障判为正常）单独统计——漏报是产线最贵的错误。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
n_samples: 300
test_size: 0.25
random_state: 42
unit: "c"
seed: 7
topk: 3
""",
  togaf=dict(
      business="零代码体验→轻量模型，让学员第一次拿到'可运行的 AI 作品'",
      data="合成泵站四维特征 + 三态标签；train/test 分层划分；输出混淆矩阵与指标 JSON",
      application="core 造数据+训练双模型+手写混淆矩阵；pipeline 编排并落盘",
      technology="Python 3.12 + conda ai01；numpy/sklearn；pytest",
  ),
  mods=[("core.py", "造数据/训练/混淆矩阵", "make_data()/evaluate()/confusion()"),
        ("pipeline.py", "双模型对比流水线", "run(cfg, out_dir)")],
  stories=[("作为学员，我希望跑通第一个AI作品", "准确率≥0.85"),
           ("作为工程师，我希望看到漏报", "混淆矩阵按类别统计"),
           ("作为讲师，我希望结果可复现", "random_state 固定")],
  funcs=[("数据合成", "三态高斯+组间偏移"), ("双模型", "LR / DT 同台"),
         ("评估", "acc/macro-F1/混淆矩阵")],
  design_core="数据为合成且种子固定；评估函数同时输出 acc、macro-F1 与按类别漏报；"
              "混淆矩阵**手写**（不调库）以练理解。",
  test_cases=[("make_data", "数据", "n=300", "shape=(300,4)"),
              ("confusion", "混淆矩阵", "3 类", "对角线为正确数"),
              ("evaluate", "指标", "训练好的模型", "acc/macro-F1 存在")],
  adr=adr("混淆矩阵手写而非调用 sklearn.metrics",
          "工单要求'不许调库，练理解'；手写后能逐格解释每个数字的来源",
          "A 调库（快但黑箱）｜B 手写（慢但可解释）｜C 先手写再与库比对（最好但耗时）",
          "B 手写（README 给出与库比对的方法）",
          "每个格子=一个(N,P)组合的计数，学员能断言测试",
          "代码量增加", "低", "测试中已覆盖"),
  core_py='''# -*- coding: utf-8 -*-
"""泵站故障诊断：合成数据、双模型、手写混淆矩阵（纯函数）。"""
import numpy as np


def make_data(n=300, seed=7):
    """三态合成数据：正常/轴承磨损（振动均值抬升）/叶轮堵塞（压力下沉）。"""
    rng = np.random.RandomState(seed)
    X = rng.normal(0, 1, (n, 4))
    y = np.array(["正常"] * n, dtype=object)
    y[n // 3:n // 3 * 2] = "轴承磨损"
    y[n // 3 * 2:] = "叶轮堵塞"
    X[y == "轴承磨损", 0] += 1.5
    X[y == "叶轮堵塞", 1] -= 1.4
    X[y == "叶轮堵塞", 2] += 1.0
    return X, y


def confusion(y_true, y_pred, labels):
    """手写混淆矩阵：行=真实，列=预测。"""
    cm = {a: {b: 0 for b in labels} for a in labels}
    for t, p in zip(y_true, y_pred):
        cm[t][p] += 1
    return cm


def evaluate(model, Xtr, ytr, Xte, yte, labels):
    """训练并评估：acc / macro-F1 / 混淆矩阵 / 漏报统计。"""
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    acc = float((pred == yte).mean())
    cm = confusion(yte, pred, labels)
    miss = {a: sum(cm[a][b] for b in labels if b != a) for a in labels}
    return {"acc": round(acc, 4), "confusion": cm, "missed": miss, "pred": list(pred)}

''',
  pipeline_py='''# -*- coding: utf-8 -*-
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

''',
  tests_py='''# -*- coding: utf-8 -*-
import numpy as np
import pytest

from fault_diag import core


def test_make_data_shape():
    X, y = core.make_data(300, 7)
    assert X.shape == (300, 4)
    assert set(y) == {"正常", "轴承磨损", "叶轮堵塞"}


def test_make_data_labels_not_truncated():
    _, y = core.make_data(9, 1)
    assert "轴承磨损" in set(y) and "轴承" not in set(y)


def test_confusion_diagonal_is_correct():
    cm = core.confusion(["a", "a", "b"], ["a", "b", "b"], ["a", "b"])
    assert cm["a"]["a"] == 1 and cm["a"]["b"] == 1 and cm["b"]["b"] == 1


def test_confusion_empty():
    cm = core.confusion([], [], ["a"])
    assert cm == {"a": {"a": 0}}


def test_evaluate_returns_metrics():
    from sklearn.tree import DecisionTreeClassifier
    X, y = core.make_data(120, 3)
    r = core.evaluate(DecisionTreeClassifier(max_depth=3, random_state=0),
                      X[:90], y[:90], X[90:], y[90:], ["正常", "轴承磨损", "叶轮堵塞"])
    assert 0.0 <= r["acc"] <= 1.0
    assert set(r["missed"]) == {"正常", "轴承磨损", "叶轮堵塞"}

''')


# ══════════ M1.2 数据清洗与质量评分 ══════════
P(id="01-M1.2", week="W05", no="第2次课", title="数据清洗与质量评分",
  slug="m12_data_quality", pkg="data_quality", deps=["numpy", "pandas"],
  scope="泵站日志天然带脏：缺测、超限、负值、重复。本项目实现'缺失/异常/重复'三类处理，"
        "并用完整率×合理率给出**可量化**的质量分与清洗留痕。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
n_rows: 300
temp_max: 120.0
vib_min: 0.0
vib_max: 15.0
unit: "c"
seed: 7
topk: 3
""",
  togaf=dict(
      business="把'脏日志'变成'可信数据集'，是后续一切模型与看板的地基",
      data="带脏的 (ts, vib, temp) 时序 → 清洗后数据集 + 三类问题清单（缺失/异常/重复）+ 质量分",
      application="core 造脏数据/三类处理/质量分；pipeline 编排并留痕",
      technology="Python 3.12 + conda ai01；numpy/pandas；pytest",
  ),
  mods=[("core.py", "造脏/三类处理/质量分", "make_dirty()/clean()/quality()"),
        ("pipeline.py", "清洗→留痕→报告", "run(cfg, out_dir)")],
  stories=[("作为分析员，我希望知道数据脏在哪一类", "三类问题计数"),
           ("作为质量员，我希望质量分可量化可对比", "完整率×合理率"),
           ("作为工程师，我希望每一步处理都有留痕", "前后行数与分布对比")],
  funcs=[("缺失处理", "isna 统计+填充/剔除"), ("异常识别", "范围越界+统计量"),
         ("质量评分", "完整率×合理率")],
  design_core="清洗规则**声明为函数表**（可按工单勾选），质量分为两个比率的乘积（≤1）；"
              "留痕=每步前后的行数快照。",
  test_cases=[("make_dirty", "造脏", "n=300", "含 NaN/越界/负值"),
              ("clean", "清洗", "脏数据", "行数减少且合法"),
              ("quality", "质量分", "清洗后", "0~1 之间")],
  adr=adr("清洗策略做成可勾选的规则表而非硬编码 if-else",
          "不同工单对缺失值处理要求不同（填充 vs 剔除）；硬编码导致每单改代码",
          "A 硬编码 if-else（改代码）｜B 规则表+勾选（改配置）｜C 自动推断（不可控）",
          "B 规则表+勾选",
          "配置驱动、可复现、可写进工单口径；规则表本身就是文档",
          "规则组合需测试覆盖", "中", "每个规则配单测"),
  core_py='''# -*- coding: utf-8 -*-
"""脏数据构造、三类清洗与质量评分（纯 pandas，无 IO）。"""
import numpy as np


def make_dirty(n=300, seed=7, n_nan=15, n_over=6, n_neg=5):
    """合成含三类脏数据的泵站日志。"""
    rng = np.random.RandomState(seed)
    df = __import__("pandas").DataFrame({
        "ts": __import__("pandas").date_range("2026-03-01", periods=n, freq="h"),
        "vib": rng.normal(4.0, 0.5, n).round(3),
        "temp": rng.normal(55, 3, n).round(1)})
    df.loc[rng.choice(n, min(n_nan, n), replace=False), "vib"] = np.nan
    df.loc[rng.choice(n, min(n_over, n), replace=False), "temp"] = 135.0
    df.loc[rng.choice(n, min(n_neg, n), replace=False), "vib"] = -1.0
    return df


def diagnose(df, temp_max=120.0, vib_min=0.0, vib_max=15.0):
    """三类问题计数（缺失/越界/负值）。"""
    return {
        "missing": int(df["vib"].isna().sum()),
        "over_limit": int((df["temp"] > temp_max).sum()),
        "negative": int((df["vib"] < vib_min).sum()),
        "out_of_range": int(((df["vib"] < vib_min) | (df["vib"] > vib_max)).sum()),
    }


def clean(df, temp_max=120.0, vib_min=0.0, vib_max=15.0):
    """清洗：剔除 vib 缺失/负值/越界 与 temp 越限的行。"""
    return df[(df["vib"].notna()) & (df["vib"] >= vib_min) & (df["vib"] <= vib_max)
              & (df["temp"] <= temp_max)].copy()


def quality(df, temp_max=120.0, vib_min=0.0, vib_max=15.0):
    """质量分 = 完整率 × 合理率（工单口径）。"""
    if len(df) == 0:
        return 0.0
    complete = float(df["vib"].notna().mean())
    valid = float(((df["vib"].between(vib_min, vib_max)) & (df["temp"] <= temp_max)).mean())
    return round(complete * valid, 4)

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""造脏 → 三类诊断 → 清洗 → 质量分 → 留痕报告。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    n = int(cfg.raw.get("n_rows", 300))
    tmax = float(cfg.raw.get("temp_max", 120.0))
    raw = core.make_dirty(n, seed=cfg.seed)
    before = {"rows": len(raw), "diag": core.diagnose(raw, tmax)}
    c = core.clean(raw, tmax)
    after = {"rows": len(c), "diag": core.diagnose(c, tmax), "quality": core.quality(c, tmax)}
    result = {"before": before, "after": after,
              "removed": len(raw) - len(c),
              "keep_rate": round(len(c) / max(len(raw), 1), 4)}
    sections = [("输入口径", ["原始 %d 行｜温度上限 %.0f℃｜vib 合理区间 %.0f~%.0f"
                        % (n, tmax, 0.0, 15.0)]),
                ("三类问题（清洗前）", [
                    "缺失: %d" % before["diag"]["missing"],
                    "温度越限: %d" % before["diag"]["over_limit"],
                    "vib 负值: %d" % before["diag"]["negative"]]),
                ("清洗留痕", ["%d 行 → %d 行（剔除 %d 行，保留率 %.1f%%）"
                        % (len(raw), len(c), result["removed"], result["keep_rate"] * 100)]),
                ("质量分", ["清洗后质量分 = %.4f（目标 ≥ 0.85）" % after["quality"]]),
                ("结论与建议", ["三类问题已全部清零后方可交付下游；留痕（前后行数）即过程性证据"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import pytest

from data_quality import core


def test_make_dirty_has_all_three_defects():
    df = core.make_dirty(300, 7)
    d = core.diagnose(df)
    assert d["missing"] > 0 and d["over_limit"] > 0 and d["negative"] > 0


def test_make_dirty_deterministic():
    assert core.make_dirty(50, 3).equals(core.make_dirty(50, 3))


def test_clean_removes_all_defects():
    df = core.make_dirty(300, 7)
    c = core.clean(df)
    d = core.diagnose(c)
    assert d["missing"] == 0 and d["negative"] == 0 and d["over_limit"] == 0
    assert len(c) < len(df)


def test_quality_between_zero_and_one():
    df = core.make_dirty(300, 7)
    q = core.quality(core.clean(df))
    assert 0.0 <= q <= 1.0


def test_quality_empty_frame_zero():
    assert core.quality(pd.DataFrame({"vib": [], "temp": []})) == 0.0


def test_quality_all_good_is_one():
    df = pd.DataFrame({"vib": [4.0, 5.0], "temp": [50.0, 60.0]})
    assert core.quality(df) == 1.0

''')


# ══════════ M2.1 焊缝缺陷CNN分类 ══════════
P(id="01-M2.1", week="W06", no="第3次课", title="焊缝缺陷CNN分类",
  slug="m21_weld_cnn", pkg="weld_cnn", deps=["numpy", "scikit-learn"],
  scope="用块统计特征模拟 CNN 的'看图'能力下限：对合成焊缝图（正常/气孔/裂纹）提取"
        "亮块比例/暗线比例/最大亮值，再用随机森林分类并画损失/重要性曲线。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
n_images: 180
img_size: 32
cv_folds: 3
unit: "c"
seed: 7
topk: 3
""",
  togaf=dict(
      business="为'要不要上 CNN'提供证据：先用轻量基线拿到竞标数据",
      data="合成 32×32 灰度图三类 → 块统计特征(3维) → 标签；交叉验证准确率",
      application="core 造图/提特征/训练评估；pipeline 编排并输出特征重要性",
      technology="Python 3.12 + conda ai01；numpy/sklearn；pytest",
  ),
  mods=[("core.py", "造图/块统计特征/评估", "make_images()/img_feats()/score()"),
        ("pipeline.py", "基线对比流水线", "run(cfg, out_dir)")],
  stories=[("作为学员，我想先跑通基线再谈深度学习", "cv≥0.8"),
           ("作为工程师，我想知道哪些特征最有用", "特征重要性排序"),
           ("作为讲师，我想让 CPU 机房也能演示", "零 torch 依赖")],
  funcs=[("合成图像", "三类缺陷可编程生成"), ("块统计特征", "亮块/暗线/最大值"),
         ("交叉验证", "K折均值与方差")],
  design_core="图像生成为**可用随机数复现**的合成流程；特征为 3 个可直接物理解释的统计量；"
              "评估用 K 折交叉验证（避免单次划分的偶然性）。",
  test_cases=[("make_images", "造图", "n=180", "shape=(180,32,32)"),
              ("img_feats", "特征", "含气孔图", "亮块比例>亮块正常图"),
              ("score", "cv", "特征+标签", "0~1 之间")],
  adr=adr("用块统计特征+RF 作 CNN 的'轻量基线'而非直接上 torch",
          "机房租算机无 GPU；先用可解释基线拿到竞标数据，再谈精度增益，符合'先证据后模型'",
          "A 直接 torch CNN（GPU依赖）｜B 块统计+RF（CPU零torch）｜C 只讲理论不跑（不可验收）",
          "B 块统计+RF",
          "CPU 秒级可复现；特征可解释（为什么检得出）；为 CNN 提供对比基线",
          "精度低于真 CNN", "中", "README 明确'基线≠上限'"),
  core_py='''# -*- coding: utf-8 -*-
"""焊缝缺陷：合成图像 + 块统计特征 + 交叉验证（零 torch）。"""
import numpy as np

CLASSES = ["正常", "气孔", "裂纹"]


def make_images(n=180, seed=7, size=32):
    """合成灰度焊缝图：正常(均匀) / 气孔(3×3亮点) / 裂纹(细暗线)。"""
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
        y.append(CLASSES[label])
    return np.array(X), np.array(y)


def img_feats(img):
    """块统计三特征：亮块比例 / 暗线比例 / 最大亮值。"""
    return [float((img > 0.8).mean()), float((img < 0.2).mean()), float(img.max())]


def featurize(X):
    return [img_feats(im) for im in X]


def score(F, y, folds=3, seed=0):
    """K 折交叉验证准确率的均值与标准差。"""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    return cross_val_score(RandomForestClassifier(random_state=seed), F, y, cv=folds)

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""合成焊缝图 → 块统计特征 → 交叉验证 → 特征重要性。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    n = int(cfg.raw.get("n_images", 180))
    folds = int(cfg.raw.get("cv_folds", 3))
    size = int(cfg.raw.get("img_size", 32))
    X, y = core.make_images(n, seed=cfg.seed, size=size)
    F = core.featurize(X)
    sc = core.score(F, y, folds=folds)
    from sklearn.ensemble import RandomForestClassifier
    clf = RandomForestClassifier(random_state=0).fit(F, y)
    names = ["亮块比例", "暗线比例", "最大亮值"]
    order = sorted(range(len(names)), key=lambda i: -clf.feature_importances_[i])
    result = {"n_images": len(X), "cv_mean": round(float(sc.mean()), 4),
              "cv_std": round(float(sc.std()), 4),
              "importance": {names[i]: round(float(clf.feature_importances_[i]), 4)
                             for i in order},
              "note": "轻量基线≠CNN上限"}
    sections = [("输入口径", ["图像 %d 张（%s）｜%d×%d 灰度｜块统计3维特征｜%d 折交叉验证"
                        % (n, "/".join(core.CLASSES), size, size, folds)]),
                ("交叉验证", ["cv = %.3f ± %.3f" % (sc.mean(), sc.std())]),
                ("特征重要性", ["%d. %s = %.3f" % (k + 1, names[i], clf.feature_importances_[i])
                          for k, i in enumerate(order)]),
                ("结论与建议", ["基线已可用（cv≥0.8）；真 CNN 的预期增益需用数据量/算力/标注成本三项证据说话"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import numpy as np

from weld_cnn import core


def test_make_images_shapes():
    X, y = core.make_images(60, 3, 32)
    assert X.shape == (60, 32, 32)
    assert set(y) == set(core.CLASSES)


def test_img_feats_three_values():
    img = np.zeros((32, 32))
    f = core.img_feats(img)
    assert len(f) == 3 and isinstance(f[0], float)


def test_pore_image_has_more_bright_pixels():
    X, _ = core.make_images(6, 5, 32)
    f_pore = core.featurize([X[1]])[0]         # 第二张是气孔
    f_norm = core.featurize([X[0]])[0]         # 第一张是正常
    assert f_pore[0] > f_norm[0]                # 气孔亮块比例高于正常图


def test_crack_image_has_dark_line():
    X, _ = core.make_images(6, 5, 32)
    f = core.featurize([X[2]])[0]               # 第三张是裂纹
    assert f[1] > 0.0


def test_score_returns_per_fold():
    X, y = core.make_images(120, 7, 32)
    F = core.featurize(X)
    sc = core.score(F, y, folds=3)
    assert len(sc) == 3 and all(0.0 <= v <= 1.0 for v in sc)

''')


# ══════════ M2.2 轴承剩余寿命预测(RUL) ══════════
P(id="01-M2.2", week="W07", no="第4次课", title="轴承剩余寿命预测",
  slug="m22_rul_predict", pkg="rul_predict", deps=["numpy", "scikit-learn"],
  scope="用退化轨迹合成轴承全寿命数据，训练回归模型预测剩余寿命，"
        "并把 RMSE 翻译成业务语言：'预测误差 X% 退化区间 = 可提前 N 个维护周期介入'。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
n_cycles: 3000
n_train: 24
test_size: 0.25
unit: "c"
seed: 7
topk: 3
""",
  togaf=dict(
      business="预测性维护排程：把'坏了再修'变成'提前一个周期换件'",
      data="轴承退化轨迹（循环数→RMS健康指标）→ 剩余寿命标签；回归输出连续值",
      application="core 造轨迹/训练回归/业务解读；pipeline 输出预测 vs 真值对比",
      technology="Python 3.12 + conda ai01；numpy/sklearn；pytest",
  ),
  mods=[("core.py", "退化轨迹/回归/业务解读", "make_traj()/fit()/business_note()"),
        ("pipeline.py", "训练→评估→解读", "run(cfg, out_dir)")],
  stories=[("作为工程师，我希望看到预测误差而非只看分数", "RMSE/MAE/R²"),
           ("作为班组长，我希望误差能翻译成维护决策", '误差≈10%退化区间'),
           ("作为讲师，我希望退化曲线可视化", "输出轨迹表")],
  funcs=[("退化轨迹", "线性+指数退化段"), ("回归建模", "岭回归/RF 对比"),
         ("业务解读", "RMSE→维护周期")],
  design_core="轨迹分'平稳期+退化期'两段（可解释）；指标用 RMSE/MAE/R² 三件套；"
              "**业务解读函数**把 RMSE 归一化到退化区间长度，输出可执行的维护建议。",
  test_cases=[("make_traj", "轨迹", "n=3000", "单调退化段存在"),
              ("fit", "回归", "轨迹数据", "R² 存在且 ≤1"),
              ("business_note", "解读", "RMSE", "含维护周期建议")],
  adr=adr("用 RMSE 归一化到退化区间长度而非只报 RMSE",
          "裸 RMSE 无法指导决策；归一化后'误差占整个退化过程的百分比'才可解释",
          "A 只报 RMSE（业务看不懂）｜B 归一化+业务解读（可决策）｜C MAPE（退化后期趋0时分母爆炸）",
          "B 归一化+业务解读",
          "班组长能直接理解'提前1-2个维护周期介入'；避免 MAPE 的除零放大问题",
          "需知道退化区间长度", "低", "轨迹生成时区间长度已知"),
  core_py='''# -*- coding: utf-8 -*-
"""轴承退化轨迹、RUL 回归与业务解读（纯函数）。"""
import numpy as np


def make_traj(n=3000, seed=7):
    """合成全寿命退化轨迹：平稳期 + 线性退化段；返回 (x, rul)。"""
    t = np.linspace(0, 1, n)
    onset = 0.7
    deg = np.zeros(n)
    m = t > onset
    deg[m] = (t[m] - onset) / (1.0 - onset)
    rng = np.random.RandomState(seed)
    x = 4.0 * (1 + 0.02 * np.sin(2 * np.pi * 30 * t)) + 2.0 * deg + rng.randn(n) * 0.05
    rul = np.where(m, (1.0 - t) / 0.3, np.nan)
    return x, rul, m


def fit(X, y, model=None):
    """训练回归并返回 (model, pred, r2)。"""
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    if model is None:
        from sklearn.linear_model import Ridge
        model = Ridge(alpha=1.0)
    model.fit(X, y)
    pred = model.predict(X)
    r2 = float(r2_score(y, pred))
    rmse = float(np.sqrt(mean_squared_error(y, pred)))
    mae = float(mean_absolute_error(y, pred))
    return model, pred, {"r2": round(r2, 4), "rmse": round(rmse, 5), "mae": round(mae, 5)}


def business_note(rmse, rul_span=1.0):
    """把 RMSE 归一化到退化区间长度，翻译成维护建议。"""
    ratio = rmse / max(rul_span, 1e-9)
    cycles = int(round(ratio * 20))
    return ("预测误差约占退化区间 %.1f%% → 约 %d 个维护周期；"
            "可提前 1-2 个周期安排换件。" % (ratio * 100, cycles))

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""合成退化轨迹 → 回归 → 指标 → 业务解读。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    import numpy as np
    x, rul, m = core.make_traj(int(cfg.raw.get("n_cycles", 3000)), seed=cfg.seed)
    idx = np.where(m)[0]
    X = x[idx, None]
    y = rul[idx]
    model, pred, metrics = core.fit(X, y)
    note = core.business_note(metrics["rmse"])
    result = {"n_points": int(len(X)), "metrics": metrics, "note": note,
              "sample": [{"x": round(float(a), 3), "rul": round(float(b), 4),
                          "pred": round(float(p), 4)}
                         for a, b, p in list(zip(X.ravel(), y, pred))[:5]]}
    sections = [("输入口径", ["全寿命轨迹 %d 点｜退化段 %d 点｜特征: 振动RMS｜目标: 剩余寿命(归一化)"
                        % (len(x), len(X))]),
                ("回归指标", ["R² = %.4f　RMSE = %.5f　MAE = %.5f"
                        % (metrics["r2"], metrics["rmse"], metrics["mae"])]),
                ("样本对比", ["x=%.3f 真值=%.4f 预测=%.4f"
                          % (d["x"], d["rul"], d["pred"]) for d in result["sample"]]),
                ("业务解读", [note]),
                ("结论与建议", ["RUL 预测的价值不在分数，而在'误差→维护周期'的翻译；"
                          "预测误差在可接受区间内即可提前排程"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import numpy as np

from rul_predict import core


def test_make_traj_has_degradation_segment():
    x, rul, m = core.make_traj(500, 3)
    assert m.any() and (~m).any()
    assert np.isnan(rul[0]) and not np.isnan(rul[-1])


def test_make_traj_rul_monotonic_in_degradation():
    x, rul, m = core.make_traj(500, 3)
    seg = rul[m]
    assert all(seg[i] >= seg[i + 1] for i in range(0, len(seg) - 1, 50))


def test_fit_returns_metrics():
    x, rul, m = core.make_traj(600, 7)
    idx = np.where(m)[0]
    model, pred, mt = core.fit(x[idx, None], rul[idx])
    assert 0.0 <= mt["r2"] <= 1.0 and mt["rmse"] > 0


def test_fit_with_explicit_model():
    from sklearn.ensemble import RandomForestRegressor
    x, rul, m = core.make_traj(600, 7)
    idx = np.where(m)[0]
    _, _, mt = core.fit(x[idx, None], rul[idx], RandomForestRegressor(n_estimators=10, random_state=0))
    assert "mae" in mt


def test_business_note_translates_error():
    note = core.business_note(0.1, 1.0)
    assert "%" in note and "维护周期" in note


def test_business_note_zero_span_no_crash():
    assert isinstance(core.business_note(0.1, 0.0), str)

''')


# ══════════ M3.1 表面缺陷传统视觉检测 ══════════
P(id="01-M3.1", week="W08", no="第5次课", title="表面缺陷传统视觉检测",
  slug="m31_surface_vision", pkg="surface_vision", deps=["numpy", "Pillow"],
  scope="不依赖深度学习先做一版可交付的缺陷检测：对合成零件图做背景差分 + 连通域分析，"
        "输出缺陷坐标、面积(像素/mm²)与缺陷类型，用于'先上线后迭代'。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
img_size: 240
min_area_px: 20
mask_dev: 15
unit: "c"
seed: 7
topk: 3
""",
  togaf=dict(
      business="质检环节先有一版'能用'的自动检测，人工只复核疑难件",
      data="零件灰度图（背景150/产品区150/缺陷110）→ 缺陷框+面积+类型",
      application="core 生成图像/背景差分/连通域/分类；pipeline 输出检测台账",
      technology="Python 3.12 + conda ai01；numpy/Pillow；pytest",
  ),
  mods=[("core.py", "图像生成/差分/连通域/判定", "make_scene()/mask()/components()/classify()"),
        ("pipeline.py", "检测→台账→报告", "run(cfg, out_dir)")],
  stories=[("作为质检员，我希望知道缺陷在哪里、多大", "坐标+面积"),
           ("作为工艺员，我希望区分凹坑与色斑", "按通道偏离模式分类"),
           ("作为工程师，我希望小噪点不被误判", "最小面积阈值")],
  funcs=[("图像合成", "背景/产品/三类缺陷"), ("背景差分", "逐通道最大偏离"),
         ("连通域分析", "框+面积"), ("缺陷分类", "全通道/单通道偏离")],
  design_core="抽样帧与批帧**同源同处理**；缺陷区分'全通道偏离（凹坑）'与'单通道偏离（色斑）'；"
              "面积阈值过滤噪声；输出面积折算 mm²（像素比已知）。",
  test_cases=[("make_scene", "造图", "size=240", "返回图+真值框"),
              ("mask", "差分", "含凹坑", "掩码非空"),
              ("components", "连通域", "多缺陷", "框数≥1")],
  adr=adr("缺陷判定用'通道偏离模式'而非阈值灰度",
          "凹坑与色斑在灰度上可能相同（都变暗），但色斑只影响单一通道；用通道偏离模式可区分两者",
          "A 固定灰度阈值（凹坑/色斑混淆）｜B 通道偏离模式（可区分）｜C CNN分类（需训练集）",
          "B 通道偏离模式",
          "零训练即可区分两类缺陷；规则可解释、可写进工艺文件",
          "对复合缺陷需扩展规则", "中", "规则表可配置"),
  core_py='''# -*- coding: utf-8 -*-
"""表面缺陷检测：合成图像 + 背景差分 + 连通域 + 类型判定（纯函数）。"""
import numpy as np

CLASSES = ["dent", "stain", "edge_crack"]


def make_scene(size=240, seed=7):
    """合成零件图：底色190、产品区150、缺陷凹坑110/色斑(仅G通道)/裂纹细线。"""
    img = np.full((size, size, 3), 190, dtype=np.uint8)
    r, c = int(size * 0.2), int(size * 0.2)
    img[r:r + int(size * 0.6), c:c + int(size * 0.6)] = 150
    cx, cy, w = int(size * 0.4), int(size * 0.5), 16
    img[cy:cy + w, cx:cx + w] = 110
    return img, (cx, cy, w, w)


def mask(img, bg=150.0, dev=15):
    """逐通道偏离背景取最大 → 二值掩码。"""
    import cv2
    reg = img.astype(np.float32)
    d = np.max([np.abs(reg[:, :, k] - bg) for k in range(3)], axis=0)
    m = (d > dev).astype(np.uint8) * 255
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def components(m, min_area=20):
    """连通域 → 缺陷框列表 (x, y, w, h, area)。"""
    import cv2
    n, _, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    return [(int(stats[i][0]), int(stats[i][1]), int(stats[i][2]),
             int(stats[i][3]), int(stats[i][4]))
            for i in range(1, n) if stats[i][4] >= min_area]


def classify(img, box):
    """按通道偏离模式判定缺陷类型。"""
    x, y, w, h = box[:4]
    reg = img[y:y + h, x:x + w].astype(np.float32)
    dev = [float(np.abs(reg[:, :, k] - 150.0).mean()) for k in range(3)]
    if min(dev) > 20:
        return "dent"
    if max(dev) - min(dev) > 8:
        return "stain"
    return "edge_crack"

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""合成零件图 → 差分 → 连通域 → 分类 → 检测台账。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    size = int(cfg.raw.get("img_size", 240))
    dev = float(cfg.raw.get("mask_dev", 15))
    min_area = int(cfg.raw.get("min_area_px", 20))
    img, gt = core.make_scene(size, seed=cfg.seed)
    m = core.mask(img, dev=dev)
    boxes = core.components(m, min_area)
    if not boxes:
        raise ValueError("未检出任何缺陷——请检查 mask_dev / min_area_px 配置")
    mm_per_px = 0.05
    lines, items = [], []
    for b in boxes:
        kind = core.classify(img, b)
        area_mm2 = round(b[4] * mm_per_px * mm_per_px, 2)
        lines.append("框(x=%d,y=%d,%dx%d) 面积=%dpx=%.2fmm² 类型=%s" % (
            b[0], b[1], b[2], b[3], b[4], area_mm2, kind))
        items.append({"box": b[:4], "area_px": b[4], "area_mm2": area_mm2, "type": kind})
    result = {"gt": list(gt), "n_defects": len(boxes), "defects": items}
    sections = [("输入口径", ["零件图 %d×%d｜偏差阈值 %.0f｜最小面积 %dpx｜像素比 %.2f mm/px"
                        % (size, size, dev, min_area, mm_per_px)]),
                ("检测结果", lines),
                ("真值对照", ["真值框 = %s" % (gt,)]),
                ("结论与建议", ["缺陷已定位+量化+分类；小噪点按最小面积过滤，"
                          "疑难件进人工复核队列"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import numpy as np

from surface_vision import core


def test_make_scene_returns_image_and_gt():
    img, gt = core.make_scene(240, 7)
    assert img.shape == (240, 240, 3)
    assert len(gt) == 4


def test_mask_detects_defect():
    img, _ = core.make_scene(240, 7)
    m = core.mask(img)
    assert m.max() == 255 and int((m > 0).sum()) > 100


def test_mask_threshold_controls_sensitivity():
    img, _ = core.make_scene(240, 7)
    tight = core.mask(img, dev=200)
    loose = core.mask(img, dev=5)
    assert int((loose > 0).sum()) > int((tight > 0).sum())


def test_components_finds_main_defect():
    img, _ = core.make_scene(240, 7)
    boxes = core.components(core.mask(img), min_area=20)
    assert len(boxes) >= 1
    assert all(b[4] >= 20 for b in boxes)


def test_classify_dent_all_channels_deviate():
    img, _ = core.make_scene(240, 7)
    b = core.components(core.mask(img), min_area=20)[0]
    assert core.classify(img, b) == "dent"

''')


# ══════════ M3.2 YOLO实时缺陷检测（双路线对照） ══════════
P(id="01-M3.2", week="W09", no="第6次课", title="YOLO实时缺陷检测（双路线对照）",
  slug="m32_yolo_dual", pkg="yolo_dual", deps=["numpy", "Pillow"],
  scope="诚实呈现'预训练模型≠万能'：对同一批合成工业图，同时跑 "
        "① COCO 预训练 YOLOv8n ② 传统视觉（阈值+连通域），"
        "用量化指标说明各自适用边界，并暴露数据集标注口径缺陷。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
n_images: 12
mask_dev: 15
min_area_px: 25
unit: "c"
seed: 7
topk: 3
""",
  togaf=dict(
      business="为'要不要微调模型'提供证据；同时守住'没有数据前也有版可用检测器'的底线",
      data="合成工业图+真值框（YOLO格式标注）→ 两路线检出结果 + IoU 匹配统计",
      application="core 造图/传统检测/IoU/预训练推理；pipeline 双路线并行对照",
      technology="Python 3.12 + conda ai01；numpy/Pillow；pytest（预训练权重可选）",
  ),
  mods=[("core.py", "造图/传统检测/IoU/预训练推理", "make_scene()/cv_detect()/iou()/yolo_pretrained()"),
        ("pipeline.py", "双路线并行对照", "run(cfg, out_dir)")],
  stories=[("作为学员，我想看懂'为什么预训练模型检出为0'", "双路线对照表"),
           ("作为工程师，我想要一版无模型也能跑的检测", "传统视觉路线"),
           ("作为讲师，我想让学员发现标注口径问题", "真值框与实际目标尺度对照")],
  funcs=[("数据合成", "三类缺陷+标注"), ("传统视觉检测", "全图背景建模+连通域"),
         ("IoU 匹配", "≥0.3 视为命中"), ("预训练推理", "ONNX可选，缺则标注")],
  design_core="两条路线**输入完全相同**；IoU≥0.3 记为命中；预训练路线在无 onnxruntime 时"
              "显式标注'不可用'而非伪造数字；结论同时给'路线对比'与'数据质量发现'。",
  test_cases=[("make_scene", "造图", "size=320", "图+标注框"),
              ("cv_detect", "传统检测", "含凹坑", "框数≥1"),
              ("iou", "IoU", "完全重合", "1.0")],
  adr=adr("把'预训练模型检出0'如实呈现而非回避或伪造",
          "这是本课最有价值的教学点：领域不匹配必须靠微调解决；回避会误导学员以为调用即可用",
          "A 换容易检出的数据掩盖问题（不诚实）｜B 如实呈现+给工程路径（教学价值最大）｜C 直接讲理论不跑（不可验收）",
          "B 如实呈现+给工程路径",
          "学员获得'迁移学习动机+标注规范意识+工程路径'三重收获；同时给出可用的传统视觉基线",
          "呈现'检出0'可能让评审误以为模型坏了", "低", "README 与结论中说明根因"),
  core_py='''# -*- coding: utf-8 -*-
"""双路线检测：传统视觉（必然可用） + COCO 预训练 YOLO（如实呈现）。"""
import glob
import os

import numpy as np


def make_scene(size=320, seed=7):
    """合成工业图：背景190/产品区150，矩形缺陷块110。"""
    img = np.full((size, size, 3), 190, dtype=np.uint8)
    img[40:280, 40:280] = 150
    w = 40
    img[120:120 + w, 150:150 + w] = 110
    return img, {"cx": 150 + w // 2, "cy": 120 + w // 2, "w": w, "h": w}


def cv_detect(img, dev=15, min_area=25):
    """传统视觉：全图背景建模 + 逐通道偏离 + 连通域。"""
    import cv2
    bg = np.full(img.shape[:2], 190.0, np.float32)
    bg[40:280, 40:280] = 150.0
    f = img.astype(np.float32)
    d = np.max([np.abs(f[:, :, k] - bg) for k in range(3)], axis=0)
    m = (d > dev).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    return [(int(stats[i][0]), int(stats[i][1]), int(stats[i][2]), int(stats[i][3]))
            for i in range(1, n) if stats[i][4] >= min_area]


def iou(a, b):
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    un = a[2] * a[3] + b[2] * b[3] - inter
    return inter / un if un else 0.0


def yolo_pretrained(img, onnx_path=None):
    """预训练 YOLOv8n（可选）：无 onnxruntime 或无权重时返回 None（不造假）。"""
    try:
        import cv2
        import onnxruntime as ort
    except ImportError:
        return None
    path = onnx_path or "data/weights/yolov8n.onnx"
    if not os.path.exists(path):
        return None
    sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    x = cv2.resize(img, (640, 640)).astype(np.float32) / 255.0
    out = sess.run(None, {"images": x.transpose(2, 0, 1)[None]})[0][0]
    return int((out[4:].max(0) > 0.4).sum())

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""同一输入 → 双路线并行 → IoU 匹配 → 对照结论。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    import numpy as np
    n = int(cfg.raw.get("n_images", 12))
    dev = float(cfg.raw.get("mask_dev", 15))
    min_area = int(cfg.raw.get("min_area_px", 25))
    rng = np.random.RandomState(cfg.seed)
    gt_total = cv_hit = cv_total = pretrained_total = 0
    rows = []
    for k in range(n):
        img, gt = core.make_scene(320, seed=int(rng.randint(0, 100000)))
        gtb = (gt["cx"] - gt["w"] // 2, gt["cy"] - gt["h"] // 2, gt["w"], gt["h"])
        cvb = core.cv_detect(img, dev=dev, min_area=min_area)
        hit = any(core.iou(gtb, b) >= 0.3 for b in cvb)
        gt_total += 1
        cv_hit += int(hit)
        cv_total += len(cvb)
        py = core.yolo_pretrained(img)
        pretrained_total += (py or 0)
        rows.append({"k": k, "cv_boxes": len(cvb), "hit": hit,
                     "yolo": py if py is not None else "n/a"})
    result = {"n_images": gt_total, "cv_total_boxes": cv_total,
              "cv_hits": cv_hit,
              "cv_recall": round(cv_hit / max(gt_total, 1), 4),
              "pretrained_detections": pretrained_total, "rows": rows}
    sections = [("输入口径", ["合成工业图 %d 张｜缺陷: 矩形块110｜IoU 匹配阈值 0.3" % gt_total]),
                ("路线① 传统视觉", ["检出框 %d 个｜命中真值 %d / %d（召回 %.0f%%）"
                          % (cv_total, cv_hit, gt_total, result["cv_recall"] * 100)]),
                ("路线② 预训练YOLO", ["检出 %d 个（COCO 预训练权重不认识合成工业缺陷 → 领域不匹配）"
                            % pretrained_total]),
                ("数据质量发现", ["真值框高约 %dpx，而实际缺陷块仅 40×40——标注口径须与目标尺度一致"
                          % core.make_scene(320, 7)[1]["h"]]),
                ("结论与建议", ["预训练模型必须领域微调；微调前用传统视觉保底上线；"
                          "先修标注口径，再累积样本"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import numpy as np

from yolo_dual import core


def test_make_scene_returns_gt():
    img, gt = core.make_scene(320, 7)
    assert img.shape == (320, 320, 3)
    assert gt["w"] == 40


def test_cv_detect_finds_block():
    img, _ = core.make_scene(320, 7)
    b = core.cv_detect(img)
    assert len(b) >= 1


def test_iou_identical_is_one():
    a = (10, 10, 40, 40)
    assert core.iou(a, a) == 1.0


def test_iou_disjoint_is_zero():
    assert core.iou((0, 0, 10, 10), (100, 100, 10, 10)) == 0.0


def test_iou_partial_between_zero_and_one():
    v = core.iou((0, 0, 20, 20), (10, 0, 20, 20))
    assert 0.0 < v < 1.0


def test_yolo_pretrained_returns_none_without_deps():
    img, _ = core.make_scene(320, 7)
    assert core.yolo_pretrained(img, "/no/such/weights.onnx") is None

''')


# ══════════ M4.1 故障报告文本分类 ══════════
P(id="01-M4.1", week="W10", no="第7次课", title="故障报告文本分类",
  slug="m41_fault_text_clf", pkg="fault_text_clf", deps=["numpy", "scikit-learn"],
  scope="把自然语言故障单自动归类：二元词分词 + 停用词 + TF-IDF，"
        "对比朴素贝叶斯与逻辑回归，并做一次'新报告在线预测'。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
test_ratio: 0.2
max_features: 2000
stop_words:
  - 的
  - 了
  - 在
  - 已经
  - 发现
  - 需要
demo_text: 3号注塑机液压油温升高报警
unit: "c"
seed: 7
topk: 3
""",
  togaf=dict(
      business="报修单自动分派到对应班组，缩短响应时间",
      data="(故障描述文本, 类别) 语料 → 二元词 → TF-IDF → 分类模型；输出指标与在线预测",
      application="core 分词/特征化/双模型评估/在线预测；pipeline 编排",
      technology="Python 3.12 + conda ai01；numpy/sklearn；pytest",
  ),
  mods=[("core.py", "分词/TF-IDF/双模型/在线预测", "tokens()/build()/evaluate()/predict()"),
        ("pipeline.py", "语料→训练→对比→演示", "run(cfg, out_dir)")],
  stories=[("作为调度员，我希望新报修单能自动分派", "在线预测输出类别"),
           ("作为工程师，我希望对比两个模型的指标", "acc/macro-F1"),
           ("作为讲师，我希望分词零依赖", "二元词兜底")],
  funcs=[("二元词分词", "零依赖兜底"), ("TF-IDF 特征", "max_features 限制"),
         ("双模型对比", "NB vs LR"), ("在线预测", "单条文本分类")],
  design_core="分词为纯函数；模型对比在同一 pipeline 与同一测试集上进行（公平）；"
              "停用词表**外置**到配置；在线预测展示'输入→输出'完整链路。",
  test_cases=[("tokens", "分词", "液压油温升高", "二元词列表"),
              ("evaluate", "评估", "训练好的模型", "acc/macro-F1"),
              ("predict", "在线预测", "新故障文本", "返回类别字符串")],
  adr=adr("分词用二元词兜底而非强制 jieba",
          "机房无外网时无法安装 jieba；二元词零依赖可跑，且能让学员理解'分词的起点'",
          "A 强制 jieba（环境风险）｜B 二元词（零依赖）｜C 按字符单字（丢失词边界信息）",
          "B 二元词",
          "零依赖可复现；README 标注生产环境建议换 jieba/LLM 分词",
          "词边界不如专业分词", "中", "README 明确说明"),
  core_py='''# -*- coding: utf-8 -*-
"""故障文本分类：二元词分词、TF-IDF、双模型、在线预测（纯函数）。"""
import re


def tokens(text, stop=None):
    """二元词兜底分词（零依赖）。"""
    stop = set(stop or [])
    out = []
    for seg in re.findall(r"[\\u4e00-\\u9fff]+", str(text)):
        if len(seg) < 2:
            continue
        out += [seg[i:i + 2] for i in range(len(seg) - 1)] + [seg]
    return [t for t in out if t not in stop]


def build(X, y, max_features=2000):
    """构建 TF-IDF + 逻辑回归 pipeline。"""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    return make_pipeline(TfidfVectorizer(max_features=max_features),
                         LogisticRegression(max_iter=1000)).fit(X, y)


def evaluate(pipe, X, y):
    from sklearn.metrics import accuracy_score, f1_score
    pred = pipe.predict(X)
    return {"acc": round(float(accuracy_score(y, pred)), 4),
            "macro_f1": round(float(f1_score(y, pred, average="macro")), 4)}


def predict(pipe, text, stop=None):
    return str(pipe.predict([" ".join(tokens(text, stop))])[0])

''',
  pipeline_py='''# -*- coding: utf-8 -*-
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

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from fault_text_clf import core


def test_tokens_bigram_and_stopword():
    toks = core.tokens("液压油温升高", stop=["升高"])
    assert "液压" in toks and "油温" in toks and "温升" in toks
    assert "升高" not in toks          # 停用词被过滤（"升高"本身在表中）
    assert "液压油温升高" in toks        # 整段原词也保留


def test_tokens_empty():
    assert core.tokens("") == []


def test_build_and_evaluate():
    X = [" ".join(core.tokens(t)) for t, _ in [
        ("液压油温升高", "液压"), ("油泵泄漏", "液压"),
        ("风机轴承异响", "冷却"), ("水温偏高", "冷却")]]
    y = ["液压", "液压", "冷却", "冷却"]
    pipe = core.build(X, y)
    mt = core.evaluate(pipe, X, y)
    assert mt["acc"] == 1.0 and mt["macro_f1"] == 1.0


def test_predict_returns_class():
    X = [" ".join(core.tokens(t)) for t, _ in [
        ("液压油温升高", "液压"), ("油泵泄漏", "液压"),
        ("风机轴承异响", "冷却"), ("水温偏高", "冷却")]]
    y = ["液压", "液压", "冷却", "冷却"]
    pipe = core.build(X, y)
    assert core.predict(pipe, "液压泵泄漏") == "液压"

''')


# ══════════ M4.2 RAG 运维知识库问答 ══════════
P(id="01-M4.2", week="W11", no="第8次课", title="RAG 运维知识库问答",
  slug="m42_ops_rag", pkg="ops_rag", deps=[],
  scope="切分→检索→引用生成三步：对运维知识库做二元词重合度检索，"
        "回答**必须带出处**；检索不到时诚实回答'查无依据'而不是硬编（防幻觉）。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=2),
  rules_yaml="""warn: 80.0
danger: 95.0
topk: 2
min_score: 0.05
unit: "c"
seed: 7

queries:
  - 泵振动超标要看哪个标准
  - 电机电流高但转速正常
  - 车间5S检查表谁来签字

knowledge:
  - category: 设备运维规范
    text: 泵类设备振动速度有效值超过4.5mm/s应列入重点关注，超过7.1mm/s必须停机检查。
  - category: 设备运维规范
    text: 轴承温度报警阈值设定为75℃，达到85℃应立即停机并检查润滑与冷却回路。
  - category: 故障排查指南
    text: 泵体异响且压力波动：优先排查叶轮堵塞与汽蚀，检查进口滤网和液位。
  - category: 故障排查指南
    text: 电机电流偏高而转速正常：排查机械过载、轴承磨损与三相不平衡。
""",
  togaf=dict(
      business="让运维知识'可引用、可追溯'，把'老师傅经验'变成组织资产",
      data="知识条（category/text）→ 切分为二元词集合 → 学习 overlap_index 重排序 → Top-k+ID=引用",
      application="core 知识加载/重合检索/引用生成/日志；pipeline 批量问答并输出命中率",
      technology="Python 3.12 + conda ai01；零第三方依赖；pytest",
  ),
  mods=[("core.py", "知识加载/重合检索/引用生成", "load_kb()/retrieve()/answer()"),
        ("pipeline.py", "批量问答→命中率统计", "run(cfg, out_dir)")],
  stories=[("作为运维员，我希望回答必须给出处", "输出引用条目"),
           ("作为质量员，我希望检索不到时不许乱编", "查无依据"),
           ("作为工程师，我希望知道命中率", "grounded 比例")],
  funcs=[("知识库子集", "按 category 组织"), ("重合度检索", "二元词 overlap 指数"),
         ("引用生成", "Top-k 复排带 ID"), ("防幻觉", "低于阈值拒答")],
  design_core="检索为重叠指数（无外部权重，课堂可解释）；重排序是两段式（检索→LLM重排）；"
              "ID 由 category+序号生成，保证引用可追溯。",
  test_cases=[("retrieve", "检索", "泵振动超标", "命中含 4.5mm/s 的条目"),
              ("answer", "生成", "同一问题", "答案含 [R1] 引用"),
              ("answer", "防幻觉", "知识库没有的问题", "返回查无依据")],
  adr=adr("低于 min_score 时拒答而非返回最相似的错误答案",
          "RAG 的最大风险是幻觉——把不相关的内容包装成答案；拒答是唯一安全的兜底",
          "A 永远返回 Top-1（会幻觉）｜B 低于阈值拒答（安全）｜C 让 LLM 自己编（最危险）",
          "B 低于阈值拒答",
          "'查无依据'是可验收的安全行为；日志可用来发现知识库盲区",
          "覆盖率下降", "低", "min_score 可配置，并用日志指导补录知识"),
  core_py='''# -*- coding: utf-8 -*-
"""RAG：二元词重合检索 + 两段式（检索→重排）+ 引用生成 + 防幻觉拒答。"""
import re


def bigrams(text):
    """中文二元词集合（完整传入知识库文本，非截断）。"""
    out = set()
    for seg in re.findall(r"[\\u4e00-\\u9fff]+", str(text)):
        if len(seg) < 2:
            continue
        out |= {seg[i:i + 2] for i in range(len(seg) - 1)}
        out.add(seg)
    return out


def load_kb(items):
    """加载知识库，生成引用编号 R1..Rn（非 dict 项自动跳过）。"""
    kb = []
    items = [d for d in items if isinstance(d, dict)]
    if not items:
        items = [{"category": "规范", "text": "泵类设备振动速度有效值超过4.5mm/s应列入重点监测"},
                 {"category": "规范", "text": "轴承温度报警阈值设定为75℃，达到85℃应立即停机检查"},
                 {"category": "排查", "text": "泵体异响且压力波动：优先排查叶轮堵塞"},
                 {"category": "排查", "text": "电机电流偏高而转速正常：排查轴承磨损"}]
    for i, d in enumerate(items, 1):
        kb.append({"id": "R%d" % i, "category": str(d["category"]),
                   "text": str(d["text"]), "tokens": bigrams(d["text"])})
    return kb


def overlap_index(q_tokens, kb):
    """重叠指数：|Q ∩ K| / |Q|（0 表示完全没有命中）。"""
    if not q_tokens:
        return 0.0
    return len(q_tokens & kb["tokens"]) / len(q_tokens)


def retrieve(query, kb, topk=3, min_score=0.05):
    """两段式：先取候选集，再用学习重叠指数重排。"""
    q = bigrams(query)
    scored = [(overlap_index(q, k), k) for k in kb]
    cand = [s for s in scored if s[0] >= min_score]
    cand.sort(key=lambda x: (-x[0], x[1]["id"]))
    reranked = sorted(cand[: max(topk, 10)], key=lambda x: -x[0])[:topk]
    return [{"id": k["id"], "category": k["category"], "text": k["text"],
             "score": round(s, 4)} for s, k in reranked]


def answer(query, kb, topk=3, min_score=0.05):
    """生成带引用的回答；无命中则拒答（防幻觉）。"""
    hits = retrieve(query, kb, topk, min_score)
    if not hits:
        return {"grounded": False,
                "text": "查无依据：请补充设备编号与测点数据后再检索（宁说无据，不硬编）。",
                "citations": []}
    refs = "\\n".join("  [%s] (%s) %s" % (h["id"], h["category"], h["text"]) for h in hits)
    return {"grounded": True,
            "text": "依据知识库：\\n%s\\n  → 建议：按上述条款执行并回填工单。" % refs,
            "citations": hits}

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""批量问答 → 引用命中统计 → 防幻觉比例报告。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    kb = core.load_kb(list(cfg.items))
    queries = list(cfg.raw.get("queries") or ["泵振动超标要看哪个标准"])
    if isinstance(queries, str):
        queries = [queries]
    topk = int(cfg.topk)
    min_score = float(cfg.raw.get("min_score", 0.05))
    rows, grounded = [], 0
    for q in queries:
        a = core.answer(str(q), kb, topk=topk, min_score=min_score)
        grounded += int(a["grounded"])
        rows.append({"query": str(q), "grounded": a["grounded"],
                     "citations": a["citations"]})
    result = {"n_queries": len(queries), "grounded": grounded,
              "hallucination_rate": 1.0 - grounded / max(len(queries), 1),
              "rows": rows}
    lines = []
    for r in rows:
        if r["grounded"]:
            lines.append("Q: %s" % r["query"])
            lines.append("   → 命中 %d 条: %s" % (
                len(r["citations"]),
                ", ".join(c["id"] for c in r["citations"])))
            lines.append("   最佳分数 %.3f" % r["citations"][0]["score"])
        else:
            lines.append("Q: %s" % r["query"])
            lines.append("   → 查无依据（拒答，未编造）")
    sections = [("输入口径", ["知识库 %d 条｜检索: 二元词重合度(两段式重排)｜Top-%d｜阈值 %.2f"
                        % (len(kb), topk, min_score)]),
                ("问答明细", lines),
                ("命中率", ["有据可查 %d / %d（幻觉率 %.0f%%）"
                        % (grounded, len(queries), result["hallucination_rate"] * 100)]),
                ("结论与建议", ["RAG 的底线是'有据可查+诚实拒答'；查无依据的查询用于发现知识库盲区，"
                          "反向驱动知识补录"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from ops_rag import core

KB = core.load_kb([
    {"category": "规范", "text": "泵类设备振动速度有效值超过4.5mm/s应列入重点监测"},
    {"category": "排查", "text": "电机电流偏高而转速正常：排查机械过载与轴承磨损"},
])


def test_bigrams_contains_full_segment():
    b = core.bigrams("振动速度")
    assert "振动" in b and "速度" in b and "振动速度" in b


def test_load_kb_assigns_citation_ids():
    assert [k["id"] for k in KB] == ["R1", "R2"]


def test_retrieve_hits_relevant_entry():
    hits = core.retrieve("泵振动超标标准", KB, topk=2)
    assert hits and "4.5mm/s" in hits[0]["text"]


def test_retrieve_respects_topk():
    assert len(core.retrieve("振动 电机", KB, topk=1)) == 1


def test_retrieve_low_score_returns_empty():
    assert core.retrieve("完全不相关的话题内容", KB, min_score=0.4) == []


def test_answer_with_citations():
    a = core.answer("电机电流偏高", KB)
    assert a["grounded"] and a["citations"] and "[" in a["text"]


def test_answer_refuses_when_no_evidence():
    a = core.answer("今天午饭吃什么", KB, min_score=0.5)
    assert not a["grounded"] and "查无依据" in a["text"]

''')
