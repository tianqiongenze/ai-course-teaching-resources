# -*- coding: utf-8 -*-
"""控制台入口：pyproject.toml 的 [project.scripts] 声明的正是本模块 main()。

pip install -e . 之后可直接键入脚本名（等价 python run.py）：
  m11_fault_diag                 跑完整流水线并落盘 output/
  m11_fault_diag --check         环境自检（工单"预习自测"：报告装了哪些库）
  m11_fault_diag --tier          打印工单 M1.1 D/C/B/A 档位门槛 + 实测规范率
  m11_fault_diag --style-only    只做 PEP 8 规范体检（不跑业务）
  m11_fault_diag --set k=v       命令行临时覆盖配置（改配置不改代码的延伸）
"""
import argparse
import os
import sys

from . import config as C
from . import io_utils
from . import pipeline as P
from . import stylecheck as S

ROOT = S.project_root(os.path.abspath(__file__))
SCRIPT = "m11_fault_diag"
DESC = "泵类设备故障诊断分类（01-AI应用基础 W04 第1次课）"
DATA_FILE = "pump_fault.csv"
# 工单 M1.1《四、验收标准》四档；末列是"规范率"门槛（%）——
#   D 档取工单明文"代码规范率≥70%"；C/B/A 档取工单"五、通用量表·代码规范"行 70/80/90。
#   门槛由 src/fault_diag/stylecheck.py 实测比对，不写死结论。
TIERS = [
    ("及格(D)", "准确率≥0.75；能口述四项指标（准确率/精确率/召回率/F1）含义", 70),
    ("良好(C)", "准确率≥0.80；指标解读准确无误（各类 P/R/F1 明细可复核）", 70),
    ("优秀(B)", "准确率≥0.85；三模型对比表完整；决策矩阵填写规范", 80),
    ("优(A)", "达 B 且：对比分析引用指标差异解释业务影响；代码含函数化封装", 90),
]
CLAIMED = "A（真实数据 450 条 + LR/DT/RF 三模型 + 决策矩阵交付）"


def _typed(v):
    """命令行传进来的永远是 str——按 int/float/bool 试还原（见工单预习自测）。"""
    low = v.strip().lower()
    if low in ("true", "false"):
        return low == "true"
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            continue
    return v


def apply_overrides(cfg, pairs):
    """--set key=value 覆盖配置项（raw + 具名属性双写，保持口径一致）。"""
    for kv in pairs or []:
        key, _, val = kv.partition("=")
        key, val = key.strip(), val.strip()
        if not key or not _:
            raise SystemExit("--set 需写作 key=value，收到: %r" % kv)
        cfg.raw[key] = _typed(val)
        if hasattr(cfg, key) and key != "items":
            setattr(cfg, key, _typed(val))
    return cfg


def style_min(cfg):
    """报告用规范率门槛：config 的 style_min 优先，缺省取 A 档线（最严的那档）。"""
    try:
        return float(cfg.raw.get("style_min", TIERS[-1][2]))
    except (TypeError, ValueError, AttributeError):
        return float(TIERS[-1][2])


def env_check():
    """环境自检：打印第三方库可用性——"环境也是选型维度"（课堂离线照样跑）。"""
    mods = ["numpy", "sklearn.linear_model", "sklearn.ensemble", "sklearn.tree",
            "sklearn.model_selection", "sklearn.preprocessing", "sklearn.metrics",
            "yaml", "pycodestyle", "flake8", "pandas", "matplotlib"]
    print("[%s] 环境自检 · Python %s" % (SCRIPT, sys.version.split()[0]))
    for m in mods:
        try:
            mod = __import__(m, fromlist=["_"])
            ver = getattr(mod, "__version__", "已安装")
            print("  OK   %-24s %s" % (m, ver))
        except ImportError:
            print("  MISS %-24s 将走内置兜底路径（不影响交付）" % m)
    data = io_utils.course_data(DATA_FILE)
    if data:
        print("  OK   %-24s %s" % ("data/" + DATA_FILE, data))
    else:
        print("  MISS %-24s 未找到，流水线改用合成兜底数据并在报告如实标注"
              % ("data/" + DATA_FILE,))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog=SCRIPT, description=DESC)
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "rules.yaml"))
    ap.add_argument("--outdir", default=os.path.join(ROOT, "output"))
    ap.add_argument("--quiet", action="store_true", help="只落盘，不打印报告正文")
    ap.add_argument("--check", action="store_true", help="环境自检")
    ap.add_argument("--tier", action="store_true", help="打印工单档位门槛")
    ap.add_argument("--style-only", action="store_true", help="只跑规范体检")
    ap.add_argument("--set", dest="overrides", action="append", metavar="K=V",
                    help="临时覆盖配置项，可重复使用")
    a = ap.parse_args(argv)

    if a.check:
        return env_check()
    if a.tier:
        stats = S.scan_project(ROOT)
        print("工单 %s 验收档位（实测规范率 %.1f%%，引擎 %s）:"
              % (DESC, stats["rate"], stats["engine"]))
        for name, need, gate in TIERS:
            mark = "实测达标" if stats["rate"] >= gate else "规范率不足"
            print("  %-8s 规范率≥%2.0f%% [%s] ｜ %s" % (name, gate, mark, need))
        print("  承诺档位: %s" % CLAIMED)
        return 0
    if a.style_only:
        stats = S.scan_project(ROOT)
        print("\n".join(S.format_section(stats, style_min(C.load_config(a.config)))))
        return 0 if stats["violations"] == 0 else 1

    cfg = apply_overrides(C.load_config(a.config), a.overrides)
    sections = P.run(cfg, out_dir=a.outdir, style_min=style_min(cfg))
    if not a.quiet:
        from . import report as R
        print(R.render(sections))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
