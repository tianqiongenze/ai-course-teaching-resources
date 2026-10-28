# -*- coding: utf-8 -*-
"""工单 M2.2 四档验收断言——每档都钉在"本次运行实测值"上，能力删掉必须红。

判据与 tiers.verdict / cli --tier 同源（工单《四、验收标准》原文）：
D MSE<0.15+完成预测与可视化；C MSE≤0.12+对照基线说明 LSTM 增益；
B MSE<0.10+对比≥2 种模型并解读；A 达 B 且预测曲线有拐点分析+对窗口长度
做敏感性实验。断言只看真实产物（留出设备 MSE、png 磁盘字节、真训模型数、
实测增益差、拐点循环号、逐窗口实测 MSE），口头解读类归 manual、不自动判达标。
门槛数字一律读自 config/rules.yaml 的 tiers 段（工单原文数字，降门槛=造假）。
"""
import os

import pytest

from rul_predict import config as C
from rul_predict import pipeline, tiers

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(PROJ, "config", "rules.yaml")
OUT = os.path.join(PROJ, "output", "test_run")


@pytest.fixture(scope="module")
def built():
    """跑一次完整流水线（LSTM+对照+拐点+敏感性），模块内断言共用同一批实测值。"""
    sections, result = pipeline.build(C.load_config(CFG), out_dir=OUT)
    return sections, result


def tiers_of(v):
    return {t["tier"][-2]: t for t in v["tiers"]}


def _verdict_from(built_result, **overrides):
    """在真实实测字典上改单项能力——验证档位由输入决定而非常量。"""
    raw = C.load_config(CFG).raw.get("tiers") or {}
    gates = {"d": float(raw.get("mse_d", 0.15)),
             "c": float(raw.get("mse_c", 0.12)),
             "b": float(raw.get("mse_b", 0.10))}
    m = dict(built_result["tiers"]["measured"])
    m.update(overrides)
    return tiers.verdict(gates, m)


def _gate(key, default):
    return float((C.load_config(CFG).raw.get("tiers") or {}).get(key, default))


def test_real_bearing_npz_is_used(built):
    _, r = built
    assert not r["synthetic"], (
        "本机存在 data/bearing_rul.npz，必须走真实数据而非合成兜底")
    assert r["source"].endswith("bearing_rul.npz")
    assert r["shape"] == [5400, 20] and r["n_dev"] == 30


def test_device_level_split_has_no_leakage(built):
    """同一台设备只出现在一侧（防泄漏）：训练窗数 + 测试窗数 = 全部窗数。"""
    _, r = built
    assert r["n_train"] + r["n_test"] == r["shape"][0]
    assert len(set(r["test_devices"])) == r["n_test"] // r["windows_per_device"]


def test_D_prediction_and_visualization_are_real(built):
    """D 档：预测真跑（逐轮 loss 下降）+ 曲线图真落盘（字节 >1000）。"""
    _, r = built
    m = r["tiers"]["measured"]
    assert m["pred_ok"] and m["viz_ok"]
    losses = r["lstm_losses"]
    assert losses and len(losses) > 3 and losses[-1] < losses[0]
    art = r["artifacts"]["prediction_curve"]
    path = os.path.join(OUT, art["path"])
    assert art["exists"] and os.path.exists(path) and art["bytes"] > 1000, (
        "预测曲线未真实落盘: %s" % art)


def test_delivered_mse_meets_gate_b(built):
    _, r = built
    gate_b = _gate("mse_b", 0.10)
    assert r["mse"] < gate_b, (
        "交付模型留出实测 MSE %.6f 未达工单 B 档线 %.2f" % (r["mse"], gate_b))


def test_B_model_comparison_is_a_real_multi_run(built):
    """B 档：≥2 种模型在同一设备级切分上真训真测，指标各不相同（非复制粘贴）。"""
    _, r = built
    m = r["tiers"]["measured"]
    assert m["multi_model"] and m["n_models"] >= 2
    assert len(r["model_rows"]) == m["n_models"]
    assert len({row["mse"] for row in r["model_rows"]}) == len(r["model_rows"])
    assert all(row["mse"] > 0 for row in r["model_rows"])


def test_C_lstm_gain_over_linear_baseline_is_measured(built):
    """C 档：增益 = 线性基线实测 MSE − LSTM 实测 MSE，正负由实测说了算。"""
    _, r = built
    m = r["tiers"]["measured"]
    if m["mse_baseline"] is None:                 # torch 缺失时按 MISS 处理
        assert not m["gain_ok"] and m["miss_note"]
        pytest.skip("torch 不可用，LSTM 增益本轮无实测值")
    assert m["gain"] == pytest.approx(m["mse_baseline"] - m["mse"], abs=1e-7)
    assert m["gain_ok"] is (m["gain"] > 0)
    assert r["delivered"] == "LSTM", "工单指定主模型为 LSTM，实测可用就必须交付它"


def test_A_knee_analysis_is_measured_on_the_curve(built):
    """A 档：拐点由平滑序列实测检出，且竖线画进了落盘曲线图。"""
    _, r = built
    m = r["tiers"]["measured"]
    assert m["knee_ok"] and m["knee_idx"] is not None
    slopes = [k for k in r["knee_analysis"] if k["method"].startswith("斜率法")]
    assert slopes and slopes[0]["knee_cycle"] == m["knee_idx"]
    assert any(k["offset_cycles"] is not None for k in r["knee_analysis"])
    assert r["fleet_knee_median"] is not None


