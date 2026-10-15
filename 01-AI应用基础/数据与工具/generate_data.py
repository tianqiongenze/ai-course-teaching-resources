# -*- coding: utf-8 -*-
"""
《AI应用基础》课程本地数据一键生成器（离线机房可用）
用法:
    python generate_data.py all       # 生成全部数据
    python generate_data.py m1        # M1 泵类设备故障数据
    python generate_data.py m2img     # M2.1 焊接缺陷图像(CNN)
    python generate_data.py m2rul     # M2.2 轴承剩余寿命序列(LSTM)
    python generate_data.py m3        # M3.1 产品表面缺陷图像(测量)
    python generate_data.py m3yolo    # M3.2 YOLO检测图像+标注
    python generate_data.py m4        # M4.1 故障报告语料
    python generate_data.py m4kb      # M4.2 工业知识库(RAG)
输出目录: ./data/
"""
import json
import os
import random
import sys

import numpy as np

random.seed(42)
np.random.seed(42)
OUT = "data"


def _mkdir(p):
    os.makedirs(p, exist_ok=True)


# ----------------------------------------------------------------------
# M1/M1.2 泵类设备故障诊断数据
# ----------------------------------------------------------------------
def gen_m1(n_per_class=150):
    """三类状态: 0无故障 1轴承磨损 2叶轮堵塞
    特征: 转速rpm 温度temp 压力pressure 振动vib 电流amp
    规则: 故障体现在振动/温度/压力分布漂移, 与真实故障物理一致"""
    rows, labels = [], []
    for i in range(n_per_class):
        rpm = random.uniform(1450, 1550)
        rows.append([rpm, random.uniform(45, 60), random.uniform(0.40, 0.50),
                     random.uniform(1.0, 2.0), random.uniform(9.5, 10.5)])
        labels.append(0)
    for i in range(n_per_class):
        rpm = random.uniform(1450, 1550)
        rows.append([rpm, random.uniform(60, 78), random.uniform(0.38, 0.48),
                     random.uniform(3.5, 6.5), random.uniform(10.5, 12.5)])
        labels.append(1)
    for i in range(n_per_class):
        rpm = random.uniform(1450, 1550)
        rows.append([rpm, random.uniform(50, 65), random.uniform(0.20, 0.34),
                     random.uniform(2.5, 4.5), random.uniform(12.5, 15.5)])
        labels.append(2)
    X = np.array(rows)
    # 引入少量噪声样本(模拟现场脏数据, 供M1.2清洗)
    bad = np.random.randint(0, len(X), size=8)
    X[bad] += np.random.uniform(-8, 8, size=(8, 5))
    idx = np.random.permutation(len(X))
    X, y = X[idx], np.array(labels)[idx]
    _mkdir(OUT)
    with open(os.path.join(OUT, "pump_fault.csv"), "w", encoding="utf-8") as f:
        f.write("rpm,temp_c,pressure_mpa,vibration_mm_s,current_a,label\n")
        for row, lab in zip(X, y):
            f.write(",".join(f"{v:.3f}" for v in row) + f",{lab}\n")
    print("M1 ->", os.path.join(OUT, "pump_fault.csv"), X.shape)


# ----------------------------------------------------------------------
# M2.1 焊接缺陷图像 (64x64灰度, 4类, 纯numpy生成, CPU训练tiny-CNN约2分钟)
# ----------------------------------------------------------------------
CLASSES_M21 = ["normal", "porosity", "slag", "crack"]


