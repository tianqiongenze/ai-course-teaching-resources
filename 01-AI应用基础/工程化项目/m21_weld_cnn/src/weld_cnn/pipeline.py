# -*- coding: utf-8 -*-
"""合成焊缝图 → 块统计特征 → 交叉验证 → 特征重要性。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    n = int(cfg.raw.get("n_images", 180))
    folds = int(cfg.raw.get("cv_folds", 3))
    size = int(cfg.raw.get("img_size", 32))
    X, y = core.make_images(n, seed=cfg.seed, size=size)
    F = core.featurize(X)
    sc = core.score(F, y, folds=folds)
    from sklearn.ensemble import RandomForestClassifier
    clf = RandomForestClassifier(random_state=0).fit(F, y)
    names = ["亮块比例", "暗线比例", "最大亮值"]
    order = sorted(range(len(names)), key=lambda i: -clf.feature_importances_[i])
    result = {"n_images": len(X), "cv_mean": round(float(sc.mean()), 4),
              "cv_std": round(float(sc.std()), 4),
              "importance": {names[i]: round(float(clf.feature_importances_[i]), 4)
                             for i in order},
              "note": "轻量基线≠CNN上限"}
    sections = [("输入口径", ["图像 %d 张（%s）｜%d×%d 灰度｜块统计3维特征｜%d 折交叉验证"
                % (n, "/".join(core.CLASSES), size, size, folds)]),
                ("交叉验证", ["cv = %.3f ± %.3f" % (sc.mean(), sc.std())]),
                ("特征重要性", ["%d. %s = %.3f" % (k + 1, names[i], clf.feature_importances_[i])
                 for k, i in enumerate(order)]),
                ("结论与建议", ["基线已可用（cv≥0.8）；真 CNN 的预期增益需用数据量/算力/标注成本三项证据说话"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections
