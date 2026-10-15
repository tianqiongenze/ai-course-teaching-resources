# -*- coding: utf-8 -*-

from surface_vision import core


def test_make_scene_returns_image_and_gt():
    img, gt = core.make_scene(240, 7)
    assert img.shape == (240, 240, 3)
    assert len(gt) == 4


def test_mask_detects_defect():
    img, _ = core.make_scene(240, 7)
    m = core.mask(img)
    assert m.max() == 255 and int((m > 0).sum()) > 100


def test_mask_threshold_controls_sensitivity():
    img, _ = core.make_scene(240, 7)
    tight = core.mask(img, dev=200)
    loose = core.mask(img, dev=5)
    assert int((loose > 0).sum()) > int((tight > 0).sum())


def test_components_finds_main_defect():
    img, _ = core.make_scene(240, 7)
    boxes = core.components(core.mask(img), min_area=20)
    assert len(boxes) >= 1
    assert all(b[4] >= 20 for b in boxes)


def test_classify_dent_all_channels_deviate():
    img, _ = core.make_scene(240, 7)
    b = core.components(core.mask(img), min_area=20)[0]
    assert core.classify(img, b) == "dent"
