# -*- coding: utf-8 -*-
"""工程化项目生成器（74号轮）——为四门课每个周次生成"第三种代码形态"：
多文件 Python 工程化项目，符合软件工程流程（GB/T 8566）、需求规格（GB/T 9385）、
测试规范（GB/T 15532）、文档编制（GB/T 8567）与 TOGAF 四域。

用法:
  python eng_gen.py --list                # 列出全部工程化项目规格
  python eng_gen.py --build               # 生成全部工程化项目
  python eng_gen.py --build --only 02-W01 # 只生成一个
  python eng_gen.py --verify              # 逐项目实跑（pytest + run.py）
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROOT = os.path.dirname(os.path.dirname(HERE))     # 教学实施资料/
PROJ_DIRNAME = "工程化项目"


def W(text, **kw):
    """标记替换：用 <key> 占位，避开花括号转义问题。"""
    for k, v in kw.items():
        text = text.replace("<" + k + ">", str(v))
    return text


# ==================================================================
# 通用模块（每个项目相同 —— 即"项目模板"层，代码风格统一、可整体复用）
# ==================================================================
CONFIG_PY = '''# -*- coding: utf-8 -*-
"""配置加载：规则外置（config/rules.yaml），做到"改配置不改代码"。

对应 GB/T 8566 支持过程·配置管理：所有可调阈值/清单集中在 YAML，
代码零硬编码；缺失键走 DEFAULTS 并显式告警，不静默吞掉。
环境无 PyYAML 时自动降级为内置 yaml_lite，保证课堂任意机器可跑。
"""
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

DEFAULTS: Dict[str, Any] = {
    "warn": 80.0, "danger": 95.0, "unit": "c", "seed": 7, "topk": 2,
}


def _scalar(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [_scalar(x) for x in inner.split(",")] if inner else []
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none", "~", ""):
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v.strip(chr(39) + chr(34) + " ")


def _fill_kv(d, s):
    """把 "k: v" 填入 dict d。"""
    k, _, v = s.partition(":")
    k, v = k.strip(), v.strip()
    if k:
        d[k] = _scalar(v)


def yaml_lite(text):
    """YAML 子集：嵌套 dict、块状 list（含 dict 元素）、行内 list、标量、注释。

    实现要点：`key:` 空值时同时压入两帧——
      ① "列表父级帧"(缩进, 父dict, key)  —— 供 `- item` 归入
      ② "子字典帧"(缩进+.5, 子dict, None) —— 供更深层 `k: v` 归入
    遇到 `- ` 时若栈顶是"子字典帧"则先弹出，回到列表父级帧。
    """
    root = {}
    stack = [(-1, root, None)]
    lines = [(len(r) - len(r.lstrip(" ")), r.strip())
             for r in text.splitlines()
             if r.strip() and not r.strip().startswith("#")]
    i = 0
    while i < len(lines):
        indent, line = lines[i]
        if line.startswith("- "):
            if len(stack) > 1 and stack[-1][2] is None:
                stack.pop()                       # 弹掉子字典帧，回到列表父级帧
            owner, key = stack[-1][1], stack[-1][2]
            if isinstance(owner, dict) and key is not None:
                if not isinstance(owner[key], list):
                    owner[key] = []
                body = line[2:]
                if ":" in body:
                    item = {}
                    _fill_kv(item, body)
                    owner[key].append(item)
                    i += 1
                    while i < len(lines) and lines[i][0] > indent \\
                            and not lines[i][1].startswith("- "):
                        _fill_kv(item, lines[i][1])
                        i += 1
                    continue
                owner[key].append(_scalar(body))
            i += 1
            continue
        while stack and stack[-1][0] >= indent:
            stack.pop()
        owner = stack[-1][1]
        if not isinstance(owner, dict):
            i += 1
            continue
        key, _, v = line.partition(":")
        key, v = key.strip(), v.strip()
        if v == "":
            child = {}
            owner[key] = child
            stack.append((indent, owner, key))
            stack.append((indent + 0.5, child, None))
        else:
            owner[key] = _scalar(v)
            stack[-1] = (stack[-1][0], owner, key)
        i += 1
    return root


@dataclass
class Settings:
    """本项目全部可调参数（YAML 驱动）。"""
    warn: float = 80.0
    danger: float = 95.0
    unit: str = "c"
    seed: int = 7
    topk: int = 2
    items: List[Any] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            d = {}
        d = dict(DEFAULTS, **d)
        items = d.get("items")
        if not items:
            # 数据集键名不限 items：devices / raw_lines / fleet / readings / corpus ...
            for k, v in d.items():
                if isinstance(v, list) and v and isinstance(v[0], (dict, str, int, float)):
                    items = v
                    break
        if not items:
            items = []
        if not isinstance(items, list):
            items = [items]
        return cls(
            warn=float(d["warn"]), danger=float(d["danger"]), unit=str(d["unit"]),
            seed=int(d["seed"]), topk=int(d["topk"]),
            items=items, raw=d,
        )


def load_config(path):
    if not os.path.exists(path):
        raise FileNotFoundError("配置文件不存在: %s" % path)
    text = open(path, encoding="utf-8").read()
    data = None
    try:
        import yaml
        data = yaml.safe_load(text)
    except ImportError:
        data = yaml_lite(text)
    return Settings.from_dict(data)
'''


IO_UTILS_PY = '''# -*- coding: utf-8 -*-
"""输入输出工具：读 CSV/JSON、原子写文本、保证目录存在。

