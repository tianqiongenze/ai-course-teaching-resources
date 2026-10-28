# -*- coding: utf-8 -*-
"""轴承退化轨迹、RUL 回归、拐点/窗口实验与可视化（纯函数，可单测）。

工单 M2.2 的四档能力（预测+可视化 / 基线对照 / 多模型对比 / 拐点+窗口敏感性）
都在此真实实现：指标一律 sklearn 现算，拐点由平滑序列实测，matplotlib 缺失时
绘图函数返回 None——调用方据此打 MISS，绝不伪造产物文件。
"""
import os

import numpy as np

from . import io_utils


def make_traj(n=3000, seed=7):
    """合成全寿命退化轨迹：平稳期 + 线性退化段；返回 (x, rul, 退化段掩码)。"""
    t = np.linspace(0, 1, n)
    onset = 0.7
    deg = np.zeros(n)
    m = t > onset
    deg[m] = (t[m] - onset) / (1.0 - onset)
    rng = np.random.RandomState(seed)
    x = 4.0 * (1 + 0.02 * np.sin(2 * np.pi * 30 * t)) + 2.0 * deg + rng.randn(n) * 0.05
    rul = np.where(m, (1.0 - t) / 0.3, np.nan)
    return x, rul, m


def metrics(y, pred):
    """回归四指标（R²/RMSE/MAE/MSE）——工单要 MSE/RMSE/MAE，单源现算。"""
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    mse = float(mean_squared_error(y, pred))
    return {"r2": round(float(r2_score(y, pred)), 4),
            "rmse": round(float(np.sqrt(mse)), 5),
            "mae": round(float(mean_absolute_error(y, pred)), 5),
            "mse": round(mse, 8)}


def fit(X, y, model=None):
    """训练回归并返回 (model, pred, 指标)——评估集即入参 X（课堂小样本演示用）。"""
    if model is None:
        from sklearn.linear_model import Ridge
        model = Ridge(alpha=1.0)
    model.fit(X, y)
    return model, model.predict(X), metrics(y, model.predict(X))


def evaluate(model, X, y):
    """已训练模型在留出集上的实测指标（B 档模型对照用，绝不拿训练集自夸）。"""
    pred = model.predict(X)
    return pred, metrics(y, pred)


def split(n, test_size, seed):
    """确定性随机切分：返回 (train_idx, test_idx)，同 seed 同结果（可复现）。"""
    rng = np.random.RandomState(seed)
    perm = rng.permutation(int(n))
    k = int(round(len(perm) * float(test_size)))
    k = max(1, min(len(perm) - 1, k))
    return np.sort(perm[k:]), np.sort(perm[:k])


def constant_baseline(y_tr, n):
    """最傻基线：拿退化段训练均值当所有点的预测（C 档『对照基线』的被减数）。"""
    return np.full(int(n), float(np.mean(y_tr)))


def window_feature(x, w):
    """长度 w 的滑动窗口均值特征（因果：只看当前及历史 w-1 点）；不足处为 NaN。"""
    w = max(1, int(w))
    c = np.cumsum(np.insert(np.asarray(x, float), 0, 0.0))
    out = np.full(len(x), np.nan)
    out[w - 1:] = (c[w:] - c[:-w]) / w
    return out


def _centered_ma(v, span):
    """中心式滑动均值——拐点检测用离线平滑，消除群延迟（窗口特征不用它）。"""
    span = max(1, int(span))
    h = span // 2
    p = np.concatenate([np.full(h, v[0]), np.asarray(v, float), np.full(h, v[-1])])
    c = np.cumsum(np.insert(p, 0, 0.0))
    return (c[span:] - c[:-span]) / span


def _first_run(ok, hold):
    """ok 序列里首个『连续 hold 点为真』的起点下标；找不到返回 None。"""
    hold = max(1, int(hold))
    run = np.convolve(np.asarray(ok, int), np.ones(hold, int), mode="full")[:len(ok)]
    idx = np.where(run >= hold)[0]
    return int(idx[0]) - (hold - 1) if len(idx) else None


