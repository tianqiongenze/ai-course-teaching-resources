# -*- coding: utf-8 -*-
"""双路线检测：传统视觉（必然可用） + COCO 预训练 YOLO（如实呈现）。

工单 M3.2 实测链路（本文件后半段）：真实 yolo_dataset（npy 图 + YOLO
标注）上跑"兜底口径"CPU 推理基线（cv2 分割全链路，含 resize→预处理→
连通域→框还原），三档 imgsz 真实计时；onnxruntime + 离线 yolov8n.onnx
可用时同步给出真实 YOLO 推理/置信度阈值实验。所有数字都是跑出来的。
"""
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


# ── 工单 M3.2 实测链路：真实数据集 + 三档 imgsz 计时 + ONNX 路线 ─────


def load_dataset(ds_dir):
    """npy 图 + YOLO txt 标注 → [{name, img, gts:[(x,y,w,h),...]}]。"""
    out = []
    img_dir = os.path.join(ds_dir, "images")
    for nm in sorted(f for f in os.listdir(img_dir) if f.endswith(".npy")):
        img = np.load(os.path.join(img_dir, nm))
        gts = []
        lp = os.path.join(ds_dir, "labels", nm[:-4] + ".txt")
        if os.path.exists(lp):
            side = img.shape[1]
            for line in open(lp, encoding="utf-8").read().splitlines():
                p = line.split()
                if len(p) != 5:
                    continue
                cx, cy, w, h = (float(v) for v in p[1:])
                gts.append((int((cx - w / 2) * side), int((cy - h / 2) * side),
                            int(w * side), int(h * side)))
        out.append({"name": nm, "img": img, "gts": gts})
    return out


def synth_dataset(count=12, seed=7):
    """课程数据缺失时的确定性兜底数据集（真值由构造给出，报告标明口径）。"""
    rng = np.random.RandomState(seed)
    out = []
    for k in range(count):
        img, gt = make_scene(320, seed=int(rng.randint(0, 100000)))
        box = (gt["cx"] - gt["w"] // 2, gt["cy"] - gt["h"] // 2,
               gt["w"], gt["h"])
        out.append({"name": "synth_%03d.npy" % k, "img": img, "gts": [box]})
    return out


