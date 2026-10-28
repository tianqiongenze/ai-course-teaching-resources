# -*- coding: utf-8 -*-
"""工单 M3.1 四档验收断言——每档都钉在"实测值"上，能力抽掉就必须红。

档位判据与 tiers.verdict / cli --tier / report.txt 同源：
D 正确检出并标注+误差<10%；C 误差<8%+双阈值策略对比完整；
B 误差<5%+标注图要素齐全（框+文字+图例+字节数）；A 达B且多缺陷件
全检出+误检率=0+成因分析行。反向断言全部用 verdict 手工构造同一
口径——误差调大、策略对比缺失、误检出现时档位必须下降。
"""
import copy
import os

import pytest

from surface_vision import config as C
from surface_vision import pipeline, tiers

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(PROJ, "config", "rules.yaml")
OUT = os.path.join(PROJ, "output", "test_run")


@pytest.fixture(scope="module")
def built():
    """实跑一次完整测量链路，模块内所有断言共用同一批实测值。"""
    sections, result = pipeline.build(C.load_config(CFG), out_dir=OUT)
    return sections, result


def tiers_of(v):
    """verdict 返回 → {档位字母: 判定}（实测与手工构造走同一口径）。"""
    return {t["tier"][-2]: t for t in v["tiers"]}


def test_D_all_parts_detected_and_annotated(built):
    _, r = built
    m = r["measured"]
    assert m["parts_detected"] == m["parts_total"] > 0, (
        "工单 D 档要求每件真实零件都被检出")
    assert m["err_mean"] < r["tiers"]["gates"]["d_err_pct"], "D 档误差线"


def test_C_two_threshold_strategies_really_compared(built):
    """两策略都必须在全部件上真跑出误差——决策矩阵不许留空行。

    注意：global(T=100) 在细划痕上实测漏检是本工单的教学点（思考题：
    照明不均时全局阈值会怎样），"对比记录完整"判的是两策略全量真跑，
    主策略(otsu)全检出。
    """
    _, r = built
    for s in ("global", "otsu"):
        st = r["strategies"][s]
        assert st["detected"] >= 1, "%s 策略没真跑出检出" % s
        assert st["err_max"] >= 0.0, "%s 策略没有实测误差记录" % s
    assert r["measured"]["cmp_ok"] and r["measured"]["err_mean"] < 8.0
    assert r["measured"]["parts_detected"] == r["measured"]["parts_total"]


def test_B_annotated_pngs_are_real_files(built):
    """B 档：标注图真落盘——文件存在、字节>1000、框/文字/图例要素实测计数。"""
    _, r = built
    paths = [p["path"] for p in r["annotated_pngs"]]
    assert len(paths) >= 3
    for p in paths:
        assert os.path.exists(p), "结果图必须真实落盘: %s" % p
        assert os.path.getsize(p) > 1000, "%s 小于 1000 字节，不是有效图" % p
    png_meta = [p for p in r["annotated_pngs"]]
    assert all(p["boxes"] >= 1 and p["labels"] >= 1 and p["legend"]
               for p in png_meta), "框/文字/图要素缺一不可"


def test_A_multi_defect_all_found_zero_fp(built):
    _, r = built
    m = r["measured"]
    assert m["multi_detected"] == m["multi_total"] >= 2, "多缺陷件必须全部检出"
    assert m["fp_count"] == 0, "误检率必须实测为 0"
    assert m["noise_filtered"] >= 1, "4×4 假缺陷点必须真的被面积门槛剔除"
    assert r["multi"]["cause_lines"], "成因分析行（由实测数生成）必须存在"


def test_all_four_tiers_pass_and_claim_is_highest(built):
    _, r = built
    got = tiers_of(r["tiers"])
    for key in ("D", "C", "B", "A"):
        assert got[key]["pass"], "%s 档实测未达标: %s" % (key, got[key])
    assert r["tiers"]["claimed"] == "优(A)"
    assert "验收档位判定（实测）" in open(
        os.path.join(OUT, "report.txt"), encoding="utf-8").read()


def test_err_blowup_drops_every_tier(built):
    """反向证明①：把实测误差调到 12%（>10），连 D 档都不许过。"""
    _, r = built
    m = copy.deepcopy(r["measured"])
    m["err_mean"] = 12.0
    down = tiers.verdict(r["tiers"]["gates"], m)
    assert down["claimed"] == "未达 D 档"


def test_cmp_missing_drops_to_D(built):
    """反向证明②：两种阈值策略对比记录缺失时，C 档及其以上必须红。"""
    _, r = built
    m = copy.deepcopy(r["measured"])
    m["cmp_ok"] = False
    down = tiers.verdict(r["tiers"]["gates"], m)
    got = tiers_of(down)
    assert got["D"]["pass"] and not got["C"]["pass"]
    assert down["claimed"] == "及格(D)"


def test_one_false_positive_drops_to_B(built):
    """反向证明③：出现 1 个误检框，A 档必须掉到 B。"""
    _, r = built
    m = copy.deepcopy(r["measured"])
    m["fp_count"] = 1
    down = tiers.verdict(r["tiers"]["gates"], m)
    got = tiers_of(down)
    assert got["B"]["pass"] and not got["A"]["pass"]
    assert down["claimed"] == "优秀(B)"


def test_missing_pngs_drops_B_to_C(built):
    """反向证明④：合格标注图不足 3 张（比如落盘失败），B 档必须红。"""
    _, r = built
    m = copy.deepcopy(r["measured"])
    m["png_valid"] = 2
    down = tiers.verdict(r["tiers"]["gates"], m)
    got = tiers_of(down)
    assert got["C"]["pass"] and not got["B"]["pass"]
    assert down["claimed"] == "良好(C)"


def test_manual_items_never_auto_pass(built):
    """无法机器判定的条目只进人工答辩清单，报告里必须逐条列出。"""
    _, r = built
    lines = tiers.render_manual(r["tiers"])
    assert lines[0].startswith("人工答辩项 %d 条" % len(r["tiers"]["manual"]))
    assert len(r["tiers"]["manual"]) >= 3
