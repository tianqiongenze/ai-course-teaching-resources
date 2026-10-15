# -*- coding: utf-8 -*-
"""M3.2 统一评估脚本（v3.1新增：统一mAP/检出率口径）
用途: 教师端统一测试集统一口径评估, 学生提交 predictions.json
用法:
    python eval_m32.py --demo      # 生成基准 predictions 示例(跑ONNX模型)
    python eval_m32.py predictions.json
学生提交格式(predictions.json):
    [{"file": "img_040.npy", "boxes": [[cls_id, cx, cy, w, h, conf], ...]}, ...]
    坐标为0-1归一化(yolo格式); cls_id: 0=dent 1=stain 2=edge_crack
测试集: data/yolo_dataset 后20张(img_040~img_059), 全班统一, 禁止改动
输出: 检出率(IoU>=0.5且类别正确)、误检数、逐图明细
"""
import glob
import json
import os
import sys

TEST_START = 40                     # img_040 之后为统一测试集


def load_truth():
    d = "data/yolo_dataset"
    out = {}
    for lp in sorted(glob.glob(os.path.join(d, "labels", "*.txt"))):
        name = os.path.basename(lp).replace(".txt", ".npy")
        idx = int(os.path.basename(lp)[4:7])
        if idx < TEST_START:
            continue
        boxes = []
        for line in open(lp):
            p = line.split()
            if len(p) == 5:
                boxes.append([int(p[0])] + [float(x) for x in p[1:]])
        out[name] = boxes
    return out


def iou(a, b):
    ax1, ay1, ax2, ay2 = a[1] - a[3] / 2, a[2] - a[4] / 2, a[1] + a[3] / 2, a[2] + a[4] / 2
    bx1, by1, bx2, by2 = b[1] - b[3] / 2, b[2] - b[4] / 2, b[1] + b[3] / 2, b[2] + b[4] / 2
    ix = max(0, min(ax2, bx2) - max(ax1, bx1))
    iy = max(0, min(ay2, by2) - max(ay1, by1))
    inter = ix * iy
    return inter / (a[3] * a[4] + b[3] * b[4] - inter + 1e-9)


def evaluate(pred_file, conf_th=0.4):
    preds = {p["file"]: [b for b in p["boxes"] if b[5] >= conf_th]
             for p in json.load(open(pred_file))}
    truth = load_truth()
    tp = fn = fp = 0
    detail = []
    for name, gt in truth.items():
        pd_boxes = preds.get(name, [])
        matched = set()
        for g in gt:
            hit = next((i for i, p in enumerate(pd_boxes)
                        if i not in matched and p[0] == g[0]
                        and iou(g, p) >= 0.5), None)
            if hit is not None:
                matched.add(hit)
                tp += 1
            else:
                fn += 1
        fp += len(pd_boxes) - len(matched)
        detail.append((name, len(gt), len(pd_boxes),
                       sum(1 for i in range(len(pd_boxes)) if i in matched)))
    rec = tp / max(tp + fn, 1)
    print(f"统一测试集: {len(truth)}张 | conf>={conf_th}")
    print(f"检出率(IoU≥0.5同类) = {tp}/{tp+fn} = {rec:.1%} | 误检 = {fp}")
    print("评分口径: 检出率≥70%达及格线mAP口径, ≥80%优秀(教师端换算)")
    for row in detail[:10]:
        print("  %s 标注%d 预测%d 命中%d" % row)


def demo():
    """教师基准: 用ONNX预训练模型跑统一测试集(预期低检出→印证微调必要性)"""
    import cv2
    import numpy as np
    import onnxruntime as ort
    sess = ort.InferenceSession("data/weights/yolov8n.onnx",
                                providers=["CPUExecutionProvider"])
    preds = []
    for ip in sorted(glob.glob("data/yolo_dataset/images/*.npy")):
        idx = int(os.path.basename(ip)[4:7])
        if idx < TEST_START:
            continue
        img = np.load(ip).astype(np.uint8)
        x = cv2.resize(img, (640, 640)).astype(np.float32) / 255.0
        out = sess.run(None, {"images": x.transpose(2, 0, 1)[None]})[0][0]
        cls = out[4:]
        conf, cid = cls.max(0), cls.argmax(0)
        keep = np.where(conf > 0.4)[0]
        boxes = [[int(cid[i]), float(out[1, i] / 640), float(out[0, i] / 640),
                  float(out[2, i] / 640), float(out[3, i] / 640), float(conf[i])]
                 for i in keep[:8]]
        preds.append({"file": os.path.basename(ip), "boxes": boxes})
    json.dump(preds, open("teacher_baseline.json", "w"), indent=1)
    print("已生成 teacher_baseline.json")
    evaluate("teacher_baseline.json")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        evaluate(sys.argv[1] if len(sys.argv) > 1 else "predictions.json")
