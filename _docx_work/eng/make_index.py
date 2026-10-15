# -*- coding: utf-8 -*-
"""为四门课的 工程化项目/ 生成索引 README.md。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eng_specs as S

ROOT = r"D:/Python编程实战/教学实施资料"

HEAD = """# {course} · 工程化项目索引（第三种代码形态）

> 74号轮 · 每个周次一个**可运行的 Python 工程化项目**：多文件分层、规则外置、pytest 三档测试、8 份国标/TOGAF 过程文档，共 {n} 个周次全覆盖。

## 一、三种代码形态的定位

| 形态 | 目录 | 定位 |
|---|---|---|
| ① starter | `../学生代码框架/` | 学生填空起步（TODO 骨架） |
| ② 教师参考 | `../教师参考/` | 完成态参考（单文件示意） |
| ③ **工程化项目（本目录）** | `工程化项目/` | **企业级工程结构 + 全套流程资料** |

## 二、项目清单（{n} 个）

| # | 工单 | 周次 | 目录 | 核心功能 |
|---|---|---|---|---|
"""

TAIL = """
## 三、每个项目的结构（23 个文件）

```
<slug>/
├── README.md               # 三种形态定位 + 目录 + 验收口径
├── pyproject.toml          # 包元数据 + pytest 配置
├── requirements.txt        # 依赖清单
├── .gitignore
├── run.py                  # 唯一入口（argparse CLI）
├── config/rules.yaml       # 规则外置：改配置不改代码
├── src/<pkg>/
│   ├── config.py           # YAML 加载 + Settings（含 yaml_lite 零依赖兜底）
│   ├── core.py             # 纯函数领域逻辑（零 IO，可单测）
│   ├── io_utils.py         # CSV/JSON/原子写
│   ├── report.py           # 报告渲染
│   └── pipeline.py         # load → process → evaluate → report 编排
├── tests/
│   ├── test_core.py        # 正常 / 边界 / 异常三档
│   └── test_config.py      # 配置加载与校验
└── docs/                   # 8 份过程文档
    ├── 01-需求规格.md       # GB/T 9385
    ├── 02-架构说明.md       # TOGAF 四域
    ├── 03-设计说明.md
    ├── 04-测试计划与报告.md  # GB/T 15532
    ├── 05-运行手册.md
    ├── 06-配置管理与变更记录.md  # GB/T 8566 配置管理
    ├── 07-ADR-001-架构决策记录.md
    └── 08-国标与TOGAF映射.md  # GB/T 8566 过程组落地表

## 四、30 秒跑起来

```bash
cd <slug>
python run.py                 # 输出 output/report.txt + result.json
python -m pytest -q           # 全量测试（应全绿）
```

## 五、验收口径

- `python -m pytest -q` 全绿；`python run.py` 生成 `output/report.txt`
- 配置修改不需改代码；二次运行结果一致（随机种子固定）
- 8 份过程文档齐全，可直接构成期末答辩的材料链

## 六、生成与重放

生成器：`_docx_work/eng/`（`eng_gen.py` + `eng_specs.py` + `specs_01/02/03/05.py`）
重放：`python _docx_work/eng/eng_gen.py --build`　验证：`python _docx_work/eng/verify_projects.py`

> 本索引由生成器自动产出（改 `specs_*.py` 后重跑 `eng_gen.py --build`，索引同步更新）。
"""


def main():
    by = {}
    for s in S.SPECS:
        by.setdefault(s["course"], []).append(s)
    for course, specs in sorted(by.items()):
        specs.sort(key=lambda x: (x["week"], x["no"]))
        lines = [HEAD.format(course=course, n=len(specs))]
        for i, s in enumerate(specs, 1):
            lines.append("| %d | %s | %s %s | `%s/` | %s |\n" % (
                i, s["id"], s["week"], s["no"], s["slug"], s["title"]))
        path = os.path.join(ROOT, course, "工程化项目", "README.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(lines) + TAIL)
        print("已写 %s (%d 项)" % (os.path.relpath(path, ROOT).replace("\\", "/"), len(specs)))


if __name__ == "__main__":
    main()
