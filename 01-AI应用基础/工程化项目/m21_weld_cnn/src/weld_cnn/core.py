# -*- coding: utf-8 -*-
"""焊缝缺陷：合成图像 + 块统计特征 + 交叉验证（零 torch）。"""
import numpy as np

CLASSES = ["正常", "气孔", "裂纹"]


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
