# -*- coding: utf-8 -*-

from fault_diag import core


def test_make_data_shape():
    X, y = core.make_data(300, 7)
    assert X.shape == (300, 4)
    assert set(y) == {"正常", "轴承磨损", "叶轮堵塞"}


def test_make_data_labels_not_truncated():
    _, y = core.make_data(9, 1)
    assert "轴承磨损" in set(y) and "轴承" not in set(y)


def test_confusion_diagonal_is_correct():
    cm = core.confusion(["a", "a", "b"], ["a", "b", "b"], ["a", "b"])
    assert cm["a"]["a"] == 1 and cm["a"]["b"] == 1 and cm["b"]["b"] == 1


def test_confusion_empty():
    cm = core.confusion([], [], ["a"])
    assert cm == {"a": {"a": 0}}


def test_evaluate_returns_metrics():
    from sklearn.tree import DecisionTreeClassifier
    X, y = core.make_data(120, 3)
    r = core.evaluate(DecisionTreeClassifier(max_depth=3, random_state=0),
                      X[:90], y[:90], X[90:], y[90:], ["正常", "轴承磨损", "叶轮堵塞"])
    assert 0.0 <= r["acc"] <= 1.0
    assert set(r["missed"]) == {"正常", "轴承磨损", "叶轮堵塞"}