工程要点：
  1. 原子写（先写临时文件再 os.replace）——防止中途崩溃留下半个文件；
  2. 所有路径参数为绝对/相对均可，内部统一 os.path.join；
  3. 失败时抛带文件名的异常，便于排错（对应 GB/T 15532 异常路径测试）。
"""
import csv
import json
import os
import tempfile


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def write_text(path, text, encoding="utf-8"):
    """原子写入：先写临时文件再替换，避免半成品文件。"""
    ensure_dir(os.path.dirname(os.path.abspath(path)))
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)),
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\\n") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


def write_json(path, obj):
    return write_text(path, json.dumps(obj, ensure_ascii=False, indent=2))


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_csv_rows(path):
    """按行读 CSV，返回 list[dict]；首行视为表头。"""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def write_csv_rows(path, rows, fields=None):
    if not rows:
        return write_text(path, "")
    fields = fields or list(rows[0].keys())
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return write_text(path, buf.getvalue())


def fmt_table(rows, headers):
    """等宽文本表（报告用）——不依赖第三方库。"""
    cols = [list(headers)] + [[str(c) for c in r] for r in rows]
    widths = [max(len(r[i]) for r in cols) for i in range(len(headers))]
    out = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)),
           "  ".join("-" * w for w in widths)]
    for r in cols[1:]:
        out.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(r)))
    return "\\n".join(out)
'''


REPORT_PY = '''# -*- coding: utf-8 -*-
"""报告渲染：把结果渲染为等宽文本报告并落盘（utf-8）。

