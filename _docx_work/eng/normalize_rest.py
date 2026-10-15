# -*- coding: utf-8 -*-
"""76号轮·非 eng 区域最终规范化（autopep8 安全集 + 续行修复）"""
import glob
import os
import subprocess

PY = r"C:/Users/Lenovo/AppData/Local/Temp/audit/env314/Scripts/python.exe"
ROOT = r"D:/Python编程实战/教学实施资料"

os.chdir(ROOT)
files = [f for f in glob.glob("**/*.py", recursive=True)
         if "_docx_work" not in f and "__pycache__" not in f
         and "工程化项目" not in f and "site-packages" not in f]
print("非 eng 文件: %d" % len(files))

CODES = "E1,E2,E3,E4,E5,E7,W2,W3"
for i in range(0, len(files), 40):
    subprocess.run([PY, "-m", "autopep8", "--in-place", "--max-line-length=120",
                    "--select", CODES, "--aggressive"] + files[i:i + 40],
                   capture_output=True, text=True)
print("autopep8 完成")

# 复检
r = subprocess.run([PY, "-m", "flake8", "--max-line-length=120"] + files,
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
left = [l for l in r.stdout.splitlines() if l.strip()]
print("剩余: %d" % len(left))
for l in left[:20]:
    print("   ", l[:110])
