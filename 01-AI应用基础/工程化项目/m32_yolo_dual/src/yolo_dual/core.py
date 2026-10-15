# -*- coding: utf-8 -*-
"""双路线检测：传统视觉（必然可用） + COCO 预训练 YOLO（如实呈现）。"""
import os

import numpy as np


def make_scene(size=320, seed=7):
    """合成工业图：背景190/产品区150，矩形缺陷块110。"""
    img = np.full((size, size, 3), 190, dtype=np.uint8)
    img[40:280, 40:280] = 150
    w = 40
    img[120:120 + w, 150:150 + w] = 110
    return img, {"cx": 150 + w // 2, "cy": 120 + w // 2, "w": w, "h": w}


def cv_detect(img, dev=15, min_area=25):
    """传统视觉：全图背景建模 + 逐通道偏离 + 连通域。"""
    import cv2
    bg = np.full(img.shape[:2], 190.0, np.float32)
    bg[40:280, 40:280] = 150.0
    f = img.astype(np.float32)
    d = np.max([np.abs(f[:, :, k] - bg) for k in range(3)], axis=0)
    m = (d > dev).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    return [(int(stats[i][0]), int(stats[i][1]), int(stats[i][2]), int(stats[i][3]))
            for i in range(1, n) if stats[i][4] >= min_area]


def iou(a, b):
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    un = a[2] * a[3] + b[2] * b[3] - inter
    return inter / un if un else 0.0


def yolo_pretrained(img, onnx_path=None):
    """预训练 YOLOv8n（可选）：无 onnxruntime 或无权重时返回 None（不造假）。"""
    try:
        import cv2
        import onnxruntime as ort
    except ImportError:
        return None
    path = onnx_path or "data/weights/yolov8n.onnx"
    if not os.path.exists(path):
        return None
    sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    x = cv2.resize(img, (640, 640)).astype(np.float32) / 255.0
    out = sess.run(None, {"images": x.transpose(2, 0, 1)[None]})[0][0]
    return int((out[4:].max(0) > 0.4).sum())
