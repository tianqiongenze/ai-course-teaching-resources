# -*- coding: utf-8 -*-
"""76号轮·specs 最后 2 处 E128 修复（续行对齐到视觉缩进 28 列）"""
import ast
import os

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
SP26 = " " * 26
SP28 = " " * 28


def patch(fn, old, new, label):
    s = open(fn, encoding="utf-8").read()
    if old not in s:
        print("  [MISS]", fn, label)
        return
    s = s.replace(old, new, 1)
    ast.parse(s)
    open(fn, "w", encoding="utf-8", newline="\n").write(s)
    print("  [OK]", fn, label)


# w02_alarm_engine：结论与建议 两行续行 26→28
patch("specs_02.py",
      '                ("结论与建议", ["紧急级告警必须立即停机并回填工单；"' + chr(10)
      + SP26 + '"去重抑制 %d 条属预期行为（防刷屏）"' + chr(10)
      + SP26 + '% (len(out) - len(fired))])]',
      '                ("结论与建议", ["紧急级告警必须立即停机并回填工单；"' + chr(10)
      + SP28 + '"去重抑制 %d 条属预期行为（防刷屏）"' + chr(10)
      + SP28 + '% (len(out) - len(fired))])]',
      "w02 续行 26→28")

# w12_capstone：流水线产物 三行续行 26→28
patch("specs_02.py",
      '                ("流水线产物", ["① clean_data.csv（清洗后数据集）",' + chr(10)
      + SP26 + '"② quarantine.json（隔离区 %d 条）" % len(quarantine),' + chr(10)
      + SP26 + '"③ result.json（含分级与词频）", "④ report.txt（本报告）"]),',
      '                ("流水线产物", ["① clean_data.csv（清洗后数据集）",' + chr(10)
      + SP28 + '"② quarantine.json（隔离区 %d 条）" % len(quarantine),' + chr(10)
      + SP28 + '"③ result.json（含分级与词频）", "④ report.txt（本报告）"]),',
      "w12 续行 26→28")

print("完成")
