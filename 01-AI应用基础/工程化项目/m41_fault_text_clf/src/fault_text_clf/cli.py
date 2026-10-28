# -*- coding: utf-8 -*-
"""控制台入口：pyproject.toml 的 [project.scripts] 声明的正是本模块 main()。

pip install -e . 之后可直接键入脚本名（等价 python run.py）：
  m41_fault_text_clf                 跑完整流水线并落盘 output/
  m41_fault_text_clf --check         环境自检（工单"预习自测"：报告装了哪些库）
  m41_fault_text_clf --tier          打印工单 M4.1 D/C/B/A 档位门槛 + 实测规范率
  m41_fault_text_clf --style-only    只做 PEP 8 规范体检（不跑业务）
  m41_fault_text_clf --set k=v       命令行临时覆盖配置（改配置不改代码的延伸）
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
SCRIPT = "m41_fault_text_clf"
DESC = "故障报告文本自动分类（01-AI应用基础 W10 第7次课）"
DATA_FILE = "fault_reports.csv"
# 工单 M4.1《四、验收标准》四档判据与数字门槛的单一出处在 tiers.py +
# config/rules.yaml 的 tiers: 段（tests/test_tiers.py 同一口径）。
#   本工单未逐档写规范率，门槛取 M1.1 工单"五、通用量表·代码规范"行 D60/C70/B80/A90。
#   准确率/新文本/对比/关键词/混淆矩阵/调优全部由流水线实测判定；
#   达不到就印"未达标"，不降阈值、不挑数据。


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
    gates = T.gates_from(cfg)
    try:
        return float(cfg.raw.get("style_min", gates["style"][-1]))
    except (TypeError, ValueError, AttributeError):
        return float(gates["style"][-1])


def env_check():
    """环境自检：打印第三方库可用性——"环境也是选型维度"（jieba 缺失时走二元词兜底）。"""
    mods = ["numpy", "sklearn.feature_extraction.text", "sklearn.linear_model",
            "sklearn.naive_bayes", "sklearn.pipeline", "sklearn.metrics",
            "sklearn.model_selection", "jieba", "yaml", "pycodestyle",
            "flake8", "matplotlib"]
    print("[%s] 环境自检 · Python %s" % (SCRIPT, sys.version.split()[0]))
    for m in mods:
        try:
            mod = __import__(m, fromlist=["_"])
            ver = getattr(mod, "__version__", "已安装")
            print("  OK   %-26s %s" % (m, ver))
        except ImportError:
            print("  MISS %-26s 将走内置兜底路径（不影响交付）" % m)
    data = io_utils.course_data(DATA_FILE)
    if data:
        print("  OK   %-26s %s" % ("data/" + DATA_FILE, data))
    else:
        print("  MISS %-26s 未找到，只能用语料兜底（准确率档位口径会随之下降）"
              % ("data/" + DATA_FILE,))
    return 0


def _gate_txt(sub):
    """把某档的数字门槛渲染成 'acc_min≥0.75 new_min≥3' 形式（--tier 打印用）。"""
    parts = []
    for k, v in sub.items():
        if isinstance(v, bool):
            parts.append("%s=%s" % (k, "必须" if v else "跳过"))
        else:
            parts.append("%s≥%g" % (k, v))
    return " ".join(parts)


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
        cfg = C.load_config(a.config)
        gates = T.gates_from(cfg)
        stats = S.scan_project(ROOT)
        print("工单 %s 验收档位（实测规范率 %.1f%%，引擎 %s）:"
              % (DESC, stats["rate"], stats["engine"]))
        for i, key in enumerate(T.KEYS):
            name, need, _ = T.TIERS[i]
            mark = "规范率达标" if stats["rate"] >= gates["style"][i] else "规范率不足"
            print("  %-8s 规范率≥%.0f%% [%s] ｜ %s ｜ 数字门槛: %s"
                  % (name, gates["style"][i], mark, need,
                     _gate_txt(gates[key])))
        print("  功能门实测判定（准确率/新文本/对比/关键词/混淆/调优）见 "
              "output/report.txt 的 [验收档位判定（实测）] 段")
        print("  人工答辩项 %d 条: %s" % (len(T.MANUAL), "；".join(T.MANUAL)))
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
