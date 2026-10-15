# -*- coding: utf-8 -*-
"""《Python程序设计（项目实战）》（pp03 环境）8 个工单的工程化项目规格。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eng_helpers import stories, funcs, tcases, adr, finalize

COURSE = "03-Python程序设计-项目实战"
ENV = "pp03"
SPECS = []


def P(**kw):
    SPECS.append(finalize(dict(course=COURSE, env=ENV, deps=kw.pop("deps", []), **kw)))


# ══════════ P1.1 Python 五题闯关 ══════════
P(id="03-P1.1", week="W01", no="第1次课", title="Python 五题闯关",
  slug="p11_exercises", pkg="exercise_five", deps=[],
  scope="C 底子转 Python 的五道标准题：单位换算器、一元二次方程、设备增删改查、"
        "PLC 子类、异常保护文件读取。每题独立函数+断言，跑通即交付。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
unit: "c"
seed: 7
topk: 3

devices:
  - id: 01
    name: 注塑机A
  - id: 02
    name: 冷却泵B
  - id: 03
    name: 空压机C
""",
  togaf=dict(
      business="新员工入职测评：吴工按五题结果定岗定层（D/C/B/A）",
      data="题目输入输出样例即数据契约（每题≥3组：正常/边界/异常）",
      application="单入口 run() 调度 5 个互不耦合的函数 t1()~t5()",
      technology="Python 3.12 + conda pp03；零第三方依赖；pytest",
  ),
  mods=[("core.py", "五题纯函数实现", "c_to_f()/quad()/crud()/plc()/safe_read()"),
        ("io_utils.py", "安全读文件", "safe_read_lines()")],
  stories=[("作为新员工，我希望五题都能独立运行", "每函数有 ≥3 组断言"),
           ("作为吴工，我希望用例覆盖边界", "空输入/极值/异常三档")],
  funcs=[("单位换算", "℃→℉ 带容差"), ("一元二次", "判别式三分支"),
         ("设备CRUD", "增删改查字典实现"), ("子类", "PLC 继承 Device"),
         ("安全读", "文件不存在返回标记")],
  design_core="五个函数零耦合、零全局状态；每函数三档测试（正常/边界/异常）；中文引号与 Tab 混用"
              "是本课两大高频陷阱，用测试固定行为。",
  test_cases=[("c_to_f", "换算", "0℃→32℉", "误差<1e-9"),
              ("quad", "方程", "判别式<0", "返回复根提示"),
              ("crud", "CRUD", "增/删", "字典长度变化正确")],
  adr=adr("五题用纯函数而非类",
          "周1目标是语法迁移；纯函数能聚焦'输入→输出'，不被类语法分散注意力",
          "A 纯函数（聚焦语法）｜B 类（引入额外概念）｜C 混合（不一致）",
          "A 纯函数", "每函数三行即可验证；测试直观", "暂不涉及状态管理", "低", "周7再引入类"),
  core_py='''# -*- coding: utf-8 -*-
"""五题实现：单位换算 / 一元二次 / 设备CRUD / PLC子类 / 安全读取。"""


def c_to_f(celsius):
    """摄氏度 → 华氏度。"""
    return celsius * 9.0 / 5.0 + 32.0


def kpa_to_mpa(kpa):
    return kpa / 1000.0


def quad(a, b, c):
    """一元二次方程：返回根列表；判别式<0 返回复根描述。"""
    d = b * b - 4 * a * c
    if d < 0:
        return ["complex"]
    if d == 0:
        return [-b / (2 * a)]
    import math
    r = math.sqrt(d)
    return [(-b + r) / (2 * a), (-b - r) / (2 * a)]


class Device:
    def __init__(self, code, name):
        self.code, self.name = code, name


class PLC(Device):
    """PLC 子类：扩展扫描周期（ms）。"""
    def __init__(self, code, name, scan_ms=100):
        super().__init__(code, name)
        self.scan_ms = scan_ms


class Registry:
    """设备增删改查（字典为存储，O(1) 查找）。"""
    def __init__(self):
        self._d = {}

    def add(self, dev):
        self._d[dev.code] = dev
        return dev

    def remove(self, code):
        return self._d.pop(code, None)

    def get(self, code):
        return self._d.get(code)

    def count(self):
        return len(self._d)


def safe_read(path):
    """异常保护读取：文件不存在返回标记而非崩溃。"""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "FILE_NOT_FOUND"

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""五题闯关流水线：逐题运行并把结果写入台账。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    results = []
    results.append(("t1 单位换算", "36℃ → %.2f℉" % core.c_to_f(36.0)))
    roots = core.quad(1, -3, 2)
    results.append(("t2 一元二次", "x^2-3x+2 → %s" % roots))
    results.append(("t2 边界", "判别式<0 → %s" % core.quad(1, 0, 1)))
    reg = core.Registry()
    for i, d in enumerate(cfg.items or [], 1):
        reg.add(core.PLC(str(d.get("id", i)), str(d.get("name", "设备")),
                         scan_ms=100 * i))
    results.append(("t3 设备CRUD", "注册 %d 台，删除后 %d 台"
                % (reg.count(), reg.count() - (1 if reg.remove("02") is not None else 0))))
    p = os.path.join(out_dir, "demo.txt")
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_text(p, "hello")
    results.append(("t4 PLC子类", "扫描周期 %dms"
                % (list(reg._d.values())[0].scan_ms if reg.count() else 100)))
    results.append(("t5 安全读取", "存在→%s / 不存在→%s"
                % (core.safe_read(p)[:5], core.safe_read("/no/such"))))
    result = {k: v for k, v in results}
    sections = [("输入口径", ["设备 %d 台｜题库 5 道（语法迁移）" % len(cfg.items or [])]),
                ("逐题结果", ["%s: %s" % (k, v) for k, v in results]),
                ("结论与建议", ["五题全过 = 及格（≥3题）；五题+边界断言+注释全齐 = 优秀（A层）"])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from exercise_five import core


def test_c_to_f_freezing_and_boiling():
    assert core.c_to_f(0) == 32.0 and core.c_to_f(100) == 212.0


def test_kpa_to_mpa():
    assert core.kpa_to_mpa(450.0) == 0.45


@pytest.mark.parametrize("a,b,c,exp", [(1, -3, 2, [2.0, 1.0]), (1, 2, 1, [-1.0])])
def test_quad_real_roots(a, b, c, exp):
    assert core.quad(a, b, c) == exp


def test_quad_complex_marker():
    assert core.quad(1, 0, 1) == ["complex"]


def test_quad_zero_discriminant_double_root():
    assert core.quad(1, -2, 1) == [1.0]


def test_registry_crud():
    reg = core.Registry()
    reg.add(core.Device("D1", "泵"))
    assert reg.count() == 1 and reg.get("D1").name == "泵"
    assert reg.remove("D1") is not None and reg.count() == 0
    assert reg.remove("NOPE") is None


def test_plc_inherits_device_and_extends():
    p = core.PLC("P1", "PLC", 50)
    assert isinstance(p, core.Device) and p.scan_ms == 50 and p.code == "P1"


def test_safe_read_missing_file():
    assert core.safe_read("/no/such/file") == "FILE_NOT_FOUND"

''')


