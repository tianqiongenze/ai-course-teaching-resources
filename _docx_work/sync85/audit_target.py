# -*- coding: utf-8 -*-
"""85c：《AI技术应用基础》目标目录全面审查（公开分享 + 提交审查标准）。

维度：
A 完整性  B 跨文件一致性  C 旧口径残留  D 教学方案专项
E PPT 专项  F 任务单专项  G 文档规范
"""
import glob
import os
import re

import docx
from pptx import Presentation
from pptx.util import Emu

TGT = r"D:/工业互联网应用2026~2027第一学期（前八周）/2026级/《AI技术应用基础》"

WEEKS = [7, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
TIMES = [10, 5, 60, 15, 55, 15]

issues = []      # (级别, 类别, 描述)
stats = {}


def add(level, cat, msg):
    issues.append((level, cat, msg))


def uniq(row):
    out, seen = [], set()
    for c in row.cells:
        k = id(c._tc)
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
    return out


def all_text(d):
    """docx 全文（段落 + 表格）。"""
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            for c in uniq(row):
                parts.append(c.text)
    return "\n".join(parts)


# ─────────────── A 完整性 ───────────────
def check_completeness():
    print("\n=== A 完整性 ===")
    dirs = {
        "任务单": "《AI技术应用基础》-任务单",
        "授课计划": "《AI技术应用基础》-授课计划",
        "教学PPT": "《AI技术应用基础》-教学PPT",
        "教学设计": "《AI技术应用基础》-教学设计",
        "课程标准": "《AI技术应用基础》-课程标准",
    }
    for name, sub in dirs.items():
        p = os.path.join(TGT, sub)
        if not os.path.isdir(p):
            add("严重", "完整性", "缺少目录: %s" % sub)
            continue
        fs = [f for f in os.listdir(p) if not f.startswith("~$")]
        stats[name] = len(fs)
        print("  %-6s %d 个文件" % (name, len(fs)))

    # 数量校验
    gd = [f for f in os.listdir(os.path.join(TGT, dirs["任务单"])) if f.endswith(".docx")]
    pp = [f for f in os.listdir(os.path.join(TGT, dirs["教学PPT"])) if f.endswith(".pptx")]
    if len(gd) != 12:
        add("严重", "完整性", "任务单应为 12 个，实际 %d" % len(gd))
    if len(pp) != 24:
        add("严重", "完整性", "教学PPT应为 24 册，实际 %d" % len(pp))

    # 任务单周次前缀
    gw = sorted(int(re.match(r"W(\d{2})", f).group(1)) for f in gd if re.match(r"W(\d{2})", f))
    if gw != WEEKS:
        add("严重", "完整性", "任务单周次不符: %s" % gw)
    else:
        print("  任务单周次: %s ✔" % gw)

    # 残留临时文件
    junk = []
    for root, _, files in os.walk(TGT):
        for f in files:
            if f.startswith("~$") or f.endswith((".tmp", ".bak", ".bak79")):
                junk.append(os.path.join(root, f))
    if junk:
        add("提示", "完整性", "存在临时/备份文件 %d 个" % len(junk))
    else:
        print("  无临时/备份文件 ✔")


# ─────────────── B 跨文件一致性 ───────────────
def weeks_covered(text):
    """解析文本中覆盖的周次：支持「第7周」「第7、10周」「第11-14周」。"""
    got = set()
    for m in re.finditer(r"第\s*(\d{1,2})(?:\s*[-–~至]\s*(\d{1,2}))?\s*周", text):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        got.update(range(min(a, b), max(a, b) + 1))
    # 「第7、10周」
    for m in re.finditer(r"第((?:\d{1,2}[、，,])+\d{1,2})周", text):
        for x in re.findall(r"\d{1,2}", m.group(1)):
            got.add(int(x))
    return got


def check_consistency():
    print("\n=== B 跨文件一致性 ===")
    texts = {}
    for key, sub in [
        ("课标", "《AI技术应用基础》-课程标准"),
        ("授课计划", "《AI技术应用基础》-授课计划"),
        ("教学方案", "《AI技术应用基础》-教学设计"),
    ]:
        f = [x for x in glob.glob(os.path.join(TGT, sub, "*.docx")) if not os.path.basename(x).startswith("~$")][0]
        texts[key] = all_text(docx.Document(f))

    # ① 周次覆盖
    for key, txt in texts.items():
        got = weeks_covered(txt)
        miss = [w for w in WEEKS if w not in got]
        if miss:
            add("重要", "一致性", "%s 缺周次: %s" % (key, miss))
        else:
            print("  %-6s 12 个周次齐全 ✔" % key)

    # ② 时段口径
    for key in ("教学方案", "授课计划"):
        if "1班" not in texts[key] or "2班" not in texts[key]:
            add("重要", "一致性", "%s 缺 1班/2班 时段标注" % key)
        else:
            print("  %-6s 1班/2班时段 ✔" % key)

    # ③ 考核口径
    for key, txt in texts.items():
        if key == "教学方案":
            ok = "工单40%" in txt and "小组项目30%" in txt
        else:
            ok = ("40%" in txt and "30%" in txt)
        if not ok:
            add("重要", "一致性", "%s 考核口径未含 工单40/小组项目30" % key)
        else:
            print("  %-6s 考核口径 ✔" % key)

    # ④ 课程名 / 学期 / 班级
    if "AI技术应用基础" not in texts["课标"]:
        add("重要", "一致性", "课标课程名不符")
    if "第1学期" not in texts["授课计划"]:
        add("重要", "一致性", "授课计划学期未更新为第1学期")
    if "2026级" not in texts["授课计划"]:
        add("重要", "一致性", "授课计划班级未更新为2026级")
    print("  课程名/学期/班级 校验完成")


# ─────────────── C 旧口径残留 ───────────────
def check_residue():
    print("\n=== C 旧口径残留 ===")
    PATS = [
        ("第1-12周", "旧开课周次"),
        ("第4-15周", "旧开课周次"),
        ("第5-16周", "旧开课周次"),
        ("2次/周", "旧排课频次"),
        ("2次×80分钟", "旧课时口径"),
        ("2025级", "旧年级"),
        ("学年第2学期", "旧学期"),
        ("AI应用基础（48课时版）", "旧课程名"),
        ("M1.1", "旧8课次体系"),
        ("M8.2", "旧8课次体系"),
    ]
    for sub in ["《AI技术应用基础》-课程标准", "《AI技术应用基础》-授课计划", "《AI技术应用基础》-教学设计"]:
        f = [x for x in glob.glob(os.path.join(TGT, sub, "*.docx")) if not os.path.basename(x).startswith("~$")][0]
        txt = all_text(docx.Document(f))
        hits = [(k, d) for k, d in PATS if k in txt]
        if hits:
            for k, d in hits:
                add("重要", "残留", "%s 含旧口径「%s」(%s)" % (os.path.basename(sub)[:14], k, d))
        else:
            print("  %-18s 无旧口径残留 ✔" % os.path.basename(sub)[:16])

    # 任务单
    bad = []
    for f in sorted(glob.glob(os.path.join(TGT, "《AI技术应用基础》-任务单", "*.docx"))):
        if os.path.basename(f).startswith("~$"):
            continue
        txt = all_text(docx.Document(f))
        for k in ("2课时（80分钟）", "第4周", "第5周", "第6周"):
            if k in txt and not re.search(r"第\d{2}周", k):
                bad.append((os.path.basename(f)[:20], k))
    if bad:
        for b in bad[:6]:
            add("提示", "残留", "任务单 %s 含「%s」" % b)
    else:
        print("  任务单 无 2课时80分钟 残留 ✔")


# ─────────────── D 教学方案专项 ───────────────
def check_lesson_plan():
    print("\n=== D 教学方案专项 ===")
    f = [x for x in glob.glob(os.path.join(TGT, "《AI技术应用基础》-教学设计", "*.docx"))
         if not os.path.basename(x).startswith("~$")][0]
    d = docx.Document(f)
    if len(d.tables) != 13:
        add("严重", "教学方案", "表格数应为 13，实际 %d" % len(d.tables))
    for ti in range(1, 13):
        t = d.tables[ti]
        u1 = uniq(t.rows[1])
        slot = u1[-1].text.strip() if u1 else ""
        wk = WEEKS[ti - 1]
        if not re.search(r"第%d周周五1~4节（1班）、5~8节（2班）" % wk, slot):
            add("严重", "教学方案", "表%d 时间格式不符: %s" % (ti, slot))
        # 课时
        keshí = [c.text.strip() for c in u1 if "160分钟" in c.text]
        if not keshí:
            add("重要", "教学方案", "表%d 课时未标 4课时（160分钟）" % ti)
        # 任务实施
        tot, empty = 0, []
        for j, ri in enumerate((13, 14, 16, 17, 19, 20)):
            u = uniq(t.rows[ri])
            if len(u) < 5:
                add("严重", "教学方案", "表%d R%d 列数异常" % (ti, ri))
                continue
            m = re.match(r"(\d+)分钟", u[4].text.strip())
            tot += int(m.group(1)) if m else 0
            for k, tag in ((1, "教师行为"), (2, "学生行为"), (3, "节点目标")):
                if len(u[k].text.strip()) < 6:
                    empty.append("%s.%s" % (ri, tag))
            # 学时与标准一致
            if m and int(m.group(1)) != TIMES[j]:
                add("重要", "教学方案", "表%d R%d 学时 %s 非标准 %d" % (ti, ri, m.group(1), TIMES[j]))
        if tot != 160:
            add("严重", "教学方案", "表%d 任务实施合计 %d 分钟（应 160）" % (ti, tot))
        if empty:
            add("重要", "教学方案", "表%d 内容过简: %s" % (ti, ",".join(empty)))
    print("  12 表 时间/课时/160分钟/内容 校验完成")


# ─────────────── E PPT 专项 ───────────────
def check_pptx():
    print("\n=== E 教学PPT专项 ===")
    fs = sorted(f for f in glob.glob(os.path.join(TGT, "《AI技术应用基础》-教学PPT", "*.pptx"))
                if not os.path.basename(f).startswith("~$"))
    total_pages = 0
    for f in fs:
        base = os.path.basename(f)
        m = re.match(r"W(\d{2})-第(\d+)次课", base)
        if not m:
            add("提示", "PPT", "文件名不合规范: %s" % base[:40])
        try:
            prs = Presentation(f)
        except Exception as e:
            add("严重", "PPT", "%s 打开失败: %s" % (base[:30], e))
            continue
        n = len(prs.slides)
        total_pages += n
        if n > 80:
            add("重要", "PPT", "%s 页数 %d > 80" % (base[:30], n))
        # 越界
        over = 0
        for s in prs.slides:
            for sh in s.shapes:
                try:
                    L, T = Emu(sh.left).inches, Emu(sh.top).inches
                    W, H = Emu(sh.width).inches, Emu(sh.height).inches
                except Exception:
                    continue
                if L + W > 13.45 or T + H > 7.65 or L < -0.05 or T < -0.05:
                    over += 1
        if over:
            add("提示", "PPT", "%s 有 %d 个形状越界" % (base[:30], over))
        # 封面周次与文件名一致（仅查含「次课（2课时」的封面框）
        try:
            cover = None
            for sh in prs.slides[0].shapes:
                if not sh.has_text_frame:
                    continue
                t = sh.text_frame.text
                if "次课（2课时" in t:
                    mm = re.search(r"第\s*(\d{1,2})\s*周", t)
                    if mm:
                        cover = int(mm.group(1))
            if cover is None:
                add("提示", "PPT", "%s 封面未找到周次" % base[:30])
            elif cover != int(m.group(1)):
                add("严重", "PPT", "%s 封面周次 %d ≠ 文件名 %s" % (base[:30], cover, m.group(1)))
        except Exception:
            pass
    print("  %d 册 / 合计 %d 页（平均 %.0f 页）" % (len(fs), total_pages, total_pages / max(len(fs), 1)))
    stats["PPT总页数"] = total_pages


# ─────────────── F 任务单专项 ───────────────
def check_gongdan():
    print("\n=== F 任务单专项 ===")
    fs = sorted(f for f in glob.glob(os.path.join(TGT, "《AI技术应用基础》-任务单", "*.docx"))
                if not os.path.basename(f).startswith("~$"))
    for f in fs:
        base = os.path.basename(f)
        m = re.match(r"W(\d{2})_", base)
        if not m:
            continue
        wk = int(m.group(1))
        try:
            d = docx.Document(f)
        except Exception as e:
            add("严重", "任务单", "%s 打开失败: %s" % (base[:30], e))
            continue
        txt = all_text(d)
        if not re.search(r"第%d周\s*[·・]\s*4课时（160分钟）" % wk, txt):
            add("重要", "任务单", "%s 头部周次/课时不符" % base[:34])
        if "4课时" not in txt:
            add("重要", "任务单", "%s 未标 4课时" % base[:34])
        for lvl in ("D层", "C层", "B层", "A层"):
            if lvl not in txt:
                add("提示", "任务单", "%s 缺 %s 任务" % (base[:28], lvl))
    print("  %d 个任务单校验完成" % len(fs))


# ─────────────── G 文档规范 ───────────────
def check_doc_quality():
    print("\n=== G 文档规范 ===")
    BAD = ["\ufffd", "□" * 0, "TODO", "XXX", "待补", "占位", "示例文本"]
    for sub in ["《AI技术应用基础》-课程标准", "《AI技术应用基础》-授课计划", "《AI技术应用基础》-教学设计"]:
        f = [x for x in glob.glob(os.path.join(TGT, sub, "*.docx")) if not os.path.basename(x).startswith("~$")][0]
        d = docx.Document(f)
        txt = all_text(d)
        for b in BAD:
            if b and b in txt:
                add("重要", "规范", "%s 含异常标记「%s」" % (os.path.basename(sub)[:14], b))
        # 空表格单元格统计（仅关键表）
        print("  %-18s %d 段 / %d 表" % (os.path.basename(sub)[:16], len(d.paragraphs), len(d.tables)))

    # 文件名规范
    for root, _, files in os.walk(TGT):
        for f in files:
            if f.startswith("~$"):
                add("提示", "规范", "残留临时文件: %s" % f)
            if re.search(r"[\s]{2,}", f):
                add("提示", "规范", "文件名含连续空格: %s" % f[:40])
    print("  文件名规范校验完成")


def check_naming_consistency():
    """课程名 / 页脚 / 页眉 一致性。"""
    print("\n=== H 课程名一致性 ===")
    bad = 0
    fs = sorted(f for f in glob.glob(os.path.join(TGT, "《AI技术应用基础》-教学PPT", "*.pptx"))
                if not os.path.basename(f).startswith("~$"))
    for f in fs:
        prs = Presentation(f)
        t1 = ""
        for sh in prs.slides[0].shapes:
            if sh.has_text_frame and "课时版" in sh.text_frame.text:
                t1 = sh.text_frame.text
                break
        if "AI技术应用基础" not in t1:
            add("重要", "命名", "%s 封面课程名未统一" % os.path.basename(f)[:34])
            bad += 1
        # 页脚抽查末页
        foot = ""
        last = prs.slides[-1]
        for sh in last.shapes:
            if sh.has_text_frame and "两江智造" in sh.text_frame.text:
                foot = sh.text_frame.text
                break
        if foot and "AI技术应用基础" not in foot:
            add("提示", "命名", "%s 页脚课程名未统一" % os.path.basename(f)[:34])
            bad += 1
    print("  PPT 课程名：%d 册异常" % bad)

    bad = 0
    for f in sorted(glob.glob(os.path.join(TGT, "《AI技术应用基础》-任务单", "*.docx"))):
        if os.path.basename(f).startswith("~$"):
            continue
        d = docx.Document(f)
        head = "\n".join(p.text for p in d.paragraphs[:4])
        if "AI技术应用基础" not in head:
            add("重要", "命名", "%s 页眉课程名未统一" % os.path.basename(f)[:34])
            bad += 1
    print("  任务单课程名：%d 个异常" % bad)


def check_compliance():
    """公开分享合规：敏感信息 / 版权 / 署名。"""
    print("\n=== I 公开分享合规 ===")
    SENS = [r"1[3-9]\d{9}", r"\d{17}[\dXx]", r"password\s*=", r"api[_-]?key\s*=", r"sk-[A-Za-z0-9]{16,}"]
    hits = []
    for root, _, files in os.walk(TGT):
        for fn in files:
            if not fn.endswith((".docx", ".pptx")):
                continue
            p = os.path.join(root, fn)
            try:
                if fn.endswith(".docx"):
                    txt = all_text(docx.Document(p))
                else:
                    prs = Presentation(p)
                    txt = "\n".join(
                        sh.text_frame.text
                        for s in prs.slides for sh in s.shapes if sh.has_text_frame)
            except Exception:
                continue
            for pat in SENS:
                if re.search(pat, txt):
                    hits.append((fn[:34], pat))
    if hits:
        for h in hits[:6]:
            add("重要", "合规", "%s 疑似敏感信息 %s" % h)
    else:
        print("  无手机号/身份证/密钥等敏感信息 ✔")

    # 版权声明
    has_copy = False
    for root, _, files in os.walk(TGT):
        for fn in files:
            if fn.endswith(".docx"):
                try:
                    if "版权" in all_text(docx.Document(os.path.join(root, fn))):
                        has_copy = True
                except Exception:
                    pass
    if not has_copy:
        add("提示", "合规", "目录内无版权/使用声明文件（公开分享建议补一份）")
    else:
        print("  含版权声明 ✔")


def main():
    check_completeness()
    check_consistency()
    check_residue()
    check_lesson_plan()
    check_pptx()
    check_gongdan()
    check_doc_quality()
    check_naming_consistency()
    check_compliance()

    print("\n" + "=" * 62)
    sev = {"严重": 0, "重要": 0, "提示": 0}
    for lv, cat, msg in issues:
        sev[lv] = sev.get(lv, 0) + 1
    print("审查结果：严重 %d · 重要 %d · 提示 %d" % (sev.get("严重", 0), sev.get("重要", 0), sev.get("提示", 0)))
    if issues:
        print("\n问题清单：")
        for lv, cat, msg in issues:
            print("  [%s] %-8s %s" % (lv, cat, msg))
    else:
        print("未发现问题 ✔")
    print("\n统计:", stats)


if __name__ == "__main__":
    main()
