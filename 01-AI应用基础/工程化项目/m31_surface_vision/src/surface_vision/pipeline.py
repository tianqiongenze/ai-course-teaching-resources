# -*- coding: utf-8 -*-
"""合成零件图 → 差分 → 连通域 → 分类 → 检测台账。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    size = int(cfg.raw.get("img_size", 240))
    dev = float(cfg.raw.get("mask_dev", 15))
    min_area = int(cfg.raw.get("min_area_px", 20))
    img, gt = core.make_scene(size, seed=cfg.seed)
    m = core.mask(img, dev=dev)
    boxes = core.components(m, min_area)
    if not boxes:
        raise ValueError("未检出任何缺陷——请检查 mask_dev / min_area_px 配置")
    mm_per_px = 0.05
    lines, items = [], []
    for b in boxes:
        kind = core.classify(img, b)
        area_mm2 = round(b[4] * mm_per_px * mm_per_px, 2)
        lines.append("框(x=%d,y=%d,%dx%d) 面积=%dpx=%.2fmm² 类型=%s" % (
            b[0], b[1], b[2], b[3], b[4], area_mm2, kind))
        items.append({"box": b[:4], "area_px": b[4], "area_mm2": area_mm2, "type": kind})
    result = {"gt": list(gt), "n_defects": len(boxes), "defects": items}
    sections = [("输入口径", ["零件图 %d×%d｜偏差阈值 %.0f｜最小面积 %dpx｜像素比 %.2f mm/px"
                % (size, size, dev, min_area, mm_per_px)]),
                ("检测结果", lines),
                ("真值对照", ["真值框 = %s" % (gt,)]),
                ("结论与建议", ["缺陷已定位+量化+分类；小噪点按最小面积过滤，"
                 "疑难件进人工复核队列"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections
