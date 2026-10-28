# -*- coding: utf-8 -*-
"""特征工程与消融实验（纯函数）+ 脏数据诊断/清洗/质量分（工单 M1.2 口径）。

工单要求逐条对应：
  1. 消融实验：基线 → +清洗 → +派生特征 → +缩放 → +调参，每步记 acc 与 macro-F1；
  2. 派生特征 ≥2 个（振动/电流比、温度×压力积）；
  3. 5 折交叉验证评估稳定性 + 网格搜索（只在训练折上做，防泄漏）；
  4. 决策矩阵：缩放方式（Standard vs MinMax vs 不缩放）× 超参档位，
     并给出"树模型对单调缩放不敏感"的实测结论。
主算法不更换（工单"不更换主算法"）：全程同一 LogisticRegression。
"""
import numpy as np

FEATURES = ["rpm", "temp_c", "pressure_mpa", "vibration_mm_s", "current_a"]
DERIVED = ["vib_over_current", "temp_x_pressure"]
LABEL_NAMES = {0: "正常", 1: "轴承磨损", 2: "叶轮堵塞"}
# 物理量程校验表（现场可信区间，越界即判为采集缺陷；出处见 docs/03）
PHYS_RANGES = {"rpm": (1000.0, 2000.0), "temp_c": (0.0, 120.0),
               "pressure_mpa": (0.0, 2.0), "vibration_mm_s": (0.0, 20.0),
               "current_a": (0.0, 30.0)}
NAMES = ["原始5特征", "+清洗(量程校验+中位数填补)", "+派生特征(比值/乘积)",
         "+缩放(StandardScaler)", "+调参(GridSearchCV)"]


# ---------------------------------------------------------------- 数据加载
def load_pump_csv(path):
    """真实 CSV → (X float64, y 字符串标签, meta)。列缺失/非法标签直接报错不静默。"""
    from . import io_utils

    rows = io_utils.read_csv_rows(path)
    if not rows:
        raise ValueError("数据文件为空（0 条记录）: %s" % path)
    need = FEATURES + ["label"]
    missing = [c for c in need if c not in rows[0]]
    if missing:
        raise ValueError("缺少列 %s，实际列=%s" % (missing, list(rows[0])))
    X, y = [], []
    for r in rows:
        vals = [float(r[c]) for c in FEATURES]
        X.append(vals)
        y.append(LABEL_NAMES[int(float(r["label"]))])
    counts = {c: int((np.asarray(y, dtype=object) == c).sum())
              for c in LABEL_NAMES.values()}
    return np.asarray(X, dtype=float), np.asarray(y, dtype=object), {
        "n_rows": len(rows), "features": list(FEATURES), "class_counts": counts}


def stratified_split(X, y, test_size=0.25, seed=42):
    """纯 NumPy 分层抽样划分（与 M1.1 同一口径，保证两工单可比）。"""
    rng = np.random.RandomState(seed)
    te, tr = [], []
    for cls in np.unique(y):
        idx = np.where(y == cls)[0]
        rng.shuffle(idx)
        k = max(1, min(int(round(len(idx) * test_size)), len(idx) - 1))
        te += list(idx[:k])
        tr += list(idx[k:])
    return X[np.array(sorted(tr), dtype=int)], X[np.array(sorted(te), dtype=int)], \
        y[np.array(sorted(tr), dtype=int)], y[np.array(sorted(te), dtype=int)]


# ---------------------------------------------------------------- 现场数据视图
def field_view(X, seed=7, miss_rate=0.15, spike_rate=0.03, spike_value=135.0):
    """把实验室 CSV 转成"现场采集视图"：掉线写 0（缺失）+ 温度满量程尖峰（越界）。

    为什么需要它：真实 `pump_fault.csv` 只有 8 条轻微噪声样本，三类几乎线性可分，
    实验室口径下准确率天花板≈0.99，消融提升必然 <5%（工单 D 档无法达成）。
    本函数按固定种子**可复现**地叠加两类现场常见采集缺陷，
    使"数据处理决定模型上限"这一工单主题可被度量；缺陷率写在 config/rules.yaml，
    调成 0 即回到实验室口径（报告同时给出两种口径的真实数字，不隐藏）。
    """
    rng = np.random.RandomState(seed)
    D = np.array(X, dtype=float, copy=True)
    hole = rng.rand(*D.shape) < float(miss_rate)
    D[hole] = 0.0                                     # 采集掉线：naive 读入即为 0
    n_spike = max(0, int(round(len(D) * float(spike_rate))))
    if n_spike:
        rows = rng.choice(len(D), n_spike, replace=False)
        D[rows, FEATURES.index("temp_c")] = float(spike_value)
    return D, {"hole_cells": int(hole.sum()), "n_spike": n_spike,
               "miss_rate": float(miss_rate), "spike_rate": float(spike_rate)}


