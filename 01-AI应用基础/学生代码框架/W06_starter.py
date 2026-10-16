# -*- coding: utf-8 -*-
# [教学脚手架] 下列导入/变量供 TODO 完成后使用，故标注 noqa 而非删除
"""M2.1 工业焊接缺陷检测(tiny-CNN, CPU约2分钟) —— 学生代码框架"""
import json
import os

import numpy as np
import torch
import torch.nn as nn

ROOT = "data/weld_images"
CLASSES = ["normal", "porosity", "slag", "crack"]


class TinyCNN(nn.Module):
    """2卷积+2全连接; 完成TODO-1的forward"""

    def __init__(self, num_classes=4):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 8, 3)    # 64→62
        self.pool = nn.MaxPool2d(2, 2)     # 62→31
        self.conv2 = nn.Conv2d(8, 16, 3)   # 31→29 →pool→14
        self.fc1 = nn.Linear(16 * 14 * 14, 64)
        self.fc2 = nn.Linear(64, num_classes)

    def forward(self, x):
        """TODO-1: conv1→relu→pool→conv2→relu→pool→flatten→fc1→relu→fc2"""
        # === 你的代码 ===
        raise NotImplementedError


def load_dataset():
    with open(os.path.join(ROOT, "index.json"), encoding="utf-8") as f:
        meta = json.load(f)
    X = np.stack([np.load(os.path.join(ROOT, m["file"])) for m in meta])
    y = np.array([CLASSES.index(m["label"]) for m in meta])
    X = X.astype(np.float32) / 255.0          # 归一化(勿忘!)
    X = X[:, None, :, :]                      # (N,1,64,64) 通道维
    idx = np.random.RandomState(42).permutation(len(X))
    X, y = X[idx], y[idx]
    n_train = int(len(X) * 0.8)
    return (X[:n_train], y[:n_train]), (X[n_train:], y[n_train:])


def main():
    (Xtr, ytr), (Xte, yte) = load_dataset()
    print("形状追踪: 输入", Xtr.shape, "(N,C,H,W)")
    device = "cpu"
    model = TinyCNN().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1.5e-3)  # noqa: F841
    lossf = nn.CrossEntropyLoss()  # noqa: F841

    xt = torch.tensor(Xte)
    yt = torch.tensor(yte)
    for epoch in range(6):
        model.train()
        # TODO-2: 小批量训练(batch=32): 前向→loss→反向→step, 累计打印epoch loss
        # === 你的代码 ===
        model.eval()
        with torch.no_grad():
            pred = model(xt).argmax(1)
            acc = (pred == yt).float().mean().item()
        print(f"epoch {epoch + 1}  测试准确率={acc:.3f}")

    # TODO-3: 任取2张测试图, 输出预测类别与softmax置信度
    # TODO-4: (优秀)数据增强: 随机水平翻转后再训练, 对比准确率
    # TODO-5: (优秀)绘制loss曲线与混淆矩阵(matplotlib)


if __name__ == "__main__":
    main()
