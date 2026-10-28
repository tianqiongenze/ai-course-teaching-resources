# -*- coding: utf-8 -*-
"""工单 M2.1 四档验收断言——每档都钉在"本次运行实测值"上，能力删掉必须红。

判据与 tiers.verdict / cli --tier 同源（工单《四、验收标准》原文）：
D 准确率≥0.80+训练-评估流程+形状表基本正确；C ≥0.85+形状表完整无误；
B ≥0.88+数据增强（翻转/平移）双臂对比；A 达 B 且 loss 曲线/混淆矩阵真实
落盘 + 误判样本被代码真实挑出。断言只看真实产物（png 字节、双臂 loss、
钩子形状表），口头解释类归 manual、不自动判达标。
"""
import os

import pytest

from weld_cnn import config as C
from weld_cnn import pipeline, tiers

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(PROJ, "config", "rules.yaml")
OUT = os.path.join(PROJ, "output", "test_run")


@pytest.fixture(scope="module")
def built():
    """跑一次完整双臂训练，模块内所有断言共用同一批实测值。"""
    sections, result = pipeline.build(C.load_config(CFG), out_dir=OUT)
    return sections, result


def tiers_of(v):
    return {t["tier"][-2]: t for t in v["tiers"]}


def _verdict_from(built_result, **overrides):
    """在真实实测字典上改单项能力——验证档位由输入决定而非常量。"""
    cfg = C.load_config(CFG)
    tcfg = cfg.raw.get("tiers") or {}
    gates = {"d": float(tcfg.get("acc_d", 0.80)),
             "c": float(tcfg.get("acc_c", 0.85)),
             "b": float(tcfg.get("acc_b", 0.88))}
    m = dict(built_result["tiers"]["measured"])
    m.update(overrides)
    return tiers.verdict(gates, m)


def test_real_weld_data_is_used(built):
    _, r = built
    assert r["source"].startswith("真实课程数据"), (
        "本机存在 data/weld_images，必须走真实数据而非合成兜底")
    assert r["classes_balance"] == [60, 60, 60, 60] or min(
        r["classes_balance"]) > 0, "工单口径四类均衡数据实测计数"


def test_D_training_flow_actually_ran(built):
    """D 档：双臂逐轮 loss 是真实训练产物（loss 序列>3 点且在下降）。"""
    _, r = built
    assert r["tiers"]["measured"]["flow"], "训练-评估流程必须真实跑通"
    losses = r["losses_noaug"]
    assert losses and len(losses) > 3 and losses[-1] < losses[0]


def test_D_shape_trace_measured_matches_formula(built):
    """形状表：forward hook 实测段数≥4 且逐段等于卷积算式期望（工单 C 档
    '完整无误'的机器口径，本次必须全对）。"""
    _, r = built
    m = r["tiers"]["measured"]
    assert m["shape_stages"] >= 4 and m["shape_basic"]
    assert m["shape_match"] == m["shape_stages"], (
        "形状表实测与期望不一致: %s" % r["shape_trace"])
    csv_path = os.path.join(OUT, "shape_trace.csv")
    assert os.path.exists(csv_path) and os.path.getsize(csv_path) > 100


def test_delivered_accuracy_meets_gate_b(built):
    _, r = built
    gate_b = (C.load_config(CFG).raw.get("tiers") or {})["acc_b"]
    assert r["acc"] >= float(gate_b), (
        "交付臂实测准确率 %.4f 低于工单 B 档门槛 %.2f" % (r["acc"], gate_b))


def test_B_augmentation_comparison_is_a_real_two_arm_run(built):
    """B 档：增强（翻转/平移）不是嘴上说说——两臂各自真训练、同一测试集，
    Δ 是实测差值。"""
    _, r = built
    m = r["tiers"]["measured"]
    assert m["aug_done"] and m["acc_aug"] is not None
    assert r["losses_aug"] and r["losses_noaug"]
    assert m["aug_delta"] == round(m["acc_aug"] - m["acc_noaug"], 4)
    # 工单 B 档只要求"对比效果"——Δ 如实呈现即可，正负都由实测说了算


def test_A_plots_are_real_png_artifacts(built):
    """A 档：loss 曲线与混淆矩阵 png 真实落盘且字节 >1000。"""
    _, r = built
    for key in ("loss_curve", "confusion_matrix"):
        art = r["artifacts"][key]
        path = os.path.join(OUT, art["path"])
        assert art["exists"] and os.path.exists(path), "%s 未落盘" % key
        assert art["bytes"] > 1000, "%s 字节数 %d，疑似空图" % (key, art["bytes"])


def test_A_misjudge_or_risk_samples_are_real_rows(built):
    """A 档代码化的一半：误判样本被真实挑出（或全对时列最低置信度高危样本），
    标签/预测/置信度都来自真实预测张量。口头解释仍是 manual。"""
    _, r = built
    m = r["tiers"]["measured"]
    assert m["miss_done"], "误判/高危样本一条都没挑出来，A 档该能力就是缺"
    rows = r["miss_samples"] or r["lowconf_samples"]
    assert rows and "test_idx" in rows[0]


def test_claim_is_highest_tier_and_all_four_pass(built):
    _, r = built
    got = tiers_of(r["tiers"])
    for key in ("D", "C", "B", "A"):
        assert got[key]["pass"], "%s 档实测未达标: %s" % (key, got[key])
    assert r["tiers"]["claimed"] == "优(A)"


def test_manual_items_are_declared_never_auto_passed(built):
    """人工答辩项必须明列（口头解释/企业元签认），不参与自动判定。"""
    _, r = built
    assert len(r["tiers"]["manual"]) >= 2
    assert not r["tiers"]["measured"].get("manual_done", False)


def test_claim_drops_when_accuracy_low(built):
    """反向证明 1：准确率换差值（0.79 < 0.80），承诺档位必须立刻掉下来。"""
    _, r = built
    down = _verdict_from(r, acc=0.79)
    assert down["claimed"] == "未达及格(D)"
    assert tiers_of(down)["A"]["pass"] is False


def test_claim_drops_when_augmentation_arm_missing(built):
    """反向证明 2：删掉增强对比能力（aug_done=False），A/B 档必须掉到 C。"""
    _, r = built
    down = _verdict_from(r, aug_done=False, aug_delta=None, acc_aug=None)
    got = tiers_of(down)
    assert got["D"]["pass"] and got["C"]["pass"]
    assert not got["B"]["pass"] and not got["A"]["pass"]
    assert down["claimed"] == "良好(C)"


def test_claim_drops_when_plots_not_written(built):
    """反向证明 3：png 没落盘（plots_ok=False），只该停在 B。"""
    _, r = built
    down = _verdict_from(r, plots_ok=False, loss_png_bytes=0, cm_png_bytes=0)
    got = tiers_of(down)
    assert got["B"]["pass"] and not got["A"]["pass"]
    assert down["claimed"] == "优秀(B)"


def test_verdict_is_function_of_inputs_not_constant(built):
    """同一批实测、只动一个输入 → 结论不同：档位由数据决定。"""
    _, r = built
    hi = _verdict_from(r)
    lo = _verdict_from(r, acc=0.83)
    assert hi["claimed"] == "优(A)"
    assert tiers_of(lo)["B"]["pass"] is False
    assert hi["claimed"] != lo["claimed"]
