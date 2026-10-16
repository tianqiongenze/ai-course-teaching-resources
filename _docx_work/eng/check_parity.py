# -*- coding: utf-8 -*-
"""三形态（starter / 教师参考 / 工程化项目）同源性校验。

校验维度：
  A 存在性  —— 同一工单的三形态实体是否齐全
  B 领域同源 —— 工程化项目 core.py 的核心标识符，是否能在 starter / 教师参考中找到同领域证据
  C 口径同源 —— 阈值类常量（warn/danger/seed/topk）在三者中是否一致（提示级，不硬失败）

用法：
  python _docx_work/eng/check_parity.py
  python _docx_work/eng/check_parity.py --json        # 供流水线消费
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import eng_specs as S

ROOT = os.path.dirname(os.path.dirname(HERE))

# 工单 id -> (starter 文件名, 教师参考 solutions 函数名)
# 说明：starter 与 solutions 的命名早于工程化项目，二者映射在此集中声明，便于后续重命名时单点维护。
MAP = {
    # 01-AI应用基础
    "01-M1.1": ("W04_starter.py", "m11"),
    "01-M1.2": ("W05_starter.py", "m12"),
    "01-M2.1": ("W06_starter.py", "m21"),
    "01-M2.2": ("W07_starter.py", "m22"),
    "01-M3.1": ("W08_starter.py", "m31"),
    "01-M3.2": ("W09_starter.py", "m32"),
    "01-M4.1": ("W10_starter.py", "m41"),
    "01-M4.2": ("W11_starter.py", "m42"),
    # 02-程序设计基础（无独立 solutions 模块，教师参考以 starter 同目录参考实现为准）
    "02-W01": ("W01_device_init.py", None),
    "02-W02": ("W02_alarm_if.py", None),
    "02-W03": ("W03_alarm_loop.py", None),
    "02-W04": ("W04_device_class.py", None),
    "02-W05": ("W05_inherit.py", None),
    "02-W06": ("W06_robust_collector.py", None),
    "02-W07": ("W07_parser.py", None),
    "02-W08": ("W08_fileio.py", None),
    "02-W09": ("W09_wordcloud_report.py", None),
    "02-W10": ("W10_report_pdf.py", None),
    "02-W11": ("W11_collector.py", None),
    "02-W12": ("W12_project_template.py", None),
    # 03-Python程序设计-项目实战（starter 命名与 slug 不完全一致，逐项声明）
    "03-P1.1": ("W01_exercises.py", "p11"),
    "03-P1.2": ("W02_template.py", "p12"),
    "03-P2.1": ("W03_pipeline.py", "p21"),
    "03-P2.2": ("W04_features.py", "p22"),
    "03-P3": ("W05_dashboard.py", "p33"),
    "03-P4": ("W06_collector.py", "p41"),
    "03-P5": ("W07_warehouse.py", "p55"),
    "03-P6": ("W08_ml_service.py", "p66"),
    # 05-AI应用基础48课时版
    "05-M1-1a": ("W07_clean_starter.py", "m11a"),
    "05-M1-1b": ("W10_feature_starter.py", "m11b"),
    "05-M2-1a": ("W11_classify_starter.py", "m21a"),
    "05-M2-2": ("W12_tuning_starter.py", "m22"),
    "05-M2-3a": ("W13_mlp_starter.py", "m23a"),
    "05-M2-3b": ("W14_bidding_starter.py", "m23b"),
    "05-M3-1": ("W15_transfer_starter.py", "m31"),
    "05-M3-2": ("W16_detect_starter.py", "m32"),
    "05-M4-1": ("W17_prompt_starter.py", "m41"),
    "05-M4-2": ("W18_rag_starter.py", "m42"),
    "05-M5-1": ("W19_multiagent_starter.py", "m51"),
    "05-Z": ("W20_defense_starter.py", "z"),
}

# 领域关键词：用于判定"同一领域"的兜底证据（大小写不敏感）
DOMAIN_WORDS = {
    "清洗": ["清洗", "clean", "缺失", "nan", "越界"],
    "分类": ["分类", "classif", "混淆矩阵", "confusion", "clf"],
    "特征": ["特征", "feature", "rms", "fft", "freq"],
    "检测": ["检测", "detect", "iou", "yolo", "mask"],
    "文本": ["分词", "token", "tfidf", "prompt", "rag", "检索"],
    "调度": ["调度", "policy", "agent", "奖励", "reward"],
    "回归": ["回归", "regress", "rul", "rmse", "寿命"],
    "迁移": ["迁移", "transfer", "pca", "冻结", "frozen"],
    "调优": ["调参", "tuning", "grid", "random", "search"],
    "神经网络": ["mlp", "neural", "神经网络", "epoch", "loss"],
    "告警": ["告警", "alarm", "warn", "danger", "level"],
    "文件": ["csv", "json", "write", "read", "原子"],
    "采集": ["采集", "collect", "batch", "retry", "pending"],
    "报表": ["报表", "report", "kpi", "oee", "pdf"],
    "对象": ["class", "继承", "inherit", "device", "对象"],
    "解析": ["解析", "parse", "报文", "packet"],
    "数据": ["orm", "index", "query", "table"],
    "模板": ["模板", "template", "skeleton", "工程"],
    "答辩": ["答辩", "defense", "档案袋", "layer"],
}

CORE_IDENT = re.compile(r"^def ([a-z_][a-z0-9_]*)", re.M)
CONST_NUM = re.compile(r"^\s*([A-Za-z_]+)\s*[:=]\s*([0-9]+\.?[0-9]*)", re.M)


def read(path):
    try:
        return open(path, encoding="utf-8").read().lower()
    except Exception:
        return ""


def domain_hits(text):
    """返回文本命中的领域标签集合。"""
    t = text.lower()
    return {d for d, words in DOMAIN_WORDS.items() if any(w.lower() in t for w in words)}


def check_one(spec):
    pid = spec["id"]
    course = spec["course"]
    starter_name, sol_fn = MAP.get(pid, (None, None))
    res = {"id": pid, "course": course, "slug": spec["slug"], "title": spec["title"]}

    # ── A 存在性 ──
    eng_dir = os.path.join(ROOT, course, "工程化项目", spec["slug"])
    res["eng_exists"] = os.path.isdir(eng_dir)

    starter_path = None
    if starter_name:
        cand = os.path.join(ROOT, course, "学生代码框架", starter_name)
        if os.path.exists(cand):
            starter_path = cand
    res["starter"] = os.path.basename(starter_path) if starter_path else None
    res["starter_exists"] = starter_path is not None

    sol_path = os.path.join(ROOT, course, "教师参考", "solutions.py")
    if os.path.exists(sol_path) and sol_fn:
        m = re.search(r"^def %s\s*\(" % re.escape(sol_fn),
                      open(sol_path, encoding="utf-8").read(), re.M)
        res["solution_fn"] = sol_fn if m else None
    elif not sol_fn:
        res["solution_fn"] = "(无独立参考模块)"
    else:
        res["solution_fn"] = None
    res["solution_exists"] = bool(res.get("solution_fn"))

    # ── B 领域同源：工程化项目 core.py 的领域词 ∩ starter/教师参考 的领域词 ──
    core_path = os.path.join(eng_dir, "src", spec["pkg"], "core.py")
    eng_text = read(core_path)
    eng_dom = domain_hits(eng_text)
    st_dom = domain_hits(read(starter_path)) if starter_path else set()
    if res.get("solution_fn") and res["solution_fn"] != "(无独立参考模块)":
        src = open(sol_path, encoding="utf-8").read()
        i = src.find("def %s(" % res["solution_fn"])
        sol_text = src[i:i + 4000].lower()
        sol_dom = domain_hits(sol_text)
    else:
        sol_dom = set()
    res["eng_domain"] = sorted(eng_dom)
    res["shared_with_starter"] = sorted(eng_dom & st_dom)
    res["shared_with_solution"] = sorted(eng_dom & sol_dom)

    # ── C 口径同源：阈值常量比对（提示级） ──
    def consts(text):
        return {k: float(v) for k, v in CONST_NUM.findall(text)}
    eng_c = consts(eng_text)
    yaml_p = os.path.join(eng_dir, "config", "rules.yaml")
    yaml_c = consts(read(yaml_p)) if os.path.exists(yaml_p) else {}
    res["threshold_keys"] = sorted(set(eng_c) & set(yaml_c))[:6]

    # ── 判定 ──
    checks = []
    checks.append(("A-工程化项目存在", res["eng_exists"]))
    if starter_name:
        checks.append(("A-starter存在", res["starter_exists"]))
    if sol_fn:
        checks.append(("A-教师参考存在", res["solution_exists"]))
    # 领域同源：starter 或 教师参考 至少一方与工程化项目共享 ≥1 个领域标签
    shared_ok = bool(res["shared_with_starter"] or res["shared_with_solution"])
    checks.append(("B-领域同源", shared_ok))
    res["passed"] = all(v for _, v in checks)
    res["checks"] = {k: v for k, v in checks}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    rows = [check_one(s) for s in S.SPECS]
    ok = sum(1 for r in rows if r["passed"])
    mapped = sum(1 for r in rows if r["id"] in MAP)

    if a.json:
        print(json.dumps({"total": len(rows), "passed": ok, "rows": rows},
                         ensure_ascii=False, indent=2))
        return

    print()
    print("=" * 74)
    print("三形态同源性校验（starter / 教师参考 / 工程化项目）")
    print("=" * 74)
    print("%-10s %-22s %-6s %-9s %-9s %s" % ("工单", "工程化项目", "starter", "教师参考", "领域同源", "判定"))
    print("-" * 74)
    for r in rows:
        print("%-10s %-22s %-6s %-9s %-9s %s" % (
            r["id"], r["slug"][:22],
            "OK" if r["starter_exists"] else ("-" if r["starter"] is None else "缺"),
            "OK" if r["solution_exists"] else "缺",
            "OK" if (r["shared_with_starter"] or r["shared_with_solution"]) else "弱",
            "PASS" if r["passed"] else "FAIL"))
    print("-" * 74)
    print("映射覆盖 %d / %d 　通过 %d / %d" % (mapped, len(rows), ok, len(rows)))

    weak = [r for r in rows if not (r["shared_with_starter"] or r["shared_with_solution"])]
    if weak:
        print()
        print("领域同源较弱（需人工确认口径是否一致）:")
        for r in weak:
            print("  %-10s %-22s 工程化项目领域=%s" % (r["id"], r["slug"], r["eng_domain"]))
    missing = [r for r in rows if not r["eng_exists"]]
    if missing:
        print()
        print("缺失工程化项目:")
        for r in missing:
            print("  %-10s %s" % (r["id"], r["slug"]))
    print("=" * 74)


if __name__ == "__main__":
    main()
