# -*- coding: utf-8 -*-
"""工单 M4.1 四档验收断言——每档都钉在"实测值"上，能力删掉就必须红。

档位判据与 tiers.verdict / cli --tier 同源（工单验收标准表）：
D 准确率≥0.75+库外新文本实测预测；C ≥0.80+两分类器对比完整；
B ≥0.85+Top10 关键词全类覆盖；A 达B且混淆矩阵定位易混对+词典/ngram 实测调优。
fixture 用本次 pytest 进程真实跑完整流水线，断言只看真实产物文件与计数。
"""
import os

import pytest

from fault_text_clf import config as C
from fault_text_clf import io_utils, pipeline, tiers

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(PROJ, "config", "rules.yaml")
OUT = os.path.join(PROJ, "output", "test_run")


@pytest.fixture(scope="module")
def built():
    """跑一次完整训练-评估-预测链路，模块内所有断言共用同一批实测值。"""
    return pipeline.build(C.load_config(CFG), out_dir=OUT)


def tiers_of(v):
    """tiers.verdict 的返回 → {档位字母: 判定}（实测与手工构造同一口径）。"""
    return {t["tier"][-2]: t for t in v["tiers"]}


def _real_verdict(r, **override):
    """在实测值上只改动一个能力开关——档位必须随之下降（反向证明）。"""
    m = r["tiers"]["measured"]
    kw = {"gates": r["tiers"]["gates"], "rate": r["style_rate"],
          "acc": m["acc"], "n_new": m["n_new"], "new_match": m["new_match"],
          "n_models": m["n_models"], "kw_classes": m["kw_classes"],
          "n_classes": m["n_classes"], "cm": r["confusion"],
          "tuning_done": m["tuning_done"], "tune_delta": m["tune_delta"]}
    kw.update(override)
    return tiers.verdict(**kw)


def test_gate_numbers_come_from_rules_yaml():
    """门槛数字外置在 rules.yaml 的 tiers: 段，代码读出即判定口径。"""
    g = tiers.gates_from(C.load_config(CFG))
    assert g["D"]["acc_min"] == 0.75 and g["C"]["acc_min"] == 0.80
    assert g["B"]["acc_min"] == 0.85 and g["D"]["new_min"] == 3


def test_D_predicts_new_texts_outside_corpus(built):
    _, r = built
    assert r["n_new"] >= 3, "工单要求对 3 条库外新文本真实调用 predict"
    assert r["n_match"] >= 2, "新文本预测命中数由真实模型输出实测"
    assert all(p["text"] for p in r["new_pred"])


def test_C_two_classifiers_measured_on_same_split(built):
    _, r = built
    mt = r["metrics"]
    assert "LR基线(1,1)" in mt and "NB基线(1,1)" in mt
    assert mt["LR基线(1,1)"]["acc"] >= 0.75 and mt["NB基线(1,1)"]["acc"] >= 0.75


def test_B_top_keywords_cover_every_class(built):
    _, r = built
    kw = r["keywords"]
    assert set(kw) == set(r["classes"]), "每类都要有实测 Top 关键词表"
    assert all(len(v) >= 5 for v in kw.values())


def test_A_confusion_pair_located_by_measurement(built):
    _, r = built
    cm = r["confusion"]
    assert cm["top_pair"] is not None
    assert cm["top_pair"]["count"] >= 1


def test_A_tuning_actually_ran(built):
    _, r = built
    assert r["userdict_loaded"] and os.path.exists(r["userdict"])
    assert r["ngram_tune"] >= 2
    assert r["tune_delta"] == pytest.approx(
        r["tier_acc"] - r["metrics"]["LR基线(1,1)"]["acc"], abs=1e-4)


def test_real_artifacts_exist_and_are_not_empty(built):
    """产物只认真实文件：json/csv/png 存在且字节数>1000。"""
    _, r = built
    for name, path in r["artifacts"].items():
        assert path and os.path.exists(path), "%s 缺失" % name
        assert os.path.getsize(path) > 1000, "%s 体量不足: %s" % (name, path)
    data = io_utils.read_json(r["artifacts"]["result_json"])
    assert "tiers" in data


def test_report_contains_tier_section(built):
    """run.py 的报告必须有 [验收档位判定（实测）] 段与人工答辩清单。"""
    _, r = built
    text = open(os.path.join(OUT, "report.txt"), encoding="utf-8").read()
    assert "[验收档位判定（实测）]" in text
    assert "人工答辩项 %d 条" % len(r["tiers"]["manual"]) in text


def test_all_four_tiers_pass_and_claim_is_highest(built):
    _, r = built
    got = tiers_of(r["tiers"])
    for key in ("D", "C", "B", "A"):
        assert got[key]["pass"], "%s 档实测未达标: %s" % (key, got[key])
    assert r["tiers"]["claimed"] == "优(A)"


def test_claim_drops_when_accuracy_below_gate(built):
    """反向证明：准确率降到 0.82（B 档门槛之下），B/A 必须红、C 仍绿。"""
    _, r = built
    got = tiers_of(_real_verdict(r, acc=0.82))
    assert got["A"]["pass"] is False and got["B"]["pass"] is False
    assert got["C"]["pass"] and got["D"]["pass"]


def test_claim_drops_to_D_when_no_two_classifier_compare(built):
    _, r = built
    got = tiers_of(_real_verdict(r, n_models=1))
    assert got["C"]["pass"] is False and got["D"]["pass"]


def test_D_fails_when_new_text_predictions_missing(built):
    """库外新文本一条都没预测（n_new=0），D 档就不达标。"""
    _, r = built
    got = tiers_of(_real_verdict(r, n_new=0, new_match=0))
    assert got["D"]["pass"] is False


def test_A_fails_when_tuning_removed(built):
    """去掉自建词典/ngram（tuning_done=False），A 必须掉到 B。"""
    _, r = built
    got = tiers_of(_real_verdict(r, tuning_done=False))
    assert got["A"]["pass"] is False and got["B"]["pass"]


def test_A_fails_when_no_confusion_evidence(built):
    """混淆矩阵退化到连近误都没有（top_pair=None），A 不达标。"""
    _, r = built
    empty_cm = {"off_diag": 0, "method": "无", "top_pair": None,
                "matrix": r["confusion"]["matrix"],
                "labels": r["confusion"]["labels"]}
    got = tiers_of(_real_verdict(r, cm=empty_cm))
    assert got["A"]["pass"] is False and got["B"]["pass"]
