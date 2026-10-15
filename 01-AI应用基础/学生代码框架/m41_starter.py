# -*- coding: utf-8 -*-
# [教学脚手架] 下列导入/变量供 TODO 完成后使用，故标注 noqa 而非删除
"""M4.1 工业故障报告自动分类 —— 学生代码框架"""
import csv

import jieba  # noqa: F401
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report  # noqa: F401
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

DATA = "data/fault_reports.csv"
STOP = set("的 了 在 是 请 尽快 处理 影响 生产 班中 巡检 发现 已 挂牌 停机".split())


def load():
    texts, labels = [], []
    with open(DATA, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            texts.append(row["text"])
            labels.append(row["label"])
    return texts, labels


def cut(text):
    """TODO-1: jieba分词+去停用词, 空格连接"""
    # === 你的代码 ===
    raise NotImplementedError


def main():
    texts, labels = load()
    corpus = [cut(t) for t in texts]
    n = int(len(corpus) * 0.8)
    tr_x, te_x = corpus[:n], corpus[n:]  # noqa: F841
    tr_y, te_y = labels[:n], labels[n:]  # noqa: F841

    results = {}  # noqa: F841
    for name, clf in [("朴素贝叶斯", MultinomialNB()),
                      ("逻辑回归", LogisticRegression(max_iter=1000))]:
        pipe = make_pipeline(TfidfVectorizer(max_features=2000), clf)  # noqa: F841
        # TODO-2: fit(tr_x, tr_y) → predict(te_x) → 记录accuracy
        # 注意: TfidfVectorizer只在训练集fit(Pipeline已保证)
        # === 你的代码 ===
        # results[name] = acc
        # print(classification_report(te_y, pred))

    # TODO-3: 新文本预测(自收集的2条+示例)
    # for q in ["3号注塑机液压油温升高报警", "包装线PLC从站掉线"]:
    #     print(q, "->", pipe.predict([cut(q)]))

    # TODO-4: 每类Top10关键词(pipe[:-1].get_feature_names_out + coef/feature_log_prob_)
    # TODO-5: (优秀)混淆矩阵: 哪两类易混? 为什么?


if __name__ == "__main__":
    main()
