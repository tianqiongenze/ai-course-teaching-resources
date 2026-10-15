# -*- coding: utf-8 -*-

from fault_text_clf import core


def test_tokens_bigram_and_stopword():
    toks = core.tokens("液压油温升高", stop=["升高"])
    assert "液压" in toks and "油温" in toks and "温升" in toks
    assert "升高" not in toks          # 停用词被过滤（"升高"本身在表中）
    assert "液压油温升高" in toks        # 整段原词也保留


def test_tokens_empty():
    assert core.tokens("") == []


def test_build_and_evaluate():
    X = [" ".join(core.tokens(t)) for t, _ in [
        ("液压油温升高", "液压"), ("油泵泄漏", "液压"),
        ("风机轴承异响", "冷却"), ("水温偏高", "冷却")]]
    y = ["液压", "液压", "冷却", "冷却"]
    pipe = core.build(X, y)
    mt = core.evaluate(pipe, X, y)
    assert mt["acc"] == 1.0 and mt["macro_f1"] == 1.0


def test_predict_returns_class():
    X = [" ".join(core.tokens(t)) for t, _ in [
        ("液压油温升高", "液压"), ("油泵泄漏", "液压"),
        ("风机轴承异响", "冷却"), ("水温偏高", "冷却")]]
    y = ["液压", "液压", "冷却", "冷却"]
    pipe = core.build(X, y)
    assert core.predict(pipe, "液压泵泄漏") == "液压"
