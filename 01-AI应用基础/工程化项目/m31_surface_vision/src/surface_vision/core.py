# -*- coding: utf-8 -*-
"""表面缺陷检测：合成图像 + 背景差分 + 连通域 + 类型判定（纯函数）。

工单 M3.1 实测链路（本文件后半段）只吃真实零件图与教师真值：
灰度化→高斯滤波→阈值分割（全局/Otsu 两策略）→外轮廓→contourArea/
minAreaRect→像素当量换算 mm。误差 = |实测-真值|/真值，全部现场复算。
"""
import os

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


# ── 工单 M3.1 实测链路：真实零件 + 双阈值策略 + 多缺陷件 ─────────────


def gray_of(img):
    """BGR → 灰度 + 高斯 3×3（工单三.1 预处理链）。

    为什么用 3×3 而不是 5×5：划痕最细仅 2~3px，5×5 会把细线中心抬到
    全局阈值之上（实测漏检 21/40 件）——滤波强度也是测量口径的一部分。
    """
    import cv2
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(g, (3, 3), 0)


def binarize(g, strategy, t_fixed=100):
    """决策矩阵两行：全局阈值(工单例 100) / Otsu 自动阈值。

    BINARY_INV：零件图缺陷暗(≈60)、背景亮(≈200)，反之二值化方向就反了
    （工单"六、常见错误"第 3 条）。
    """
    import cv2
    if strategy == "otsu":
        t, m = cv2.threshold(g, 0, 255,
                             cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    else:
        t, m = cv2.threshold(g, float(t_fixed), 255, cv2.THRESH_BINARY_INV)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return float(t), m


def part_defects(m, min_area, mm_per_px):
    """外轮廓(RETR_EXTERNAL，防内轮廓重复计数) → 缺陷清单 + 小面积噪点数。

    面积口径：外轮廓填充后的像素计数——contourArea(多边形)对阶梯边界
    有系统性低估（实测 253px 的凹坑只报 224，Pick 定理所致），两者
    都写进记录，误差判定吃更贴合物理面积的像素计数口径。
    """
    import cv2
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL,
                               cv2.CHAIN_APPROX_SIMPLE)
    buf = np.zeros(m.shape, np.uint8)
    defects, noise = [], 0
    k2 = mm_per_px * mm_per_px
    for c in cnts:
        buf[:] = 0
        cv2.drawContours(buf, [c], -1, 255, -1)
        px = int(cv2.countNonZero(buf))
        if px < min_area:
            noise += 1
            continue
        rx, ry, rw, rh = cv2.boundingRect(c)
        (_, _), (w1, h1), _ = cv2.minAreaRect(c)
        defects.append({"box": (int(rx), int(ry), int(rw), int(rh)),
                        "area_px": px,
                        "contour_area_px": round(cv2.contourArea(c), 1),
                        "area_mm2": round(px * k2, 2),
                        "len_mm": round(max(w1, h1) * mm_per_px, 2)})
    return defects, noise


def err_pct(measured, truth):
    """测量误差%：|实测-真值|/真值×100——档位门槛吃的就是这个实测值。"""
    return abs(measured - truth) / truth * 100.0


def iou(a, b):
    """两框 (x,y,w,h) 交并比——多缺陷件"全部检出/误检"的匹配依据。"""
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    un = a[2] * a[3] + b[2] * b[3] - inter
    return inter / un if un else 0.0


def extract_defect(img, t_fixed=100):
    """抠出真实零件图中的缺陷像素块，供拼装多缺陷件。

    用原始灰度 <130（缺陷 60 / 背景 200 的中点）而不是滤波后再阈值：
    细划痕滤波后核心区可能高于 100，抠体会漏像素、贴板后就缺一段。
    """
    import cv2
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ys, xs = np.where(g < 130)
    if len(ys) == 0:
        return None
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    patch = img[y0:y1 + 1, x0:x1 + 1].copy()
    pmask = g[y0:y1 + 1, x0:x1 + 1] < 130
    return patch, pmask


def build_multi_part(sources, speck=3):
    """多缺陷件 = 3 件真实零件的缺陷块拼到同一空白板（A 档实测样本）。

    sources: [(patch, pmask, gt_dict), ...]，逐块贴放并记录贴放后 bbox；
    speck: 撒入 speck 个 4×4 假缺陷点（面积 16px 低于 min_area_px，但
    能在开运算后存活）——误检成因分析的实测来源。
    """
    h, w = 240, 320
    board = np.full((h, w, 3), 200, np.uint8)
    gts, top = [], 10
    for patch, pmask, gt in sources:
        ph, pw = patch.shape[:2]
        if top + ph >= h - 8:
            break
        region = board[top:top + ph, 10:10 + pw]
        region[pmask] = patch[pmask]
        g = dict(gt)
        g["box"] = (10, top, pw, ph)
        gts.append(g)
        top += ph + 16
    for k in range(speck):
        sx, sy = w - 30, 10 + k * 14
        board[sy:sy + 4, sx:sx + 4] = 60
    return board, gts


def annotate(img, defects, path, meta_lines):
    """原图画框 + 尺寸文字 + 图例 → 结果图落盘，返回机检要素计数。

    "美观"里可机械核对的部分（框画了几何、文字几条、图例有无、文件
    是否真实落盘）在这里实测；主观观感归人工答辩项。
    """
    import cv2
    canvas = img.copy()
    n_box = n_lab = 0
    for d in defects:
        x, y, w, h = d["box"]
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (0, 0, 255), 2)
        n_box += 1
        txt = d.get("label") or ("a=%.2f" % d.get("area_mm2", 0.0))
        cv2.putText(canvas, txt, (x, max(12, y - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        n_lab += 1
    lw, lh = canvas.shape[1], canvas.shape[0]
    px0, py0 = max(0, lw - 128), 6
    py1 = py0 + 16 * len(meta_lines) + 20
    cv2.rectangle(canvas, (px0, py0), (lw - 8, py1), (255, 255, 255), -1)
    cv2.rectangle(canvas, (px0, py0), (lw - 8, py1), (0, 0, 0), 1)
    for i, s in enumerate(meta_lines):
        cv2.putText(canvas, s[:24], (px0 + 4, py0 + 16 + 16 * i),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 1)
    ok = cv2.imwrite(path, canvas)
    return {"boxes": n_box, "labels": n_lab,
            "legend": bool(ok and meta_lines),
            "bytes": os.path.getsize(path) if ok else 0, "path": path}


def synth_parts(count=8, seed=7):
    """课程数据目录缺失时的确定性兜底零件（教师真值口径同样由构造产生）。

    为什么兜底而不是报错：课堂离线机照样要出四档实测；兜底件类型只有
    pit（长度类不伪造），报告里会标明"合成兜底"口径。
    """
    rng = np.random.RandomState(seed)
    parts = []
    for _ in range(count):
        img = np.full((240, 320, 3), 200, np.uint8)
        side = int(rng.randint(10, 22))
        cy, cx = int(rng.randint(40, 200)), int(rng.randint(40, 260))
        img[cy:cy + side, cx:cx + side] = 60
        parts.append({"name": "synth_pit_%03d" % len(parts), "img": img,
                      "type": "pit", "gt_area": round(side * side * 0.01, 2),
                      "gt_len": None})
    return parts
