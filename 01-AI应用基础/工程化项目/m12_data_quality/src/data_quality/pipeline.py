# -*- coding: utf-8 -*-
"""造脏 → 三类诊断 → 清洗 → 质量分 → 留痕报告。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    n = int(cfg.raw.get("n_rows", 300))
    tmax = float(cfg.raw.get("temp_max", 120.0))
    raw = core.make_dirty(n, seed=cfg.seed)
    before = {"rows": len(raw), "diag": core.diagnose(raw, tmax)}
    c = core.clean(raw, tmax)
    after = {"rows": len(c), "diag": core.diagnose(c, tmax), "quality": core.quality(c, tmax)}
    result = {"before": before, "after": after,
              "removed": len(raw) - len(c),
              "keep_rate": round(len(c) / max(len(raw), 1), 4)}
    sections = [("输入口径", ["原始 %d 行｜温度上限 %.0f℃｜vib 合理区间 %.0f~%.0f"
                % (n, tmax, 0.0, 15.0)]),
                ("三类问题（清洗前）", [
                    "缺失: %d" % before["diag"]["missing"],
                    "温度越限: %d" % before["diag"]["over_limit"],
                    "vib 负值: %d" % before["diag"]["negative"]]),
                ("清洗留痕", ["%d 行 → %d 行（剔除 %d 行，保留率 %.1f%%）"
                 % (len(raw), len(c), result["removed"], result["keep_rate"] * 100)]),
                ("质量分", ["清洗后质量分 = %.4f（目标 ≥ 0.85）" % after["quality"]]),
                ("结论与建议", ["三类问题已全部清零后方可交付下游；留痕（前后行数）即过程性证据"])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections
