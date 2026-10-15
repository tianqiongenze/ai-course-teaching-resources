# -*- coding: utf-8 -*-
import numpy as np

from weld_cnn import core


def test_make_images_shapes():
    X, y = core.make_images(60, 3, 32)
    assert X.shape == (60, 32, 32)
    assert set(y) == set(core.CLASSES)


def test_img_feats_three_values():
    img = np.zeros((32, 32))
    f = core.img_feats(img)
    assert len(f) == 3 and isinstance(f[0], float)


def test_pore_image_has_more_bright_pixels():
    X, _ = core.make_images(6, 5, 32)
    f_pore = core.featurize([X[1]])[0]         # 第二张是气孔
    f_norm = core.featurize([X[0]])[0]         # 第一张是正常
    assert f_pore[0] > f_norm[0]                # 气孔亮块比例高于正常图


def test_crack_image_has_dark_line():
    X, _ = core.make_images(6, 5, 32)
    f = core.featurize([X[2]])[0]               # 第三张是裂纹
    assert f[1] > 0.0


def test_score_returns_per_fold():
    X, y = core.make_images(120, 7, 32)
    F = core.featurize(X)
    sc = core.score(F, y, folds=3)
    assert len(sc) == 3 and all(0.0 <= v <= 1.0 for v in sc)
