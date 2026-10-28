# -*- coding: utf-8 -*-
"""工单 M4.2 四档验收断言——每档都钉在"实测值"上，能力删掉就必须红。

档位判据与 tiers.verdict / cli --tier 同源（工单验收标准表）：
D 正确回答≥5（真实题库实测命中）；C ≥7+Prompt 三版对比有实测结论；
B ≥10+RAG 链路完整+对比纯 LLM 实测提升；A 达B且 Agent 两步推理/多轮对话/
容错(重试/降级)注入实测通过。fixture 用本次 pytest 进程真实跑完整链路，
断言只看真实产物文件与真实计数；本机无 LLM 服务 → 一切判定均在确定性兜底
路径上成立（报告已如实标注兜底口径）。
"""
import os

import pytest

from ops_rag import config as C
from ops_rag import core, io_utils, pipeline, tiers

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(PROJ, "config", "rules.yaml")
OUT = os.path.join(PROJ, "output", "test_run")


@pytest.fixture(scope="module")
def built():
    """跑一次完整问答链路，模块内所有断言共用同一批实测值。"""
    return pipeline.build(C.load_config(CFG), out_dir=OUT)


def tiers_of(v):
    """tiers.verdict 的返回 → {档位字母: 判定}（实测与手工构造同一口径）。"""
    return {t["tier"][-2]: t for t in v["tiers"]}


def _real_verdict(r, **override):
    """在实测值上只改动一个能力开关——档位必须随之下降（反向证明）。"""
    m = r["tiers"]["measured"]
    kw = {"gates": r["tiers"]["gates"], "rate": r["style_rate"],
          "n_correct": m["n_correct"], "n_refuse_ok": m["n_refuse_ok"],
          "versions_run": m["versions_run"], "prompt_gap": m["prompt_gap"],
          "chain_ok": m["chain_ok"], "gain": m["gain"],
          "agent_ok": m["agent_ok"], "multi_turn_ok": m["multi_turn_ok"],
          "fault_ok": m["fault_ok"]}
    kw.update(override)
    return tiers.verdict(**kw)


def test_gate_numbers_come_from_rules_yaml():
    """门槛数字外置在 rules.yaml 的 tiers: 段，代码读出即判定口径。"""
    g = tiers.gates_from(C.load_config(CFG))
    assert g["D"]["correct_min"] == 5 and g["C"]["correct_min"] == 7
    assert g["B"]["correct_min"] == 10 and g["C"]["prompt_versions_min"] == 3
    assert g["B"]["gain_min"] == 1 and g["A"]["tools_min"] == 2


def test_kb_loaded_from_real_course_data(built):
    """知识库出处实测：本机有 data/knowledge_base.json 就必须真读到 13 条。"""
    _, r = built
    assert r["kb_size"] == 13, "课程知识库应实测读满 13 条，实际 %d（%s）" % (
        r["kb_size"], r["kb_source"])


def test_D_correct_answers_measured_on_real_bank(built):
    _, r = built
    assert r["n_correct"] >= 5, "真实题库实测正确回答数不足 5"
    assert all(x["expect"] == "(库外)" or x["reply"] for x in r["qa_rows"])


def test_D_out_of_bank_refused(built):
    """幻觉红线：库外问题实测必须拒答（宁说无据，不硬编）。"""
    _, r = built
    assert r["n_refuse_ok"] == 2
    for x in r["qa_rows"]:
        if x["expect"] == "(库外)":
            assert x["grounded"] is False, "库外问题被硬编回答: %s" % x["question"]


def test_C_prompt_three_versions_actually_ran(built):
    _, r = built
    assert len(r["prompt_scores"]) == 3
    assert r["prompt_gap"] > 0, "三版回答必须测出分差（真实文本数出来的）"
    assert r["prompt_best"] == "example"


def test_B_chain_complete_and_gain_measured(built):
    _, r = built
    assert r["n_correct"] >= 10 and r["chain_ok"]
    assert r["gain"] == r["n_correct"] - r["pure_llm_correct"] > 0, \
        "提升必须是两次真实运行（RAG/无上下文）的命中差"


