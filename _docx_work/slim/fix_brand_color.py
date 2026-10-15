# -*- coding: utf-8 -*-
"""76号轮·PPT 品牌配色归一（zip 级 XML 替换，最稳健）

缺陷：02-程序设计基础/V1授课PPT 全 23 册用橙 #E8611A，其余档用 #F5670F（同课程内不一致）。
修复：在该目录内把 XML 中的 E8611A 统一替换为 F5670F（文字色/填充色/主题色一并生效）。
"""
import glob
import os
import shutil
import sys
import tempfile
import zipfile

ROOT = r"D:/Python编程实战/教学实施资料"
TARGET_DIR = os.path.join(ROOT, "02-程序设计基础", "V1授课PPT")
OLD, NEW = "E8611A", "F5670F"


def fix_zip(path):
    tmp = path + ".tmp76"
    n = 0
    with zipfile.ZipFile(path, "r") as zin, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.lower().endswith((".xml", ".rels")):
                try:
                    txt = data.decode("utf-8")
                except UnicodeDecodeError:
                    zout.writestr(item, data)
                    continue
                if OLD in txt.upper():
                    cnt = txt.upper().count(OLD)
                    txt = txt.replace(OLD, NEW).replace(OLD.lower(), NEW)
                    n += cnt
                data = txt.encode("utf-8")
            zout.writestr(item, data)
    if n:
        os.replace(tmp, path)
    else:
        os.remove(tmp)
    return n


def main():
    dry = "--apply" not in sys.argv
    files = sorted(f for f in glob.glob(os.path.join(TARGET_DIR, "*.pptx")) if "~$" not in f)
    tot = nf = 0
    for p in files:
        try:
            if dry:
                raw = open(p, "rb").read().upper()
                c = raw.count(OLD.encode())
            else:
                c = fix_zip(p)
        except PermissionError:
            print("  锁定跳过:", os.path.basename(p)[:46])
            continue
        if c:
            nf += 1
            tot += c
    print("%s：%d 册 / %d 处 %s → %s" % ("空跑" if dry else "已修复", nf, tot, OLD, NEW))


if __name__ == "__main__":
    main()