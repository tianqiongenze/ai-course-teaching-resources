# -*- coding: utf-8 -*-

from yolo_dual import core


def test_make_scene_returns_gt():
    img, gt = core.make_scene(320, 7)
    assert img.shape == (320, 320, 3)
    assert gt["w"] == 40


def test_cv_detect_finds_block():
    img, _ = core.make_scene(320, 7)
    b = core.cv_detect(img)
    assert len(b) >= 1


def test_iou_identical_is_one():
    a = (10, 10, 40, 40)
    assert core.iou(a, a) == 1.0


def test_iou_disjoint_is_zero():
    assert core.iou((0, 0, 10, 10), (100, 100, 10, 10)) == 0.0


def test_iou_partial_between_zero_and_one():
    v = core.iou((0, 0, 20, 20), (10, 0, 20, 20))
    assert 0.0 < v < 1.0


def test_yolo_pretrained_returns_none_without_deps():
    img, _ = core.make_scene(320, 7)
    assert core.yolo_pretrained(img, "/no/such/weights.onnx") is None
