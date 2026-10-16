# -*- coding: utf-8 -*-
# [教学脚手架] 下列导入/变量供 TODO 完成后使用，故标注 noqa 而非删除
"""M1.2 特征工程优化 —— 学生代码框架
先运行 m11 完成版获得基线, 在此逐步添加优化并记录消融表。
"""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression  # noqa: F401
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GridSearchCV, cross_val_score, train_test_split  # noqa: F401

DATA = "data/pump_fault.csv"
ABLATION = []   # 消融记录: (步骤名, 准确率, F1)


def load_data(path):
    data = np.genfromtxt(path, delimiter=",", skip_header=1)
    return data[:, :5], data[:, 5].astype(int)


def evaluate(tag, Xtr, Xte, ytr, yte, model=None):
    model = model or RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(Xtr, ytr)
    acc = accuracy_score(yte, model.predict(Xte))
    f1 = f1_score(yte, model.predict(Xte), average="macro")
    ABLATION.append((tag, acc, f1))
    print(f"[消融] {tag:<22} 准确率={acc:.3f}  F1={f1:.3f}")
    return acc


def clean_outliers(X, y):
    """TODO-1 清洗噪声样本: 对每个特征按3σ截断(记录删除条数)
    提示: z=(X-X.mean(0))/X.std(0); mask=(np.abs(z)<3).all(axis=1)"""
    # === 你的代码 ===
    return X, y


def build_features(X):
    """TODO-2 派生特征≥2个: 如 vibration/current, temp*pressure
    返回 (N, 5+k) 的新数组"""
    # === 你的代码 ===
    return X


def main():
    X, y = load_data(DATA)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25,
                                          stratify=y, random_state=42)
    base = evaluate("基线(原始)", Xtr, Xte, ytr, yte)

    # 步骤1: 清洗
    Xc, yc = clean_outliers(X, y)
    Xtr2, Xte2, ytr2, yte2 = train_test_split(Xc, yc, test_size=0.25,
                                              stratify=yc, random_state=42)
    evaluate("+清洗", Xtr2, Xte2, ytr2, yte2)

    # TODO-3: +新特征  (提示: 对训练/测试集用同一规则构建)
    # TODO-4: +归一化  (Min-Max或StandardScaler, 思考树模型是否需要→写进决策)
    # TODO-5: +网格搜索(GridSearchCV, 只在训练集上做!)

    # TODO-6: 5折交叉验证稳定性
    # scores = cross_val_score(..., cv=5); print("CV:", scores.mean(), "+/-", scores.std())

    print("\n===== 消融实验表 =====")
    for tag, acc, f1 in ABLATION:
        print(f"{tag:<24}{acc:>8.3f}{f1:>8.3f}")
    print(f"基线→最优提升: {(max(a for _, a, _ in ABLATION) - base) * 100:.1f}%")


if __name__ == "__main__":
    main()