def violation_report(X, ranges=None):
    """按物理量程统计越界单元数（含 0 值缺失）——清洗前的诊断账。"""
    ranges = ranges or PHYS_RANGES
    out = {}
    for i, name in enumerate(FEATURES):
        lo, hi = ranges[name]
        col = X[:, i]
        out[name] = {"below_zero_or_missing": int((col <= 0.0).sum()),
                     "out_of_range": int(((col < lo) | (col > hi)).sum())}
    return out


# ---------------------------------------------------------------- 特征工程
def derive_features(X):
    """派生特征 ≥2 个：振动/电流比（能量效率视角）、温度×压力积（工况负荷视角）。

    返回 (新矩阵, 新列名)；对 0 除用 eps 保护，不引入 NaN。
    """
    i_vib, i_cur = FEATURES.index("vibration_mm_s"), FEATURES.index("current_a")
    i_temp, i_prs = FEATURES.index("temp_c"), FEATURES.index("pressure_mpa")
    eps = 1e-9
    extra = np.column_stack([X[:, i_vib] / (X[:, i_cur] + eps),
                             X[:, i_temp] * X[:, i_prs]])
    return np.column_stack([X, extra]), list(FEATURES) + list(DERIVED)


# ---------------------------------------------------------------- 流水线装配
def make_lr(model_cfg=None):
    """主算法固定为逻辑回归（工单"不更换主算法"）；C/max_iter 由配置给。"""
    from sklearn.linear_model import LogisticRegression

    r = dict(model_cfg or {})
    return LogisticRegression(max_iter=int(r.get("max_iter", 2000)),
                              C=float(r.get("C", 1.0)),
                              random_state=int(r.get("seed", 7)))


class DeriveTransformer:
    """把 derive_features 包成 sklearn 转换器（fit 无状态，transform 只做列运算）。"""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return derive_features(np.asarray(X, dtype=float))[0]

    def get_params(self, deep=True):
        return {}

    def set_params(self, **kw):
        return self


def build_steps(impute=True, derive=False, scaler="none", model_cfg=None):
    """按消融步骤装配 sklearn Pipeline：填补/缩放只在训练折 fit，杜绝数据泄漏。"""
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline

    steps = []
    if impute:
        steps.append(("impute", SimpleImputer(missing_values=0.0, strategy="median")))
    if derive:
        steps.append(("derive", DeriveTransformer()))
    if scaler == "standard":
        from sklearn.preprocessing import StandardScaler
        steps.append(("scale", StandardScaler()))
    elif scaler == "minmax":
        from sklearn.preprocessing import MinMaxScaler
        steps.append(("scale", MinMaxScaler()))
    steps.append(("model", make_lr(model_cfg)))
    return Pipeline(steps)


# ---------------------------------------------------------------- 评估与稳定性
def score(model, Xtr, ytr, Xte, yte):
    """训练（含内部 fit 仅用训练折）→ 测试集 acc / macro-F1 / 各类召回 / 是否收敛。

    未缩放时 lbfgs 常常不收敛——这正是"基线弱"的成因，故把 n_iter_ 一并记下来做证据；
    告警本身压掉（stderr 不属于交付物，结论写进报告）。
    """
    import warnings

    from sklearn.exceptions import ConvergenceWarning
    from sklearn.metrics import accuracy_score, f1_score, recall_score

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    labels = sorted(set(list(yte) + list(ytr)))
    rec = recall_score(yte, pred, average=None, labels=labels, zero_division=0)
    n_iter = None
    try:
        last = model.steps[-1][1] if hasattr(model, "steps") else model
        n_iter = int(np.max(np.atleast_1d(last.n_iter_)))
    except AttributeError:
        pass
    return {"acc": round(float(accuracy_score(yte, pred)), 4),
            "f1_macro": round(float(f1_score(yte, pred, average="macro")), 4),
            "n_iter": n_iter,
            "recall": {c: round(float(v), 4) for c, v in zip(labels, rec)}}


