# -*- coding: utf-8 -*-
"""教学资源库·全量自检总脚本（73号轮）

一键复现全部质量门禁，产出结构化报告。用于：
  · 每次资源更新后的回归自检（CI 式）
  · 公开分享/评审前的体检

用法:
  python check_all.py            # 全量检查
  python check_all.py --json     # 输出 JSON（供外部流水线消费）

退出码: 0=全部通过；1=存在失败项
"""
import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_PAGES = 80


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def pptx_files():
    return [p for p in glob.glob(os.path.join(ROOT, "**", "*.pptx"), recursive=True)
            if "~$" not in p and "_docx_work" not in p]


def py_files():
    return [p for p in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True)
            if "_docx_work" not in p and "site-packages" not in p
            and os.path.basename(p) != "check_all.py"]   # 排除本脚本（其内含检测用正则字面量）


# ── 检查项 ────────────────────────────────────────────────────────
def check_ppt_pages():
    from pptx import Presentation
    over, fail = [], []
    counts = {}
    for p in sorted(pptx_files()):
        try:
            n = len(Presentation(p).slides)
        except Exception as e:
            fail.append((rel(p), str(e)[:60]))
            continue
        key = "/".join(rel(p).split("/")[:2])
        counts.setdefault(key, {"n": 0, "pages": 0, "max": 0})
        counts[key]["n"] += 1
        counts[key]["pages"] += n
        counts[key]["max"] = max(counts[key]["max"], n)
        if n > MAX_PAGES:
            over.append((rel(p), n))
    detail = "  ".join(f"{k}:{v['n']}册/{v['pages']}页/最大{v['max']}"
                       for k, v in sorted(counts.items()))
    return (not over and not fail), f"打开失败{len(fail)} 超{MAX_PAGES}页{len(over)}", detail


def check_ppt_footers():
    from pptx import Presentation
    bad = []
    for p in sorted(pptx_files()):
        try:
            prs = Presentation(p)
        except Exception:
            continue
        n = len(prs.slides)
        for i, s in enumerate(prs.slides, 1):
            for sh in s.shapes:
                if not sh.has_text_frame:
                    continue
                for pa in sh.text_frame.paragraphs:
                    for r in pa.runs:
                        m = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", r.text)
                        if m and (int(m.group(1)) != i or int(m.group(2)) != n):
                            bad.append((rel(p), i, r.text, n))
    return not bad, f"页脚编号异常 {len(bad)} 处", ""


def check_shots():
    from pptx import Presentation
    stat = {}
    for p in sorted(pptx_files()):
        try:
            prs = Presentation(p)
        except Exception:
            continue
        hit = "无"
        for s in prs.slides:
            t = "".join(r.text for sh in s.shapes if sh.has_text_frame
                        for pa in sh.text_frame.paragraphs for r in pa.runs)
            if "工单完成效果图" in t or "完成后长这样" in t:
                hit = "效果图"
            elif "课堂实况与运行截图" in t and "教师课后替换" in t:
                hit = "占位"
        stat.setdefault(hit, 0)
        stat[hit] += 1
    ok = stat.get("占位", 0) == 0
    return ok, f"效果图 {stat.get('效果图', 0)} 册 / 空白占位 {stat.get('占位', 0)} 册 / 无 {stat.get('无', 0)} 册", ""


def check_code():
    import ast
    syn, todo, lines = [], 0, 0
    pats = {
        "pymodbus位置参数": r"ModbusTcpClient\(\s*[a-zA-Z_]+\s*,\s*[a-zA-Z_]+\s*\)",
        "ndarray.ptp()": r"\.ptp\(\)",
        "np.float_/np.bool_": r"np\.(float_|bool_|int_|object_)\b",
        "np.NaN/np.Inf": r"np\.(NaN|Inf)\b",
        "numpy固定宽度字符串截断": r"np\.array\(\[[\"'][^\"']{1,4}[\"']\]\s*\*\s*\w+\)",
    }
    drift = {k: [] for k in pats}
    for p in py_files():
        try:
            src = open(p, encoding="utf-8").read()
        except Exception:
            continue
        lines += src.count("\n")
        todo += len(re.findall(r"TODO", src))
        try:
            ast.parse(src)
        except SyntaxError as e:
            syn.append((rel(p), e.lineno))
        # 逐行扫描并跳过注释行（避免"说明避坑"的注释被误判为真实用法）
        for ln, line in enumerate(src.splitlines(), 1):
            s = line.strip()
            if s.startswith("#"):
                continue
            code = line.split("#")[0] if "#" in line else line
            for k, pat in pats.items():
                if re.search(pat, code):
                    drift[k].append(f"{rel(p)}:{ln}")
    drift = {k: v for k, v in drift.items() if v}
    ok = not syn and not drift
    detail = f"{len(py_files())} 文件 / {lines} 行 / TODO {todo}"
    if drift:
        detail += "  ⚠ " + "; ".join(f"{k}×{len(v)}" for k, v in drift.items())
    return ok, f"语法错误 {len(syn)} · API漂移 {len(drift)} 类", detail