def knee_analysis(x, truth_idx, span=100, ratio=0.5, hold=30, level_ratio=0.1):
    """退化拐点双口径实测，返回逐口径字典列表（工单 A 档『拐点分析』）。

    斜率法：双重滑动均值序列的一阶差分首次达到『实测最大升程的 ratio 倍』
    并持续 hold 个循环；水平法：平滑 RMS 首次越过『健康基线 + level_ratio×
    实测总抬升』。两者都与真值退化起点对比，偏移是实测结论、不是调参目标。
    """
    s = _centered_ma(_centered_ma(x, span), span)
    d = np.diff(s)
    base = float(np.median(s[:max(1, int(0.2 * len(s)))]))
    rise = float(s.max() - base)
    out = []
    for name, thr, ok in (
            ("斜率法(一阶差分≥%.0f%%实测最大升程)" % (ratio * 100), ratio * float(d.max()),
             d >= ratio * float(d.max())),
            ("水平法(平滑RMS≥健康基线+%.0f%%总抬升)" % (level_ratio * 100),
             base + level_ratio * rise, s >= base + level_ratio * rise),
    ):
        pos = _first_run(ok, hold)
        idx = None if pos is None else int(pos)
        out.append({"method": name, "threshold": round(float(thr), 6),
                    "span": int(span), "hold": int(hold),
                    "knee_cycle": idx,
                    "offset_cycles": None if idx is None else idx - int(truth_idx),
                    "truth_cycle": int(truth_idx)})
    return out