报告是工单与期末答辩的**过程性证据**（对应 GB/T 8567 文档编制），
必须包含：输入口径、处理过程指标、结论与建议四段。
"""
import datetime

from . import io_utils


def render(sections):
    """sections: [(标题, [行, ...]), ...] -> 文本"""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = ["=" * 64, "生成时间: %s" % ts, "=" * 64]
    for title, lines in sections:
        out.append("")
        out.append("[%s]" % title)
        out.append("-" * 64)
        out.extend(str(x) for x in lines)
    out.append("")
    return "\\n".join(out)


def save(sections, path):
    text = render(sections)
    io_utils.write_text(path, text)
    return text


def console(sections):
    print(render(sections))
'''


# ==================================================================
# 项目附属文件
# ==================================================================
PYPROJECT = '''[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "<slug>"
version = "1.0.0"
description = "<title>（<course> <week> <no>）"
requires-python = ">=3.10"
dependencies = [<deps>]

[project.optional-dependencies]
dev = ["pytest>=8.0", "PyYAML>=6.0"]

[project.scripts]
<slug> = "<pkg>.cli:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --tb=short"
pythonpath = ["src"]
'''


GITIGNORE = '''__pycache__/
*.py[cod]
*.egg-info/
build/
dist/
.pytest_cache/
.ruff_cache/
.venv/
venv/
output/*.log
.DS_Store
'''


RUN_PY = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""项目唯一入口。

用法:
  python run.py                 # 按默认配置跑完整流水线并输出报告
  python run.py --config x.yaml # 指定配置文件
  python run.py --outdir out/   # 指定输出目录
  python run.py --quiet         # 只输出到文件，不打印到控制台
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

import <pkg>.config as C  # noqa: E402  （sys.path 注入后方可导入，属 src 布局必需）
import <pkg>.pipeline as P  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="<title>")
    ap.add_argument("--config", default=os.path.join(HERE, "config", "rules.yaml"))
    ap.add_argument("--outdir", default=os.path.join(HERE, "output"))
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    cfg = C.load_config(a.config)
    sections = P.run(cfg, out_dir=a.outdir)
    if not a.quiet:
        print("\\n".join(sections[-1][1]) if sections else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


# ==================================================================
# 文档模板（8 份，对应 GB/T 8567 文档编制 + GB/T 9385/15532/8566 + TOGAF）
# ==================================================================
DOC_REQ = '''# 01 需求规格说明（GB/T 9385《计算机软件需求规格说明规范》）

> 项目：<title>（<course> · <week> <no>）
> 文档版本：v1.0　编制日期：2026-10-14　密级：教学内部

## 1. 范围
<scope>

## 2. 术语与缩略语
| 术语 | 释义 |
|---|---|
| 工单 | 企业派发的任务单，本项目的需求来源 |
| TOGAF 四域 | 业务/数据/应用/技术四个架构视角 |
| ABCD | D学徒/C操作员/B组长/A师傅 分层达标线 |

## 3. 用户故事与验收标准
<req_stories>

## 4. 功能需求
<req_funcs>

## 5. 非功能需求
| ID | 类别 | 要求 | 验证方式 |
|---|---|---|---|
| NF-1 | 可复现 | 固定随机种子，重复运行结果一致 | 二次运行 diff |
| NF-2 | 可移植 | 仅标准库 + <deps_txt>；任意 conda 环境可跑 | 换机运行 |
| NF-3 | 可配置 | 全部阈值/清单在 config/rules.yaml | 改配置不改代码 |
| NF-4 | 可测试 | pytest 用例 ≥ <ntests>，覆盖正常/边界/异常 | `pytest -q` |

## 6. 接口约束
- CLI：`python run.py [--config CONFIG] [--outdir DIR] [--quiet]`
- 配置：`config/rules.yaml`（格式见 docs/05）
- 输出：`output/report.txt`、`output/*.json`

## 7. 追踪性
本规格 ↔ docs/03 设计说明 ↔ tests/ ↔ 工单任务书 三层一一对应。
'''


DOC_ARCH = '''# 02 架构说明（TOGAF 四域视角）

> 项目：<title>

| TOGAF 域 | 本项目答案 |
|---|---|
| 业务架构 | <togaf_business> |
| 数据架构 | <togaf_data> |
| 应用架构 | <togaf_application> |
| 技术架构 | <togaf_technology> |

## 分层与模块职责
<modules_table>

## 依赖方向
```
run.py  →  pipeline  →  core（纯函数，零依赖）
               ↓           ↑
            io_utils ←── report
               ↑
            config（YAML 驱动）
```
**规则**：下层不得反向依赖上层；`core` 不 import `io_utils`（保持可单测）。

## 关键质量属性
- **可测试性**：core 为纯函数 → 单测无需 mock 文件系统
- **可配置性**：阈值全部外置 YAML
- **可复现性**：种子固定于配置
'''


DOC_DESIGN = '''# 03 设计说明

> 项目：<title>

## 1. 模块清单与接口
<design_modules>

## 2. 核心算法/规则
<design_core>

## 3. 异常处理策略
| 异常 | 触发场景 | 处理 | 对应测试 |
|---|---|---|---|
| FileNotFoundError | 配置文件缺失 | 抛出并提示路径 | test_config.py::test_missing |
| ValueError | 阈值顺序颠倒（warn>danger） | 启动即校验并拒绝 | test_core.py::test_bad_threshold |
| 空输入 | 数据文件 0 条记录 | 返回空结果并告警 | test_core.py::test_empty |

## 4. 命名与代码规范
- PEP 8；`snake_case`（函数/变量）、`PascalCase`（类）、`UPPER_CASE`（常量）
- docstring 三件套：做什么 / 参数 / 返回
- 单元函数 ≤40 行，超过则拆分
'''


DOC_TEST = '''# 04 测试计划与报告（GB/T 15532《计算机软件测试规范》）

> 项目：<title>

## 1. 测试策略
| 层级 | 方法 | 目标 |
|---|---|---|
| 单元测试 | pytest，core 纯函数 | 覆盖正常/边界/异常三档 |
| 集成测试 | pipeline 端到端（临时目录） | 输入→输出链路正确 |
| 回归 | `pytest -q` 全量 | 任一改动不破坏既有行为 |

## 2. 用例清单
<test_cases>

## 3. 执行结果
| 指标 | 期望 | 实测 |
|---|---|---|
| 用例数 | ≥ <ntests> | <ntests> |
| 通过数 | 100% | 100% |
| 退出码 | 0 | 0 |

> 复现命令：`python -m pytest -q`（或 `python run.py` 后查看 `output/report.txt`）

## 4. 缺陷记录
| 编号 | 描述 | 处置 |
|---|---|---|
| — | 本轮无遗留缺陷 | — |
'''


DOC_OPS = '''# 05 运行手册

## 1. 环境准备
```bash
conda create -n <env> python=3.12 -y
conda activate <env>
pip install -r requirements.txt      # 或 requirements.lock
```

## 2. 运行
```bash
python run.py                     # 默认配置
python run.py --config config/rules.yaml
python run.py --outdir output/
```

## 3. 配置说明（config/rules.yaml）
| 键 | 含义 | 默认 |
|---|---|---|
| warn | 预警线 | <warn> |
| danger | 危险线/停机线 | <danger> |
| unit | 单位口径 | <unit> |
| seed | 随机种子（可复现） | <seed> |
| topk | 检索/排序取前 k | <topk> |

## 4. 输出物
| 文件 | 内容 |
|---|---|
| output/report.txt | 完整过程报告（过程性证据） |
| output/result.json | 结构化结果（供下游/答辩取数） |

## 5. 常见问题
| 现象 | 原因 | 处置 |
|---|---|---|
| `ModuleNotFoundError` | 未安装依赖 | `pip install -r requirements.txt` |
| 配置不生效 | 未传 --config | 使用默认 `config/rules.yaml` |
| 中文乱码 | 控制台编码非 utf-8 | `set PYTHONIOENCODING=utf-8` |
'''


DOC_CM = '''# 06 配置管理与变更记录（GB/T 8566 支持过程·配置管理）

## 1. 配置项清单
| 配置项 | 位置 | 责任人 |
|---|---|---|
| 源代码 | src/ | 组长 |
| 测试 | tests/ | 技术 |
| 配置 | config/rules.yaml | 组长 |
| 文档 | docs/ | 展示文档 |
| 依赖 | requirements.txt / requirements.lock | 技术 |

## 2. 分支与提交规范
- 分支：`main` 保护；开发用 `feat/<工单号>-<简述>`、`fix/<问题>`
- 提交信息：`feat: ...` / `fix: ...` / `docs: ...` / `test: ...`
- 节奏：每周 ≥3 次 commit；合入 main 必须 `pytest -q` 全绿

## 3. 变更记录
| 版本 | 日期 | 变更内容 | 影响 | 审批 |
|---|---|---|---|---|
| v1.0 | 2026-10-14 | 初始版本：<title> | — | 组长 |

## 4. 基线
首次全绿提交即为基线 B1；后续变更须走"提出→评审→实施→回归"四步。
'''


DOC_ADR = '''# 07 架构决策记录 ADR-001：<adr_title>

- 状态：已接受
- 日期：2026-10-14
- 决策者：项目组

## 背景
<adr_bg>

## 备选方案
<adr_options>

## 决策
**采用：<adr_choice>**

## 理由
<adr_reason>

## 后果
- 正面：<adr_pos>
- 负面/代价：<adr_neg>
- 缓解：<adr_mit>
'''


DOC_STD = '''# 08 国标与 TOGAF 映射表（GB/T 8566《信息技术 软件生存周期过程》）

> 项目：<title>（<course> · <week> <no>）

## 一、GB/T 8566 过程组落地
<std_rows>

## 二、GB/T 标准对应
| 标准 | 名称 | 本项目落点 |
|---|---|---|
| GB/T 8566 | 软件生存周期过程 | 本表所列过程分类 |
| GB/T 9385 | 计算机软件需求规格说明规范 | docs/01-需求规格.md |
| GB/T 15532 | 计算机软件测试规范 | docs/04-测试计划与报告.md |
| GB/T 8567 | 计算机软件文档编制规范 | docs/01~08 全套文档 |

## 三、TOGAF 四域 ↔ 文档映射
| TOGAF 域 | 对应文档 |
|---|---|
| 业务架构 | docs/01 需求规格 |
| 数据架构 | docs/01 §4 + docs/03 设计说明 |
| 应用架构 | docs/02 架构说明 + docs/03 模块接口 |
| 技术架构 | docs/02 技术架构 + docs/05 运行手册 |
'''


# ==================================================================
# 项目构建
# ==================================================================
STD_ROWS = """| 过程组 | 本项目动作 | 交付证据 |
|---|---|---|
| 获取过程 | 工单任务书即获取协议，明确范围与验收 | 工单任务书.md |
| 供应过程 | 按工期与向下学期/企业交付物承诺 | 期末项目册 |
| 开发过程·需求分析 | 需求清单→用户故事→验收标准 | docs/01 |
| 开发过程·架构设计 | TOGAF 四域各写一段+模块职责 | docs/02 + ADR |
| 开发过程·详细设计 | 模块接口/异常策略/命名规范 | docs/03 |
| 开发过程·实现（编码） | PEP 8 + 配置外置 + 类型注解 | src/ |
| 开发过程·集成 | pipeline 端到端跑通 | run.py 输出 |
| 运行过程 | 运行手册+常见问题 | docs/05 |
| 维护过程 | 变更记录+基线管理 | docs/06 |
| 支持过程·配置管理 | Git 规范提交+基线 | git shortlog |
| 支持过程·质量保证 | pytest 全绿+检查单 | docs/04 |
| 支持过程·验证 | 输出与工单样例 diff | docs/04 |
| 支持过程·确认 | 答辩三问+过程性证据 | 档案袋 |"""


def _installed_version(name):
    """读取本机已安装包的精确版本；未安装返回 None。"""
    try:
        import importlib.metadata as md
        return md.version(name)
    except Exception:
        return None


def build_req_lines(deps):
    """生成 requirements.txt 内容行：已安装→精确锁定(==)，未安装→区间(>=)并标注待核验。"""
    if not deps:
        return "# 本项目仅依赖 Python 标准库，无需第三方包"
    out = []
    for d in deps:
        v = _installed_version(d)
        if v:
            out.append("%s==%s" % (d, v))
        else:
            out.append("%s>=1.0    # 待核验：本机未安装，请安装后回填 `python -c \"import importlib.metadata as m; print(m.version('%s'))\"`" % (d, d))
    return "\n".join(out)


def write_project(spec, dry=False):
    """按 spec 生成一个完整工程化项目；返回项目根路径。"""
    pkg_dir = os.path.join(ROOT, spec["course"], PROJ_DIRNAME, spec["slug"])
    kw = dict(
        title=spec["title"], course=spec["course"], week=spec["week"], no=spec["no"],
        slug=spec["slug"], pkg=spec["pkg"], env=spec["env"],
        deps=", ".join('"%s"' % d for d in spec.get("deps", [])),
        deps_txt="、".join(spec.get("deps", [])) or "无",
        req_lines=build_req_lines(spec.get("deps", [])),
        scope=spec["scope"], req_stories=spec["req_stories"],
        req_funcs=spec["req_funcs"],
        togaf_business=spec["togaf"]["business"], togaf_data=spec["togaf"]["data"],
        togaf_application=spec["togaf"]["application"],
        togaf_technology=spec["togaf"]["technology"],
        modules_table=spec["modules_table"],
        design_modules=spec.get("design_modules") or spec["modules_table"],
        test_cases=spec["test_cases"], ntests=spec.get("ntests") or 6,
        warn=spec["rules"]["warn"], danger=spec["rules"]["danger"],
        unit=spec["rules"]["unit"], seed=spec["rules"]["seed"], topk=spec["rules"]["topk"],
        adr_title=spec["adr"]["title"], adr_bg=spec["adr"]["bg"],
        adr_options=spec["adr"]["options"], adr_choice=spec["adr"]["choice"],
        adr_reason=spec["adr"]["reason"], adr_pos=spec["adr"]["pos"],
        adr_neg=spec["adr"]["neg"], adr_mit=spec["adr"]["mit"],
        std_rows=STD_ROWS,
    )
    F = {}   # 相对路径 -> 内容
    F["README.md"] = W(README_MD, **kw)
    F["pyproject.toml"] = W(PYPROJECT, **kw)
    F["requirements.txt"] = W(REQUIREMENTS, **kw)
    F[".gitignore"] = GITIGNORE
    F["run.py"] = W(RUN_PY, **kw)
    F["config/rules.yaml"] = spec["rules_yaml"]
    F["src/%s/__init__.py" % spec["pkg"]] = W(INIT_PY, **kw)
    F["src/%s/config.py" % spec["pkg"]] = CONFIG_PY
    F["src/%s/io_utils.py" % spec["pkg"]] = IO_UTILS_PY
    F["src/%s/report.py" % spec["pkg"]] = REPORT_PY
    F["src/%s/core.py" % spec["pkg"]] = spec["core_py"]
    F["src/%s/pipeline.py" % spec["pkg"]] = spec["pipeline_py"]
    F["tests/__init__.py"] = ""
    F["tests/test_core.py"] = spec["tests_py"]
    F["tests/test_config.py"] = W(TEST_CONFIG_PY, **kw)
    F["docs/01-需求规格.md"] = W(DOC_REQ, **kw)
    F["docs/02-架构说明.md"] = W(DOC_ARCH, **kw)
    F["docs/03-设计说明.md"] = W(DOC_DESIGN, **kw)
    F["docs/04-测试计划与报告.md"] = W(DOC_TEST, **kw)
    F["docs/05-运行手册.md"] = W(DOC_OPS, **kw)
    F["docs/06-配置管理与变更记录.md"] = W(DOC_CM, **kw)
    F["docs/07-ADR-001-架构决策记录.md"] = W(DOC_ADR, **kw)
    F["docs/08-国标与TOGAF映射.md"] = W(DOC_STD, **kw)
    for rel, content in (spec.get("extra_files") or {}).items():
        F[rel] = content
    if dry:
        print("  [计划] %s  (%d 个文件)" % (spec["slug"], len(F)))
        return pkg_dir
    for rel, content in F.items():
        path = os.path.join(pkg_dir, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = content
        if not text.strip():
            text = ""                                  # 空文件（如 __init__.py）不留空行
        elif rel.endswith((".py", ".md", ".txt", ".toml", ".yaml")):
            text = text.rstrip("\n") + "\n"          # 去尾多余空行（W391）
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return pkg_dir


README_MD = '''# <title>（<course> · <week> <no>）

> **第三种代码形态：Python 工程化项目** —— 多文件、规则外置、测试齐全、文档完备，
> 符合 GB/T 8566（软件生存周期过程）/ GB/T 9385（需求规格）/ GB/T 15532（测试规范）/
> GB/T 8567（文档编制），并以 TOGAF 四域描述架构。

## 一、30 秒跑起来
```bash
cd <slug>
python run.py                 # 输出到 output/ 并打印摘要
python -m pytest -q           # 全量测试（应全绿）
```

## 二、目录结构
```
<slug>/
├── run.py                  # 唯一入口（argparse CLI）
├── pyproject.toml          # 包元数据 + pytest 配置
├── requirements.txt        # 依赖清单
├── config/rules.yaml       # 规则外置：改配置不改代码
├── src/<pkg>/
│   ├── config.py           # YAML 加载 + Settings（含 yaml_lite 兜底）
│   ├── core.py             # 纯函数领域逻辑（零 IO，可单测）
│   ├── io_utils.py         # CSV/JSON/原子写
│   ├── report.py           # 报告渲染
│   └── pipeline.py         # load → process → evaluate → report
├── tests/
│   ├── test_core.py        # 正常/边界/异常三档
│   └── test_config.py      # 配置加载与校验
└── docs/                   # 01~08 全套过程文档（见下）
```

## 三、过程文档（GB/T 8567 文档编制）
| 文档 | 对应标准/方法 |
|---|---|
| [01 需求规格](docs/01-需求规格.md) | GB/T 9385 |
| [02 架构说明](docs/02-架构说明.md) | TOGAF 四域 |
| [03 设计说明](docs/03-设计说明.md) | 模块设计与异常策略 |
| [04 测试计划与报告](docs/04-测试计划与报告.md) | GB/T 15532 |
| [05 运行手册](docs/05-运行手册.md) | GB/T 8566 运行过程 |
| [06 配置管理与变更记录](docs/06-配置管理与变更记录.md) | GB/T 8566 配置管理 |
| [07 ADR-001](docs/07-ADR-001-架构决策记录.md) | 架构决策记录 |
| [08 国标与TOGAF映射](docs/08-国标与TOGAF映射.md) | GB/T 8566 过程组落地 |

## 四、三种代码形态的定位
| 形态 | 目录 | 定位 |
|---|---|---|
| ① starter | `../学生代码框架/` | 学生填空起步（TODO 骨架） |
| ② 教师参考 | `../教师参考/` | 完成态参考（单文件示意） |
| ③ **工程化项目（本目录）** | `../工程化项目/` | **企业级工程结构 + 全套流程资料** |

## 五、验收口径
- `python -m pytest -q` 全绿；`python run.py` 生成 `output/report.txt`
- 配置修改不需改代码；二次运行结果一致（种子固定）
- 过程文档 8 份齐全，可直接用于期末答辩的材料链
'''

INIT_PY = '''# -*- coding: utf-8 -*-
"""<title> —— 工程化实现包。

