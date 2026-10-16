# -*- coding: utf-8 -*-
"""82轮·solutions.py 解析（AST 版，精确）"""
import ast


def parse_solutions(sol_path):
    """解析 solutions.py → {工单函数名: {'inner': {函数名: 源码}, 'driver': 驱动源码}}"""
    src = open(sol_path, encoding="utf-8").read()
    tree = ast.parse(src)
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        inner, drv = {}, []
        for st in node.body:
            if isinstance(st, ast.FunctionDef):
                seg = ast.get_source_segment(src, st)
                if seg:
                    # get_source_segment 首行(def)无缩进、body 保留 8 空格
                    # 规范化为：def 顶格 + body 4 空格
                    lines = seg.split("\n")
                    fixed = [lines[0]] + [
                        (l[4:] if l.startswith("    ") else l) for l in lines[1:]
                    ]
                    inner[st.name] = "\n".join(fixed).rstrip() + "\n"
            else:
                seg = ast.get_source_segment(src, st)
                if seg:
                    drv.append(seg)
        # driver 去掉一层缩进（原在函数体内 4 空格）
        driver_lines = []
        for seg in drv:
            for ln in seg.split("\n"):
                driver_lines.append(ln[4:] if ln.startswith("    ") else ln)
            driver_lines.append("")
        out[node.name] = {"inner": inner, "driver": "\n".join(driver_lines).rstrip() + "\n"}
    return out


if __name__ == "__main__":
    import sys
    sm = parse_solutions(sys.argv[1])
    for k, v in sm.items():
        print("%-6s inner=%s" % (k, list(v["inner"].keys())))
        print("       driver 前100: %r" % v["driver"][:100])
