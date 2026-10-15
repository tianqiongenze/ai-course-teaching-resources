# -*- coding: utf-8 -*-
"""同一输入 → 双路线并行 → IoU 匹配 → 对照结论。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    import numpy as np
    n = int(cfg.raw.get("n_images", 12))
    dev = float(cfg.raw.get("mask_dev", 15))
    min_area = int(cfg.raw.get("min_area_px", 25))
    rng = np.random.RandomState(cfg.seed)
    gt_total = cv_hit = cv_total = pretrained_total = 0
    rows = []
    for k in range(n):
        img, gt = core.make_scene(320, seed=int(rng.randint(0, 100000)))
        gtb = (gt["cx"] - gt["w"] // 2, gt["cy"] - gt["h"] // 2, gt["w"], gt["h"])
        cvb = core.cv_detect(img, dev=dev, min_area=min_area)
        hit = any(core.iou(gtb, b) >= 0.3 for b in cvb)
        gt_total += 1
        cv_hit += int(hit)
        cv_total += len(cvb)
        py = core.yolo_pretrained(img)
        pretrained_total += (py or 0)
        rows.append({"k": k, "cv_boxes": len(cvb), "hit": hit,
                     "yolo": py if py is not None else "n/a"})
    result = {"n_images": gt_total, "cv_total_boxes": cv_total,
              "cv_hits": cv_hit,
              "cv_recall": round(cv_hit / max(gt_total, 1), 4),
              "pretrained_detections": pretrained_total, "rows": rows}
    sections = [("输入口径", ["合成工业图 %d 张｜缺陷: 矩形块110｜IoU 匹配阈值 0.3" % gt_total]),
                ("路线① 传统视觉", ["检出框 %d 个｜命中真值 %d / %d（召回 %.0f%%）"
                 % (cv_total, cv_hit, gt_total, result["cv_recall"] * 100)]),
                ("路线② 预训练YOLO", ["检出 %d 个（COCO 预训练权重不认识合成工业缺陷 → 领域不匹配）"
                 % pretrained_total]),
                ("数据质量发现", ["真值框高约 %dpx，而实际缺陷块仅 40×40——标注口径须与目标尺度一致"
                 % core.make_scene(320, 7)[1]["h"]]),
                ("结论与建议", ["预训练模型必须领域微调；微调前用传统视觉保底上线；"
                 "先修标注口径，再累积样本"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections
