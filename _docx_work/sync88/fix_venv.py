# -*- coding: utf-8 -*-
"""88：清除 venv/虚拟环境 表述，统一为 Anaconda（conda）环境。

范围：03 源包 + 目标目录 2025级/《Python程序设计》
（02 源包与 2026级/《程序设计基础》经扫描为 0 处，无需处理）
"""
import glob
import os
import sys

import docx
from pptx import Presentation

SRC = r"D:/Python编程实战/教学实施资料/03-Python程序设计-项目实战"
TGT = r"D:/工业互联网应用2026~2027第一学期（前八周）/2025级/《Python程序设计》"

# 长串优先（避免二次替换）
RULES = [
    ("venv/conda沙箱", "conda环境沙箱"),
    ("venv虚拟环境与requirements.txt依赖管理", "conda环境与requirements.txt依赖管理"),
    ("venv虚拟环境", "conda环境"),
    ("虚拟环境（venv）与依赖管理", "conda环境与依赖管理"),
    ("虚拟环境（venv）", "conda环境"),
    ("venv为什么必须.gitignore", "conda环境为什么不必进.gitignore"),
    ("1. venv/与__pycache__必须进.gitignore", "1. __pycache__必须进.gitignore（conda环境在Anaconda目录，无需提交）"),
    ("venv/与__pycache__必须进.gitignore", "__pycache__必须进.gitignore（conda环境在Anaconda目录）"),
    ("交付标准工程模板（venv+Git+目录规范）", "交付标准工程模板（conda环境+Git+目录规范）"),
    ("venv+requirements+首次规范commit", "conda环境+requirements+首次规范commit"),
    ("venv可用+仓库+结构完整", "conda环境可用+仓库+结构完整"),
    ("venv沙箱隔离", "conda环境隔离"),
    ("venv+requirements", "conda环境+requirements"),
    ("venv+Git+目录规范", "conda环境+Git+目录规范"),
    ("venv被提交", "环境目录被提交"),
    ("加venv/与__pycache__/", "加__pycache__/（conda环境在Anaconda目录）"),
    ("没激活venv", "没激活conda环境"),
    ("看终端前缀(venv)", "看终端前缀(环境名)"),
    ("虚拟环境=每台机器各配工具箱", "conda环境=每台机器各配工具箱"),
    ("虚拟环境的作用理解（隔离与可复现）", "conda环境的作用理解（隔离与可复现）"),
    ("虚拟环境作用的理解（隔离与可复现）", "conda环境作用的理解（隔离与可复现）"),
    ("PEP 8、Git工作流、虚拟环境、单元测试", "PEP 8、Git工作流、conda环境、单元测试"),
    ("PEP 8、venv、Git、项目结构、pytest", "PEP 8、conda环境、Git、项目结构、pytest"),
    ("学生首次接触Git与虚拟环境", "学生首次接触Git与conda环境"),
    ("2. 虚拟环境（venv）与依赖管理", "2. conda环境与依赖管理"),
    ("掌握venv虚拟环境", "掌握conda环境"),
    ("venv与依赖管理流程", "conda环境与依赖管理流程"),
    ("精讲演示venv创建", "精讲演示conda环境创建"),
    ("C类完成venv与基本提交", "C类完成conda环境与基本提交"),
    ("（venv环境，基于P1.2模板）", "（conda环境，基于P1.2模板）"),
    ("B02 venv/conda沙箱", "B02 conda环境沙箱"),
    ("2. venv沙箱隔离；requirements.txt冻结", "2. conda环境隔离；requirements.txt冻结"),
    ("venv环境", "conda环境"),
    ("venv沙箱", "conda环境沙箱"),
    ("venv", "conda环境"),
    ("虚拟环境", "conda环境"),
]


def apply_rules(text):
    n = 0
    for old, new in RULES:
        if old in text:
            n += text.count(old)
            text = text.replace(old, new)
    return text, n


def fix_para_runs(par):
    """段落级替换（run 级优先，跨 run 合并）。"""
    total = 0
    for old, new in RULES:
        done = False
        for r in par.runs:
            if old in r.text:
                r.text = r.text.replace(old, new)
                total += 1
                done = True
        if done:
            continue
        if old in par.text and par.runs:
            par.runs[0].text = par.text.replace(old, new)
            for r in par.runs[1:]:
                r.text = ""
            total += 1
    return total


def fix_docx(f):
    d = docx.Document(f)
    n = 0
    for par in d.paragraphs:
        n += fix_para_runs(par)
    for t in d.tables:
        for row in t.rows:
            seen = set()
            for c in row.cells:
                k = id(c._tc)
                if k in seen:
                    continue
                seen.add(k)
                for par in c.paragraphs:
                    n += fix_para_runs(par)
    return d, n


def fix_pptx(f):
    prs = Presentation(f)
    n = 0
    for s in prs.slides:
        for sh in s.shapes:
            if not sh.has_text_frame:
                continue
            for par in sh.text_frame.paragraphs:
                n += fix_para_runs(par)
    return prs, n


def main():
    apply = "--apply" in sys.argv
    jobs = [
        ("源包03", SRC, ["LS3.3*.docx", "*授课计划表*.docx", "*课程标准*.docx",
                        "分层工单/*.docx", "V2授课PPT/*.pptx",
                        "Python工程化实践指南*.docx", "期末工业级项目册*.docx"]),
        ("目标2025级", TGT, ["*教学设计/*.docx", "*授课计划/*.docx", "*课程标准/*.docx",
                          "*任务单/*.docx", "*教学PPT/*.pptx"]),
    ]
    grand = 0
    failed = []
    for label, base, pats in jobs:
        print("\n### %s" % label)
        files = []
        for pat in pats:
            files += glob.glob(os.path.join(base, pat))
        files = sorted({f for f in files if not os.path.basename(f).startswith("~$")})
        for f in files:
            try:
                if f.endswith(".docx"):
                    obj, n = fix_docx(f)
                else:
                    obj, n = fix_pptx(f)
            except Exception as e:
                print("  [SKIP] %s: %s" % (os.path.basename(f)[:34], str(e)[:40]))
                continue
            if n:
                if apply:
                    try:
                        obj.save(f)
                    except PermissionError:
                        print("  [占用] %-46s %d 处（稍后重试）" % (os.path.basename(f)[:46], n))
                        failed.append(f)
                        continue
                print("  %-52s %d 处" % (os.path.basename(f)[:52], n))
                grand += n
    print("\n合计 %d 处；%s" % (grand, "已写入" if apply else "空跑"))


if __name__ == "__main__":
    main()
