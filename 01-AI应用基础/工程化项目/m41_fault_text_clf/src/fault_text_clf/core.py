# -*- coding: utf-8 -*-
"""故障文本分类：二元词分词、TF-IDF、双模型、在线预测（纯函数）。"""
import re


def tokens(text, stop=None):
    """二元词兜底分词（零依赖）。"""
    stop = set(stop or [])
    out = []
    for seg in re.findall(r"[\u4e00-\u9fff]+", str(text)):
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
