# -*- coding: utf-8 -*-
"""焊缝缺陷：真实课程数据 + tiny-CNN（torch 真实路径）+ 零 torch 轻量兜底。

工单 M2.1 要求四类（正常/气孔/夹渣/裂纹）、64×64、2 卷积层 tiny-CNN。
"环境也是选型维度"：torch 在场就走真实训练（增强/无增强双臂，逐轮 loss、
形状钩子、混淆矩阵、误判样本全部实测）；torch 缺失则退回本模块原有的
块统计 + 随机森林轻量基线，并在报告里如实标 MISS——绝不把"没练成 CNN"
说成"无证据也达标"。make_images/featurize/score 是兜底与旧测试的基座，
保留不动。
"""
import os
import time

import numpy as np

from . import io_utils

CLASSES = ["正常", "气孔", "裂纹"]                    # 旧三分类兜底（勿删，旧测试依赖）
WORK_CLASSES = ["正常", "气孔", "夹渣", "裂纹"]        # 工单四类，顺序与 index.json 一致
_LABEL_ID = {"normal": 0, "porosity": 1, "slag": 2, "crack": 3}


def make_images(n=180, seed=7, size=32):
    """合成灰度焊缝图：正常(均匀) / 气孔(3×3亮点) / 裂纹(细暗线)。"""
    rng = np.random.RandomState(seed)
    X, y = [], []
    for i in range(n):
        img = rng.normal(0.5, 0.08, (size, size))
        label = i % 3
        if label == 1:
            r0, c0 = rng.randint(4, size - 4, 2)
            img[r0:r0 + 3, c0:c0 + 3] += 0.5
        if label == 2:
            r0 = rng.randint(6, size - 6)
            img[r0:r0 + 1, 4:size - 4] -= 0.35
        X.append(img)
        y.append(CLASSES[label])
    return np.array(X), np.array(y)


def img_feats(img):
    """块统计三特征：亮块比例 / 暗线比例 / 最大亮值。"""
    return [float((img > 0.8).mean()), float((img < 0.2).mean()), float(img.max())]


def featurize(X):
    return [img_feats(im) for im in X]


def score(F, y, folds=3, seed=0):
    """K 折交叉验证准确率的均值与标准差。"""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    return cross_val_score(RandomForestClassifier(random_state=seed), F, y, cv=folds)


# ── 以下为工单 M2.1 实测路径（真实数据 + tiny-CNN 双臂）──────────────
def load_weld_images():
    """读课程真实数据 data/weld_images/index.json（4类×60，64×64 uint8）。

    归一化 x/255 是工单"常见错误"第一条的正解——不归一化 loss 居高不下。
    找不到返回 None，调用方降级合成兜底并在报告如实标注。
    """
    import json
    idx_path = io_utils.course_data("weld_images", "index.json")
    if not idx_path or not os.path.exists(idx_path):
        return None
    base = os.path.dirname(idx_path)
    try:
        entries = json.load(open(idx_path, encoding="utf-8"))
    except (ValueError, OSError):
        return None
    X, y = [], []
    for e in entries:
        p = os.path.join(base, e["file"])
        if not os.path.exists(p) or e["label"] not in _LABEL_ID:
            return None
        X.append(np.load(p).astype(np.float32) / 255.0)
        y.append(_LABEL_ID[e["label"]])
    return np.stack(X), np.array(y, dtype=np.int64)


