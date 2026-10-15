# -*- coding: utf-8 -*-
"""76号轮·收尾修复（check_env E501/E305 + teacher E131/E262/E731）"""
import os
import re

ROOT = r"D:/Python编程实战/教学实施资料"
os.chdir(ROOT)


def patch(path, old, new, label):
    s = open(path, encoding="utf-8").read()
    if old not in s:
        print("  [MISS]", label)
        return
    open(path, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
    print("  [OK]", label)


# ① check_env.py：三条超长 check 拆行
p = "03-Python程序设计-项目实战/check_env.py"
patch(p,
      'check("Python≥3.12", True, lambda: (__import__("sys").version_info >= (3, 12) and "v%d.%d" % sys.version_info[:2]) or (_ for _ in ()).throw(RuntimeError(sys.version.split()[0])))',
      'def _py_ver():\n'
      '    if sys.version_info >= (3, 12):\n'
      '        return "v%d.%d" % sys.version_info[:2]\n'
      '    raise RuntimeError(sys.version.split()[0])\n'
      '\n'
      '\n'
      'check("Python≥3.12", True, _py_ver)',
      "check_env Python 版本检查拆行")

patch(p,
      'check("Git", True, lambda: __import__("subprocess").run(["git", "--version"], capture_output=True, text=True).stdout.strip())',
      'check("Git", True, lambda: __import__("subprocess").run(\n'
      '    ["git", "--version"], capture_output=True, text=True).stdout.strip())',
      "check_env Git 检查拆行")

patch(p,
      'check("conda环境(需先conda activate pp03)", True, lambda: ("conda" in sys.executable or "envs" in sys.executable) or (_ for _ in ()).throw(RuntimeError(f"当前Python路径不含conda/envs: {sys.executable}（需conda activate pp03后再运行）")))',
      'def _conda_ok():\n'
      '    if "conda" in sys.executable or "envs" in sys.executable:\n'
      '        return True\n'
      '    raise RuntimeError(\n'
      '        "当前Python路径不含 conda/envs: %s（需 conda activate pp03 后再运行）" % sys.executable)\n'
      '\n'
      '\n'
      'check("conda环境(需先conda activate pp03)", True, _conda_ok)',
      "check_env conda 检查拆行")

# ② check_env.py：check_p7() 前 2 空行
patch(p, '\n\ncheck_p7()', '\n\n\ncheck_p7()', "check_env E305 空行")

# ③ teacher：E131 悬挂缩进（两处同型）
for f in ("05-AI应用基础48课时版/教师参考/solutions.py",
          "05-AI应用基础48课时版/教师参考/solutions_multi_ai48.py"):
    patch(f,
          '        "示例": "示例：输入\'电机异响发热\'→输出\'建议：检查轴承润滑\'。"\n'
          '            "现在：泵振动8Hz/16Hz特征频率抬升，请按示例格式给处置建议。",',
          '        "示例": "示例：输入\'电机异响发热\'→输出\'建议：检查轴承润滑\'。"\n'
          '                "现在：泵振动8Hz/16Hz特征频率抬升，请按示例格式给处置建议。",',
          "E131 %s" % f.split("/")[-1])

# ④ multi_ai48：E262 注释空格归一
patch("05-AI应用基础48课时版/教师参考/solutions_multi_ai48.py",
      "        #  线性detrend去不掉局部斜坡)",
      "        # 线性 detrend 去不掉局部斜坡)",
      "E262 注释空格")

# ⑤ multi_ai48：E731 lambda → def
patch("05-AI应用基础48课时版/教师参考/solutions_multi_ai48.py",
      "        label = lambda X: (X[:, 0] > 0).astype(int)          # 规律藏在第0维\n"
      "        return big, small, test, label(small), label(test)",
      "        def label(X):                                        # 规律藏在第0维\n"
      "            return (X[:, 0] > 0).astype(int)\n"
      "\n"
      "        return big, small, test, label(small), label(test)",
      "E731 lambda→def")
print("完成")