# ══════════ P1.2 标准工程模板生成 ══════════
P(id="03-P1.2", week="W01", no="第2次课", title="标准工程模板生成",
  slug="p12_proj_template", pkg="proj_template", deps=[],
  scope="10 分钟内生成符合团队规范的 Python 工程骨架：src/tests/docs/config 四目录、"
        ".gitignore、README 三段、requirements 兜底；让新人第一天就按规范写代码。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
project_name: pump-ops
python_version: ">=3.10"
deps:
  - numpy
  - pandas
unit: "c"
seed: 7
topk: 3
""",
  togaf=dict(
      business="把'新人第一天的手工建目录'变成一键规范骨架，减少不规范代码的源头",
      data="项目名/依赖清单/起始配置 → 生成 10 个标准文件",
      application="模板文件用居中的常量表管理；新增文件=改表，不改逻辑",
      technology="Python 3.12 + conda pp03；仅标准库；pytest",
  ),
  mods=[("core.py", "模板定义 + 生成器 + 自检", "FILES()/ensure()/verify()"),
        ("io_utils.py", "原子写", "write_text()")],
  stories=[("作为组长，我希望新项目骨架统一", "10 文件齐备"), ("作为安全审计，我希望 .gitignore 一定在", "verify() 校验")],
  funcs=[("模板集中", "FILE_TEMPLATES 表驱动"), ("原子生成", "write_text()"), ("生成后自检", "verify()")],
  design_core="模板全集中在 `FILE_TEMPLATES`（src/init、tests、README、.gitignore）；"
              "生成后 verify() 强制校验必须文件在、空目录不存在——把目录结构纳入测试。",
  test_cases=[("template_files", "模板", "P2.5依赖为空", "仍生成 README/.gitignore"),
              ("verify", "自检", "生成后", "missing==[]"),
              ("verify", "自检", "空目录", "多余文件/空目录")],
  adr=adr("未安装可选依赖时用 requirements.txt 兜底而非 pyproject.toml",
          "课堂机器可能无法安装新版 setuptools；requirements.txt 是最通用兜底",
          "A pyproject（墙）｜B requirements.txt（稳）｜C both（重复真源）",
          "B requirements.txt", "最通用、最不易翻车；README 说明安装命令", "构建能力弱", "低", "README 已写"),
  core_py='''# -*- coding: utf-8 -*-
"""标准工程模板：表驱动 + 原子生成 + 生成后自检。"""
import os

README = """# {name}

## 一、跑起来
```bash
pip install -r requirements.txt
python run.py
python -m pytest -q
```

## 二、目录
- src/（包代码，按层拆 module）
- tests/（pytest，正常/边界/异常三档）
- docs/（过程文档）
- config/（YAML，规则外置）

## 三、提交历史
- 分支 main 保护；提交信息 feat:/fix:/docs:/test:
"""

GITIGNORE = """__pycache__/
*.py[cod]
.pytest_cache/
.venv/
output/*.log
"""


def file_templates(name, deps):
    """返回 {相对路径: 内容}（表驱动，新增文件只需加一行）。"""
    return {
        "README.md": README.format(name=name),
        ".gitignore": GITIGNORE,
        "requirements.txt": "\\n".join(["# %s 依赖" % name] + list(deps)) + "\\n",
        "src/__init__.py": '"""%s 实现包。"""\\n__version__ = "1.0.0"\\n' % name,
        "tests/__init__.py": "",
        "run.py": "print('hello %s')\\n" % name,
    }


def ensure(root, files):
    """原子生成；已存在则不覆盖（防误覆盖）。"""
    made, kept = [], []
    for rel, content in files.items():
        path = os.path.join(root, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if os.path.exists(path):
            kept.append(rel)
            continue
        with open(path, "w", encoding="utf-8", newline="\\n") as f:
            f.write(content)
        made.append(rel)
    return made, kept


def verify(root, files):
    """生成后自检：必须文件都在、无空目录、无 .pyc。"""
    missing = [rel for rel in files
               if not os.path.exists(os.path.join(root, rel.replace("/", os.sep)))]
    empty_dirs, junk = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath == root or "__pycache__" in dirpath:
            continue
        if not filenames and not dirnames:
            empty_dirs.append(os.path.relpath(dirpath, root))
        junk += [f for f in filenames if f.endswith(".pyc")]
    return {"missing": missing, "empty_dirs": empty_dirs, "junk": junk}

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""按配置生成标准工程骨架，并强制自检。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    import tempfile
    name = str(cfg.raw.get("project_name", "pump-ops"))
    deps = cfg.raw.get("deps") or []
    root = os.path.join(out_dir, "skeleton")
    os.makedirs(root, exist_ok=True)
    files = core.file_templates(name, deps)
    made, kept = core.ensure(root, files)
    rep = core.verify(root, files)
    ok = not rep["missing"] and not rep["empty_dirs"] and not rep["junk"]
    result = {"name": name, "n_files": len(files), "made": made,
              "kept": kept, "verify": rep, "passed": ok}
    sections = [("输入口径", ["项目 %s｜依赖 %s｜模板 %d 个文件"
                        % (name, "/".join(deps) or "无", len(files))]),
                ("生成结果", ["新建 %d 个：%s" % (len(made), ", ".join(made)),
                          "已存在跳过 %d 个" % len(kept)]),
                ("自检", ["missing=%d empty_dirs=%d junk=%d"
                       % (len(rep["missing"]), len(rep["empty_dirs"]), len(rep["junk"]))]),
                ("结论与建议", ["骨架自检 %s；新人第一天就在规范结构里写代码"
                          % ("通过" if ok else "失败——请检查模板表")])]
    os.makedirs(out_dir, exist_ok=True)
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import os

from proj_template import core


def test_file_templates_core_files_present():
    f = core.file_templates("proj", [])
    for k in ("README.md", ".gitignore", "src/__init__.py", "tests/__init__.py"):
        assert k in f


def test_file_templates_deps_written():
    f = core.file_templates("proj", ["numpy"])
    assert "numpy" in f["requirements.txt"]


def test_ensure_idempotent(tmp_path):
    f = core.file_templates("proj", ["pandas"])
    m1, k1 = core.ensure(str(tmp_path), f)
    m2, k2 = core.ensure(str(tmp_path), f)
    assert len(m1) == len(f) and not k1
    assert m2 == [] and len(k2) == len(f)


def test_verify_passes_after_ensure(tmp_path):
    f = core.file_templates("proj", ["pandas"])
    core.ensure(str(tmp_path), f)
    rep = core.verify(str(tmp_path), f)
    assert rep["missing"] == [] and rep["junk"] == []

''')


# ══════════ P2.1 Pandas 数据清洗 ══════════
P(id="03-P2.1", week="W03", no="第5次课", title="Pandas 数据清洗管道",
  slug="p21_pandas_clean", pkg="pd_clean", deps=["pandas"],
  scope="把单文件版清洗升级为工程化：loader/cleaner 分层单一职责、规则外置 YAML、"
        "pytest≥5、口径文档化——同一任务'改规则只改1行YAML'。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
temp_max: 120.0
vib_min: 0.0
vib_max: 15.0
target_quality: 0.85
unit: "c"
seed: 7
topk: 3
""",
  togaf=dict(business="把'跑一次就扔'的清洗脚本变成可维护、可复现的数据管道",
             data="原始CSV → 规则化清洗 → 质量分 + 前后对比留痕",
             application="core 为规则表驱动清洗（纯函数）；io_utils 负责 CSV 读写",
             technology="Python 3.12 + conda pp03；pandas；pytest"),
  mods=[("core.py", "规则表驱动清洗 + 质量分", "RULES/clean()/quality()"),
        ("io_utils.py", "CSV 原子读写", "read_csv_rows()/write_csv_rows()")],
  stories=[("作为工程师，我希望改清洗规则不改代码", "YAML 外置"),
           ("作为质量员，我希望每次清洗都有留痕", "前后行数+分布快照")],
  funcs=[("规则外置", "YAML→清洗规则"), ("管道化", "loader→cleaner 分层"),
         ("质量门禁", "低于阈值告警")],
  design_core="清洗动作是**规则表**（RULES 列表），YAML 只给参数；管道分 loader/cleaner 两层，"
              "各自可单测；质量分低于目标值即视为门禁失败。",
  test_cases=[("clean", "清洗", "脏数据", "行数减少"),
              ("quality", "质量分", "清洗后", "≥target"), ("门禁", "阈值", "低质量数据", "返回 False")],
  adr=adr("清洗规则用 YAML 外置而非写死在代码",
          "产线规则随工艺调整；写死意味着每次都要改代码+走发布，且易漏改",
          "A 硬编码（快但难维护）｜B YAML 外置（改配置即生效）｜C 数据库规则表（过度）",
          "B YAML 外置", "改1行YAML即可；规则表本身就是文档；课堂对比实验可直接演示",
          "配置错误运行期才暴露", "低", "启动校验阈值顺序"),
  core_py='''# -*- coding: utf-8 -*-
"""规则表驱动的 Pandas 清洗管道（纯函数，无 IO）。"""
import pandas as pd


def make_dirty(n=200, seed=7):
    """合成含脏数据的 CSV（用于课堂对比实验）。"""
    import numpy as np
    rng = np.random.RandomState(seed)
    df = pd.DataFrame({
        "ts": pd.date_range("2026-03-01", periods=n, freq="h"),
        "vib": rng.normal(4.0, 0.5, n).round(3),
        "temp": rng.normal(55, 3, n).round(1)})
    df.loc[rng.choice(n, 10, replace=False), "vib"] = np.nan
    df.loc[rng.choice(n, 4, replace=False), "temp"] = 135.0
    df.loc[rng.choice(n, 4, replace=False), "vib"] = -1.0
    return df


def clean(df, temp_max=120.0, vib_min=0.0, vib_max=15.0):
    """三段式：去重 → 剔缺失 → 剔越界（顺序固定，保证口径可复现）。"""
    return (df.drop_duplicates()
              .dropna(subset=["vib"])
              .query("vib >= @vib_min and vib <= @vib_max and temp <= @temp_max")
              .reset_index(drop=True))


def quality(df, temp_max=120.0, vib_min=0.0, vib_max=15.0):
    """质量分 = 完整率 × 合理率。"""
    if len(df) == 0:
        return 0.0
    complete = float(df["vib"].notna().mean())
    valid = float(((df["vib"].between(vib_min, vib_max)) & (df["temp"] <= temp_max)).mean())
    return round(complete * valid, 4)


def gate(score, target=0.85):
    """质量门禁：低于目标即失败。"""
    return score >= target

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""合成脏数据 → 清洗 → 质量分 → 门禁 → 留痕。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    import pandas as pd
    tmax = float(cfg.raw.get("temp_max", 120.0))
    target = float(cfg.raw.get("target_quality", 0.85))
    raw = core.make_dirty()
    n0 = len(raw)
    c = core.clean(raw.copy(), tmax)
    q = core.quality(c, tmax)
    ok = core.gate(q, target)
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_csv_rows(os.path.join(out_dir, "clean.csv"),
                            c.to_dict("records"))
    result = {"rows_before": n0, "rows_after": len(c), "removed": n0 - len(c),
              "quality": q, "target": target, "gate_passed": ok}
    sections = [("输入口径", ["原始 %d 行｜温度上限 %.0f℃｜质量目标 %.2f" % (n0, tmax, target)]),
                ("清洗留痕", ["%d 行 → %d 行（剔除 %d 行）" % (n0, len(c), n0 - len(c))]),
                ("质量分", ["%.4f（目标 %.2f）→ 门禁 %s" % (q, target, "通过" if ok else "未通过")]),
                ("结论与建议", ["规则已外置 YAML：改 temp_max/vib 区间只需改配置，代码零改动"])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
from pd_clean import core


def test_clean_reduces_rows_and_removes_bad():
    df = core.make_dirty(n=200, seed=7)
    c = core.clean(df.copy())
    assert len(c) < len(df)
    assert c["vib"].min() >= 0.0 and c["temp"].max() <= 120.0


def test_clean_is_deduped():
    import pandas as pd
    df = pd.DataFrame({"vib": [1.0, 1.0], "temp": [10.0, 10.0]})
    assert len(core.clean(df)) == 1


def test_quality_between_0_and_1():
    df = core.make_dirty(200, 7)
    c = core.clean(df.copy())
    q = core.quality(c)
    assert 0.0 <= q <= 1.0 and q > 0.8


def test_gate_true_when_above_target():
    assert core.gate(0.9, 0.85) is True


def test_gate_false_when_below_target():
    assert core.gate(0.5, 0.85) is False


def test_empty_frame_quality_zero():
    import pandas as pd
    assert core.quality(pd.DataFrame({"vib": [], "temp": []})) == 0.0

''')


# ══════════ P2.2 特征工厂 ══════════
P(id="03-P2.2", week="W04", no="第7次课", title="特征工厂",
  slug="p22_feature_factory", pkg="feat_factory", deps=["numpy", "scikit-learn"],
  scope="从振动信号批量提取 13 维时域特征 + 4 维频域特征，并用特征重要性证明"
        "'16Hz 二倍频'才是磨损的判别指纹——特征设计直接决定模型上限。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=42, topk=6),
  rules_yaml="""warn: 80.0
danger: 95.0
n_windows: 40
n_features: 17
unit: "c"
seed: 42
topk: 6
image_shape: 64
""",
  togaf=dict(business="把'凭经验挑特征'变成可复用的特征工厂，模型效果可追溯",
             data="振动窗口 → 13维时域+4维频域 → 标签；输出特征表+重要性",
             application="core 造信号/提特征/训练排序；pipeline 输出 Top-N 与可解释结论",
             technology="Python 3.12 + conda pp03；numpy/sklearn；pytest"),
  mods=[("core.py", "信号生成 + 13+4 特征", "make_window()/feats_time()/feats_freq()"),
        ("io_utils.py", "CSV/JSON 落盘", "write_csv_rows()/write_json()")],
  stories=[("作为工程师，我希望一次拿到17维特征", "17 列"), ("作为讲师，我希望验证 a16 是关键", "重要性 Top1/2")],
  funcs=[("时域13维", "RMS/方差/峭度/…"), ("频域4维", "主频+频带能量"),
         ("重要性证明", "RF 排序")],
  design_core="每个特征一个纯函数，可单独断言；频域特征用 rfft 并做差分去趋势；"
              "重要性用 RF 输出，训练集固定种子。",
  test_cases=[("feats_time", "时域", "1 个窗口", "13 个数"),
              ("feats_freq", "频域", "1 个窗口", "4 个数")],
  adr=adr("窗口重叠+多随机实现扩展样本而非单窗口",
          "单窗口只有2个样本，特征重要性完全被噪声主导",
          "A 单窗口（样本太少）｜B 重叠滑动（部分独立）｜C 多随机实现（真正独立）",
          "C 多随机实现", "42 个独立窗口 → 重要性稳定；课堂 30 秒可复现",
          "耗时略增", "低", "n_windows 可配置"),
  core_py='''# -*- coding: utf-8 -*-
"""特征工厂：13 维时域 + 4 维频域（纯函数，可逐特征断言）。"""
import numpy as np

TIME_FEATS = ["mean", "max", "min", "median", "var", "std", "skew", "q25", "q75",
              "p05", "p95", "iqr", "rms"]


def make_window(kind, size=64, seed=None):
    """生成一个振动窗口：normal（平稳）/ abnormal（叠加冲击+抬升）。"""
    rng = np.random.RandomState(seed)
    x = rng.normal(0, 1, size)
    if kind == "abnormal":
        x[rng.randint(0, size, 5)] += 3.0        # 冲击
        x += 1.5                                  # 整体抬升
    return x


def feats_time(x):
    """13 维时域特征（固定顺序）。"""
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        raise ValueError("窗口为空")
    q = np.percentile(x, [5, 25, 50, 75, 95])
    return [
        float(x.mean()), float(x.max()), float(x.min()), float(np.median(x)),
        float(x.var()), float(x.std()), float(((x - x.mean()) ** 3).mean() / (x.std() ** 3 + 1e-12)),
        float(q[1]), float(q[3]), float(q[0]), float(q[4]), float(q[3] - q[1]),
        float(np.sqrt((x ** 2).mean())),
    ]


def feats_freq(x, fs=64.0):
    """4 维频域特征：主频 + 3 个频带能量比。"""
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        raise ValueError("窗口为空")
    spec = np.abs(np.fft.rfft(x - x.mean()))
    freqs = np.fft.rfftfreq(x.size, 1 / fs)
    total = spec.sum() + 1e-12
    main_f = float(freqs[np.argmax(spec)])
    bands = [(0, fs / 8), (fs / 8, fs / 4), (fs / 4, fs / 2)]
    return [main_f] + [float(spec[(freqs >= lo) & (freqs < hi)].sum() / total)
                       for lo, hi in bands]


def feature_names():
    return TIME_FEATS + ["main_freq", "band1", "band2", "band3"]

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""生成窗口矩阵 → 提取 17 维特征 → 固定顺序 CSV/JSON。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    n = int(cfg.raw.get("n_windows", 40))
    image_shape = int(cfg.raw.get("image_shape", 64))
    rng = np.random.RandomState(cfg.seed)
    rows, labels = [], []
    for i in range(n):
        kind = "normal" if i % 2 == 0 else "abnormal"
        x = core.make_window(kind, size=image_shape, seed=int(rng.randint(0, 100000)))
        rows.append([round(v, 6) for v in core.feats_time(x) + core.feats_freq(x)])
        labels.append(0 if kind == "normal" else 1)
    X = np.array(rows, dtype=float)
    if np.isnan(X).any():
        raise ValueError("特征矩阵含 NaN——请检查特征函数")
    clf = RandomForestClassifier(random_state=0).fit(X, labels)
    names = core.feature_names()
    order = sorted(range(len(names)), key=lambda i: -clf.feature_importances_[i])
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_csv_rows(os.path.join(out_dir, "features.csv"),
                            [dict(zip(names, r)) for r in rows])
    result = {"n_windows": n, "n_features": len(names),
              "top": [(names[i], round(float(clf.feature_importances_[i]), 4))
                      for i in order[:int(cfg.topk)]]}
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    sections = [("输入口径", ["窗口 %d 个｜特征 %d 维（时域13+频域4）"
                    % (n, len(names))]),
            ("Top 特征", ["%d. %s = %.3f" % (k + 1, names[i], clf.feature_importances_[i])
                     for k, i in enumerate(order[:int(cfg.topk)])]),
            ("结论与建议", ["特征设计决定模型上限；把重要性最高的特征做成可解释的业务指标"])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import numpy as np
import pytest

from feat_factory import core


def test_feats_time_returns_13():
    x = np.arange(20, dtype=float)
    f = core.feats_time(x)
    assert len(f) == 13 and all(isinstance(v, float) for v in f)


def test_feats_freq_returns_4():
    x = np.sin(np.linspace(0, 8, 64))
    f = core.feats_freq(x)
    assert len(f) == 4


def test_make_window_kind():
    a = core.make_window("normal", 32, 1)
    b = core.make_window("abnormal", 32, 1)
    assert a.shape == b.shape == (32,)
    assert b.mean() > a.mean()


def test_feats_empty_raises():
    with pytest.raises(ValueError):
        core.feats_time([])


def test_feature_names_count():
    assert len(core.feature_names()) == 17

''')


# ══════════ P3 KPI 驾驶舱 ══════════
P(id="03-P3", week="W05", no="第9次课", title="KPI 驾驶舱",
  slug="p33_kpi_cockpit", pkg="kpi_cockpit", deps=[],
  scope="5 个 KPI 一屏掌：合格率/OEE/告警数/在线率/达成率，"
        "用等宽文本表 + JSON 输出；streamlit 版为可选升级（特性探测降级）。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=5),
  rules_yaml="""warn: 80.0
danger: 95.0
unit: "c"
seed: 7
topk: 5

lines:
  - line: 一号产线
    planned: 960
    produced: 912
    good: 896
    oee: 86.6
  - line: 二号产线
    planned: 840
    produced: 806
    good: 791
    oee: 83.4
""",
  togaf=dict(business="让班组长 30 秒看全产线健康度，早会不再翻系统",
             data="KPI 行 → 派生指标（合格率/达成率）→ 文本表+JSON",
             application="core 计算派生指标与等宽表；pipeline 输出并可探测 streamlit",
             technology="Python 3.12 + conda pp03；零依赖可跑；pytest"),
  mods=[("core.py", "派生指标 + 等宽渲染", "derive()/render()"),
        ("io_utils.py", "JSON/文本落盘", "write_json()/write_text()")],
  stories=[("作为班组长，我希望一屏看全 5 个 KPI", "派生指标齐全"),
           ("作为讲师，我希望无 streamlit 也能跑", "特性探测降级")],
  funcs=[("派生指标", "合格率/达成率"), ("等宽表", "中文对齐计算"),
         ("降级策略", "streamlit 可选")],
  design_core="指标计算为纯函数；等宽表用**字符宽度估算**（CJK=2、ASCII=1）保证中文列对齐；"
              "streamlit 用 try-import 探测，缺失时输出文本版。",
  test_cases=[("derive", "合格率", "896/912", "0.9825"),
              ("render", "对齐", "含中文列名", "行宽一致")],
  adr=adr("等宽表按 CJK=2/ASCII=1 计算列宽",
          "直接 len() 统计会把中文按 1 字符算，导致中文列参差不齐",
          "A len()（中文错位）｜B 宽度估算（对齐）｜C 引入 rich（额外依赖）",
          "B 宽度估算", "零依赖且中文对齐；30 行代码可解释", "全角/半角混合需注意", "低", "w() 函数集中处理"),
  core_py='''# -*- coding: utf-8 -*-
"""KPI 驾驶舱：派生指标 + 等宽中文表（纯函数）。"""


def derive(k):
    produced, planned, good = float(k["produced"]), float(k["planned"]), float(k["good"])
    return {"line": str(k["line"]), "planned": int(planned), "produced": int(produced),
            "good": int(good), "oee": float(k["oee"]),
            "good_rate": round(good / produced, 4) if produced else 0.0,
            "plan_rate": round(produced / planned, 4) if planned else 0.0}


def w(s):
    """显示宽度：CJK=2，其它=1。"""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def render(rows, headers):
    """等宽文本表（中文对齐）。

    程序化发现：推导式/生成器的循环变量不得与函数后续变量同名
    （Python 闭包作用域会抛 NameError: cannot access free variable）。
    """
    cols = [list(headers)] + [[str(c) for c in row] for row in rows]
    widths = [max(w(row[i]) for row in cols) for i in range(len(headers))]

    def pad(s, n):
        s = str(s)
        return s + " " * (n - w(s))

    def line(row):
        return "  ".join(pad(row[i], widths[i]) for i in range(len(headers)))

    out = [line(cols[0]), "  ".join("-" * x for x in widths)]
    out += [line(row) for row in cols[1:]]
    return chr(10).join(out)


def table_rows(rows):
    hdr = ("产线", "计划", "产出", "合格", "合格率", "达成率", "OEE%")
    body = [(r["line"], str(r["planned"]), str(r["produced"]), str(r["good"]),
             "%.2f%%" % (r["good_rate"] * 100), "%.2f%%" % (r["plan_rate"] * 100),
             "%.1f%%" % r["oee"]) for r in rows]
    return [hdr] + body

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""KPI 行 → 派生指标 → 等宽表 → JSON（streamlit 可选降级）。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    rows = [core.derive(r) for r in (cfg.items or [])]
    if not rows:
        raise ValueError("config/rules.yaml 的 lines 为空")
    tbl = core.table_rows(rows)
    worst = min(rows, key=lambda r: r["good_rate"])
    result = {"rows": rows, "worst": worst["line"]}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "kpi.json"), result)
    try:
        import streamlit                                    # noqa: F401
        note = "streamlit 已安装——可运行 `streamlit run app.py` 升级为交互仪表盘"
    except ImportError:
        note = "未装 streamlit：本次输出文本版（特性探测降级，主流程不受影响）"
    sections = [("输入口径", ["产线 %d 条｜5 个 KPI（合格率/OEE/告警/在线/达成）" % len(rows)]),
                ("KPI 驾驶舱", core.render(tbl[1:], tbl[0]).splitlines()),
                ("关注项", ["最低合格率 %.2f%%（%s）需当日复盘"
                        % (worst["good_rate"] * 100, worst["line"])]),
                ("升级路径", [note])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from kpi_cockpit import core


def test_derive_rates():
    r = core.derive({"line": "A", "planned": 100, "produced": 80, "good": 70, "oee": 50.0})
    assert r["good_rate"] == 0.875 and r["plan_rate"] == 0.8


def test_derive_zero_division_safe():
    r = core.derive({"line": "A", "planned": 0, "produced": 0, "good": 0, "oee": 0})
    assert r["good_rate"] == 0.0 and r["plan_rate"] == 0.0


def test_width_cjk_is_two():
    assert core.w("产线") == 4 and core.w("A1") == 2


def test_render_alignment_by_display_width():
    """对齐按'显示宽度'（CJK=2）而非字符数——这是中文表格的正确口径。"""
    rows = [("一号产线", "960"), ("B", "10")]
    out = core.render(rows, ("产线", "计划")).splitlines()
    assert len({core.w(ln) for ln in out}) == 1


def test_render_first_cell_padded_to_width():
    rows = [("一号产线", "960")]
    out = core.render(rows, ("产线", "计划")).splitlines()[2]
    assert core.w(out.split("  ")[0]) == 8


def test_table_rows_shape():
    rows = [core.derive({"line": "A", "planned": 10, "produced": 9, "good": 8, "oee": 50.0})]
    tbl = core.table_rows(rows)
    assert len(tbl) == 2 and len(tbl[0]) == 7

''')


# ══════════ P4 多源数据采集中枢 ══════════
P(id="03-P4", week="W06", no="第11次课", title="多源数据采集中枢",
  slug="p41_collector_hub", pkg="collector_hub", deps=[],
  scope="三个'PLC'（本地模拟）同时说话：轮询读取 → 单位换算 → 对账恒等式校验 → "
        "本地缓存 + 断线退避重连，体现'宁可慢不可丢'。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
batch_size: 3
poll_rounds: 4
backoff_base: 0.01
unit: "c"
seed: 7
topk: 3

sources:
  - id: PLC1
    host: 127.0.0.1
    port: 5020
    scale: 10
  - id: PLC2
    host: 127.0.0.1
    port: 5021
    scale: 1
""",
  togaf=dict(business="设备数据可靠汇聚为集团级数据底座",
             data="各源寄存器原值 → ÷scale 还原 → batch；对账恒等式 Σ批次=Σ单条",
             application="core 生成读数/换算/切批/对账；pipeline 轮询多轮并统计",
             technology="Python 3.12 + conda pp03；零依赖可跑（pymodbus 可选）；pytest"),
  mods=[("core.py", "读数生成/换算/对账/退避", "read()/restore()/reconcile()/sleep_with()"),
        ("io_utils.py", "JSON 落盘", "write_json()")],
  stories=[("作为运维，我希望断线能退避重连", "指数退避"), ("作为质量员，我希望对账不平就报错", "恒等式校验")],
  funcs=[("寄存器读取", "可注入 transport"), ("单位还原", "÷scale"),
         ("对账恒等", "Σ批次=Σ单条"), ("退避重连", "指数退避")],
  design_core="registry_rate 由 transport 注入（测试用 fake）；对账为**恒等式校验**"
              "（Σ批次 == Σ单条），把'丢数'变成可断言；sleep 也注入以便测试。",
  test_cases=[("restore", "还原", "250/scale=10", "25.0"),
              ("reconcile", "对账", "一致", "True"),
              ("reconcile", "对账", "不一致", "False")],
  adr=adr("对账用Σ批次==Σ单条恒等式而非重新读取",
          "重新读取会改变系统状态且仍有幂等问题；恒等式是零副作用的校验",
          "A 重新读取比对（有副作用）｜B 恒等式校验（零副作用）｜C 不校验（风险）",
          "B 恒等式校验", "纯内存计算、零副作用、可 100% 覆盖测试",
          "无法发现'源头就错'", "低", "源头侧另做校验"),
  core_py='''# -*- coding: utf-8 -*-
"""采集中枢：读数、还原、对账恒等式、指数退避（transport 可注入）。"""


def read(transport, src):
    """从指定源读一批寄存器原值（transport 可注入，便于测试）。"""
    return [transport(src) for _ in range(int(src.get("n", 3)))]


def restore(raw, scale):
    """单位还原：寄存器原值 ÷ scale。"""
    if scale <= 0:
        raise ValueError("scale 必须为正（当前 %.3f）" % scale)
    return [v / scale for v in raw]


def reconcile(batches, flat):
    """对账恒等式：Σ批次应等于 Σ单条。"""
    sb = sum(sum(b) for b in batches)
    sf = sum(flat)
    return abs(sb - sf) < 1e-9, round(sb - sf, 9)


def sleep_with(backoff_base, attempt):
    """指数退避：base × 2^attempt。"""
    return backoff_base * (2 ** attempt)

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""多源轮询 → 还原 → 切批 → 对账 → 落盘。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    sources = list(cfg.items or [])
    if not sources:
        raise ValueError("config/rules.yaml 的 sources 为空")
    batch_size = int(cfg.raw.get("batch_size", 3))
    rounds = int(cfg.raw.get("poll_rounds", 4))
    # transport：无 pymodbus 用确定性本地模拟（课堂可跑）

    def transport(src):
        seed = abs(hash(str(src.get("id")))) % 1000
        return 250 + (seed % 7)

    all_batches, flat, per_source = [], [], {}
    for src in sources:
        sid = str(src.get("id", "PLC"))
        scale = float(src.get("scale", 1))
        sflat = []
        for r in range(rounds):
            raw = core.read(transport, src)
            vals = core.restore(raw, scale)
            sflat += vals
            all_batches.append(vals)
        per_source[sid] = {"n": len(sflat), "sum": round(sum(sflat), 4),
                           "mean": round(sum(sflat) / len(sflat), 4)}
        flat += sflat
    ok, diff = core.reconcile(all_batches, flat)
    result = {"sources": {k: v["n"] for k, v in per_source.items()},
              "per_source": per_source, "reconcile": {"ok": ok, "diff": diff},
              "n_total": len(flat)}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    sections = [("输入口径", ["数据源 %d 个｜每源 %d 轮×%d 条｜批量 %d 条"
                        % (len(sources), rounds, batch_size, batch_size)]),
                ("分源统计", ["%s: %d 条 均值 %.3f" % (k, v["n"], v["mean"])
                          for k, v in per_source.items()]),
                ("对账", ["Σ批次 - Σ单条 = %.9f → %s" % (diff, "通过" if ok else "失败")]),
                ("结论与建议", ["对账恒等式通过，说明切批与汇总无丢失；"
                          "断线时按 %.2fs 起指数退避重连" % cfg.raw.get("backoff_base", 0.01)])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from collector_hub import core


def test_restore_divides_by_scale():
    assert core.restore([250, 300], 10) == [25.0, 30.0]


@pytest.mark.parametrize("s", [0, -1])
def test_restore_rejects_non_positive_scale(s):
    with pytest.raises(ValueError):
        core.restore([1], s)


def test_reconcile_true_when_sum_matches():
    ok, diff = core.reconcile([[1.0, 2.0], [3.0]], [1.0, 2.0, 3.0])
    assert ok and diff == 0.0


def test_reconcile_false_when_sum_differs():
    ok, diff = core.reconcile([[1.0, 2.0]], [1.0, 2.0, 9.0])
    assert not ok and abs(diff + 9.0) < 1e-9


def test_sleep_with_exponential():
    assert core.sleep_with(0.01, 0) == 0.01
    assert core.sleep_with(0.01, 3) == 0.08


def test_read_uses_injected_transport():
    src = {"id": "P", "n": 3}
    out = core.read(lambda s: 250, src)
    assert out == [250, 250, 250]

''')


# ══════════ P5 数据仓库 ORM ══════════
P(id="03-P5", week="W07", no="第13次课", title="数据仓库 ORM",
  slug="p55_warehouse_orm", pkg="warehouse_orm", deps=[],
  scope="不写 SQL 也能操作数据库：手写一个极简 ORM（内存表+索引），支持"
        "条件查询、批量写入、外键约束与查询计划（是否走索引）。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=7, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
n_records: 500
index_col: device_id
unit: "c"
seed: 7
topk: 3
""",
  togaf=dict(business="让不熟悉 SQL 的学员也能可靠操作数据，并理解'为什么慢'",
             data="内存表（list of dict）+ 倒排索引；查询计划标注是否走索引",
             application="core 提供 Table/index/查询计划；pipeline 批量造数+对比演示",
             technology="Python 3.12 + conda pp03；零第三方依赖（sqlite3 可选）；pytest"),
  mods=[("core.py", "极简 ORM：建表/索引/查询/计划", "Table/create_index()/where()/explain()"),
        ("io_utils.py", "JSON 落盘", "write_json()")],
  stories=[("作为学员，我希望不写SQL也能查数据", "where()"), ("作为工程师，我想知道查询有没有走索引", "explain()")],
  funcs=[("建表", "字段类型约束"), ("索引", "倒排，O(1) 定位"),
         ("查询", "等值/范围/多条件"), ("查询计划", "是否走索引")],
  design_core="表为 list[dict]；索引为 value→set(row_idx) 倒排；`where()` 在**有索引且单等值条件**时"
              "走索引，否则全表扫描；`explain()` 明示走了哪条路径（可断言）。",
  test_cases=[("where", "等值+索引", "device_id=X", "返回匹配行"),
              ("where", "无索引", "范围查询", "全表扫描结果正确"),
              ("explain", "计划", "有索引等值", "标注 INDEX")],
  adr=adr("自研极简 ORM 而非直接引入 SQLAlchemy",
          "周7的目标是理解 ORM 在做什么（对象↔关系映射、索引、查询计划）；直接引入重库会把这层变成黑箱",
          "A SQLAlchemy（功能全但黑箱）｜B 自研极简 ORM（原理可见）｜C 直接 sqlite3+SQL（绕开ORM概念）",
          "B 自研极简 ORM", "30 行代码讲透映射/索引/计划；零依赖；README 说明生产用 SQLAlchemy",
          "功能远少于生产 ORM", "低", "README 标注生产选型"),
  core_py='''# -*- coding: utf-8 -*-
"""极简 ORM：内存表 + 倒排索引 + 查询计划（零依赖，原理可见）。"""


class Table:
    """内存表：字段约束 + 行存储 + 倒排索引。"""

    def __init__(self, name, fields):
        if not fields:
            raise ValueError("表 %s 未定义字段" % name)
        self.name = name
        self.fields = list(fields)
        self.rows = []
        self.indexes = {}          # col -> {value: set(row_idx)}

    def insert(self, rec):
        missing = [f for f in self.fields if f not in rec]
        if missing:
            raise ValueError("缺少字段: %s" % missing)
        idx = len(self.rows)
        self.rows.append(dict(rec))
        for col, inv in self.indexes.items():
            inv.setdefault(rec[col], set()).add(idx)
        return idx

    def create_index(self, col):
        if col not in self.fields:
            raise ValueError("字段不存在: %s" % col)
        inv = {}
        for i, r in enumerate(self.rows):
            inv.setdefault(r[col], set()).add(i)
        self.indexes[col] = inv
        return col

    def where(self, **kw):
        """等值查询：有索引走索引，否则全表扫描。"""
        if len(kw) == 1:
            (col, val), = kw.items()
            if col in self.indexes:
                return [self.rows[i] for i in sorted(self.indexes[col].get(val, set()))]
        return [r for r in self.rows
                if all(r.get(k) == v for k, v in kw.items())]

    def explain(self, **kw):
        if len(kw) == 1:
            (col, _), = kw.items()
            if col in self.indexes:
                return "INDEX SCAN on %s" % col
        return "FULL SCAN on %s" % self.name

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""造数 → 建索引 → 查询（有计划标注）→ 落盘。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    n = int(cfg.raw.get("n_records", 500))
    idx_col = str(cfg.raw.get("index_col", "device_id"))
    t = core.Table("sensor_log", ["device_id", "temp", "press"])
    for i in range(n):
        t.insert({"device_id": "DEV-%02d" % (i % 10 + 1),
                  "temp": round(20 + (i % 70) * 0.5, 1),
                  "press": round(0.2 + (i % 30) * 0.01, 3)})
    t.create_index(idx_col)
    q = {"device_id": "DEV-03"}
    hit = t.where(**q)
    import time
    t0 = time.time()
    for _ in range(200):
        t.where(**q)
    idx_ms = (time.time() - t0) / 200 * 1000
    t0 = time.time()
    for _ in range(20):
        t.where(temp=50.0)
    full_ms = (time.time() - t0) / 20 * 1000
    result = {"n_records": n, "index_col": idx_col, "hits": len(hit),
              "plan_indexed": t.explain(**q),
              "plan_full": t.explain(temp=50.0),
              "index_ms": round(idx_ms, 4), "full_ms": round(full_ms, 4)}
    os.makedirs(out_dir, exist_ok=True)
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    sections = [("输入口径", ["%d 条记录｜索引列 %s｜字段 device_id/temp/press" % (n, idx_col)]),
                ("查询计划", ["等值+索引: %s（%.4f ms）" % (t.explain(**q), idx_ms),
                          "无索引范围: %s（%.4f ms）" % (t.explain(temp=50.0), full_ms)]),
                ("查询结果", ["device_id=DEV-03 命中 %d 条" % len(hit)]),
                ("结论与建议", ["索引只加速'等值+高选择率'查询；范围/低选择率仍走全表扫描——"
                          "这就是生产库要写查询计划的原因"])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from warehouse_orm import core


@pytest.fixture
def tbl():
    t = core.Table("t", ["device_id", "temp"])
    for i in range(5):
        t.insert({"device_id": "DEV-01" if i % 2 else "DEV-02", "temp": float(i)})
    t.create_index("device_id")
    return t


def test_insert_requires_all_fields():
    t = core.Table("t", ["a", "b"])
    with pytest.raises(ValueError):
        t.insert({"a": 1})


def test_table_requires_fields():
    with pytest.raises(ValueError):
        core.Table("t", [])


def test_where_with_index_uses_index(tbl):
    assert tbl.explain(device_id="DEV-01") == "INDEX SCAN on device_id"


def test_where_without_index_full_scan(tbl):
    assert tbl.explain(temp=3.0) == "FULL SCAN on t"


def test_index_query_correct(tbl):
    got = tbl.where(device_id="DEV-02")
    assert len(got) == 3 and all(r["device_id"] == "DEV-02" for r in got)


def test_full_scan_correct(tbl):
    assert len(tbl.where(temp=3.0)) == 1


def test_create_index_unknown_col(tbl):
    with pytest.raises(ValueError):
        tbl.create_index("nope")


def test_index_maintained_after_insert():
    t = core.Table("t", ["k", "v"])
    t.create_index("k")
    t.insert({"k": "a", "v": 1})
    assert len(t.where(k="a")) == 1

''')


# ══════════ P6 模型训练与服务 ══════════
P(id="03-P6", week="W08", no="第15次课", title="模型训练与服务",
  slug="p66_ml_service", pkg="ml_service", deps=["numpy", "scikit-learn"],
  scope="端到端最后一步：特征矩阵→训练→评估门禁→joblib 落盘→起本地推理服务→"
        "healthz 自检。评估不达标就**拒绝上线**。",
  rules=dict(warn=80.0, danger=95.0, unit="c", seed=42, topk=3),
  rules_yaml="""warn: 80.0
danger: 95.0
n_samples: 600
test_size: 0.25
min_f1: 0.80
port: 8899
unit: "c"
seed: 42
topk: 3
""",
  togaf=dict(business="把'跑出模型'变成'可上线服务'，并守住质量门禁",
             data="特征矩阵+标签 → 训练/测试划分 → 指标 → joblib 模型文件",
             application="core 造数/训练/门禁/推理；pipeline 出指标+模型+自检",
             technology="Python 3.12 + conda pp03；numpy/sklearn/joblib；pytest"),
  mods=[("core.py", "造数/训练/门禁/推理", "make_data()/train()/gate()/predict_one()"),
        ("io_utils.py", "模型与指标落盘", "write_json()")],
  stories=[("作为工程师，我希望不达标就不上线", "min_f1 门禁"), ("作为运维，我希望服务有 healthz", "自检通过")],
  funcs=[("训练", "RF+固定种子"), ("评估门禁", "macro-F1≥阈值"),
         ("模型落盘", "joblib"), ("推理", "单条预测")],
  design_core="数据/训练/评估为纯函数；门禁不达标**抛出门禁异常**（不产出模型）；"
              "model_path 由配置驱动；推理函数只依赖 joblib，不依赖训练代码。",
  test_cases=[("make_data", "数据", "n=600", "shape=(600,5)"),
              ("train", "训练", "训练集", "返回模型+指标"),
              ("gate", "门禁", "F1<0.8", "返回 False")],
  adr=adr("评估不达标抛出门禁异常而非带病上线",
          "'先上线再说'是工业事故的起点；门禁必须是硬阻断",
          "A 带病上线（危险）｜B 门禁异常（硬阻断）｜C 只警告不阻断（形同虚设）",
          "B 门禁异常", "把'质量'变成可执行约束；CI 中可直接用退出码体现",
          "可能阻塞快速迭代", "低", "阈值可配置+README 说明"),
  core_py='''# -*- coding: utf-8 -*-
"""模型训练、评估门禁与推理（纯函数 + joblib 落盘）。"""
import os


def make_data(n=600, seed=42):
    """合成特征矩阵（5 维）与二分类标签。"""
    import numpy as np
    rng = np.random.RandomState(seed)
    X = rng.normal(0, 1, (n, 5))
    y = rng.binomial(1, 0.4, n)
    X[y == 1, :3] += 1.3
    return X, y


def train(X, y, test_size=0.25, seed=42):
    """训练随机森林并返回 (model, metrics)。"""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import f1_score
    from sklearn.model_selection import train_test_split
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=seed)
    m = RandomForestClassifier(n_estimators=100, random_state=0).fit(Xtr, ytr)
    return m, {"macro_f1": round(float(f1_score(yte, m.predict(Xte), average="macro")), 4),
               "n_train": len(Xtr), "n_test": len(Xte)}


def gate(metrics, min_f1=0.80):
    """评估门禁：macro-F1 低于阈值即不通过。"""
    return metrics["macro_f1"] >= min_f1


def save_model(model, path, metrics):
    import joblib
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    joblib.dump(model, path)
    return path


def load_model(path):
    import joblib
    if not os.path.exists(path):
        raise FileNotFoundError("模型不存在: %s" % path)
    return joblib.load(path)


def predict_one(model, feats):
    return int(model.predict([feats])[0])

''',
  pipeline_py='''# -*- coding: utf-8 -*-
"""造数 → 训练 → 门禁 → 落盘 → 推理自检。"""
import os

from . import core, io_utils, report


def run(cfg, out_dir):
    n = int(cfg.raw.get("n_samples", 600))
    min_f1 = float(cfg.raw.get("min_f1", 0.80))
    X, y = core.make_data(n, seed=cfg.seed)
    model, metrics = core.train(X, y, float(cfg.raw.get("test_size", 0.25)), seed=cfg.seed)
    ok = core.gate(metrics, min_f1)
    if not ok:
        raise RuntimeError("评估门禁未通过：macro-F1=%.4f < %.2f，拒绝上线！"
                           % (metrics["macro_f1"], min_f1))
    os.makedirs(out_dir, exist_ok=True)
    mp = core.save_model(model, os.path.join(out_dir, "model.joblib"), metrics)
    m2 = core.load_model(mp)
    preds = [core.predict_one(m2, list(X[i])) for i in range(3)]
    result = {"metrics": metrics, "min_f1": min_f1, "model": os.path.basename(mp),
              "sample_pred": preds, "gate_passed": ok}
    io_utils.write_json(os.path.join(out_dir, "result.json"), result)
    sections = [("输入口径", ["样本 %d 条｜5 维特征｜测试占比 %.0f%%｜门禁 macro-F1≥%.2f"
                        % (n, float(cfg.raw.get("test_size", 0.25)) * 100, min_f1)]),
                ("训练指标", ["macro-F1 = %.4f（训练 %d / 测试 %d）"
                          % (metrics["macro_f1"], metrics["n_train"], metrics["n_test"])]),
                ("模型产物", ["%s（joblib 落盘，可被推理服务独立加载）" % os.path.basename(mp)]),
                ("推理自检", ["前 3 条预测: %s（与真实标签 %s 对照）"
                         % (preds, [int(v) for v in y[:3]])]),
                ("结论与建议", ["门禁通过方可上线；上线后仍需监控数据漂移"])]
    report.save(sections, os.path.join(out_dir, "report.txt"))
    return sections

''',
  tests_py='''# -*- coding: utf-8 -*-
import pytest

from ml_service import core


def test_make_data_shape():
    X, y = core.make_data(200, 1)
    assert X.shape == (200, 5) and len(y) == 200


def test_train_returns_metrics():
    X, y = core.make_data(300, 2)
    m, mt = core.train(X, y)
    assert 0.0 <= mt["macro_f1"] <= 1.0 and mt["n_train"] + mt["n_test"] == 300


def test_gate_true_and_false():
    assert core.gate({"macro_f1": 0.85}, 0.80) is True
    assert core.gate({"macro_f1": 0.70}, 0.80) is False


def test_save_and_load_roundtrip(tmp_path):
    X, y = core.make_data(200, 3)
    m, _ = core.train(X, y)
    p = str(tmp_path / "m.joblib")
    core.save_model(m, p, {})
    assert core.predict_one(core.load_model(p), list(X[0])) in (0, 1)


def test_load_missing_model_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        core.load_model(str(tmp_path / "nope.joblib"))


def test_predict_one_returns_int():
    X, y = core.make_data(200, 3)
    m, _ = core.train(X, y)
    assert isinstance(core.predict_one(m, list(X[0])), int)

''')
