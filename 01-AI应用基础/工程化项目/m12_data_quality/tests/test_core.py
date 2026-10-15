# -*- coding: utf-8 -*-
import pandas as pd

from data_quality import core


def test_make_dirty_has_all_three_defects():
    df = core.make_dirty(300, 7)
    d = core.diagnose(df)
    assert d["missing"] > 0 and d["over_limit"] > 0 and d["negative"] > 0


def test_make_dirty_deterministic():
    assert core.make_dirty(50, 3).equals(core.make_dirty(50, 3))


def test_clean_removes_all_defects():
    df = core.make_dirty(300, 7)
    c = core.clean(df)
    d = core.diagnose(c)
    assert d["missing"] == 0 and d["negative"] == 0 and d["over_limit"] == 0
    assert len(c) < len(df)


def test_quality_between_zero_and_one():
    df = core.make_dirty(300, 7)
    q = core.quality(core.clean(df))
    assert 0.0 <= q <= 1.0


def test_quality_empty_frame_zero():
    assert core.quality(pd.DataFrame({"vib": [], "temp": []})) == 0.0


def test_quality_all_good_is_one():
    df = pd.DataFrame({"vib": [4.0, 5.0], "temp": [50.0, 60.0]})
    assert core.quality(df) == 1.0
