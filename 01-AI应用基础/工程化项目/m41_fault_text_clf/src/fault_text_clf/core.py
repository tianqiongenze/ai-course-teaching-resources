# -*- coding: utf-8 -*-
"""故障文本分类：分词（jieba 真实路径/二元词兜底）、TF-IDF、双模型、混淆与近误分析。

分词是"环境也是选型维度"的实测点：jieba 可用走业界标准（含自建词典），
缺失走内置二元词兜底并在报告里写明——缺库打印 MISS，绝不报成"无证据"。
"""
import os
import re

_NUM = re.compile(r"\d+(?:\.\d+)?")


def tokens(text, stop=None):
    """二元词兜底分词（零依赖）。"""
    stop = set(stop or [])
    out = []
    for seg in re.findall(r"[\u4e00-\u9fff]+", str(text)):
        if len(seg) < 2:
            continue
        out += [seg[i:i + 2] for i in range(len(seg) - 1)] + [seg]
    return [t for t in out if t not in stop]


def jieba_tokenizer(userdict=None):
    """独立 Tokenizer（不动全局 jieba）：同进程重复跑口径一致、可并行。

    userdict=None → 无自建词典基线；给路径且文件存在 → 真实加载（A 档调优项），
    返回值 (tokenizer, 词典是否实际加载)，jieba 缺失时返回 (None, False)。
    """
    try:
        import jieba
        from jieba import Tokenizer
    except ImportError:
        return None, False
    import logging
    jieba.setLogLevel(logging.ERROR)  # 词典装载日志不进课堂控制台报告
    tok = Tokenizer()
    loaded = False
    if userdict and os.path.exists(userdict):
        tok.load_userdict(userdict)
        loaded = True
    return tok, loaded


def cut(text, tok=None, stop=None):
    """分词统一口径：有 jieba Tokenizer 用真实分词，否则二元词兜底。

    过滤只去停用词与"纯数字/纯符号"——PLC/AGV 这类字母词有类别区分度，不能误删。
    """
    stop = set(stop or [])
    if tok is not None:
        raw = tok.lcut(str(text))
    else:
        return tokens(text, stop)
    out = []
    for w in raw:
        w = w.strip()
        if not w or w in stop or _NUM.fullmatch(w):
            continue
        if re.fullmatch(r"[\W_]+", w):
            continue
        out.append(w)
    return out


def feature_text(text, tok, stop):
    return " ".join(cut(text, tok, stop))


def build(X, y, max_features=2000, ngram=(1, 1)):
    """构建 TF-IDF + 逻辑回归 pipeline（vectorizer 只在训练集 fit——防数据泄漏）。"""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    return make_pipeline(TfidfVectorizer(max_features=max_features,
                                         ngram_range=tuple(ngram)),
                         LogisticRegression(max_iter=1000)).fit(X, y)


def build_nb(X, y, max_features=2000, ngram=(1, 1)):
    """朴素贝叶斯对照模型：与逻辑回归同一切分、同一向量化口径。"""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import make_pipeline
    return make_pipeline(TfidfVectorizer(max_features=max_features,
                                         ngram_range=tuple(ngram)),
                         MultinomialNB()).fit(X, y)


def evaluate(pipe, X, y):
    from sklearn.metrics import accuracy_score, f1_score
    pred = pipe.predict(X)
    return {"acc": round(float(accuracy_score(y, pred)), 4),
            "macro_f1": round(float(f1_score(y, pred, average="macro")), 4)}


def predict(pipe, text, stop=None):
    return str(pipe.predict([" ".join(tokens(text, stop))])[0])


def predict_text(pipe, text, tok=None, stop=None):
    """终模型对单条库外文本的真实预测（与训练同分词口径）。"""
    return str(pipe.predict([feature_text(text, tok, stop)])[0])


def class_keywords(pipe, k=10):
    """每类 Top-k 关键词贡献（LR 取 coef_ 正向最大；NB 取 feature_log_prob_）。"""
    vec, clf = pipe.steps[0][1], pipe.steps[1][1]
    words = list(vec.get_feature_names_out())
    labels = [str(c) for c in pipe.classes_]
    out = {}
    if hasattr(clf, "coef_"):
        co = clf.coef_
        for ci, c in enumerate(labels):
            idx = sorted(range(len(words)), key=lambda j: -co[ci][j])[:k]
            out[c] = [(words[j], round(float(co[ci][j]), 4))
                      for j in idx if co[ci][j] > 0]
    else:
        lp = clf.feature_log_prob_
        for ci, c in enumerate(labels):
            idx = sorted(range(len(words)), key=lambda j: -lp[ci][j])[:k]
            out[c] = [(words[j], round(float(lp[ci][j]), 4)) for j in idx[:k]]
    return out


def per_class_acc(pipe, X, y):
    """每类实测召回（决策矩阵的"每类准确率"行，全部来自本次预测）。"""
    pred = pipe.predict(X)
    out = {}
    for c in sorted(set(y)):
        sel = [i for i in range(len(y)) if y[i] == c]
        ok = len([i for i in sel if pred[i] == c])
        out[str(c)] = round(ok / float(len(sel)), 4)
    return out


def confusion_pair(pipe, X, y):
    """实测混淆矩阵 + 最易混类对；全对角时退化到第二选择（近误）计数——
    仍是真实输出，不编造混淆。"""
    import numpy as np
    from sklearn.metrics import confusion_matrix
    labels = [str(c) for c in pipe.classes_]
    cm = confusion_matrix(y, pipe.predict(X), labels=labels)
    off = int(cm.sum() - np.trace(cm))
    pairs, method = {}, "测试集错分计数"
    for i, a in enumerate(labels):
        for j, b in enumerate(labels):
            if i != j and cm[i][j] > 0:
                pairs[(a, b)] = int(cm[i][j])
    if not pairs:
        method = "预测正确时的第二选择近误计数"
        proba = pipe.predict_proba(X)
        for i, p in enumerate(proba):
            order = np.argsort(p)[::-1]
            top, second = labels[int(order[0])], labels[int(order[1])]
            key = (str(y[i]), top) if top != y[i] else (str(y[i]), second)
            if key[0] != key[1]:
                pairs[key] = pairs.get(key, 0) + 1
    top_pair = None
    if pairs:
        (a, b), cnt = max(pairs.items(), key=lambda kv: kv[1])
        top_pair = {"true": a, "other": b, "count": cnt}
    return {"off_diag": off, "method": method, "top_pair": top_pair,
            "matrix": [[int(v) for v in row] for row in cm], "labels": labels}
