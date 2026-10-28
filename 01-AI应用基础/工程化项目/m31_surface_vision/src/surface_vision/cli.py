# -*- coding: utf-8 -*-
"""控制台入口：pyproject.toml 的 [project.scripts] 声明的正是本模块 main()。

pip install -e . 之后可直接键入脚本名（等价 python run.py）：
  m31_surface_vision                 跑完整流水线并落盘 output/
  m31_surface_vision --check         环境自检（工单"预习自测"：报告装了哪些库）
  m31_surface_vision --tier          实跑流水线并打印工单 M3.1 四档实测判定
  m31_surface_vision --style-only    只做 PEP 8 规范体检（不跑业务）
  m31_surface_vision --set k=v       命令行临时覆盖配置（改配置不改代码的延伸）
"""
import argparse
import os
import sys

from . import config as C
from . import io_utils
from . import pipeline as P
from . import stylecheck as S
from . import tiers as T

ROOT = S.project_root(os.path.abspath(__file__))
SCRIPT = "m31_surface_vision"
DESC = "产品表面缺陷尺寸测量（01-AI应用基础 W08 第5次课）"
# 工单 M3.1《四、验收标准》四档门槛的单一出处：数字在 config/rules.yaml 的
# tiers: 段、文案在 tiers.py——--tier / report.txt / pytest 全部吃同一实测判定。
# 本工单未逐档写规范率 → 规范率只实测展示，不构成档位门。
CLAIMED = "A（真实零件+教师真值复算误差 / 双阈值策略对比 / 标注图要素机检 / 多缺陷件误检分析）"


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
    """报告用规范率展示线：config 的 style_min 优先，缺省 90（仅文案对照，
    本工单未逐档设规范率门槛，不进档位判定）。"""
    try:
        return float(cfg.raw.get("style_min", 90.0))
    except (TypeError, ValueError, AttributeError):
        return 90.0


def env_check():
    """环境自检：打印第三方库可用性——"环境也是选型维度"（课堂离线照样跑）。"""
    mods = ["numpy", "cv2", "PIL", "matplotlib", "yaml", "pycodestyle", "flake8", "sklearn"]
    print("[%s] 环境自检 · Python %s" % (SCRIPT, sys.version.split()[0]))
    for m in mods:
        try:
            mod = __import__(m, fromlist=["_"])
            ver = getattr(mod, "__version__", "已安装")
            print("  OK   %-26s %s" % (m, ver))
        except ImportError:
            print("  MISS %-26s cv2 是本项目硬依赖，缺失时流水线无法运行（请 pip install opencv-python）"
                  % m)
    parts = io_utils.course_data("surface_parts")
    if parts:
        print("  OK   %-26s %s（本项目按合成件跑，真实件供对照）" % ("data/surface_parts", parts))
    else:
        print("  MISS %-26s 未找到，按内置合成件运行" % "data/surface_parts")
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
        _sections, result = P.build(cfg, out_dir=a.outdir,
                                    style_min=style_min(cfg))
        v = result["tiers"]
        print("工单 %s 验收档位（实测规范率 %.1f%%，引擎 %s——只作展示不构成档位门）:"
              % (DESC, result["style_rate"], result["style_engine"]))
        for line in T.render_lines(v):
            print("  " + line)
        for line in T.render_manual(v):
            print("  " + line)
        print("  承诺档位: %s ｜ 实测达成: %s" % (CLAIMED, v["claimed"]))
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
