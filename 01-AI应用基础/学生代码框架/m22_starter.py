# -*- coding: utf-8 -*-
# [教学脚手架] 下列导入/变量供 TODO 完成后使用，故标注 noqa 而非删除
"""M2.2 轴承剩余寿命(RUL)预测(LSTM, CPU) —— 学生代码框架"""
import numpy as np
import torch
import torch.nn as nn

DATA = "data/bearing_rul.npz"


class RULNet(nn.Module):

    def __init__(self, hidden=32):
        super().__init__()
        self.lstm = nn.LSTM(input_size=1, hidden_size=hidden,
                            batch_first=True)
        self.fc = nn.Linear(hidden, 1)

    def forward(self, x):                # x: (N, 20, 1)
        out, _ = self.lstm(x)            # (N,20,H)
        last = out[:, -1, :]             # 取最后时刻 → (N,H)
        return self.fc(last).squeeze(-1)  # (N,)


def visualize_window():
    """预习用: 看见'输入窗口→标签'的对应关系(运行即出图)"""
    import matplotlib.pyplot as plt
    d = np.load(DATA)
    X, y = d["X"], d["y"]
    i = 100
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.plot(range(i, i + 20), X[i], "o-", label="输入窗口(振动)")
    ax.axvline(i + 20, color="r", ls="--", label=f"预测点RUL={y[i]:.2f}")
    ax.set_xlabel("时间步")
    ax.legend()
    plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS"]
    plt.tight_layout()
    plt.savefig("window_demo.png", dpi=120)
    print("已保存 window_demo.png")


def main():
    d = np.load(DATA)
    X, y = d["X"].astype(np.float32), d["y"].astype(np.float32)
    X = X[:, :, None]                    # (N,20)→(N,20,1)
    n = int(len(X) * 0.8)
    Xtr, ytr = torch.tensor(X[:n]), torch.tensor(y[:n])  # noqa: F841
    Xte, yte = torch.tensor(X[n:]), torch.tensor(y[n:])

    model = RULNet()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)  # noqa: F841
    lossf = nn.MSELoss()

    for epoch in range(60):
        model.train()
        # TODO-1: 全批量(或batch=64)训练, 每10轮打印loss
        # === 你的代码 ===
        if (epoch + 1) % 10 == 0:
            model.eval()
            with torch.no_grad():
                mse = lossf(model(Xte), yte).item()
            print(f"epoch {epoch + 1}  验证MSE={mse:.4f}")

    # TODO-2: 计算测试集 MSE/RMSE/MAE 三项指标
    # TODO-3: 选1台设备的退化段, 绘制"真实RUL vs 预测RUL"曲线
    # TODO-4: (对照)线性回归基线: 用窗口均值单特征拟合, 对比MSE
    # TODO-5: (业务解读)≤80字: RMSE=0.1对维护计划意味着什么


if __name__ == "__main__":
    import sys
    if "--viz" in sys.argv:
        visualize_window()
    else:
        main()
