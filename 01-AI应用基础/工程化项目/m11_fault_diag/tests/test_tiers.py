# -*- coding: utf-8 -*-
"""工单 M1.1《泵类设备故障诊断系统》验收档位逐档断言（D/C/B/A）。

口径说明：
  * 规范率门槛的唯一来源是 cli.TIERS（与工单表格同序），测试不另抄一份数字，
    避免"工单改了、测试没改"的脱节；数值由 stylecheck 现场实测。
  * 功能门槛断言的是流水线**实测产物**（result.json / report.txt 里的真数字），
    删掉对应能力（少训一个模型、去掉决策矩阵、指标算错）本文件必须变红。
"""
import json
import os

import pytest

from fault_diag import cli
from fault_diag import config as C
from fault_diag import core, io_utils
from fault_diag import pipeline as P
from fault_diag import stylecheck

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "config", "rules.yaml")
REPORT = os.path.join(ROOT, "output", "report.txt")


@pytest.fixture(scope="module")
def ran(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("m11tiers"))
    sections = P.run(C.load_config(CFG), out)
    res = json.load(open(os.path.join(out, "result.json"), encoding="utf-8"))
    txt = open(os.path.join(out, "report.txt"), encoding="utf-8").read()
    return out, res, txt, sections


@pytest.fixture(scope="module")
def real_data(ran):
    """合成兜底数据不参与工单档位判定（数据缺失已在报告里如实标注）。"""
    _, res, _, _ = ran
    if not res["source"].startswith("真实数据"):
        pytest.skip("课程数据 %s 不可用，档位判定不参与" % io_utils.course_data("pump_fault.csv"))
    return res


# ── 四档共同的规范率门槛（工单每档都含"代码规范率≥N%"）──
@pytest.mark.parametrize("tier,need,gate", cli.TIERS)
def test_style_rate_meets_each_tier(tier, need, gate):
    stats = stylecheck.scan_project(ROOT)
    assert stats["rate"] >= gate, \
        "%s 要求规范率≥%s%%，实测 %.1f%%（引擎 %s）" % (
            tier, gate, stats["rate"], stats["engine"])


def test_style_checker_is_real_not_stub():
    """体检必须真的数到文件与行，且能定位 file:line（防"假合规"）。"""
    stats = stylecheck.scan_project(ROOT)
    assert stats["files"] >= 8 and stats["lines"] >= 300
    assert stats["engine_kind"] in ("pycodestyle", "builtin")
    # 违规行必须可定位；无违规时 top 为空也算实测通过
    assert len(stats["top"]) == min(stats["violations"], 10)
    assert 0.0 <= stats["rate"] <= 100.0


def test_style_engine_name_declares_fallback_when_lib_missing():
    """"环境也是选型维度"：没装 pycodestyle 时引擎名必须写明内置兜底。"""
    stats = stylecheck.scan_project(ROOT)
    if stylecheck.pycodestyle_engine() is None:
        assert "内置兜底" in stats["engine"]
    else:
        assert "pycodestyle" in stats["engine"]


# ── 及格(D)：准确率≥0.75 且四项指标齐备（可口述）──
def test_d_tier_acc_gate_and_four_metrics(real_data):
    acc = real_data["metrics"]["acc"]
    assert acc >= real_data["gates"]["d"] >= 0.75, "D 档需准确率≥0.75，实测 %.4f" % acc
    for name, m in real_data["models"].items():
        for k in ("acc", "precision_macro", "recall_macro", "f1_macro"):
            assert k in m, "%s 缺指标 %s" % (name, k)


# ── 良好(C)：准确率≥0.80 且指标解读可复核（各类 P/R/F1 明细 + 宏平均自洽）──
def test_c_tier_acc_gate_and_per_class_detail(real_data):
    acc = real_data["metrics"]["acc"]
    assert acc >= real_data["gates"]["c"] >= 0.80, "C 档需≥0.80，实测 %.4f" % acc
    labels = real_data["labels"]
    for name, m in real_data["models"].items():
        assert sorted(m["per_class"]) == sorted(labels), "%s 各类明细缺类" % name
        for k in ("precision", "recall", "f1"):
            macro = round(sum(v[k] for v in m["per_class"].values()) / len(labels), 4)
            assert abs(macro - m[k + "_macro"]) <= 0.0015, \
                "%s 的 %s 宏平均 %.4f 与各类明细推算 %.4f 不符" % (name, k, m[k + "_macro"], macro)


