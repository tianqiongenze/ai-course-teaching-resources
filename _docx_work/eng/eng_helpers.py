# -*- coding: utf-8 -*-
"""工程化项目规格的 Markdown 片段助手（与 specs 模块解耦，避免循环导入）。"""


def mod_table(mods):
    out = ["| 模块 | 职责 | 关键接口 |", "|---|---|---|"]
    for m in mods:
        out.append("| `%s` | %s | `%s` |" % tuple(m))
    return "\n".join(out)


def stories(items):
    out = ["| 编号 | 用户故事 | 验收标准 |", "|---|---|---|"]
    for i, (story, acc) in enumerate(items, 1):
        out.append("| US-%02d | %s | %s |" % (i, story, acc))
    return "\n".join(out)


def funcs(items):
    out = ["| 编号 | 功能点 | 说明 |", "|---|---|---|"]
    for i, (name, desc) in enumerate(items, 1):
        out.append("| F-%02d | %s | %s |" % (i, name, desc))
    return "\n".join(out)


def tcases(items):
    out = ["| 编号 | 测试对象 | 输入 | 期望 |", "|---|---|---|---|"]
    for i, it in enumerate(items, 1):
        if len(it) == 4:            # (编号, 对象, 输入, 期望) —— 首列编号由程序生成，丢弃
            it = it[1:]
        tgt, inp, exp = it
        out.append("| TC-%02d | %s | %s | %s |" % (i, tgt, inp, exp))
    return "\n".join(out)


def adr(title, bg, options, choice, reason, pos, neg, mit):
    return dict(title=title, bg=bg, options=options, choice=choice,
                reason=reason, pos=pos, neg=neg, mit=mit)


def finalize(spec):
    """把 spec 中的列表字段转换为文档用 Markdown 字符串。"""
    if "mods" in spec:
        spec["modules_table"] = mod_table(spec.pop("mods"))
    if "stories" in spec:
        spec["req_stories"] = stories(spec.pop("stories"))
    if "funcs" in spec:
        spec["req_funcs"] = funcs(spec.pop("funcs"))
    if "test_cases" in spec:
        tc = spec.pop("test_cases")
        spec["test_cases"] = tcases(tc) if isinstance(tc, list) else tc
    return spec
