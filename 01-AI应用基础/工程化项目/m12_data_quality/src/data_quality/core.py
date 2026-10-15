# -*- coding: utf-8 -*-
"""脏数据构造、三类清洗与质量评分（纯 pandas，无 IO）。"""
import numpy as np


def make_dirty(n=300, seed=7, n_nan=15, n_over=6, n_neg=5):
    """合成含三类脏数据的泵站日志。"""
    rng = np.random.RandomState(seed)
    df = __import__("pandas").DataFrame({
        "ts": __import__("pandas").date_range("2026-03-01", periods=n, freq="h"),
        "vib": rng.normal(4.0, 0.5, n).round(3),
        "temp": rng.normal(55, 3, n).round(1)})
    df.loc[rng.choice(n, min(n_nan, n), replace=False), "vib"] = np.nan
    df.loc[rng.choice(n, min(n_over, n), replace=False), "temp"] = 135.0
    df.loc[rng.choice(n, min(n_neg, n), replace=False), "vib"] = -1.0
    return df


def diagnose(df, temp_max=120.0, vib_min=0.0, vib_max=15.0):
    """三类问题计数（缺失/越界/负值）。"""
    return {
        "missing": int(df["vib"].isna().sum()),
        "over_limit": int((df["temp"] > temp_max).sum()),
        "negative": int((df["vib"] < vib_min).sum()),
        "out_of_range": int(((df["vib"] < vib_min) | (df["vib"] > vib_max)).sum()),
    }


def clean(df, temp_max=120.0, vib_min=0.0, vib_max=15.0):
    """清洗：剔除 vib 缺失/负值/越界 与 temp 越限的行。"""
    return df[(df["vib"].notna()) & (df["vib"] >= vib_min) & (df["vib"] <= vib_max)
              & (df["temp"] <= temp_max)].copy()


def quality(df, temp_max=120.0, vib_min=0.0, vib_max=15.0):
    """质量分 = 完整率 × 合理率（工单口径）。"""
    if len(df) == 0:
        return 0.0
    complete = float(df["vib"].notna().mean())
    valid = float(((df["vib"].between(vib_min, vib_max)) & (df["temp"] <= temp_max)).mean())
    return round(complete * valid, 4)