def _weld_img(cls_id):
    img = 120 + np.random.normal(0, 6, (64, 64))          # 母材背景
    img[26:38, :] += 60 + np.random.normal(0, 5, (12, 64))  # 焊缝条带
    if cls_id == 1:      # 气孔: 亮斑群
        for _ in range(random.randint(4, 8)):
            y, x = random.randint(28, 36), random.randint(5, 58)
            r = random.randint(1, 3)
            yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
            img[y - r:y + r + 1, x - r:x + r + 1] -= 150 * (xx ** 2 + yy ** 2 <= r ** 2)
    elif cls_id == 2:    # 夹渣: 暗色不规则块
        for _ in range(random.randint(2, 4)):
            y, x = random.randint(28, 36), random.randint(8, 54)
            img[y:y + random.randint(3, 6), x:x + random.randint(6, 14)] -= 130
    elif cls_id == 3:    # 裂纹: 细长暗线
        x0 = random.randint(6, 20)
        y = random.randint(30, 35)
        for x in range(x0, min(64, x0 + random.randint(25, 40))):
            img[min(63, y + int(np.sin(x / 5) * 2)) - 1:min(63, y + int(np.sin(x / 5) * 2)) + 2, x] -= 170
    return np.clip(img, 0, 255).astype(np.uint8)


