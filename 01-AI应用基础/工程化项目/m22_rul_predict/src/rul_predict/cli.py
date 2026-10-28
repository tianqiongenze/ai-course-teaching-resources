# -*- coding: utf-8 -*-
"""控制台入口：pyproject.toml 的 [project.scripts] 声明的正是本模块 main()。

pip install -e . 之后可直接键入脚本名（等价 python run.py）：
  m22_rul_predict                 跑完整流水线并落盘 output/
  m22_rul_predict --check         环境自检（工单"预习自测"：报告装了哪些库）
  m22_rul_predict --tier          实跑一次并打印工单 M2.2 四档实测判定
  m22_rul_predict --style-only    只做 PEP 8 规范体检（不跑业务）
  m22_rul_predict --set k=v       命令行临时覆盖配置（改配置不改代码的延伸）
"""
import argparse
import os
import sys

from . import config as C
from . import pipeline as P
from . import stylecheck as S
from . import tiers as T

ROOT = S.project_root(os.path.abspath(__file__))
SCRIPT = "m22_rul_predict"
DESC = "轴承剩余寿命预测（01-AI应用基础 W07 第4次课）"
# 档位表与门槛的唯一出处是 src/rul_predict/tiers.py + config/rules.yaml 的
# tiers 段（工单《四、验收标准》逐字原句）；本文件不再复制一份，避免
# "控制台说的"与"实测判的"两套口径。工单未逐档规定规范率 → 判定不含规范率门。
TIERS = T.TIERS


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
    """--set key=value 覆盖配置项（raw + 具名属性双写，保持口径一致）。

    支持点号路径：`--set tiers.mse_b=0.05` 覆盖 rules.yaml 里嵌套的工单门槛——
    判据外置就要连"命令行临时改判据"一起成立，否则"--set 改配置"只是句空话。
    """
    for kv in pairs or []:
        key, _, val = kv.partition("=")
        key, val = key.strip(), val.strip()
        if not key or not _:
            raise SystemExit("--set 需写作 key=value，收到: %r" % kv)
        typed = _typed(val)
        node = cfg.raw
        parts = key.split(".")
        for p in parts[:-1]:
            nxt = node.get(p)
            if not isinstance(nxt, dict):
                nxt = {}
                node[p] = nxt
            node = nxt
        node[parts[-1]] = typed
        if len(parts) == 1 and hasattr(cfg, parts[0]) and parts[0] != "items":
            setattr(cfg, parts[0], typed)
    return cfg


def style_min(cfg):
    """规范率证据段显示阈值：config 的 style_min 优先。

    注意：工单 M2.2 未规定规范率档位门槛，此值**不参与**档位判定，
    只用于报告证据段的参考线显示。
    """
    try:
        return float(cfg.raw.get("style_min", 90.0))
    except (TypeError, ValueError, AttributeError):
        return 90.0


def gates_of(cfg):
    """rules.yaml tiers 段的四档 MSE 门槛（缺省即工单原文数字，代码里不写死）。"""
    raw = cfg.raw.get("tiers") if isinstance(cfg.raw.get("tiers"), dict) else {}
    return {"d": float(raw.get("mse_d", 0.15)),
            "c": float(raw.get("mse_c", 0.12)),
            "b": float(raw.get("mse_b", 0.10))}


def env_check():
    """环境自检：打印第三方库可用性——"环境也是选型维度"（缺库有兜底路径）。"""
    mods = ["numpy", "sklearn.linear_model", "sklearn.metrics",
            "sklearn.ensemble", "yaml", "pycodestyle", "flake8", "torch",
            "matplotlib", "scipy"]
    print("[%s] 环境自检 · Python %s" % (SCRIPT, sys.version.split()[0]))
    for m in mods:
        try:
            mod = __import__(m, fromlist=["_"])
            ver = getattr(mod, "__version__", "已安装")
            print("  OK   %-26s %s" % (m, ver))
        except ImportError:
            print("  MISS %-26s 将走内置兜底路径（档位判定按 MISS 处理）" % m)
    print("  说明: 工单 M2.2 主路径是 LSTM(torch)；torch 缺失时改交实测最优 "
          "sklearn 模型，C 档『对照基线说明 LSTM 增益』如实判缺并印 MISS，不伪造增益。")
    print("  注意: matplotlib 缺失时 prediction_curve.png / window_sensitivity.png "
          "不会生成 → D 档『完成预测与可视化』实测判缺（图是真落盘的，报告只认磁盘字节数）。")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog=SCRIPT, description=DESC)
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "rules.yaml"))
    ap.add_argument("--outdir", default=os.path.join(ROOT, "output"))
    ap.add_argument("--quiet", action="store_true", help="只落盘，不打印报告正文")
    ap.add_argument("--check", action="store_true", help="环境自检")
    ap.add_argument("--tier", action="store_true",
                    help="实跑流水线并打印工单档位实测判定")
    ap.add_argument("--style-only", action="store_true", help="只跑规范体检")
    ap.add_argument("--set", dest="overrides", action="append", metavar="K=V",
                    help="临时覆盖配置项，可重复使用")
    a = ap.parse_args(argv)

    if a.check:
        return env_check()
    if a.tier:
        cfg = apply_overrides(C.load_config(a.config), a.overrides)
        _sections, result = P.build(cfg, out_dir=a.outdir)
        g = gates_of(cfg)
        print("工单 %s 验收档位（档位判定不含规范率门，规范率仅作证据；"
              "实测规范率 %.1f%%，引擎 %s）:"
              % (DESC, result["style_rate"], result["style_engine"]))
        for line in T.render_lines(result["tiers"]):
            print("  " + line)
        print("  门槛来源: rules.yaml tiers 段（D<%.2f C≤%.2f B<%.2f，A 达 B）"
              % (g["d"], g["c"], g["b"]))
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
