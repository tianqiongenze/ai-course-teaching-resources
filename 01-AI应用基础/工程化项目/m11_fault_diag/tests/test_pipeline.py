# -*- coding: utf-8 -*-
"""集成测试：run.py 端到端 → output/report.txt + result.json 的档位与口径。"""
import json
import os

import pytest

from fault_diag import config as C
from fault_diag import io_utils
from fault_diag import pipeline as P

CFG = os.path.join(os.path.dirname(__file__), "..", "config", "rules.yaml")


@pytest.fixture(scope="module")
def ran(tmp_path_factory):
    cfg = C.load_config(CFG)
    out = str(tmp_path_factory.mktemp("m11out"))
    sections = P.run(cfg, out)
    return out, sections


def test_outputs_exist(ran):
    out, _ = ran
    assert os.path.exists(os.path.join(out, "report.txt"))
    assert os.path.exists(os.path.join(out, "result.json"))


def test_uses_real_dataset(ran):
    out, _ = ran
    res = json.load(open(os.path.join(out, "result.json"), encoding="utf-8"))
    if io_utils.course_data("pump_fault.csv"):
        assert res["source"].startswith("真实数据")
        assert res["n_train"] + res["n_test"] == 450
    else:
        assert "合成兜底" in res["source"]                  # 降级必须写在报告里


def test_three_models_and_four_metrics(ran):
    """工单要求三分类器 + 四项指标（acc/精确率/召回率/F1 宏平均）齐备。"""
    out, _ = ran
    res = json.load(open(os.path.join(out, "result.json"), encoding="utf-8"))
    assert set(res["models"]) == {"逻辑回归", "决策树", "随机森林"}
    for v in res["models"].values():
        for k in ("acc", "precision_macro", "recall_macro", "f1_macro"):
            assert k in v and 0.0 <= v[k] <= 1.0


def test_decision_matrix_is_a_table(ran):
    out, _ = ran
    res = json.load(open(os.path.join(out, "result.json"), encoding="utf-8"))
    rows = res["decision_matrix"]
    assert len(rows) == 3
    assert {r["决策"] for r in rows} == {"交付", "备选", "不交付"}
    txt = open(os.path.join(out, "report.txt"), encoding="utf-8").read()
    assert "决策矩阵" in txt and "候选模型" in txt


def test_tier_gates_on_delivered_model(ran):
    """工单 M1.1：及格(D) 准确率≥0.75；此处按 result.json 实测值断言。"""
    out, _ = ran
    res = json.load(open(os.path.join(out, "result.json"), encoding="utf-8"))
    if not io_utils.course_data("pump_fault.csv"):
        pytest.skip("兜底合成数据不参与工单档位判定")
    acc = res["metrics"]["acc"]
    assert acc >= res["gates"]["d"] >= 0.75
    assert acc >= res["gates"]["b"] >= 0.85                 # 优秀(B) 线
    assert res["tier"] in ("B", "A")
