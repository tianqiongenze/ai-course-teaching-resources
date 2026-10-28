# -*- coding: utf-8 -*-
"""工单 M3.2 四档验收测试：档位必须由本次真实测量算出来。

口径：
  * 判定唯一出处 = src/yolo_dual/tiers.verdict + config/rules.yaml tiers: 段；
    工单未逐档设规范率门槛 → 规范率只作展示，本文件断言它不进档位门。
  * 正向用例跑真 pipeline（真实数据集、三档真计时、双路线阈值实验），
    并复核报告里的每个数字可复算（FPS=3 轮中位数、提速=两次实测相除）。
  * 负向用例把实测字典按"能力被删"篡改（提速不足/稳定丢失/阈值缺档/
    可视化缺失/优化未落地），档位必须掉下来——判绿只能靠真本事。
"""
import os
from statistics import median

import pytest

from yolo_dual import cli
from yolo_dual import config as C
from yolo_dual import core
from yolo_dual import io_utils
from yolo_dual import pipeline as P
from yolo_dual import stylecheck
from yolo_dual import tiers

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "config", "rules.yaml")


def tiers_of(v):
    return {t["tier"][-2]: t for t in v["tiers"]}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """模块级夹具：真跑一遍完整实测链路（报告/图/json 全部落盘）。"""
    out = str(tmp_path_factory.mktemp("m32tiers"))
    sections, result = P.build(C.load_config(CFG), out_dir=out)
    txt = open(os.path.join(out, "report.txt"), encoding="utf-8").read()
    return out, sections, result, txt


# ── 正向：四档全部由实测判达 ──────────────────────────────────────
def test_claim_is_A_by_real_measurement(built):
    _, _, result, _ = built
    v = result["tiers"]
    assert v["claimed"] == "优(A)", "实测字典不达标就不许声称 A"
    assert all(t["pass"] for t in v["tiers"])


def test_D_threshold_experiment_ran_four_levels(built):
    """阈值实验四档全部真跑：每档有检出/命中/误检实测数，推理调用≥张数。"""
    _, _, result, _ = built
    g = result["tiers"]["gates"]
    ladder = result["threshold_ladder"]
    assert len(ladder) >= int(g["d_conf_levels"])
    for lev in ladder:
        assert lev["det"] >= 0 and lev["tp"] >= 0 and lev["fp"] >= 0
    m = result["measured"]
    assert m["infer_calls"] >= m["imgs_total"] > 0


def test_D_visualization_pngs_are_real_files(built):
    out, _, result, _ = built
    pngs = result["annotated_pngs"]
    assert len(pngs) >= result["tiers"]["measured"]["vis_valid"] >= 2
    for p in pngs[:2]:
        assert os.path.exists(p["path"])
        assert os.path.getsize(p["path"]) > 1000, "落盘图必须是真的（>1KB）"
        assert p["boxes"] >= 1 and p["labels"] >= 1 and p["legend"]
    assert os.path.isdir(os.path.join(out, "visualized"))


def test_C_three_sizes_really_timed(built):
    """FPS 必须是多轮真计时的中位数——写一个孤零零的数就复算不上。"""
    _, _, result, _ = built
    sizes = result["sizes"]
    assert len(sizes) == result["tiers"]["gates"]["c_imgsz_levels"]
    for s in sizes:
        assert len(s["fps_reps"]) >= 3
        assert s["fps"] == pytest.approx(median(s["fps_reps"]), abs=0.01)
        assert s["fps"] > 0 and s["det"] > 0


def test_C_chosen_config_recomputable_from_measurements(built):
    """选定配置不许拍脑袋：用实测表按同一规则复算，必须选出一样的档位。"""
    _, _, result, _ = built
    g = result["tiers"]["gates"]
    fps = {s["imgsz"]: s["fps"] for s in result["sizes"]}
    tp = {s["imgsz"]: s["tp"] for s in result["sizes"]}
    base = max(fps)
    cands = [s for s in fps if fps[s] >= float(g["fps_min"])
             and tp[s] >= tp[base]]
    assert result["chosen"] == max(cands, key=lambda s: fps[s])
    assert result["basis_ok"] is True