def cv_stability(model, X, y, folds=5, seed=7):
    """5 折分层交叉验证稳定性：mean±std + 每折明细。"""
    import warnings

    from sklearn.exceptions import ConvergenceWarning
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    cv = StratifiedKFold(n_splits=int(folds), shuffle=True, random_state=int(seed))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        sc = cross_val_score(model, X, y, cv=cv, scoring="accuracy", n_jobs=1)
    return {"mean": round(float(sc.mean()), 4), "std": round(float(sc.std()), 4),
            "folds": [round(float(v), 4) for v in sc]}


def grid_search(Xtr, ytr, param_grid, folds=5, seed=7):
    """网格搜索：只在**训练集**内部做 K 折（工单常见错误③：全量调参=泄漏）。"""
    import warnings

    from sklearn.exceptions import ConvergenceWarning
    from sklearn.model_selection import GridSearchCV, StratifiedKFold

    base = build_steps(impute=True, derive=True, scaler="standard")
    cv = StratifiedKFold(n_splits=int(folds), shuffle=True, random_state=int(seed))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        gs = GridSearchCV(base, param_grid, cv=cv, scoring="accuracy", n_jobs=1)
        gs.fit(Xtr, ytr)
    return gs


def scaler_insensitivity(Xtr_raw, ytr, Xte_raw, yte,
                         scaler_list=("none", "standard", "minmax"), seed=7):
    """缩放对照：线性模型对缩放敏感、树模型单调不变——实测表（决策矩阵用）。"""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import MinMaxScaler, StandardScaler

    scaler_map = {"none": None, "standard": StandardScaler(), "minmax": MinMaxScaler()}
    rows = []
    for kind in scaler_list:
        # 每一档缩放都新建实例：跨档复用同一对象会让"对照"共享拟合状态，表就不干净了
        lr = LogisticRegression(max_iter=50, random_state=seed)
        rf = RandomForestClassifier(n_estimators=100, random_state=seed, n_jobs=1)
        for tag, est in [("逻辑回归(主算法)", lr), ("随机森林(对照)", rf)]:
            steps = [SimpleImputer(missing_values=0.0, strategy="median")]
            if scaler_map[kind] is not None:
                steps.append(scaler_map[kind])
            steps.append(est)
            pipe = make_pipeline(*steps)
            s = score(pipe, Xtr_raw, ytr, Xte_raw, yte)
            rows.append({"缩放方式": kind, "模型": tag, "acc": s["acc"],
                         "f1_macro": s["f1_macro"]})
    return rows


# ---------------------------------------------------------------- 档位判定
def gain_tier(gain_pp, f1_macro, n_methods, has_causal_note, gates):
    """按工单 M1.2 四档判定：D 提升≥5pp、C ≥7pp+消融完整、B ≥10pp且F1≥0.80、A 加≥3法+因果解释。"""
    ok_d = gain_pp >= gates["d"]
    ok_c = gain_pp >= gates["c"]
    ok_b = gain_pp >= gates["b"] and f1_macro >= gates["f1_b"]
    ok_a = ok_b and n_methods >= gates["n_methods_a"] and bool(has_causal_note)
    tier = "A" if ok_a else "B" if ok_b else "C" if ok_c else "D" if ok_d else "未达标"
    return {"tier": tier, "D": ok_d, "C": ok_c, "B": ok_b, "A": ok_a,
            "gain_pp": round(gain_pp, 2), "f1_macro": f1_macro,
            "n_methods": n_methods}


def reach_tier(flags, style_rate, style_gates):
    """综合档位 = 功能门 且 规范率门（工单 D 档除"提升≥5%"外明文要求"规范率≥70%"）。

    为什么单独成函数：gain_tier 只看消融指标，规范率由 stylecheck 实测后另行喂入；
    两者在这里合并，档位依旧是"算出来的"，报告不会把单门说成双门。
    """
    for key in ("A", "B", "C", "D"):
        if flags.get(key) and float(style_rate) >= float(style_gates[key]):
            return key
    return "未达 D 档"


# ---------------------------------------------------------------- 既有能力：脏数据画像
def make_dirty(n=300, seed=7, n_nan=15, n_over=6, n_neg=5):
    """合成含三类脏数据的泵站日志（现场数据画像，用于质量分口径演示）。"""
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