def test_A_window_sensitivity_has_real_per_window_mse(built):
    """A 档：逐窗口真重训真测（≥2 档），MSE 来自留出设备而非训练集。"""
    _, r = built
    m = r["tiers"]["measured"]
    assert m["sens_ok"] and m["n_windows"] >= r["min_windows"]
    rows = r["window_sensitivity"]
    assert [row["window"] for row in rows] == r["windows"]
    assert all(row["mse"] > 0 for row in rows)
    assert len({row["mse"] for row in rows}) == len(rows)
    art = r["artifacts"]["window_sensitivity_png"]
    assert art["bytes"] > 1000 and os.path.exists(os.path.join(OUT, art["path"]))
    csv_stat = r["artifacts"]["window_sensitivity_csv"]
    assert csv_stat["bytes"] > 50


def test_claim_is_highest_tier_and_all_four_pass(built):
    _, r = built
    got = tiers_of(r["tiers"])
    for key in ("D", "C", "B", "A"):
        assert got[key]["pass"], "%s 档实测未达标: %s" % (key, got[key])
    assert r["tiers"]["claimed"] == "优(A)"


def test_manual_items_are_declared_never_auto_passed(built):
    """人工答辩项必须明列（口头解读/企业元签认），不参与自动判定。"""
    _, r = built
    assert len(r["tiers"]["manual"]) >= 2
    assert not r["tiers"]["measured"].get("manual_done", False)


def test_report_has_four_tier_lines_echoing_measurements(built):
    _, r = built
    text = open(os.path.join(OUT, "report.txt"), encoding="utf-8").read()
    m = r["tiers"]["measured"]
    assert "验收档位判定（实测）" in text
    head = [ln for ln in text.splitlines() if ln.startswith("实测达成档位")]
    assert head and head[0].startswith("实测达成档位: %s" % r["tiers"]["claimed"])
    assert "MSE %.6f" % m["mse"] in head[0]
    assert "预测曲线 %dB" % m["curve_png_bytes"] in head[0]
    for key in ("D", "C", "B", "A"):
        row = tiers_of(r["tiers"])[key]
        # 只认档位判定行本身（缩进开头），否则首行的"实测达成档位: 优(A)"会串台
        hit = [ln for ln in text.splitlines()
               if ln.strip().startswith(row["tier"])]
        assert hit, "报告缺 %s 档判定行" % row["tier"]
        assert ("[达标]" if row["pass"] else "[未达标]") in hit[0]
        assert ("功能OK" if row["functional"] else "功能缺") in hit[0]
    assert "人工答辩项 %d 条" % len(r["tiers"]["manual"]) in text


def test_claim_drops_when_mse_above_d_floor(built):
    """反向证明 1：MSE 0.20 > 0.15 → 连 D 都不达，承诺档位必须写未达及格(D)。"""
    _, r = built
    down = _verdict_from(r, mse=0.20)
    assert down["claimed"] == "未达及格(D)"
    assert all(not t["pass"] for t in down["tiers"])


def test_claim_drops_when_mse_crosses_c_line(built):
    """反向证明 2：MSE 0.13 > 0.12 → C 数值门塌，只保留 D。"""
    _, r = built
    down = _verdict_from(r, mse=0.13)
    got = tiers_of(down)
    assert got["D"]["pass"] and not got["C"]["pass"]
    assert down["claimed"] == "及格(D)"


def test_claim_drops_when_gain_or_models_or_plots_missing(built):
    """反向证明 3：删低档能力，高档必须跟着塌（档位递进真的咬人）。"""
    _, r = built
    no_gain = _verdict_from(r, gain_ok=False, gain=None)
    assert tiers_of(no_gain)["B"]["pass"] is False
    assert no_gain["claimed"] == "及格(D)"
    one_model = _verdict_from(r, multi_model=False, n_models=1)
    assert tiers_of(one_model)["B"]["pass"] is False
    assert one_model["claimed"] == "良好(C)"
    no_viz = _verdict_from(r, viz_ok=False, curve_png_bytes=None)
    assert no_viz["claimed"] == "未达及格(D)"
    no_sens = _verdict_from(r, sens_ok=False, n_windows=1)
    assert tiers_of(no_sens)["A"]["pass"] is False
    assert no_sens["claimed"] == "优秀(B)"
    no_knee = _verdict_from(r, knee_ok=False, knee_idx=None)
    assert tiers_of(no_knee)["A"]["pass"] is False
    assert no_knee["claimed"] == "优秀(B)"


def test_verdict_is_function_of_inputs_not_constant(built):
    """同一批实测、只动一个输入 → 结论不同：档位由数据决定。"""
    _, r = built
    hi = _verdict_from(r)
    lo = _verdict_from(r, mse=0.11)
    assert hi["claimed"] == "优(A)"
    assert tiers_of(lo)["B"]["pass"] is False
    assert hi["claimed"] != lo["claimed"]


def test_gates_come_from_config_not_hardcode(built):
    """把 B 档线压到 0.0001（工单原文 0.10）→ 同一实测 MSE 立刻不达 B：
    证明 rules.yaml 的数字确实生效，代码里没有第二套门槛。"""
    _, r = built
    raw = dict(C.load_config(CFG).raw.get("tiers") or {})
    m = dict(r["tiers"]["measured"])
    assert tiers.verdict({"d": raw["mse_d"], "c": raw["mse_c"],
                          "b": 0.0001}, m)["claimed"] != "优(A)"
    assert tiers.verdict({"d": raw["mse_d"], "c": raw["mse_c"],
                          "b": raw["mse_b"]}, m)["claimed"] == "优(A)"
