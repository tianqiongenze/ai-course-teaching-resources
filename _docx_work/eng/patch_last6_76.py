# -*- coding: utf-8 -*-
"""76号轮·最后 6 处 E127 修复"""
import os

ROOT = r"D:/Python编程实战/教学实施资料"
os.chdir(ROOT)


def patch(path, old, new, label):
    s = open(path, encoding="utf-8").read()
    if old not in s:
        print("  [MISS]", label)
        return
    open(path, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
    print("  [OK]", label)


# ① m42_starter：lambda 合为一行
patch("01-AI应用基础/学生代码框架/m42_starter.py",
      '            "阈值判定": Tool("阈值判定",\n'
      '                         lambda v: "超标,须停机检查" if float(v) > 4.5\n'
      '                                                       else "正常范围"),',
      '            "阈值判定": Tool("阈值判定", lambda v: "超标,须停机检查" if float(v) > 4.5 else "正常范围"),',
      "m42_starter lambda 合行")

# ② generate_data.py：TEMPLATES 续行统一对齐到 14 列
s = open("01-AI应用基础/数据与工具/generate_data.py", encoding="utf-8").read()
lines = s.split("\n")
out = []
in_tpl = False
for l in lines:
    if l.startswith("TEMPLATES = {"):
        in_tpl = True
    elif in_tpl and l.startswith("}"):
        in_tpl = False
    if in_tpl and l.strip().startswith('"{dev}'):
        out.append(" " * 14 + l.strip())
    else:
        out.append(l)
new = "\n".join(out)
if new != s:
    open("01-AI应用基础/数据与工具/generate_data.py", "w",
         encoding="utf-8", newline="\n").write(new)
    print("  [OK] generate_data TEMPLATES 对齐")
else:
    print("  [MISS] generate_data 未变")
print("完成")
