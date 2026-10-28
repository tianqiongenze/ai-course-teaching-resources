# -*- coding: utf-8 -*-
"""工单 M1.2 四档验收断言——每档都钉在本模块实跑出来的实测值上，能力删掉就必须红。

判据与 src/data_quality/core.gain_tier、config/rules.yaml、output/report.txt 同源
（工单《四、验收标准》表）：
  及格(D) 提升≥5pp 且规范率≥70%；良好(C) ≥7pp 且消融记录完整；
  优秀(B) ≥10pp 且 macro-F1≥0.80（交叉验证报告另有条款，机器只验其存在）；
  优(A) 达 B 且 ≥3 种优化方法 + 有因果解释。
工单里“能说明改进思路”“策略合理”这类判不了的条款，只核对报告是否如实列为
人工答辩项——既不替它们自动判达标，也不因判不了就说“无违规”。
"""
import json
import os
import re

import pytest

from data_quality import config as C
from data_quality import core
from data_quality import io_utils
from data_quality import pipeline as P

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "config", "rules.yaml")
# 档门口径的唯一出处是工单原文：测试直接回读它，防止“代码/配置改了，工单没改”而无人知晓
ORDER = os.path.normpath(os.path.join(
    ROOT, "..", "..", "工单任务书", "M1.2工单-特征工程优化的故障诊断系统.md"))

KEYS = ("D", "C", "B", "A")
# 交付产物（随仓库提交的那份 report.txt / result.json）也要跟代码同口径，不许手写档位
SHIPPED = os.path.join(ROOT, "output")


@pytest.fixture(scope="module")
def ran(tmp_path_factory):
    """跑一次完整消融流水线，模块内所有断言共用这批实测值（含 report.txt 原文）。"""
    if io_utils.course_data("pump_fault.csv") is None:
        pytest.skip("课程数据不可用: data/pump_fault.csv 未找到")
    out = str(tmp_path_factory.mktemp("m12tier"))
    P.run(C.load_config(CFG), out)
    with open(os.path.join(out, "result.json"), encoding="utf-8") as f:
        res = json.load(f)
    with open(os.path.join(out, "report.txt"), encoding="utf-8") as f:
        text = f.read()
    return res, text


def tier_section(text):
    """取出报告里的 [工单 M1.2 验收档位] 段——“报告说的”与“代码算的”在这里对账。"""
    m = re.search(r"\[工单 M1\.2 验收档位\]\n-+\n(.*?)\n(?=\n|\Z)", text, re.S)
    assert m, "report.txt 缺少 [工单 M1.2 验收档位] 段"
    return m.group(1)


def order_clause(key):
    """回读工单《四、验收标准》表里某一档的原文。"""
    if not os.path.isdir(os.path.dirname(ORDER)):
        pytest.skip("工单任务书目录不在本机: %s" % os.path.dirname(ORDER))
    with open(ORDER, encoding="utf-8") as f:
        m = re.search(r"^\|[^|]*\((%s)\)\s*\|([^|]*)\|" % key, f.read(), re.M)
    assert m, "工单验收标准表里找不到 %s 档原文（表结构变了要先同步判据）" % key
    return m.group(2)


def gate_num(pattern, text, what):
    """从工单原文抠出一个门槛数字；抠不到就红，绝不放行为“默认值”。"""
    m = re.search(pattern, text)
    assert m, "工单原文里没有“%s”这条线: %r" % (what, text)
    return float(m.group(1))


# ---------------------------------------------------------------- 正向：实测值撑得起承诺档位
def test_measured_gain_f1_methods_reach_A(ran):
    res, _ = ran
    g, t = res["gates"], res["tier"]
    assert res["gain_pp"] >= g["b"], (
        "工单 B 档要提升≥%.1fpp，本次实测只有 %.2fpp" % (g["b"], res["gain_pp"]))
    assert t["f1_macro"] >= g["f1_b"] and res["n_methods"] >= g["n_methods_a"]
    assert t["tier"] == "A" and res["tier_combined"] == "A"


def test_result_tier_recomputed_from_measured_inputs(ran):
    """result.json 的档位必须能用本次实测值 + 配置门槛原样重算出来。"""
    res, _ = ran
    again = core.gain_tier(res["gain_pp"], res["tier"]["f1_macro"], res["n_methods"],
                           "有因果解释", res["gates"])
    assert again["tier"] == res["tier"]["tier"]
    assert {k: again[k] for k in KEYS} == {k: res["tier"][k] for k in KEYS}


def test_report_tier_lines_match_the_computed_verdict(ran):
    res, text = ran
    sec = tier_section(text)
    m = re.search(r"逐项: D=(\w+) C=(\w+) B=(\w+) A=(\w+) → 达标档位 (\S+)", sec)
    assert m, "报告缺少“逐项: D=… → 达标档位 …”行"
    assert {k: v == "True" for k, v in zip(KEYS, m.group(1, 2, 3, 4))} == \
        {k: res["tier"][k] for k in KEYS}
    assert m.group(5) == res["tier"]["tier"], "报告档位与 core.gain_tier 算出的不一致"
    line = [x for x in sec.splitlines() if x.startswith("门槛 ")][0]
    g = res["gates"]
    for pattern, value in ((r"D≥([\d.]+)pp", g["d"]), (r"C≥([\d.]+)pp", g["c"]),
                           (r"B≥([\d.]+)pp", g["b"]), (r"F1≥([\d.]+)", g["f1_b"]),
                           (r"A 需≥(\d+)种方法", g["n_methods_a"])):
        printed = re.search(pattern, line)
        assert printed, "门槛行缺 %s 这一档: %s" % (pattern, line)
        assert float(printed.group(1)) == value, "报告门槛≠配置门槛: %s" % line


def test_report_gain_number_is_measured_not_written(ran):
    """报告里那串 pp/F1/方法数必须能由消融表逐行重算出来（数字只能来自实跑）。"""
    res, text = ran
    ab = res["ablation"]
    m = re.search(r"提升（口径A，百分点）= ([\d.\-]+)pp ｜ macro-F1 = ([\d.]+)"
                  r" ｜ 优化方法数 = (\d+)", tier_section(text))
    assert m, "报告缺少实测提升行"
    assert float(m.group(1)) == round((ab[-1]["acc"] - ab[0]["acc"]) * 100, 2)
    assert float(m.group(2)) == ab[-1]["f1_macro"]
    assert int(m.group(3)) == len(ab) - 1, "方法数=消融步数减基线，不是手填的数"


def test_shipped_output_tier_matches_its_own_numbers(ran):
    """随仓库交付的 output/report.txt 不得手写档位：读它自己的数字重算，必须自洽。"""
    res, _ = ran
    jpath, rpath = (os.path.join(SHIPPED, "result.json"),
                    os.path.join(SHIPPED, "report.txt"))
    if not os.path.exists(jpath):
        pytest.skip("交付产物未生成: %s（先跑 python run.py）" % jpath)
    with open(jpath, encoding="utf-8") as f:
        ship = json.load(f)
    assert ship["gates"] == res["gates"] and ship["style_gates"] == res["style_gates"]
    assert ship["tier"]["tier"] == core.gain_tier(
        ship["gain_pp"], ship["tier"]["f1_macro"], ship["n_methods"],
        "有因果解释", ship["gates"])["tier"], "交付产物里的档位与它自己的实测数字不符"
    assert ship["tier_combined"] == core.reach_tier(
        ship["tier"], ship["style_rate"], ship["style_gates"])
    with open(rpath, encoding="utf-8") as f:
        sec = tier_section(f.read())
    assert "→ 达标档位 %s" % ship["tier"]["tier"] in sec
    assert "综合达标档位（功能门 且 规范率门）= %s" % ship["tier_combined"] in sec
    assert ship["gain_pp"] == res["gain_pp"], (
        "output/ 的提升 %.2fpp ≠ 本次实跑 %.2fpp：交付产物过期或被手改，请重跑 run.py"
        % (ship["gain_pp"], res["gain_pp"]))


def test_gates_and_style_gates_come_from_config(ran):
    """门槛数字一律取自 config/rules.yaml（改配置不改代码），报告只是复述。"""
    r = C.load_config(CFG).raw
    res, _ = ran
    assert res["gates"] == {"d": float(r["gain_d"]), "c": float(r["gain_c"]),
                            "b": float(r["gain_b"]), "f1_b": float(r["f1_b"]),
                            "n_methods_a": int(r["n_methods_a"])}
    assert res["style_gates"] == {"D": float(r["style_d"]), "C": float(r["style_c"]),
                                  "B": float(r["style_b"]), "A": float(r["style_a"])}


def test_four_gates_match_work_order_verbatim(ran):
    res, text = ran
    g, sg = res["gates"], res["style_gates"]
    d_row = order_clause("D")
    assert gate_num(r"提升≥([\d.]+)%", d_row, "D 档提升") == g["d"]
    assert gate_num(r"规范率≥([\d.]+)%", d_row, "D 档规范率") == sg["D"]
    assert gate_num(r"提升≥([\d.]+)%", order_clause("C"), "C 档提升") == g["c"]
    assert "消融记录完整" in order_clause("C")
    b_row = order_clause("B")
    assert gate_num(r"提升≥([\d.]+)%", b_row, "B 档提升") == g["b"]
    assert gate_num(r"F1≥([\d.]+)", b_row, "B 档 macro-F1") == g["f1_b"]
    assert gate_num(r"≥(\d+)种优化方法", order_clause("A"), "A 档方法数") == \
        g["n_methods_a"]
    sec = tier_section(text)
    assert "门槛 D≥%.1fpp C≥%.1fpp B≥%.1fpp且F1≥%.2f A 需≥%d种方法" % (
        g["d"], g["c"], g["b"], g["f1_b"], g["n_methods_a"]) in sec, "报告门槛与工单不同口径"


def test_d_style_gate_is_not_dropped_from_report(ran):
    """工单 D 档明文“规范率≥70%”这条线曾被漏写——留一条守卫，报告与判定都要有它。"""
    res, text = ran
    sg, sec = res["style_gates"], tier_section(text)
    assert "规范率门槛 D≥%.0f%%" % sg["D"] in sec, "报告丢了 D 档的规范率线"
    assert res["style_rate"] >= sg["D"], (
        "D 档规范率实测 %.1f%% < 门槛 %.1f%%" % (res["style_rate"], sg["D"]))
    assert res["tier_combined"] == core.reach_tier(res["tier"], res["style_rate"], sg)


def test_ablation_record_is_complete_for_C(ran):
    """工单 C 档“消融记录完整”→ 五步齐全，且每步都记了处理内容/准确率/F1。"""
    res, _ = ran
    ab = res["ablation"]
    steps = [d["step"] for d in ab]
    assert len(steps) == 5
    for kw in ("基线", "清洗", "派生", "缩放", "调参"):
        assert any(kw in s for s in steps), "消融记录缺“%s”这一步" % kw
    for d in ab:
        assert {"step", "acc", "f1_macro", "recall"} <= set(d)
        assert 0.0 <= d["acc"] <= 1.0 and 0.0 <= d["f1_macro"] <= 1.0


def test_cv_report_present_for_B(ran):
    """B 档“交叉验证报告规范”可机器核验的部分：5 折明细落进 json 且真写进了报告。"""
    res, text = ran
    cv = res["cv_stability"]
    assert len(cv["folds"]) == 5 and all(0.0 <= v <= 1.0 for v in cv["folds"])
    assert 0.0 <= cv["std"] <= 1.0 and 0.0 <= cv["mean"] <= 1.0
    assert "训练集 5 折 accuracy" in text


def test_style_engine_named_truthfully(ran):
    """没装 pycodestyle 时引擎名必须写“内置兜底”——不许把“没检查”报成“零违规”。"""
    res, _ = ran
    assert res["style_engine_kind"] in ("pycodestyle", "builtin")
    expect = "pycodestyle" if res["style_engine_kind"] == "pycodestyle" else "内置兜底"
    assert expect in res["style_engine"], "引擎名与实际使用的检查器不符"
    assert res["style_checked_files"] > 0 and res["style_checked_lines"] > 0
    assert res["style_rate"] == round(
        (1.0 - res["style_violations"] / float(res["style_checked_lines"])) * 100, 1)


def test_human_items_listed_but_not_auto_passed(ran):
    """判不了的条款必须列为人工答辩项，且不得混进自动判定的那一行替学生宣布达标。"""
    res, text = ran
    items = res["human_review_items"]
    assert len(items) == len(P.HUMAN_ITEMS) and len(items) >= 4
    sec = tier_section(text)
    assert "人工答辩项 %d 条" % len(items) in sec
    assert "教师答辩时确认" in sec and "未计入上方判定" in sec
    for it in items:
        assert it["item"] in sec, "人工答辩项未逐条写进报告: %s" % it["item"]
        assert it["item"] not in [ln for ln in sec.splitlines()
                                  if ln.startswith("逐项")][0]


# ---------------------------------------------------------------- 反向：抽掉能力就掉档
def test_gain_below_D_gate_fails(ran):
    """反向①：实测提升压到 5.0pp 之下 → D 档不达标，档位为“未达标”。"""
    res, _ = ran
    weak = core.gain_tier(res["gates"]["d"] - 0.01, res["tier"]["f1_macro"],
                          res["n_methods"], "有因果解释", res["gates"])
    assert weak["D"] is False and weak["tier"] == "未达标"
    assert res["tier"]["D"] is True, "本次实测应是达标的，反向用例不能反过来污染正例"


def test_dropping_methods_breaks_A(ran):
    """反向②：优化方法降到 <3 种 → A 不达标（B 仍达，说明只有 A 的那道门被抽走）。"""
    res, _ = ran
    g = res["gates"]
    fewer = core.gain_tier(res["gain_pp"], res["tier"]["f1_macro"], g["n_methods_a"] - 1,
                           "有因果解释", g)
    assert fewer["A"] is False and fewer["B"] is True and fewer["tier"] == "B"


def test_dropping_causal_note_breaks_A(ran):
    """反向③：因果解释被删成空串 → A 掉回 B（工单 A 档要求“有因果解释”）。"""
    res, _ = ran
    no_note = core.gain_tier(res["gain_pp"], res["tier"]["f1_macro"], res["n_methods"],
                             "", res["gates"])
    assert no_note["A"] is False and no_note["tier"] == "B"


def test_style_rate_below_gate_breaks_combined_D(ran):
    """反向④：规范率落到工单 D 档线以下 → 综合档位直接不达标（提升再高也没用）。"""
    res, _ = ran
    sg = res["style_gates"]
    assert core.reach_tier(res["tier"], sg["D"] - 0.01, sg) == "未达 D 档"
    assert core.reach_tier(res["tier"], sg["A"], sg) == "A"


def test_tier_follows_gates_not_a_hardcoded_label(ran):
    """把 B 档门槛抬到实测之上，档位必须随之掉下来——证明档位是算出来的。"""
    res, _ = ran
    raised = dict(res["gates"], b=res["gain_pp"] + 0.01)
    down = core.gain_tier(res["gain_pp"], res["tier"]["f1_macro"], res["n_methods"],
                          "有因果解释", raised)
    assert down["B"] is False and down["A"] is False and down["tier"] == "C"


# ---------------------------------------------------------------- 边界：工单写“≥”，取等即达标
def test_exact_gate_values_count_as_pass(ran):
    """边界：工单写的是“≥”，取等即达标——门槛口径不能被写成“>”。"""
    res, _ = ran
    g, sg = res["gates"], res["style_gates"]
    flags = {"D": True, "C": False, "B": False, "A": False}
    assert core.gain_tier(g["d"], 0.9, 4, "x", g)["tier"] == "D"
    assert core.gain_tier(g["d"] - 0.01, 0.9, 4, "x", g)["tier"] == "未达标"
    assert core.gain_tier(g["c"], 0.9, 4, "x", g)["tier"] == "C"
    # 恰好 10.0pp + F1 恰好 0.80 + 方法数不足 3 → 停在 B（A 的门槛另算）
    assert core.gain_tier(g["b"], g["f1_b"], g["n_methods_a"] - 1, "x", g)["tier"] == "B"
    assert core.gain_tier(g["b"], g["f1_b"] - 0.001, 4, "x", g)["tier"] == "C"
    assert core.gain_tier(g["b"], g["f1_b"], g["n_methods_a"], "因果", g)["tier"] == "A"
    assert core.gain_tier(g["b"], g["f1_b"], g["n_methods_a"] - 1, "因果", g)["tier"] == "B"
    assert core.reach_tier(flags, sg["D"], sg) == "D"
    assert core.reach_tier(flags, sg["D"] - 0.01, sg) == "未达 D 档"