def gen_m2img(n_per_class=60):
    d = os.path.join(OUT, "weld_images")
    for c in CLASSES_M21:
        _mkdir(os.path.join(d, c))
    meta = []
    for ci, c in enumerate(CLASSES_M21):
        for i in range(n_per_class):
            arr = _weld_img(ci)
            name = f"{c}_{i:03d}.npy"
            np.save(os.path.join(d, c, name), arr)
            meta.append({"file": f"{c}/{name}", "label": c})
    with open(os.path.join(d, "index.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print("M2.1 ->", d, len(meta), "张")


# ----------------------------------------------------------------------
# M2.2 轴承剩余寿命(RUL)时间序列
# ----------------------------------------------------------------------
def gen_m2rul(n_units=30, length=200):
    """每台设备: 振动均值随退化进程上升(健康→失效), RUL标签=剩余步数/length"""
    X, y = [], []
    for u in range(n_units):
        base = np.random.uniform(0.8, 1.2)
        wear = np.linspace(0, 1, length) ** 1.6
        series = base + 2.2 * wear + np.random.normal(0, 0.12, length)
        series += np.array([0.15 * np.sin(i / 17 + u) for i in range(length)])
        w = 20
        for t in range(w, length):
            X.append(series[t - w:t])
            y.append(1.0 - (t - w) / (length - w - 1))   # RUL归一化1→0
    X, y = np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)
    np.savez(os.path.join(OUT, "bearing_rul.npz"), X=X, y=y)
    print("M2.2 ->", os.path.join(OUT, "bearing_rul.npz"), X.shape)


# ----------------------------------------------------------------------
# M3.1 产品表面缺陷图像(测量任务, 像素当量0.1mm/px)
# ----------------------------------------------------------------------
def gen_m3(n=40):
    d = os.path.join(OUT, "surface_parts")
    _mkdir(d)
    truth = []
    for i in range(n):
        img = np.full((240, 320), 200, dtype=np.uint8)
        # 随机划痕(细长)或凹坑(圆斑)
        if random.random() < 0.5:
            y0, x0 = random.randint(60, 180), random.randint(40, 160)
            ln, ang = random.randint(40, 120), random.uniform(0, np.pi)
            dx, dy = int(np.cos(ang) * ln), int(np.sin(ang) * ln)
            for s in np.linspace(0, 1, ln):
                yy = int(y0 + dy * s)
                xx = int(x0 + dx * s)
                img[yy - 1:yy + 2, xx - 1:xx + 2] = 60
            truth.append({"file": f"part_{i:03d}.png", "type": "scratch",
                          "length_mm": round(ln * 0.1, 2)})
        else:
            cy, cx = random.randint(80, 160), random.randint(80, 240)
            r = random.randint(6, 18)
            yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
            img[cy - r:cy + r + 1, cx - r:cx + r + 1][xx ** 2 + yy ** 2 <= r ** 2] = 60
            truth.append({"file": f"part_{i:03d}.png", "type": "pit",
                          "area_mm2": round(np.pi * (r * 0.1) ** 2, 2)})
        try:
            from PIL import Image
            Image.fromarray(img).save(os.path.join(d, f"part_{i:03d}.png"))
        except ImportError:                       # 无Pillow时以npy兜底
            np.save(os.path.join(d, f"part_{i:03d}.npy"), img)
    with open(os.path.join(d, "ground_truth.json"), "w", encoding="utf-8") as f:
        json.dump(truth, f, ensure_ascii=False, indent=1)
    print("M3.1 ->", d, n, "件(ground_truth.json为教师核对用, 勿下发)")


# ----------------------------------------------------------------------
# M3.2 YOLO检测图像 + YOLO格式标注(3类缺陷)
# ----------------------------------------------------------------------
def gen_m3yolo(n=60):
    d = os.path.join(OUT, "yolo_dataset")
    img_d, lbl_d = os.path.join(d, "images"), os.path.join(d, "labels")
    _mkdir(img_d)
    _mkdir(lbl_d)
    classes = ["dent", "stain", "edge_crack"]
    for i in range(n):
        img = np.full((320, 320, 3), 190, dtype=np.uint8)
        img += np.random.normal(0, 10, img.shape).astype(np.uint8)
        # 模拟产品轮廓
        img[40:280, 40:280] = 150
        lines = []
        for _ in range(random.randint(1, 3)):
            c = random.choice(classes)
            cx, cy = random.uniform(0.2, 0.8), random.uniform(0.2, 0.8)
            w, h = random.uniform(0.08, 0.25), random.uniform(0.08, 0.25)
            x0, y0 = int(cx * 320 - w * 160), int(cy * 320 - h * 160)
            x1, y1 = int(cx * 320 + w * 160), int(cy * 320 + h * 160)
            if c == "dent":
                img[y0:y1, x0:x1] = 110
            elif c == "stain":
                img[y0:y1, x0:x1, 1] = 140
            else:
                img[y0:y0 + 4, x0:x1] = 70
            lines.append(f"{classes.index(c)} {cx:.4f} {cy:.4f} {w:.4f} {h:.4f}")
        np.save(os.path.join(img_d, f"img_{i:03d}.npy"), img)
        with open(os.path.join(lbl_d, f"img_{i:03d}.txt"), "w") as f:
            f.write("\n".join(lines))
    with open(os.path.join(d, "classes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(classes))
    print("M3.2 ->", d, n, "张+标注")


# ----------------------------------------------------------------------
# M4.1 工业故障报告语料(5类, ≥200条)
# ----------------------------------------------------------------------
TEMPLATES = {
    "传动系统": ["{dev}皮带打滑异响，{pos}温度偏高", "{dev}减速机振动剧烈伴随杂音",
             "{dev}联轴器对中不良，轴承座发热", "{dev}齿轮箱磨损，铁屑超标",
             "{dev}链条松动跳齿，张紧力不足"],
    "冷却系统": ["{dev}冷却水流量不足，{pos}温差增大", "{dev}冷却塔风机停转，水温告警",
             "{dev}换热器结垢，换热效率下降", "{dev}冷却泵机械密封泄漏",
             "{dev}冷媒压力异常，压缩机频繁启停"],
    "电气系统": ["{dev}变频器过流报警，{pos}电流波动大", "{dev}接触器触点烧蚀，相序异常",
             "{dev}PLC通信中断，从站掉线", "{dev}电缆绝缘老化，接地故障",
             "{dev}断路器误跳闸，负载短路保护动作"],
    "液压系统": ["{dev}油泵压力不足，{pos}上升缓慢", "{dev}液压油污染度超标，滤芯堵塞",
             "{dev}电磁阀卡滞，换向失灵", "{dev}油缸内泄，保压不住",
             "{dev}油温过高，冷却回路失效"],
    "仪表气动": ["{dev}温度变送器读数漂移，{pos}偏差超限", "{dev}压力表指针卡死",
             "{dev}气动调节阀振荡，定位器故障", "{dev}液位计虚假液位，泡沫干扰",
             "{dev}流量计累积量跳变，接地干扰"],
}
DEVS = ["1号注塑机", "3号数控车床", "空压机B", "冷却水泵2", "AGV充电站",
        "5号压铸机", "辊道输送线", "包装机A", "中央冷水机组", "行车2"]
POSS = ["驱动端", "非驱动端", "主回路", "控制柜", "回油口", "出口管线"]


def gen_m4(n_per_class=45):
    rows = []
    for label, tmpls in TEMPLATES.items():
        for i in range(n_per_class):
            t = random.choice(tmpls)
            text = t.format(dev=random.choice(DEVS), pos=random.choice(POSS))
            noise = random.choice(["，请尽快处理", "，影响生产节拍", "，已挂牌停机", "，班中巡检发现", ""])
            rows.append((text + noise, label))
    random.shuffle(rows)
    with open(os.path.join(OUT, "fault_reports.csv"), "w", encoding="utf-8") as f:
        f.write("text,label\n")
        for text, label in rows:
            f.write(f'"{text}","{label}"\n')
    print("M4.1 ->", os.path.join(OUT, "fault_reports.csv"), len(rows), "条")


# ----------------------------------------------------------------------
# M4.2 工业知识库(RAG用, JSON)
# ----------------------------------------------------------------------
KB = {
    "设备运维规范": [
        "泵类设备振动速度有效值超过4.5mm/s应列入重点关注，超过7.1mm/s必须停机检查。",
        "轴承温度报警阈值设定为75℃，达到85℃应立即停机并检查润滑与冷却回路。",
        "变频器过流报警时，应先检查负载卡滞与加减速时间设置，再检查电流检测板。",
        "液压油污染度NAS等级超过9级必须更换滤芯并排查污染源。",
        "PLC从站通信中断时，按'检查物理链路→查终端电阻→查从站电源→重启主站'顺序排查。",
    ],
    "故障排查指南": [
        "泵体异响且压力波动：优先排查叶轮堵塞与汽蚀，检查进口滤网和液位。",
        "电机电流偏高而转速正常：排查机械过载、轴承磨损与三相不平衡。",
        "冷却水温持续偏高：检查冷却塔填料、风机转向与喷头堵塞情况。",
        "气动阀动作迟缓：检查气源压力（应≥0.4MPa）、滤杯积水与定位器反馈杆。",
        "传感器读数漂移：先做三点校准，若仍漂移检查屏蔽接地与变送器供电。",
    ],
    "工艺参数标准": [
        "注塑成型熔体温度范围190-230℃，模温60-90℃，保压时间为冷却时间的1/3。",
        "中央冷水机组供水温度设定7℃回水12℃，温差超过5℃提示换热不良。",
        "空压机排气压力设定0.7-0.8MPa，比功率超过6.0kW/(m³/min)提示效率劣化。",
    ],
}


def gen_m4kb():
    _mkdir(OUT)
    with open(os.path.join(OUT, "knowledge_base.json"), "w", encoding="utf-8") as f:
        json.dump(KB, f, ensure_ascii=False, indent=2)
    print("M4.2 ->", os.path.join(OUT, "knowledge_base.json"),
          sum(len(v) for v in KB.values()), "条知识")


if __name__ == "__main__":
    tasks = {
        "m1": gen_m1, "m2img": gen_m2img, "m2rul": gen_m2rul, "m3": gen_m3,
        "m3yolo": gen_m3yolo, "m4": gen_m4, "m4kb": gen_m4kb,
    }
    args = sys.argv[1:] or ["all"]
    if args == ["all"] or args[0] == "all":
        _mkdir(OUT)
        for fn in tasks.values():
            fn()
    else:
        _mkdir(OUT)
        for a in args:
            tasks[a]()
    print("完成。数据输出目录:", os.path.abspath(OUT))
