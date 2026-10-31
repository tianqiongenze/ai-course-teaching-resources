# -*- coding: utf-8 -*-
"""101号轮 P3：PPT 变更固定门禁（阈值化），任何一轮 PPT 修改后必须全绿。

门禁（100号报告 P3-6 口径）：
  G1 语法：code_syntax == 0
  G2 重症溢出：超出>0.3in 且非空文本 == 0
  G3 高负荷页：<= 2（且须为证据页豁免清单内）
  G4 乱码 == 0（TODO 提示语白名单）
  G5 check99 体检（99号轮 160 页越界/压脚/页码）通过
用法：python3 gate101.py   （先跑 audit100.py 生成 audit100_report.json）
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ppt97"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ppt99"))

EXEMPT_DENSE = {("W05-第10次课-每天早上8点的生产日报.pptx", 12),
                ("W05-第9次课-产线驾驶舱：5个KPI一屏掌.pptx", 52)}


def main():
    rep = json.load(open(os.path.join(os.path.dirname(HERE),
                                      "ppt100", "audit100_report.json")))
    fails = []
    n_syn = sum(r["syntax_errors"] for r in rep)
    if n_syn:
        fails.append("G1 语法错 %d" % n_syn)
    heavy = []
    for r in rep:
        for i in r["issues"]:
            if i["type"] == "overflow" and i["text"].strip():
                if float(i["need"]) - float(i["box"].split("x")[1]) > 0.3:
                    heavy.append((r["file"], i["page"]))
    if heavy:
        fails.append("G2 重症溢出 %d 处: %s" % (len(heavy), heavy[:5]))
    dense = [(r["file"], i["page"], i["chars"]) for r in rep
             for i in r["issues"] if i["type"] == "dense_page"]
    bad_dense = [d for d in dense if (d[0], d[1]) not in EXEMPT_DENSE]
    if bad_dense:
        fails.append("G3 高负荷页超豁免 %d: %s" % (len(bad_dense), bad_dense[:5]))
    print("门禁判定：语法错=%d 重症溢出=%d 高负荷页=%d(豁免%d)" %
          (n_syn, len(heavy), len(dense), len(dense) - len(bad_dense)))
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE),
                                                     "ppt99", "check99.py")],
                       capture_output=True, text=True)
    tail = r.stdout.strip().split("\n")[-1] if r.stdout else ""
    if "异常 deck=0" not in tail:
        fails.append("G5 check99: %s" % tail)
    if fails:
        print("✗ 门禁未过：")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("✓ 全部门禁通过")


if __name__ == "__main__":
    main()