def test_B_speedup_is_two_real_timings_divided(built):
    _, _, result, _ = built
    fps = {s["imgsz"]: s["fps"] for s in result["sizes"]}
    base = max(fps)
    expect = round((fps[result["chosen"]] / fps[base] - 1) * 100, 1)
    assert result["speedup_pct"] == pytest.approx(expect, abs=0.11)
    assert result["speedup_pct"] >= float(
        result["tiers"]["gates"]["b_speedup_pct"])


def test_B_stability_vectors_identical(built):
    _, _, result, _ = built
    vecs = result["stability_vectors"]
    assert len(vecs) >= 3 and result["stable_ok"]
    assert all(v == vecs[0] for v in vecs)
    assert len(vecs[0]) == result["measured"]["imgs_total"]


def test_A_optimizations_implemented_and_quantified(built):
    """输入裁剪与多线程都要真实现真计时；增益取实测最大项并如实记录代价。"""
    _, _, result, txt = built
    opts = result["opts"]
    assert any("裁剪" in k for k in opts) and any("线程" in k for k in opts)
    gains = [o["gain_pct"] for o in opts.values()]
    assert result["measured"]["opt_gain_pct"] == max(gains)
    assert result["measured"]["opt_gain_pct"] >= float(
        result["tiers"]["gates"]["a_opt_gain_pct"])
    assert "精度代价" in txt, "裁剪召回实测损失必须如实写进报告"


def test_report_contains_tier_section_and_caliber(built):
    _, _, _, txt = built
    assert "[验收档位判定（实测）]" in txt
    assert "实测达成档位: 优(A)" in txt
    assert "兜底口径" in txt, "无 ultralytics 的兜底路线必须标明口径"
    for tier in ("及格(D)", "良好(C)", "优秀(B)", "优(A)"):
        hits = [ln for ln in txt.splitlines() if tier in ln and "门槛" in ln]
        assert hits and "[达标]" in hits[0], "%s 档位行必须跟着实测走" % tier


def test_style_rate_is_display_only(built):
    """工单没写规范率档位门槛 → 不许自创：gates 里不得出现规范率键。"""
    _, _, result, txt = built
    assert not any("style" in k or "rate" in k for k in
                   result["tiers"]["gates"])
    assert "规范率仅作实测展示" in txt


def test_onnx_route_reported_truthfully(built):
    _, _, result, txt = built
    if result["onnx_ladder"]:
        assert len(result["onnx_ladder"]) == len(result["threshold_ladder"])
        det_sum = sum(o["det"] for o in result["onnx_ladder"])
        if det_sum == 0:
            assert "领域不匹配" in txt, "零检出现象要如实给出动机说明"
    else:
        assert "MISS" in result["onnx_status"]


def test_dual_route_and_real_photo_honesty(built):
    _, _, result, txt = built
    assert "推理路线" in txt
    assert result["ultra_status"].split("（")[0] in ("OK", "MISS")
    assert result["ultra_status"] in txt, "ultralytics 可用性必须如实写进报告"
    assert "实物照" in txt and result["photo_status"] in txt


# ── 负向：能力被删/数字被夸大 → 档位必须掉 ────────────────────────
# 用"实测值全通过的基准 m"做单点篡改：只考判定逻辑，不被本机计时噪声牵连。
def base_m(result):
    g = result["tiers"]["gates"]
    m = dict(result["measured"])
    m.update(conf_levels=int(g["d_conf_levels"]), vis_valid=int(g["d_min_vis_png"]),
             fps_levels=int(g["c_imgsz_levels"]),
             fps_values={160: 600.0, 320: 180.0, 640: 45.0},
             basis_ok=True, speedup_pct=300.0, stable_ok=True,
             opt_impl=True, opt_gain_pct=100.0)
    return m


def test_base_m_really_claims_A(built):
    """基准自检：全能力实测在场时判定必须是 A——负向用例的地基。"""
    _, _, result, _ = built
    assert tiers.verdict(result["tiers"]["gates"],
                         base_m(result))["claimed"] == "优(A)"


def test_speedup_below_gate_drops_to_C(built):
    """提速掉到工单 50% 线以下 → B 必须红（累计链跟着 A 一起红）。"""
    _, _, result, _ = built
    m = dict(base_m(result), speedup_pct=30.0)
    v = tiers.verdict(result["tiers"]["gates"], m)
    assert v["claimed"] == "良好(C)"
    assert not tiers_of(v)["B"]["pass"] and not tiers_of(v)["A"]["pass"]


def test_stability_lost_drops_to_C(built):
    _, _, result, _ = built
    m = dict(base_m(result), stable_ok=False)
    assert tiers.verdict(result["tiers"]["gates"], m)["claimed"] == "良好(C)"


def test_threshold_levels_missing_drops_below_D(built):
    """阈值实验只跑 2 档（缺对比记录）→ D 直接不达标。"""
    _, _, result, _ = built
    m = dict(base_m(result), conf_levels=2)
    v = tiers.verdict(result["tiers"]["gates"], m)
    assert v["claimed"] == "未达 D 档"


def test_visualization_zero_drops_below_D(built):
    _, _, result, _ = built
    m = dict(base_m(result), vis_valid=0)
    assert tiers.verdict(result["tiers"]["gates"], m)["claimed"] == "未达 D 档"


def test_optimization_removed_drops_to_B(built):
    """A 档优化没落地（只实现不量化也不行）→ 必须掉回 B。"""
    _, _, result, _ = built
    m = dict(base_m(result), opt_impl=False, opt_gain_pct=0.0)
    assert tiers.verdict(result["tiers"]["gates"], m)["claimed"] == "优秀(B)"


def test_imgsz_ladder_incomplete_drops_to_D(built):
    """三档只实测两档 → C 判不足，累计链停在 D。"""
    _, _, result, _ = built
    m = dict(base_m(result), fps_levels=2,
             fps_values={160: 600.0, 320: 180.0})
    assert tiers.verdict(result["tiers"]["gates"], m)["claimed"] == "及格(D)"


def test_manual_items_never_auto_pass(built):
    """人工答辩项绝不掺进档位判定；claimed 不依赖 manual。"""
    _, _, result, _ = built
    v = result["tiers"]
    assert v["manual"] == tiers.MANUAL and len(tiers.MANUAL) >= 3
    lines = tiers.render_manual(v)
    assert lines[0] == "人工答辩项 %d 条，教师答辩时确认:" % len(tiers.MANUAL)
    vb = tiers.verdict(result["tiers"]["gates"], base_m(result))
    assert vb["manual"] == tiers.MANUAL
    assert vb["claimed"] == "优(A)"      # manual 在场也不给任何档加/减分


# ── 兜底路径本身可用（环境缺库时也走确定性合成数据）──────────────
def test_synth_fallback_dataset_is_deterministic():
    a = core.synth_dataset(4, seed=7)
    b = core.synth_dataset(4, seed=7)
    assert [d["name"] for d in a] == [d["name"] for d in b]
    dets = core.infer(a[0]["img"], imgsz=320, dev=12.0, min_area=15)
    tp, fp = core.match_stats(a[0]["gts"], dets, 0.3)
    assert tp == 1 and fp == 0, "合成兜底件必须能被兜底口径真实检出"


def test_onnx_session_degrades_without_weird_exception():
    assert core.onnx_session("/no/such/model.onnx") is None


def test_cli_check_reports_environment(capsys):
    assert cli.main(["--check"]) == 0
    out = capsys.readouterr().out
    assert "环境自检" in out and ("  OK   " in out or "  MISS " in out)


def test_style_engine_real_and_clean():
    """新增代码自身要过 PEP 8（工单通用红线），规范率引擎不许是 stub。"""
    stats = stylecheck.scan_project(ROOT)
    assert stats["engine_kind"] in ("pycodestyle", "builtin")
    assert stats["violations"] == 0, \
        "违规明细: %s" % stats["top"]
    assert stats["files"] >= 9 and stats["lines"] >= 400


def test_course_data_resolution_is_used_for_weights():
    """权重路径走 io_utils.course_data（环境也是选型维度：离线就如实显示缺失）。"""
    path = io_utils.course_data(*cli.WEIGHTS)
    assert path is None or os.path.exists(path)
