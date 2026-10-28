# -*- coding: utf-8 -*-
"""集成测试：消融流水线端到端 + 工单 M1.2 档位产物校验。"""
import json
import os

import pytest

from data_quality import config as C
from data_quality import io_utils
from data_quality import pipeline as P

CFG = os.path.join(os.path.dirname(__file__), "..", "config", "rules.yaml")


@pytest.fixture(scope="module")
def ran(tmp_path_factory):
    if io_utils.course_data("pump_fault.csv") is None:
        pytest.skip("课程数据不可用")
    cfg = C.load_config(CFG)
    out = str(tmp_path_factory.mktemp("m12out"))
    sections = P.run(cfg, out)
    return out, json.load(open(os.path.join(out, "result.json"), encoding="utf-8"))


def test_missing_data_raises(tmp_path):
    cfg = C.load_config(CFG)
    cfg.raw["data_file"] = "no_such_file.csv"
    with pytest.raises(FileNotFoundError):
        P.run(cfg, str(tmp_path))


def test_ablation_has_five_rows(ran):
    _, res = ran
    steps = [d["step"] for d in res["ablation"]]
    assert len(steps) == 5
    assert any("清洗" in s for s in steps) and any("派生" in s for s in steps)
    assert any("缩放" in s for s in steps) and any("调参" in s for s in steps)
    for d in res["ablation"]:
        assert {"acc", "f1_macro", "recall"} <= set(d)


def test_derived_features_at_least_two(ran):
    _, res = ran
    assert len(res["derived_features"]) >= 2


def test_tier_gates_from_real_run(ran):
    """工单 M1.2 四档：提升≥5pp(D)/≥7pp(C)/≥10pp且F1≥0.80(B)/≥3法+因果解释(A)。"""
    _, res = ran
    assert res["gain_pp"] >= 10.0
    assert res["tier"]["tier"] == "A"
    assert res["tier"]["B"] and res["tier"]["f1_macro"] >= 0.80
    assert res["n_methods"] >= 3


def test_cv_stability_reported(ran):
    _, res = ran
    cv = res["cv_stability"]
    assert len(cv["folds"]) == 5 and 0 <= cv["mean"] <= 1


def test_grid_search_on_train_only(ran):
    _, res = ran
    assert "model__C" in res["best_params"]
    assert len(res["grid_rows"]) >= 2
    assert res["grid_rows"][0]["训练折内5折CV均值"] >= res["grid_rows"][-1]["训练折内5折CV均值"]


def test_scaler_matrix_shows_tree_insensitivity(ran):
    """决策矩阵中树模型三档缩放准确率必须一致（工单常见错误②的实测证据）。"""
    _, res = ran
    rf = [r["acc"] for r in res["scaler_matrix"] if "对照" in r["模型"]]
    assert len(rf) == 3 and len(set(rf)) == 1


def test_lab_view_is_reported_not_hidden(ran):
    """口径B（实验室原样）也必须写入产物，避免只挑好看数字。"""
    _, res = ran
    assert "lab_view" in res
    lab = res["lab_view"]
    assert lab["final"]["acc"] >= lab["baseline"]["acc"]
