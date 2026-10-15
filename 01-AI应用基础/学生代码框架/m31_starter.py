# -*- coding: utf-8 -*-
# [教学脚手架] 下列导入/变量供 TODO 完成后使用，故标注 noqa 而非删除
"""M3.1 产品表面缺陷尺寸测量 —— 学生代码框架
像素当量: 0.1 mm/px (已标定)
"""
import glob

import cv2
import numpy as np  # noqa: F401

PX_TO_MM = 0.1
PARTS = sorted(glob.glob("data/surface_parts/part_*.png"))


def measure(path):
    """返回 标注图, [(类型, 尺寸mm)]"""
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    # TODO-1 预处理: 高斯模糊(5×5) → 阈值分割(先试100, 再试Otsu) → 开运算去噪点
    # === 你的代码 ===
    # binary = ...

    # TODO-2 轮廓: cv2.findContours(binary, cv2.RETR_EXTERNAL, ...)
    # contours, _ = ...
    contours = []          # TODO-2 完成后替换本行（占位空列表，保证骨架可运行）

    results = []
    anno = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    for cnt in contours:
        if cv2.contourArea(cnt) < 15:      # 过滤噪声小轮廓
            continue
        # TODO-3 判型: 最小外接矩形长宽比>3→划痕(长度=长边), 否则→凹坑(面积)
        # 提示: rect = cv2.minAreaRect(cnt); w,h = rect[1]; 角度用boxPoints画框
        # === 你的代码 ===
        # TODO-4 换算: 长度mm = 长边px * PX_TO_MM
        #              面积mm² = contourArea * PX_TO_MM ** 2   (注意平方!)
        # TODO-5 标注: cv2.drawContours + cv2.putText(类型+尺寸)
    return anno, results


def main():
    for p in PARTS[:5]:
        anno, res = measure(p)
        out = "result_" + p.split("/")[-1]
        cv2.imwrite(out, anno)
        print(out, "→", res)

    # TODO-6 决策矩阵: 全局100 / Otsu / 自适应 三种阈值各测5件, 记录检出与误检


if __name__ == "__main__":
    main()