# ── 优秀(B)：准确率≥0.85 + 三模型对比表完整 + 决策矩阵填写规范 ──
def test_b_tier_three_models_and_decision_matrix(real_data):
    acc = real_data["metrics"]["acc"]
    assert acc >= real_data["gates"]["b"] >= 0.85, "B 档需≥0.85，实测 %.4f" % acc
    assert len(real_data["models"]) == 3, "工单要求 LR/DT/RF 三模型，实得 %d" % len(real_data["models"])
    rows = real_data["decision_matrix"]
    assert len(rows) == 3
    assert {r["决策"] for r in rows} == {"交付", "备选", "不交付"}
    for r in rows:
        for col in ("精度预期", "训练速度", "可解释性"):
            assert 0 <= r[col] <= 5, "%s 打分 %s 越界" % (r["model"], col)
    # 综合分必须由权重×打分复算得出（防"拍脑袋填表"）
    w = {k: float(C.load_config(CFG).raw[x]) for k, x in
         (("acc", "w_acc"), ("speed", "w_speed"), ("interp", "w_interp"))}
    for r in rows:
        expect = round(r["精度预期"] * w["acc"] + r["训练速度"] * w["speed"]
                       + r["可解释性"] * w["interp"], 2)
        assert abs(r["综合"] - expect) < 0.01, "%s 综合分 %.2f ≠ 权重×打分 %.2f" % (
            r["model"], r["综合"], expect)


# ── 优(A)：达 B 且引用指标差异解释业务影响 + 代码含函数化封装 ──
def test_a_tier_business_interpretation(real_data, ran):
    _, _, txt, _ = ran
    assert real_data["tier"] in ("B", "A"), "A 档要求先达 B，实测档位 %s" % real_data["tier"]
    assert "宏平均" in txt and "漏报" in txt, "A 档要求引用指标差异解释业务影响"
    assert "误报" in txt, "A 档要求说明漏报/误报代价差异"
    acc = real_data["metrics"]["acc"]
    assert ("%.4f" % acc) in txt, "报告里的准确率必须是实测值"


def test_a_tier_function_encapsulation():
    """A 档"代码含函数化封装"：core 必须是可单测的纯函数集合，而非一坨脚本。"""
    fns = [n for n in dir(core) if callable(getattr(core, n)) and not n.startswith("_")]
    assert len(fns) >= 8, "core 公开函数应≥8 个（函数化封装），实得 %d" % len(fns)
    for n in ("load_labeled_csv", "stratified_split", "metrics_from_confusion",
              "evaluate", "decision_matrix", "tier_of"):
        assert n in fns, "core 缺少函数 %s" % n


# ── 交付证据：已提交的 output/report.txt 必须含实测规范率与档位结论 ──
def test_committed_report_contains_measured_style_rate():
    assert os.path.exists(REPORT), "先跑 python run.py 生成 output/report.txt"
    txt = open(REPORT, encoding="utf-8").read()
    assert "编码规范率（PEP 8 实测）" in txt
    stats = stylecheck.scan_project(ROOT)
    assert ("规范率实测: %.1f%%" % stats["rate"]) in txt


def test_committed_result_records_style_stats():
    res = json.load(open(os.path.join(ROOT, "output", "result.json"), encoding="utf-8"))
    stats = stylecheck.scan_project(ROOT)
    assert res["style_rate"] == pytest.approx(stats["rate"])
    assert res["style_violations"] == stats["violations"]
    assert res["style_engine"] == stats["engine"]


def test_cli_tier_prints_measured_rate(capsys):
    assert cli.main(["--tier"]) == 0
    out = capsys.readouterr().out
    stats = stylecheck.scan_project(ROOT)
    assert "实测规范率 %.1f%%" % stats["rate"] in out
    for name, _need, gate in cli.TIERS:
        assert name in out and ("≥%2.0f%%" % gate) in out
    assert ("实测达标" in out) or ("规范率不足" in out)


def test_cli_check_reports_environment(capsys):
    assert cli.main(["--check"]) == 0
    out = capsys.readouterr().out
    assert "环境自检" in out and ("  OK   " in out or "  MISS " in out)
