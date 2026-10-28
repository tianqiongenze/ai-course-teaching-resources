# 泵类设备故障诊断分类（01-AI应用基础 · W04 第1次课）

> **第三种代码形态：Python 工程化项目** —— 多文件、规则外置、测试齐全、文档完备，
> 符合 GB/T 8566（软件生存周期过程）/ GB/T 9385（需求规格）/ GB/T 15532（测试规范）/
> GB/T 8567（文档编制），并以 TOGAF 四域描述架构。

## 一、30 秒跑起来
```bash
cd m11_fault_diag
python run.py                 # 读取 data/pump_fault.csv，输出到 output/ 并打印摘要
python -m pytest -q           # 全量测试（应全绿）
```

## 二、目录结构
```
m11_fault_diag/
├── run.py                  # 唯一入口（argparse CLI）
├── pyproject.toml          # 包元数据 + pytest 配置
├── requirements.txt        # 依赖清单
├── config/rules.yaml       # 规则外置：改配置不改代码（含工单四档门槛）
├── src/fault_diag/
│   ├── config.py           # YAML 加载 + Settings（含 yaml_lite 兜底）
│   ├── core.py             # 真实CSV加载/NumPy分层划分/三模型/手写指标/决策矩阵
│   ├── io_utils.py         # CSV/JSON/原子写/等宽表/课程数据定位
│   ├── report.py           # 报告渲染
│   └── pipeline.py         # load → split → train×3 → metrics → 决策矩阵 → report
├── tests/
│   ├── test_core.py        # 正常/边界/异常三档 + 工单档位断言
│   ├── test_config.py      # 配置加载与校验
│   └── test_pipeline.py    # 端到端集成（产物、口径、三模型、矩阵）
└── docs/                   # 01~08 全套过程文档（见下）
```

## 二.五、与工单 M1.1 的对应
| 工单要求 | 本项目落点 |
|---|---|
| ① NumPy 加载 + 分层划分（test_size=0.25） | `core.load_labeled_csv()` + `core.stratified_split()` |
| ② LR/DT/RF 三分类器都训 | `pipeline.build_models()` 三件套 |
| ③ 准确率/精确率/召回率/F1（宏平均） | `core.metrics_from_confusion()`，并与 sklearn 互验 |
| ④ 决策矩阵 → 选定交付模型 | `core.decision_matrix()`，实测准确率+实测训练耗时+登记可解释性 |
| D≥0.75 / C≥0.80 / B≥0.85 / A | `config/rules.yaml` 的 acc_d/c/b/a + `tier_of()`，`tests/test_pipeline.py` 断言 |

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
