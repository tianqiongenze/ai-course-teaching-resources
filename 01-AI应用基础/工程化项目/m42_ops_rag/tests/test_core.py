# -*- coding: utf-8 -*-

from ops_rag import core

KB = core.load_kb([
    {"category": "规范", "text": "泵类设备振动速度有效值超过4.5mm/s应列入重点监测"},
    {"category": "排查", "text": "电机电流偏高而转速正常：排查机械过载与轴承磨损"},
])


def test_bigrams_contains_full_segment():
    b = core.bigrams("振动速度")
    assert "振动" in b and "速度" in b and "振动速度" in b


def test_load_kb_assigns_citation_ids():
    assert [k["id"] for k in KB] == ["R1", "R2"]


def test_retrieve_hits_relevant_entry():
    hits = core.retrieve("泵振动超标标准", KB, topk=2)
    assert hits and "4.5mm/s" in hits[0]["text"]


def test_retrieve_respects_topk():
    assert len(core.retrieve("振动 电机", KB, topk=1)) == 1


def test_retrieve_low_score_returns_empty():
    assert core.retrieve("完全不相关的话题内容", KB, min_score=0.4) == []


def test_answer_with_citations():
    a = core.answer("电机电流偏高", KB)
    assert a["grounded"] and a["citations"] and "[" in a["text"]


def test_answer_refuses_when_no_evidence():
    a = core.answer("今天午饭吃什么", KB, min_score=0.5)
    assert not a["grounded"] and "查无依据" in a["text"]
