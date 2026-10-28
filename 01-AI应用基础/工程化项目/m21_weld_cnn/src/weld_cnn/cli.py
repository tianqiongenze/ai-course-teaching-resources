# -*- coding: utf-8 -*-
"""控制台入口：pyproject.toml 的 [project.scripts] 声明的正是本模块 main()。

pip install -e . 之后可直接键入脚本名（等价 python run.py）：
  m21_weld_cnn                 跑完整流水线并落盘 output/
  m21_weld_cnn --check         环境自检（工单"预习自测"：报告装了哪些库）
  m21_weld_cnn --tier          打印工单 M2.1 D/C/B/A 档位门槛 + 实测规范率
  m21_weld_cnn --style-only    只做 PEP 8 规范体检（不跑业务）
  m21_weld_cnn --set k=v       命令行临时覆盖配置（改配置不改代码的延伸）
"""
import argparse
import os
import sys

from . import config as C
from . import pipeline as P
from . import stylecheck as S
from . import tiers as T

ROOT = S.project_root(os.path.abspath(__file__))
SCRIPT = "m21_weld_cnn"
DESC = "焊缝缺陷图像分类（01-AI应用基础 W06 第3次课）"
# 工单 M2.1 四档门槛的单一出处在 tiers.py + config/rules.yaml 的 tiers 段：
#   数值门（准确率 0.80/0.85/0.88）取自工单原文并外置在 rules.yaml（改配置不改
#   代码）；工单原文未逐档规定规范率门槛，档位判定**不含**规范率门。
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
    """规范率证据段显示阈值：config 的 style_min 优先。

    注意：工单 M2.1 未规定规范率档位门槛，此值**不参与**档位判定，
    只用于报告证据段的参考线显示。
    """
    try:
        return float(cfg.raw.get("style_min", 90.0))
    except (TypeError, ValueError, AttributeError):
        return 90.0


def env_check():
    """环境自检：打印第三方库可用性——"环境也是选型维度"（缺库有兜底路径）。"""
    mods = ["numpy", "sklearn.ensemble", "sklearn.model_selection",
            "yaml", "pycodestyle", "flake8", "torch", "torchvision",
            "matplotlib", "PIL"]
    print("[%s] 环境自检 · Python %s" % (SCRIPT, sys.version.split()[0]))
    for m in mods:
        try:
            mod = __import__(m, fromlist=["_"])
            ver = getattr(mod, "__version__", "已安装")
            print("  OK   %-26s %s" % (m, ver))
        except ImportError:
            print("  MISS %-26s 将走内置兜底路径（档位判定按 MISS 处理）" % m)
    print("  说明: 工单 M2.1 主路径为 tiny-CNN(torch) 双臂真实训练；torch 缺失时"
          "退回零 torch 轻量基线（块统计+RF 对照），CNN 能力项如实标 MISS。")
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
        cfg = apply_overrides(C.load_config(a.config), a.overrides)
        _sections, result = P.build(cfg, out_dir=a.outdir)
        gates = (cfg.raw.get("tiers") or {}) if isinstance(
            cfg.raw.get("tiers"), dict) else {}
        g = {"d": float(gates.get("acc_d", 0.80)),
             "c": float(gates.get("acc_c", 0.85)),
             "b": float(gates.get("acc_b", 0.88))}
        v = result["tiers"]
        print("工单 %s 验收档位（档位判定不含规范率门，规范率仅作证据；"
              "实测规范率 %.1f%%，引擎 %s）:"
              % (DESC, result["style_rate"], result["style_engine"]))
        for line in T.render_lines(v):
            print("  " + line)
        print("  门槛来源: rules.yaml tiers 段（D≥%.2f C≥%.2f B≥%.2f，A 达 B）"
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