def test_A_agent_two_step_actually_called_tools(built):
    _, r = built
    ag = r["agent"]
    assert set(ag["tools_called"]) >= {"QueryTool", "CalcTool"}
    assert ag["calc"]["margin"] == pytest.approx(7.5 - 7.1, abs=1e-6)
    assert "[R" in ag["aggregate"] and "0.40" in ag["aggregate"]


def test_A_multiturn_context_actually_used(built):
    _, r = built
    mt = r["dialog"]
    assert mt["focus"] == "气动阀动作迟缓"  # 由轮1 实测引用文本提取，非硬编码
    assert mt["raw_grounded"] is False, "回指不解析时应测不出命中（对照）"
    assert mt["resolved_correct"] is True
    assert r["multi_turn_ok"]


def test_A_fault_injection_recorded_real_exception(built):
    """容错是"真的把服务打挂"测出来的：异常类名与尝试次数都来自真实请求。"""
    _, r = built
    f = r["fault"]
    assert f["ok"] is False and f["attempts"] >= 2
    assert f["exc"] in ("ConnectionError", "ChunkedEncodingError") or \
        "Error" in f["exc"], "应记录真实异常类名，实际: %s" % f["exc"]
    assert r["fault_ok"]


def test_llm_path_reported_as_fallback(built):
    """本机无外部 LLM：报告必须写明走的是确定性兜底路径。"""
    _, r = built
    assert "降级确定性模板回答器" in r["llm_path"]


def test_real_artifacts_exist_and_are_not_empty(built):
    """产物只认真实文件：json/csv/png 存在且字节数>1000。"""
    _, r = built
    for name, path in r["artifacts"].items():
        assert path and os.path.exists(path), "%s 缺失" % name
        assert os.path.getsize(path) > 1000, "%s 体量不足: %s" % (name, path)
    data = io_utils.read_json(r["artifacts"]["result_json"])
    assert "tiers" in data


def test_report_contains_tier_section(built):
    """报告必须有 [验收档位判定（实测）] 段与人工答辩清单。"""
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


def test_D_fails_when_answer_count_below_five(built):
    """反向证明：实测正确回答数掉到 4（<5），D 档必须红、claimed 直接未达标。"""
    _, r = built
    v = _real_verdict(r, n_correct=4)
    got = tiers_of(v)
    assert got["D"]["pass"] is False
    assert v["claimed"] == "未达 D 档"


def test_claim_drops_when_answers_below_seven(built):
    _, r = built
    got = tiers_of(_real_verdict(r, n_correct=6))
    assert got["D"]["pass"] and got["C"]["pass"] is False


def test_C_fails_when_prompt_comparison_gone(built):
    """Prompt 对比没跑（0 版/0 分差）→ C 必须掉到 D。"""
    _, r = built
    got = tiers_of(_real_verdict(r, versions_run=0, prompt_gap=0.0))
    assert got["C"]["pass"] is False and got["D"]["pass"]


def test_B_fails_without_gain_over_pure_llm(built):
    _, r = built
    got = tiers_of(_real_verdict(r, gain=0))
    assert got["B"]["pass"] is False and got["C"]["pass"]


def test_A_fails_when_multiturn_or_fault_or_agent_missing(built):
    """去掉多轮对话 / 容错注入 / Agent 任一能力，A 档都必须掉到 B。"""
    _, r = built
    for flag in ("multi_turn_ok", "fault_ok", "agent_ok"):
        got = tiers_of(_real_verdict(r, **{flag: False}))
        assert got["A"]["pass"] is False, "%s 缺失时 A 仍判达标" % flag
        assert got["B"]["pass"], "%s 缺失应只影响 A 档" % flag


def test_resolve_ref_is_pure(built):
    """回指解析纯函数行为：有焦点必替换、无焦点原样返回（不虚构上下文）。"""
    assert core.resolve_ref("它的上限呢", "轴承温度") == "轴承温度上限呢"
    assert core.resolve_ref("它的上限呢", "") == "它的上限呢"
