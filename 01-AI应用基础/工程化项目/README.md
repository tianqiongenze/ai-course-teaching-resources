# 01-AI应用基础 · 工程化项目索引（第三种代码形态）

> 74号轮 · 每个周次一个**可运行的 Python 工程化项目**：多文件分层、规则外置、pytest 三档测试、8 份国标/TOGAF 过程文档，共 8 个周次全覆盖。

## 一、三种代码形态的定位

| 形态 | 目录 | 定位 |
|---|---|---|
| ① starter | `../学生代码框架/` | 学生填空起步（TODO 骨架） |
| ② 教师参考 | `../教师参考/` | 完成态参考（单文件示意） |
| ③ **工程化项目（本目录）** | `工程化项目/` | **企业级工程结构 + 全套流程资料** |

## 二、项目清单（8 个）

| # | 工单 | 周次 | 目录 | 核心功能 |
|---|---|---|---|---|
| 1 | 01-M1.1 | W04 第1次课 | `m11_fault_diag/` | 泵类设备故障诊断分类 |
| 2 | 01-M1.2 | W05 第2次课 | `m12_data_quality/` | 数据清洗与质量评分 |
| 3 | 01-M2.1 | W06 第3次课 | `m21_weld_cnn/` | 焊缝缺陷CNN分类 |
| 4 | 01-M2.2 | W07 第4次课 | `m22_rul_predict/` | 轴承剩余寿命预测 |
| 5 | 01-M3.1 | W08 第5次课 | `m31_surface_vision/` | 表面缺陷传统视觉检测 |
| 6 | 01-M3.2 | W09 第6次课 | `m32_yolo_dual/` | YOLO实时缺陷检测（双路线对照） |
| 7 | 01-M4.1 | W10 第7次课 | `m41_fault_text_clf/` | 故障报告文本分类 |
| 8 | 01-M4.2 | W11 第8次课 | `m42_ops_rag/` | RAG 运维知识库问答 |

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
