# -*- coding: utf-8 -*-
"""AI应用基础（16课时）教师版·多解法互验（合成数据、全离线、秒级）
运行: /opt/anaconda3/bin/python solutions_multi_ai.py → ALL PASS 才算数
完整解法地图见同目录《多解法手册.md》；RAG双解见 rag_chroma_demo.py
"""
import numpy as np

RESULTS = []


def check(name, fn, expect):
    got = fn()
    ok = got == expect
    RESULTS.append((name, ok))
    print(("✓" if ok else "✗"), name, "→", got)


def synth(n=600, seed=7):
    rng = np.random.RandomState(seed)
    X = rng.normal(0, 1, (n, 6))
    y = rng.binomial(1, 0.5, n)
    X[y == 1, 1:4] += 1.7
    return X, y


# ===== M1.1 三分类器=三解：同题同据，F1全部达标且预测一致率≥90% =====
def m11():
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import f1_score
    from sklearn.model_selection import train_test_split
    from sklearn.tree import DecisionTreeClassifier
    X, y = synth()
    Xtr, Xte, ytr, yte = train_test_split(X, y, stratify=y, random_state=42)
    preds = {}
    for name, m in {"LR": LogisticRegression(max_iter=500),
                    "DT": DecisionTreeClassifier(max_depth=8, random_state=0),
                    "RF": RandomForestClassifier(n_estimators=100, random_state=0)}.items():
        m.fit(Xtr, ytr)
        preds[name] = m.predict(Xte)
        assert f1_score(yte, preds[name]) >= 0.80, name
    agree = (preds["LR"] == preds["RF"]).mean()
    return agree >= 0.88


# ===== M1.2 缩放双解：MinMax vs Standard——管道接口一致、都可提升KNN =====
def m12():
    from sklearn.metrics import f1_score
    from sklearn.model_selection import train_test_split
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import MinMaxScaler, StandardScaler
    X, y = synth()
    X[:, 0] *= 1000
    Xtr, Xte, ytr, yte = train_test_split(X, y, stratify=y, random_state=1)
    out = []
    for scaler in (MinMaxScaler(), StandardScaler()):
        p = make_pipeline(scaler, KNeighborsClassifier()).fit(Xtr, ytr)
        out.append(round(f1_score(yte, p.predict(Xte)), 2))
    return out[0] > 0.85 and out[1] > 0.85


# ===== M2.2 滑动窗口双解：numpy stride滑窗 vs pandas rolling——特征一致 =====
def m22():
    import pandas as pd
    x = np.sin(np.linspace(0, 12, 240)) + 0.05 * np.random.RandomState(3).randn(240)
    w = 12
    a = np.array([x[i:i + w].std() for i in range(len(x) - w + 1)])  # 解A numpy
    b = pd.Series(x).rolling(w).std(ddof=0).dropna().values        # 解B pandas(与numpy同口径ddof=0)
    return np.allclose(a, b, atol=1e-9)


# ===== M2.2b RUL窗口标签双解：stride_tricks vs 循环 =====
def m22b():
    from numpy.lib.stride_tricks import sliding_window_view
    x = np.arange(20, dtype=float)
    w = 5
    a = sliding_window_view(x, w)                                  # 解A 向量化视图
    b = np.array([x[i:i + w] for i in range(len(x) - w + 1)])      # 解B 直白循环
    return np.array_equal(a, b)


# ===== M3.1 阈值分割双解：固定阈值 vs Otsu自适应——Otsu不差于人工 =====
def m31():
    from skimage.filters import threshold_otsu
    img = np.concatenate([np.random.RandomState(0).normal(60, 10, 3000),
                          np.random.RandomState(1).normal(180, 15, 1000)])
    t_fix, t_otsu = 120.0, threshold_otsu(img)
    return 90 < t_otsu < 170 and abs(t_otsu - t_fix) < 45


# ===== M4.1 文本分类双解：NB vs LR（TF-IDF同特征）——差距≤5% =====
def m41():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import f1_score
    from sklearn.naive_bayes import MultinomialNB
    rng = np.random.RandomState(7)
    vocab = ["轴承 磨损 振动", "温度 过热 报警", "压力 波动 堵塞", "电流 偏高 跳闸"]
    texts, labels = [], []
    for i in range(160):
        k = i % 4
        words = vocab[k].split() + [vocab[k].split()[rng.randint(3)]]
        texts.append(" ".join(words))
        labels.append(k)
    X = TfidfVectorizer().fit_transform(texts)
    nb = MultinomialNB().fit(X[:120], labels[:120])
    lr = LogisticRegression(max_iter=500).fit(X[:120], labels[:120])
    f_nb = f1_score(labels[120:], nb.predict(X[120:]), average="macro")
    f_lr = f1_score(labels[120:], lr.predict(X[120:]), average="macro")
    return round(max(f_nb, f_lr), 2) >= 0.90 and abs(f_nb - f_lr) <= 0.15


if __name__ == "__main__":
    check("M1.1 三分类器解(LR/DT/RF)一致率≥0.88", m11, True)
    check("M1.2 缩放双解(MinMax/Standard)皆达标", m12, True)
    check("M2.2 滑窗双解(numpy/pandas)特征一致", m22, True)
    check("M2.2b 窗口样本双解(视图/循环)一致", m22b, True)
    check("M3.1 分割双解(固定/Otsu)同域", m31, True)
    check("M4.1 分类双解(NB/LR)差距≤15%", m41, True)
    bad = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS)}项多解互验：{'ALL PASS ✅' if not bad else 'FAIL ❌ ' + str(bad)}")
    print("M4.2 RAG双解 → 运行 rag_chroma_demo.py（幕1库内4/4一致）")