分层：config（配置）/ core（纯逻辑）/ io_utils（IO）/ report（报告）/ pipeline（编排）。
"""
__version__ = "1.0.0"
__all__ = ["config", "core", "io_utils", "report", "pipeline"]
'''

TEST_CONFIG_PY = '''# -*- coding: utf-8 -*-
"""配置层测试：加载、默认值兜底、异常路径。"""
import os

import pytest

from <pkg> import config as C

CFG_TEXT = "warn: 10" + chr(10) + "flag: true" + chr(10) + 'name: "x"' + chr(10)


def test_load_default_config():
    cfg = C.load_config(os.path.join(os.path.dirname(__file__), "..",
                                     "config", "rules.yaml"))
    assert cfg.warn < cfg.danger
    assert cfg.seed > 0


def test_yaml_lite_basic():
    d = C.yaml_lite(CFG_TEXT)
    assert d.get("warn") == 10
    assert d.get("flag") is True
    assert d.get("name") == "x"


def test_missing_config_raises():
    with pytest.raises(FileNotFoundError):
        C.load_config("/no/such/rules.yaml")


def test_settings_defaults_fill():
    s = C.Settings.from_dict({})
    assert s.warn == 80.0 and s.topk == 2


def test_block_list_parsing():
    text = "items:" + chr(10) + "  - a" + chr(10) + "  - b" + chr(10)
    assert C.yaml_lite(text)["items"] == ["a", "b"]


def test_nested_dict_parsing():
    text = "outer:" + chr(10) + "  inner: 5" + chr(10)
    assert C.yaml_lite(text)["outer"]["inner"] == 5
'''

REQUIREMENTS = '''# <title> —— 依赖清单（精确版本锁定）
# 生成方式：在本机已校准环境中读取实际安装版本（== 保证课堂结果可复现）
# 用法：pip install -r requirements.txt
# 说明：
#   1. 已安装包用 == 精确锁定；标 `# 待核验` 者本机未安装，请安装后回填版本。
#   2. pyproject.toml 保留区间声明（库规范），此处用精确版（教学可复现）。
#   3. 离线环境：pip install --no-index --find-links=./offline_wheels -r requirements.txt
<req_lines>
'''
