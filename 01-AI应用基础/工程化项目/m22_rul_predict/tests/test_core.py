# -*- coding: utf-8 -*-
import numpy as np

from rul_predict import core


def test_make_traj_has_degradation_segment():
    x, rul, m = core.make_traj(500, 3)
    assert m.any() and (~m).any()
    assert np.isnan(rul[0]) and not np.isnan(rul[-1])


def test_make_traj_rul_monotonic_in_degradation():
    x, rul, m = core.make_traj(500, 3)
    seg = rul[m]
    assert all(seg[i] >= seg[i + 1] for i in range(0, len(seg) - 1, 50))


def test_fit_returns_metrics():
    x, rul, m = core.make_traj(600, 7)
    idx = np.where(m)[0]
    model, pred, mt = core.fit(x[idx, None], rul[idx])
    assert 0.0 <= mt["r2"] <= 1.0 and mt["rmse"] > 0


def test_fit_with_explicit_model():
    from sklearn.ensemble import RandomForestRegressor
    x, rul, m = core.make_traj(600, 7)
    idx = np.where(m)[0]
    _, _, mt = core.fit(x[idx, None], rul[idx], RandomForestRegressor(n_estimators=10, random_state=0))
    assert "mae" in mt


def test_business_note_translates_error():
    note = core.business_note(0.1, 1.0)
    assert "%" in note and "维护周期" in note


def test_business_note_zero_span_no_crash():
    assert isinstance(core.business_note(0.1, 0.0), str)
