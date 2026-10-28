# -*- coding: utf-8 -*-
"""控制台入口：pyproject.toml 的 [project.scripts] 声明的正是本模块 main()。

pip install -e . 之后可直接键入脚本名（等价 python run.py）：
  m32_yolo_dual                 跑完整双路线对照并落盘 output/
  m32_yolo_dual --check         环境自检（工单"预习自测"：报告装了哪些库）
  m32_yolo_dual --tier          实测跑一遍并打印 D/C/B/A 判定（含人工答辩项）
  m32_yolo_dual --style-only    只做 PEP 8 规范体检（不跑业务）
  m32_yolo_dual --set k=v       命令行临时覆盖配置（改配置不改代码的延伸）
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
SCRIPT = "m32_yolo_dual"
DESC = "产线实时缺陷检测双路线对照（01-AI应用基础 W09 第6次课）"
WEIGHTS = ("weights", "yolov8n.onnx")
# 档位判定不在本文件硬编码：门槛数字在 config/rules.yaml 的 tiers: 段，
# 判定逻辑在 src/yolo_dual/tiers.py（实测驱动，档位是算出来的不是自称的）。
CLAIMED = "A（cv2 基线兜底口径三档真计时 / 阈值四档双路线实测 / 裁剪+多线程量化增益）"


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
    """报告展示用规范率线：config 的 style_min 优先，缺省 90。
    工单未逐档设规范率门槛——此线只用于体检报告展示，不参与档位判定。"""
    try:
        return float(cfg.raw.get("style_min", 90.0))
    except (TypeError, ValueError, AttributeError):
        return 90.0


def env_check():
    """环境自检：打印第三方库可用性——"环境也是选型维度"（无权重时预训练路线如实标 n/a）。"""
    mods = ["numpy", "cv2", "onnxruntime", "torch", "ultralytics", "matplotlib",
            "yaml", "pycodestyle", "flake8"]
    print("[%s] 环境自检 · Python %s" % (SCRIPT, sys.version.split()[0]))
    for m in mods:
        try:
            mod = __import__(m, fromlist=["_"])
            ver = getattr(mod, "__version__", "已安装")
            print("  OK   %-26s %s" % (m, ver))
        except ImportError:
            print("  MISS %-26s 该路线自动降级，报告如实写 n/a（不编造检出数）" % m)
    w = io_utils.course_data(*WEIGHTS)
    if w:
        print("  OK   %-26s %s" % ("data/".join(WEIGHTS), w))
    else:
        print("  MISS %-26s 权重缺失 → 预训练 YOLO 路线不产出检出" % "data/".join(WEIGHTS))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog=SCRIPT, description=DESC)
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "rules.yaml"))
    ap.add_argument("--outdir", default=os.path.join(ROOT, "output"))
    ap.add_argument("--quiet", action="store_true", help="只落盘，不打印报告正文")
    ap.add_argument("--check", action="store_true", help="环境自检")
    ap.add_argument("--tier", action="store_true", help="实测四档判定并打印")
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