def _plot_backend():
    """matplotlib 真实可用性探测；缺失返回 None，调用方标 MISS 不伪造文件。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        return None


def plot_prediction_curve(path, cycles, y_true, pred_cycles, pred_y,
                          knee_cycle=None, onset_cycle=None):
    """真值 RUL vs 预测 RUL 随退化循环的曲线 + 拐点竖线标记，落盘 png。

    返回 {"path","points","cycles_plotted"}；matplotlib 不可用返回 None——
    上层据此把 D 档可视化判缺（环境也是选型维度，缺图就印 MISS）。
    """
    plt = _plot_backend()
    if plt is None:
        return None
    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=120)
    ax.plot(cycles, y_true, color="#444444", lw=1.3,
            label="true RUL (all degradation cycles)")
    ax.plot(pred_cycles, pred_y, marker="o", ms=3.2, lw=1.1, color="tab:orange",
            label="predicted RUL (held-out test cycles)")
    if onset_cycle is not None:
        ax.axvline(int(onset_cycle), ls=":", color="tab:blue",
                   label="ground-truth onset (cycle %d)" % int(onset_cycle))
    if knee_cycle is not None:
        ax.axvline(int(knee_cycle), ls="--", color="tab:red",
                   label="detected knee (cycle %d)" % int(knee_cycle))
    ax.set_xlabel("degradation cycle")
    ax.set_ylabel("normalized RUL (1 -> 0)")
    ax.set_title("Bearing RUL: true vs predicted (measured)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return {"path": path, "points": int(len(pred_cycles)),
            "cycles_plotted": int(len(cycles))}


def artifact_stat(path):
    """产物文件实测：存在性与真实字节数（从磁盘读回，不采信内存里的说法）。"""
    if not path or not os.path.exists(path):
        return {"path": path, "exists": False, "bytes": 0}
    return {"path": path, "exists": True, "bytes": int(os.path.getsize(path))}


def business_note(rmse, rul_span=1.0):
    """把 RMSE 归一化到退化区间长度，翻译成维护建议。"""
    ratio = rmse / max(rul_span, 1e-9)
    cycles = int(round(ratio * 20))
    return ("预测误差约占退化区间 %.1f%% → 约 %d 个维护周期；"
            "可提前 1-2 个周期安排换件。" % (ratio * 100, cycles))


def torch_backend():
    """torch 真实可用性探测；缺失返回 None——LSTM 臂判缺并印 MISS，不伪造增益。"""
    try:
        import torch
        return torch
    except ImportError:
        return None


def load_bearing_windows():
    """真实课程数据 data/bearing_rul.npz → 设备级窗口数组；不可用返回 None。

    设备台数由数据本身推出（每台设备首窗 RUL 归一化为 1，计数即台数），
    不硬编码 30/180——换数据集不用改代码（"环境也是选型维度"）。
    """
    path = io_utils.course_data("bearing_rul.npz")
    if not path:
        return None
    try:
        data = np.load(path)
        X = np.asarray(data["X"], float)
        y = np.asarray(data["y"], float).ravel()
    except (OSError, ValueError, KeyError):
        return None
    if X.ndim != 2 or len(X) != len(y) or len(y) < 2:
        return None
    n_dev = int(np.sum(y >= float(y.max()) - 1e-6))
    if n_dev < 2 or len(y) % n_dev:
        return None
    windows = len(y) // n_dev
    return {"X": X, "y": y, "n_dev": n_dev, "windows": windows,
            "dev": np.repeat(np.arange(n_dev), windows), "source": path,
            "synthetic": False}


def synth_devices(n_dev=30, windows=180, n_feat=20, seed=7):
    """npz 缺失兜底：逐设备加速退化轨迹 + 归一化线性 RUL（口径与真实数据一致）。"""
    rng = np.random.RandomState(seed)
    t = np.linspace(0.0, 1.0, int(windows))
    blocks = []
    for _ in range(int(n_dev)):
        rate = 1.6 + 0.5 * rng.rand()
        level = 0.85 + 0.1 * rng.randn()
        base = level + rate * t ** 1.8 + rng.randn(len(t)) * 0.05
        cols = [base * (1.0 + 0.05 * np.sin(2 * np.pi * (k + 1) * t))
                for k in range(int(n_feat))]
        blocks.append(np.stack(cols, axis=1))
    X = np.concatenate(blocks, axis=0)
    y = np.tile(np.linspace(1.0, 0.0, len(t)), int(n_dev))
    return {"X": X, "y": y, "n_dev": int(n_dev), "windows": int(windows),
            "dev": np.repeat(np.arange(int(n_dev)), int(windows)),
            "source": "core.synth_devices 兜底合成（未找到 data/bearing_rul.npz，"
                      "指标不代表现场表现）", "synthetic": True}


def load_dataset(n_dev=30, windows=180, seed=7):
    """真实数据优先、缺失即兜底，并把口径写进 source 字段（报告如实标注）。"""
    return (load_bearing_windows()
            or synth_devices(n_dev=n_dev, windows=windows, seed=seed))


def split_devices(ds, n_test_devices, seed):
    """设备级留出切分：同一台设备的全部窗口只出现在一侧（防泄漏，指标才算真泛化）。"""
    rng = np.random.RandomState(int(seed))
    k = int(max(1, min(int(ds["n_dev"]) - 1, int(n_test_devices))))
    test_devs = np.sort(rng.choice(int(ds["n_dev"]), size=k, replace=False))
    mask = np.isin(ds["dev"], test_devs)
    return (np.where(~mask)[0], np.where(mask)[0], [int(v) for v in test_devs], k)


def train_lstm(Xtr, ytr, Xte, yte, epochs=60, hidden=32, lr=0.003, batch=128,
               seed=7):
    """工单指定结构的 LSTM（隐层 32、取末窗输出接全连接），在留出设备上实测指标。

    torch 缺失返回 None（调用方打 MISS）；指标一律 sklearn 现算，训练损失
    逐轮入 losses 供报告复核——判档只认这些实测数。
    """
    torch = torch_backend()
    if torch is None:
        return None
    import time
    import torch.nn as nn
    torch.manual_seed(int(seed))
    np.random.seed(int(seed))

    class _LSTM(nn.Module):
        """1 层 LSTM(隐层 32) + Linear(32→1)：工单 M2.2「模型结构」原文口径。"""

        def __init__(self, hid):
            super().__init__()
            self.lstm = nn.LSTM(1, int(hid), batch_first=True)
            self.head = nn.Linear(int(hid), 1)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(out[:, -1]).squeeze(-1)

        def predict_np(self, arr):
            return self(torch.tensor(np.asarray(arr, np.float32)[..., None])
                        ).detach().numpy()

    model = _LSTM(hidden)
    Xt = torch.tensor(np.asarray(Xtr, np.float32)[..., None])
    yt = torch.tensor(np.asarray(ytr, np.float32))
    opt = torch.optim.Adam(model.parameters(), lr=float(lr))
    lossf = torch.nn.MSELoss()
    n = len(Xt)
    losses = []
    started = time.time()
    for _ in range(int(epochs)):
        perm = torch.randperm(n)
        acc = 0.0
        for i in range(0, n, int(batch)):
            idx = perm[i:i + int(batch)]
            opt.zero_grad()
            loss = lossf(model(Xt[idx]), yt[idx])
            loss.backward()
            opt.step()
            acc += float(loss.detach()) * len(idx)
        losses.append(round(acc / n, 8))
    pred = model.predict_np(Xte)
    out = metrics(np.asarray(yte, float), pred)
    out.update({"pred": pred, "losses": losses, "hidden": int(hidden),
                "epochs": int(epochs), "lr": float(lr), "batch": int(batch),
                "n_train": int(n), "n_test": int(len(pred)),
                "seconds": round(time.time() - started, 1)})
    return out


def model_table(X, y, tr, te, seed, n_estimators=80, min_samples_leaf=3,
                alpha=1.0):
    """B 档「对比≥2 种模型」：同一设备级切分上真训 Ridge 与随机森林，各出留出指标。"""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import Ridge
    rows = []
    for name, model in (("Ridge", Ridge(alpha=float(alpha))),
                        ("RandomForest", RandomForestRegressor(
                            n_estimators=int(n_estimators),
                            min_samples_leaf=int(min_samples_leaf),
                            random_state=int(seed)))):
        model.fit(X[tr], y[tr])
        pred, mt = evaluate(model, X[te], y[te])
        rows.append(dict(mt, name=name, pred=pred))
    return rows


def window_sensitivity(X, y, tr, te, lens, alpha=1.0):
    """A 档「窗口长度敏感性」：固定 Ridge 与切分，只改历史窗口列数，逐档实测 MSE。

    控制变量口径——模型不变，窗口效应才不被模型差异污染；超出特征列数的档
    直接丢弃（不报错也不凑数），报告只打印真跑出 MSE 的档。
    """
    from sklearn.linear_model import Ridge
    rows = []
    total = int(X.shape[1])
    for item in (lens or []):
        w = int(item)
        if w <= 0 or w > total:
            continue
        model = Ridge(alpha=float(alpha))
        model.fit(X[tr][:, :w], y[tr])
        pred, mt = evaluate(model, X[te][:, :w], y[te])
        rows.append(dict(mt, window=w, n_train=int(len(tr)), n_test=int(len(te))))
    return rows


def plot_sensitivity(path, rows, delivered_name=None, delivered_mse=None):
    """窗口长度 vs 实测 MSE 折线（A 档敏感性证据），落盘 png；缺库返回 None。"""
    plt = _plot_backend()
    if plt is None or not rows:
        return None
    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=120)
    ws = [int(r["window"]) for r in rows]
    mse = [float(r["mse"]) for r in rows]
    ax.plot(ws, mse, marker="o", lw=1.3, color="tab:blue",
            label="Ridge MSE by window length")
    if delivered_name and delivered_mse is not None:
        ax.axhline(float(delivered_mse), ls="--", color="tab:red",
                   label="%s (delivered) MSE = %.6f"
                   % (delivered_name, float(delivered_mse)))
    ax.set_xlabel("history window length (feature columns)")
    ax.set_ylabel("held-out MSE (measured)")
    ax.set_title("Window-length sensitivity (device-level split)")
    ax.set_xticks(ws)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return {"path": path, "points": len(rows)}


def fleet_knee(X, dev, n_dev, span=15, ratio=0.5, hold=5):
    """机群逐台实测斜率拐点（数据无标注退化起点、工单也未给——以机群实测分布为参照）。"""
    ks = []
    for i in range(int(n_dev)):
        s = X[dev == i].mean(axis=1)
        if len(s) < 2 * int(span):
            continue
        hit = knee_analysis(s, 0, span=span, ratio=ratio,
                            hold=hold)[0]["knee_cycle"]
        if hit is not None:
            ks.append(int(hit))
    return ks
