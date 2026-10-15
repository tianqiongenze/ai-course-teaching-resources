# -*- coding: utf-8 -*-
"""表面缺陷检测：合成图像 + 背景差分 + 连通域 + 类型判定（纯函数）。"""
import numpy as np

CLASSES = ["dent", "stain", "edge_crack"]


def make_scene(size=240, seed=7):
    """合成零件图：底色190、产品区150、缺陷凹坑110/色斑(仅G通道)/裂纹细线。"""
    img = np.full((size, size, 3), 190, dtype=np.uint8)
    r, c = int(size * 0.2), int(size * 0.2)
    img[r:r + int(size * 0.6), c:c + int(size * 0.6)] = 150
    cx, cy, w = int(size * 0.4), int(size * 0.5), 16
    img[cy:cy + w, cx:cx + w] = 110
    return img, (cx, cy, w, w)


def mask(img, bg=150.0, dev=15):
    """逐通道偏离背景取最大 → 二值掩码。"""
    import cv2
    reg = img.astype(np.float32)
    d = np.max([np.abs(reg[:, :, k] - bg) for k in range(3)], axis=0)
    m = (d > dev).astype(np.uint8) * 255
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def components(m, min_area=20):
    """连通域 → 缺陷框列表 (x, y, w, h, area)。"""
    import cv2
    n, _, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    return [(int(stats[i][0]), int(stats[i][1]), int(stats[i][2]),
             int(stats[i][3]), int(stats[i][4]))
            for i in range(1, n) if stats[i][4] >= min_area]


def classify(img, box):
    """按通道偏离模式判定缺陷类型。"""
    x, y, w, h = box[:4]
    reg = img[y:y + h, x:x + w].astype(np.float32)
    dev = [float(np.abs(reg[:, :, k] - 150.0).mean()) for k in range(3)]
    if min(dev) > 20:
        return "dent"
    if max(dev) - min(dev) > 8:
        return "stain"
    return "edge_crack"