def check_locks():
    missing = [d for d in ["01-AI应用基础", "02-程序设计基础",
                           "03-Python程序设计-项目实战", "05-AI应用基础48课时版"]
               if not os.path.exists(os.path.join(ROOT, d, "requirements.lock"))]
    return not missing, f"缺失锁定文件 {len(missing)} 个", ", ".join(missing)


def check_root_clean():
    junk = [f for f in os.listdir(ROOT)
            if re.search(r"\.(csv|db|log|joblib|txt)$", f)]
    return not junk, f"根目录散落产物 {len(junk)} 个", ", ".join(junk[:6])


def check_readme_index():
    """各包 README 与总索引存在性"""
    need = ["00-资源库总索引.md"] + [f"{d}/README.md" for d in
                               ["01-AI应用基础", "02-程序设计基础",
                                "03-Python程序设计-项目实战", "05-AI应用基础48课时版"]]
    miss = [n for n in need if not os.path.exists(os.path.join(ROOT, n))]
    return not miss, f"缺失索引/README {len(miss)} 个", ", ".join(miss)


def check_parity():
    """三形态（starter / 教师参考 / 工程化项目）同源性"""
    script = os.path.join(ROOT, "_docx_work", "eng", "check_parity.py")
    if not os.path.exists(script):
        return False, "校验脚本缺失", script
    import subprocess
    r = subprocess.run([sys.executable, script, "--json"], capture_output=True, timeout=300)
    try:
        data = json.loads((r.stdout or b"{}").decode("utf-8", "ignore"))
    except Exception:
        return False, "校验输出解析失败", (r.stderr or b"").decode("utf-8", "ignore")[:120]
    total = data.get("total", 0)
    passed = data.get("passed", 0)
    bad = [x["id"] for x in data.get("rows", []) if not x.get("passed")]
    return (passed == total and total >= 40), f"三形态同源 {passed}/{total}", ", ".join(bad[:6])


def check_eng_lock():
    """工程化项目 requirements.txt 已锁定精确版本（无未替换占位符）"""
    bad = []
    n = 0
    for p in glob.glob(os.path.join(ROOT, "*", "工程化项目", "*", "requirements.txt")):
        n += 1
        try:
            t = open(p, encoding="utf-8").read()
        except Exception:
            bad.append(os.path.relpath(p, ROOT))
            continue
        if "<req_lines>" in t or "<title>" in t:
            bad.append(os.path.relpath(p, ROOT))
    return (not bad and n >= 40), f"工程化依赖锁定 {n - len(bad)}/{n}", ", ".join(bad[:4])


CHECKS = [
    ("PPT页数合规(≤80)", check_ppt_pages),
    ("PPT页脚编号", check_ppt_footers),
    ("工单完成效果图覆盖", check_shots),
    ("代码语法与API漂移", check_code),
    ("依赖锁定文件", check_locks),
    ("根目录整洁", check_root_clean),
    ("索引与README", check_readme_index),
    ("三形态同源(40工单)", check_parity),
    ("工程化依赖锁定", check_eng_lock),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    results = []
    allok = True
    for name, fn in CHECKS:
        try:
            ok, summary, detail = fn()
        except Exception as e:
            ok, summary, detail = False, f"检查异常: {type(e).__name__}: {e}", ""
        allok &= ok
        results.append(dict(name=name, ok=ok, summary=summary, detail=detail))
    if a.json:
        print(json.dumps(dict(all_ok=allok, results=results), ensure_ascii=False, indent=1))
    else:
        print("=" * 74)
        print("教学资源库 · 全量自检报告（73号轮）")
        print("=" * 74)
        for r in results:
            print(f"  [{'PASS' if r['ok'] else 'FAIL'}] {r['name']:<22} {r['summary']}")
            if r["detail"]:
                print(f"         {r['detail']}")
        print("=" * 74)
        print("总结论:", "全部通过 ✔" if allok else "存在失败项 ✘")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