def synth_weld_images(n=240, seed=7, size=64):
    """真实数据缺失时的四类均衡合成兜底（报告必须标注"非真实数据"）。"""
    rng = np.random.RandomState(seed)
    per = max(n // len(WORK_CLASSES), 1)
    X, y = [], []
    for label in range(len(WORK_CLASSES)):
        for _ in range(per):
            img = rng.normal(0.5, 0.08, (size, size)).astype(np.float32)
            if label == 1:                            # 气孔：3×3 亮斑
                r0, c0 = rng.randint(4, size - 4, 2)
                img[r0:r0 + 3, c0:c0 + 3] += 0.5
            elif label == 2:                          # 夹渣：6×6 暗块
                r0, c0 = rng.randint(4, size - 8, 2)
                img[r0:r0 + 6, c0:c0 + 6] -= 0.4
            elif label == 3:                          # 裂纹：横向细暗线
                r0 = rng.randint(6, size - 6)
                img[r0:r0 + 1, 4:size - 4] -= 0.35
            X.append(img)
            y.append(label)
    return np.stack(X), np.array(y, dtype=np.int64)


def stratified_ratio_split(y, test_size, seed):
    """分层抽样划分（每类各抽 test_size），返回 (train_idx, test_idx)。"""
    rng = np.random.RandomState(seed)
    tr, te = [], []
    for cls in np.unique(y):
        idx = rng.permutation(np.where(y == cls)[0])
        n_te = max(1, int(round(len(idx) * float(test_size))))
        te.extend(idx[:n_te].tolist())
        tr.extend(idx[n_te:].tolist())
    return np.array(sorted(tr)), np.array(sorted(te))


def class_counts(y, n_cls):
    """各类真实计数——工单"四类均衡数据"的实测证据。"""
    return [int((y == c).sum()) for c in range(n_cls)]


def augment_arm(X, y, shift=2):
    """翻转（水平/垂直）+ 平移（±shift 像素）——工单 B 档"数据增强"实测臂。"""
    views = [X, X[:, ::-1, :].copy(), X[:, :, ::-1].copy(),
             np.roll(X, shift, axis=1), np.roll(X, -shift, axis=1),
             np.roll(X, shift, axis=2), np.roll(X, -shift, axis=2)]
    return (np.concatenate(views),
            np.concatenate([y] * len(views)))


def torch_available():
    """探测 torch——"环境也是选型维度"，缺失时上层走兜底并标 MISS。"""
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def _tiny_cnn(torch, nn, ch1, ch2, n_cls, img):
    """按工单口径搭 2 卷积 tiny-CNN（64×64 输入，3×3 无 padding，2×2 池化）。"""

    class TinyCNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(1, ch1, 3)
            self.pool1 = nn.MaxPool2d(2)
            self.conv2 = nn.Conv2d(ch1, ch2, 3)
            self.pool2 = nn.MaxPool2d(2)
            self.fc = nn.Linear(ch2 * fc_side(img, ch2=ch2) ** 2, n_cls)

        def forward(self, x):
            x = torch.relu(self.conv1(x))
            x = self.pool1(x)
            x = torch.relu(self.conv2(x))
            x = self.pool2(x)
            x = torch.flatten(x, 1)
            return self.fc(x)

    return TinyCNN()


def fc_side(img=64, ch2=16):
    """flatten 后每边像素数：((img-2)//2 - 2)//2——形状表期望值算式。"""
    h1 = img - 2
    p1 = h1 // 2
    h2 = p1 - 2
    return h2 // 2


def expected_shape_chain(n=1, ch1=8, ch2=16, n_cls=4, img=64):
    """按卷积算式推期望形状链（形状表"完整无误"= 实测逐段等于它）。"""
    s = fc_side(img, ch2=ch2)
    return [("input", (n, 1, img, img)),
            ("conv1", (n, ch1, img - 2, img - 2)),
            ("pool1", (n, ch1, (img - 2) // 2, (img - 2) // 2)),
            ("conv2", (n, ch2, (img - 2) // 2 - 2, (img - 2) // 2 - 2)),
            ("pool2", (n, ch2, s, s)),
            ("flatten", (n, ch2 * s * s)),
            ("fc", (n, n_cls))]


def train_cnn(Xtr, ytr, Xte, yte, epochs=40, lr=0.003, batch=64, seed=7,
              ch1=8, ch2=16, img=64):
    """真实训练-评估流程（工单 D 档），逐轮 loss/测试准确率全部实测。

    训练集与测试集显式分离传入——增强臂训练集是 7 倍展开、测试集仍是
    原 holdout，杜绝"用训练视图冒充测试"的错位刷分。
    torch 缺失返回 None（调用方记 MISS，不许拿兜底冒充 CNN 训练）。
    """
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
    except ImportError:
        return None
    torch.manual_seed(int(seed))
    n_cls = len(np.unique(ytr))
    model = _tiny_cnn(torch, nn, ch1, ch2, n_cls, img)
    opt = torch.optim.Adam(model.parameters(), lr=float(lr))
    xt = torch.tensor(np.ascontiguousarray(Xtr[:, None]))
    yt = torch.tensor(ytr)
    xq = torch.tensor(np.ascontiguousarray(Xte[:, None]))
    losses = []
    t0 = time.time()
    for _ in range(int(epochs)):
        perm = torch.randperm(len(xt))
        tot, seen = 0.0, 0
        for i in range(0, len(xt), int(batch)):
            b = perm[i:i + int(batch)]
            opt.zero_grad()
            loss = F.cross_entropy(model(xt[b]), yt[b])
            loss.backward()
            opt.step()
            tot += float(loss.detach()) * len(b)
            seen += len(b)
        losses.append(tot / max(seen, 1))
    model.eval()
    with torch.no_grad():
        logits = model(xq)
        pred = logits.argmax(1).numpy()
        conf = logits.softmax(1).max(1).values.numpy()
    acc = float((pred == yte).mean())
    return {"model": model, "losses": losses, "acc": round(acc, 4),
            "pred": pred, "conf": conf, "n_test": int(len(yte)),
            "seconds": round(time.time() - t0, 1)}


def rf_fallback(X, y, tr, te, seed=0):
    """零 torch 兜底：块统计特征 + 随机森林（只作对照，档位判定会标 MISS）。"""
    from sklearn.ensemble import RandomForestClassifier
    feats = featurize(X)
    clf = RandomForestClassifier(n_estimators=100, random_state=int(seed))
    clf.fit([feats[i] for i in tr], y[tr])
    pred = clf.predict([feats[i] for i in te])
    conf = np.full(len(te), np.nan)
    acc = float((pred == y[te]).mean())
    return {"losses": None, "acc": round(acc, 4), "pred": pred,
            "conf": conf, "idx": te, "seconds": None}


def trace_shapes(model, torch, x):
    """forward hook 实测张量形状链（工单"打印 x.shape 变化链"的自动化版）。"""
    measured = {}

    def hook(name):
        def fn(module, inputs, output):
            if name == "fc":
                measured["flatten"] = tuple(inputs[0].shape)
            measured[name] = tuple(output.shape)
        return fn

    handles = [getattr(model, m).register_forward_hook(hook(m))
               for m in ("conv1", "pool1", "conv2", "pool2", "fc")]
    try:
        with torch.no_grad():
            model(x[None, None] if x.ndim == 2 else x)
    finally:
        for h in handles:
            h.remove()
    measured["input"] = tuple((x[None, None] if x.ndim == 2 else x).shape)
    return measured


def confusion_matrix(y_true, y_pred, n_cls):
    """实测混淆矩阵：行=真实类，列=预测类。"""
    cm = np.zeros((n_cls, n_cls), dtype=int)
    for a, b in zip(y_true, y_pred):
        cm[int(a), int(b)] += 1
    return cm


def find_misclassified(idx, y_true, pred, conf, te_y):
    """真实挑出误判样本：(测试集下标, 真实标签, 预测标签, 置信度)。"""
    rows = []
    for j, (a, b) in enumerate(zip(te_y, pred)):
        if a != b:
            rows.append({"test_idx": int(idx[j]), "true": int(a),
                         "pred": int(b), "conf": round(float(conf[j]), 4)})
    return rows


def low_confidence(idx, conf, k=2, threshold=0.95):
    """无增强臂也全对时的托底：按实测置信度升序取 k 个"高危样本"。"""
    order = np.argsort(conf)[:k]
    return [{"test_idx": int(idx[j]), "conf": round(float(conf[j]), 4)}
            for j in order if float(conf[j]) < float(threshold)]


def _plot_backend():
    """matplotlib 真实可用性探测；缺失返回 None，报告标 MISS 不伪造文件。

    注册课程自带中文字体（01-AI应用基础/fonts/ZH_Font.ttf），否则图内中文
    渲染成豆腐块——图也是交付物；字体文件不存在时退回默认字体，不硬失败。
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib import font_manager
        import matplotlib.pyplot as plt
        font = os.path.normpath(os.path.join(io_utils._PROJ, "..", "..",
                                             "fonts", "ZH_Font.ttf"))
        if os.path.exists(font):
            font_manager.fontManager.addfont(font)
            name = font_manager.FontProperties(fname=font).get_name()
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
        return plt
    except ImportError:
        return None


def plot_loss_curves(arms, path):
    """loss 曲线落 png（工单 A 档"绘制 loss 曲线"的真实产物）。"""
    plt = _plot_backend()
    if plt is None:
        return None
    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
    for name, losses in arms.items():
        ax.plot(range(1, len(losses) + 1), losses, marker="o",
                markevery=max(1, len(losses) // 10), label=name)
    ax.set_xlabel("epoch")
    ax.set_ylabel("train loss (measured)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_confusion(cm, labels, path):
    """混淆矩阵落 png（真实文件，报告统计字节数作证据）。"""
    plt = _plot_backend()
    if plt is None:
        return None
    fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(int(cm[i, j])), ha="center", va="center",
                    color="black" if cm[i, j] < cm.max() / 2 else "white")
    fig.colorbar(im, ax=ax, fraction=0.046)
    ax.set_title("Confusion matrix (measured, true=row)")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def artifact_stat(path):
    """实测文件证据：存在性与字节数（pytest 断言 >1000B 用）。"""
    if path and os.path.exists(path):
        return {"path": os.path.basename(path),
                "bytes": int(os.path.getsize(path)), "exists": True}
    return {"path": os.path.basename(path) if path else None,
            "bytes": 0, "exists": False}
