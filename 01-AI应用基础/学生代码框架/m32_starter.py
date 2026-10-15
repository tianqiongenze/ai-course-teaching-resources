# -*- coding: utf-8 -*-
# [教学脚手架] 下列导入/变量供 TODO 完成后使用，故标注 noqa 而非删除
"""M3.2 产线实时缺陷检测（预训练YOLOv8n, CPU推理主线）—— 学生代码框架
自动适配两种环境: 装了ultralytics用YOLOv8n; 否则用onnxruntime+教师导出的ONNX。
"""
import glob
import time  # noqa: F401

import cv2
import numpy as np

IMGS = sorted(glob.glob("data/yolo_dataset/images/*.npy"))
CLASSES = ["dent", "stain", "edge_crack"]
W_PATH = "data/weights/yolov8n.pt"
ONNX = "data/weights/yolov8n.onnx"


def run_ultralytics(img_bgr, conf=0.4, imgsz=320):
    """方案A: ultralytics"""
    from ultralytics import YOLO
    model = YOLO(W_PATH)
    r = model.predict(img_bgr, conf=conf, imgsz=imgsz, device="cpu",
                      classes=None, verbose=False)
    return r[0].plot(), len(r[0].boxes)


def run_onnx(img_bgr, conf=0.4, imgsz=320):
    """方案B(离线备选): onnxruntime; 输入1×3×640×640, float32, /255"""
    import onnxruntime as ort
    sess = ort.InferenceSession(ONNX, providers=["CPUExecutionProvider"])
    x = cv2.resize(img_bgr, (640, 640)).astype(np.float32) / 255.0
    x = x.transpose(2, 0, 1)[None]
    out = sess.run(None, {"images": x})[0][0]        # (84,8400): 0-3=xywh, 4-83=80类分数  # noqa: F841
    # TODO-1 解析: cls = out[4:]; conf=cls.max(0), cid=cls.argmax(0); keep=conf>阈值
    # boxes = out[:4].T[keep]  (cx,cy,w,h @640, 需按原图缩放回画框)
    # === 你的代码: 统计检出数并在img_bgr画框+类别文字 ===
    return img_bgr, 0


def pick_backend():
    try:
        import ultralytics  # noqa
        return "ultralytics"
    except ImportError:
        return "onnx"


def main():
    backend = pick_backend()
    runner = run_ultralytics if backend == "ultralytics" else run_onnx
    print("后端:", backend)

    # ---- 1) 推理可视化(前5张) ----
    for p in IMGS[:5]:
        img = np.load(p).astype(np.uint8)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        anno, n = runner(img)
        cv2.imwrite("yolo_" + p.split("/")[-1].replace(".npy", ".png"), anno)
        print(p.split("/")[-1], "检出", n)

    # ---- 2) 阈值实验: conf∈{0.25,0.4,0.6,0.8} ----
    # TODO-2: 循环调用runner, 统计20张图总检出数, 填入工单表格
    # ---- 3) FPS测试: imgsz∈{160,320,640} ----
    # TODO-3: warmup 3帧后计时20帧, 打印平均FPS(只计推理段!)
    # for imgsz in (160, 320, 640):
    #     t0 = time.time()
    #     for p in IMGS[:20]: ...
    #     fps = 20 / (time.time() - t0)
    # ---- 4) 决策矩阵: 综合检出与FPS选择产线配置 ----


if __name__ == "__main__":
    main()