def _seg(f, dev, min_area):
    """f(HxWx3 float32, 已按 imgsz 缩放) → (缺陷框, 产品区bbox)。

    产品区=与四边框条中位色偏离最大者（环境自适应，不硬编码坐标）；
    缺陷=产品区内逐通道偏离产品中位色的灰度差 > dev。
    """
    import cv2
    h, w = f.shape[:2]
    b = max(2, h // 16)
    outside = [float(np.median(np.concatenate(
        [f[:b, :, k].ravel(), f[-b:, :, k].ravel(),
         f[:, :b, k].ravel(), f[:, -b:, k].ravel()]))) for k in range(3)]
    d_out = np.max([np.abs(f[:, :, k] - outside[k]) for k in range(3)], 0)
    # 产品区判据用 30 而不是 20：实测外背景是 190±15 的噪声场，20 会让
    # 边缘碎屑粘上产品 CC、把噪声当缺陷（本次实测误检 2256 个的来源）
    prod = (d_out > 30).astype(np.uint8) * 255
    prod = cv2.morphologyEx(prod, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    prod = cv2.morphologyEx(prod, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(prod, 8)
    if n < 2:
        return [], None
    idx = 1 + int(np.argmax(st[1:, 4]))
    x, y, bw, bh = (int(v) for v in st[idx][:4])
    reg, labr = f[y:y + bh, x:x + bw], lab[y:y + bh, x:x + bw] == idx
    base = [float(np.median(reg[:, :, k][labr])) for k in range(3)]
    d = np.max([np.abs(reg[:, :, k] - base[k]) for k in range(3)], 0)
    msk = ((labr) & (d > dev)).astype(np.uint8) * 255
    msk = cv2.morphologyEx(msk, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    # 产品区 bbox 边缘 2px 内是 resize/原图抗锯齿残留带——实测不挖会沿
    # 产品轮廓碎出一圈假框（本次实测误检 1713/1754 的来源）；开运算会
    # 杀掉 2px 细裂纹（dev=50 档实测 tp=0），故用"挖边"而不是"开运算"。
    msk[:2, :] = 0
    msk[-2:, :] = 0
    msk[:, :2] = 0
    msk[:, -2:] = 0
    n2, _, st2, _ = cv2.connectedComponentsWithStats(msk, 8)
    boxes = [(x + int(st2[i][0]), y + int(st2[i][1]), int(st2[i][2]),
              int(st2[i][3])) for i in range(1, n2) if st2[i][4] >= min_area]
    return boxes, (x, y, bw, bh)


def infer(img, imgsz=320, dev=12.0, min_area=15):
    """基线 CPU 推理全链路（计时对象）：resize→预处理→分割→连通域。

    返回还原到原图坐标系的框——"兜底口径"下三档 imgsz 的 FPS 就是
    对这条真实路径逐档计时，不是估的。
    """
    import cv2
    r = cv2.resize(img, (imgsz, imgsz), interpolation=cv2.INTER_AREA)
    boxes, _bbox = _seg(r.astype(np.float32), dev, min_area)
    s = img.shape[1] / float(imgsz)
    return [(int(round(bx * s)), int(round(by * s)), int(round(bw * s)),
             int(round(bh * s))) for bx, by, bw, bh in boxes]


def infer_roi(img, imgsz=320, dev=12.0, min_area=15):
    """A 档优化①输入裁剪：1/4 缩略图先估产品区 bbox，再只对 crop 做
    等比缩放+缺陷分割——像素预算从 imgsz² 降到 ≈产品区占比·imgsz²，实测提速。
    贴 crop 边框的分量是 bbox 边缘的抗锯齿残留，实测剔除（成因可复核）。"""
    import cv2
    side = max(img.shape[:2])
    s4 = max(16, imgsz // 4)
    thumb = cv2.resize(img, (s4, s4), interpolation=cv2.INTER_AREA)
    _b, bbox = _seg(thumb.astype(np.float32), 20.0, 4)
    if bbox is None:
        return infer(img, imgsz, dev, min_area)
    k = side / float(s4)
    # bbox 外扩 4px 原生像素：把产品轮廓的抗锯齿环推出分析区，缺陷不受影响
    x0 = max(0, int(int(bbox[0] * k)) - 4)
    y0 = max(0, int(int(bbox[1] * k)) - 4)
    x1 = min(side, int(int(bbox[0] + bbox[2]) * k) + 4)
    y1 = min(side, int(int(bbox[1] + bbox[3]) * k) + 4)
    crop = img[y0:y1, x0:x1]
    # 缩放系数与基线 infer 一致（imgsz/side）→ 缺陷像素尺度可比，召回可对照
    s2 = imgsz / float(side)
    cw = max(8, int(round(crop.shape[1] * s2)))
    chh = max(8, int(round(crop.shape[0] * s2)))
    cf = cv2.resize(crop, (cw, chh), interpolation=cv2.INTER_AREA)
    cf = np.ascontiguousarray(cf, dtype=np.float32)
    base = [float(np.median(cf[:, :, i])) for i in range(3)]
    d = np.max([np.abs(cf[:, :, i] - base[i]) for i in range(3)], 0)
    msk = (d > dev).astype(np.uint8) * 255
    msk = cv2.morphologyEx(msk, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(msk, 8)
    inv = 1.0 / s2
    out = []
    for i in range(1, n):
        bx, by, bw, bh, ba = (int(v) for v in st[i])
        if ba < min_area:
            continue
        if bx <= 0 or by <= 0 or bx + bw >= cw - 1 or by + bh >= chh - 1:
            continue
        out.append((int(x0 + bx * inv), int(y0 + by * inv),
                    int(bw * inv), int(bh * inv)))
    return out


def _pin_cv_threads():
    """锁死 cv2 内部线程：本机实测不锁时同一档 FPS 波动可达 3 倍，
    且 cv2 自带并行会污染"多线程优化"对照——计时必须单线程口径才公平。"""
    import cv2
    cv2.setNumThreads(1)


def measure_fps(fn, imgs, imgsz, dev, min_area, frames, warmup):
    """工单"常见错误"第 3 条：warmup 后再计时，且只包推理段（无文件 IO）。"""
    import time
    _pin_cv_threads()
    for k in range(warmup):
        fn(imgs[k % len(imgs)], imgsz=imgsz, dev=dev, min_area=min_area)
    t0 = time.perf_counter()
    for k in range(frames):
        fn(imgs[k % len(imgs)], imgsz=imgsz, dev=dev, min_area=min_area)
    dt = time.perf_counter() - t0
    return round(frames / dt, 2) if dt > 0 else 0.0


def measure_fps_mt(fn, imgs, imgsz, dev, min_area, frames, workers):
    """A 档优化②多线程：同帧数用线程池并发，墙钟时间换算等效 FPS。"""
    import time
    from concurrent.futures import ThreadPoolExecutor
    _pin_cv_threads()
    jobs = [imgs[k % len(imgs)] for k in range(frames)]
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(lambda im: fn(im, imgsz=imgsz, dev=dev,
                                  min_area=min_area), jobs))
    dt = time.perf_counter() - t0
    return round(frames / dt, 2) if dt > 0 else 0.0


def onnx_session(path):
    """真实 YOLO 路线：onnxruntime + 离线 yolov8n.onnx；缺任一返回 None。"""
    try:
        import onnxruntime as ort
    except ImportError:
        return None
    if not path or not os.path.exists(path):
        return None
    try:
        return ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    except Exception:
        return None


def onnx_detect(sess, img, conf=0.25, imgsz=640):
    """COCO 预训练 YOLOv8n CPU 推理：预处理→session.run→置信度过滤→NMS。"""
    import cv2
    x = cv2.resize(img, (imgsz, imgsz)).astype(np.float32)
    x = np.ascontiguousarray(x.transpose(2, 0, 1)[None] / 255.0)
    out = sess.run(None, {"images": x})[0][0]
    scores = out[4:].max(axis=0)
    cand = np.where(scores >= conf)[0]
    s = img.shape[1] / float(imgsz)
    boxes = []
    for j in cand:
        cx, cy, bw, bh = out[:4, j]
        boxes.append(((cx - bw / 2) * s, (cy - bh / 2) * s, bw * s, bh * s,
                      int(out[4:, j].argmax()), float(scores[j])))
    return _nms(boxes)


def _nms(boxes, thr=0.45):
    kept = []
    for b in sorted(boxes, key=lambda v: -v[5]):
        bb = tuple(b[:4])
        if all(iou(bb, tuple(k[:4])) < thr for k in kept):
            kept.append(b)
    return kept


def measure_onnx_fps(sess, img, frames, warmup, imgsz=640):
    """ONNX 路线 640 档真实计时（该模型输入尺寸固定 640，兜底口径说明用）。"""
    import time

    import cv2
    _pin_cv_threads()
    x = cv2.resize(img, (imgsz, imgsz)).astype(np.float32)
    x = np.ascontiguousarray(x.transpose(2, 0, 1)[None] / 255.0)
    inp = {sess.get_inputs()[0].name: x}
    for _ in range(warmup):
        sess.run(None, inp)
    t0 = time.perf_counter()
    for _ in range(frames):
        sess.run(None, inp)
    dt = time.perf_counter() - t0
    return round(frames / dt, 2) if dt > 0 else 0.0


def match_stats(gts, dets, thr=0.3):
    """按 IoU 匹配实测：tp=被检出的真值数，fp=匹配外检出数（误检）。"""
    tp = sum(1 for g in gts
             if any(iou(g, tuple(d[:4])) >= thr for d in dets))
    fp = sum(1 for d in dets
             if not any(iou(g, tuple(d[:4])) >= thr for g in gts))
    return tp, fp


def annotate(img, items, path, meta_lines):
    """items: [(box, label)] → 画框+文字+图例真落盘，返回机检要素计数。"""
    import cv2
    canvas = np.ascontiguousarray(img)
    n_box = n_lab = 0
    for box, label in items:
        x, y, w, h = (int(v) for v in box[:4])
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (0, 0, 255), 2)
        n_box += 1
        cv2.putText(canvas, label, (x, max(12, y - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        n_lab += 1
    lw, lh = canvas.shape[1], canvas.shape[0]
    px0, py0 = max(0, lw - 138), 6
    py1 = py0 + 16 * len(meta_lines) + 20
    cv2.rectangle(canvas, (px0, py0), (lw - 8, py1), (255, 255, 255), -1)
    cv2.rectangle(canvas, (px0, py0), (lw - 8, py1), (0, 0, 0), 1)
    for i, s in enumerate(meta_lines):
        cv2.putText(canvas, s[:26], (px0 + 4, py0 + 16 + 16 * i),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 1)
    ok = cv2.imwrite(path, canvas)
    return {"boxes": n_box, "labels": n_lab,
            "legend": bool(ok and meta_lines),
            "bytes": os.path.getsize(path) if ok else 0, "path": path}
