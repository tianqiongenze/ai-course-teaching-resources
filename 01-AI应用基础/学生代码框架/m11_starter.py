# -*- coding: utf-8 -*-
# [教学脚手架] 下列导入/变量供 TODO 完成后使用，故标注 noqa 而非删除
"""M1.1 泵类设备故障诊断系统 —— 学生代码框架（TODO处为你的任务）
运行:  python m11_starter.py            # 完成任务
       python m11_starter.py --check    # 环境自检
"""
import sys

import numpy as np

DATA = "data/pump_fault.csv"
LABELS = ["无故障", "轴承磨损", "叶轮堵塞"]


def check_env():
    try:
        import sklearn  # noqa
        ok = True
    except ImportError:
        ok = False
    print("numpy:", np.__version__, "| sklearn:", "OK" if ok else "缺失!")
    print("环境OK" if ok else "请先安装scikit-learn")


def load_data(path):
    """TODO-1 读取CSV(仅用NumPy): 返回 X(float, N×5), y(int, N,)
    提示: np.genfromtxt(path, delimiter=',', skip_header=1)"""
    # === 你的代码 ===
    raise NotImplementedError


def split(X, y, test_ratio=0.25, seed=42):
    """TODO-2 分层划分训练/测试集(每类按比例抽)
    提示: 对每类取索引打乱后切分, 最后合并打乱"""
    # === 你的代码 ===
    raise NotImplementedError


def main():
    X, y = load_data(DATA)
    print("数据形状:", X.shape, "类别分布:", np.bincount(y))

    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import (accuracy_score, precision_score,  # noqa: F401
                                 recall_score, f1_score)

    Xtr, Xte, ytr, yte = split(X, y)

    models = {
        "逻辑回归": LogisticRegression(max_iter=1000),
        "决策树": DecisionTreeClassifier(max_depth=6, random_state=42),
        "随机森林": RandomForestClassifier(n_estimators=100, random_state=42),
    }
    # TODO-3 训练三个模型并填表(宏平均: average='macro')
    print(f"{'模型':<8}{'准确率':>8}{'精确率':>8}{'召回率':>8}{'F1':>8}")
    for name, model in models.items():
        # === 训练/预测/评估, 打印一行指标 ===
        raise NotImplementedError

    # TODO-4 挑选2个测试样本预测并输出"预测 vs 真实"对照
    # TODO-5 (决策) 填写决策矩阵后, 用选定的模型输出最终结论
    print("\n决策矩阵填写后, 在此打印最终交付模型与理由(≤50字)")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check_env()
    else:
        main()
