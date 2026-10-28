# 轴承剩余寿命预测（01-AI应用基础 · W07 第4次课）

> **第三种代码形态：Python 工程化项目** —— 多文件、规则外置、测试齐全、文档完备，
> 符合 GB/T 8566（软件生存周期过程）/ GB/T 9385（需求规格）/ GB/T 15532（测试规范）/
> GB/T 8567（文档编制），并以 TOGAF 四域描述架构。

## 一、30 秒跑起来
```bash
cd m22_rul_predict
python run.py                 # 真实数据→LSTM+对照→拐点/窗口敏感性→图表→档位判定
python run.py --quiet         # 只落盘，不打印报告正文
python run.py --tier          # 打印工单 M2.2 四档"实测"判定（档位是算出来的，非自称）
python run.py --style-only    # 只做 PEP 8 规范体检（零违规才退出 0）
python run.py --check         # 环境自检：torch/matplotlib 缺失会怎样改档位口径
python -m pytest -q           # 全量测试（应全绿）
```

## 二、目录结构
```
m22_rul_predict/
├── run.py                  # 唯一入口（argparse CLI）
├── pyproject.toml          # 包元数据 + pytest 配置 + 规范体检口径
├── requirements.txt        # 依赖清单（torch/matplotlib 与档位的对应关系写在注释里）
├── config/rules.yaml       # 规则外置：改配置不改代码（工单数字 + 兜底口径分节标注）
├── src/rul_predict/
│   ├── cli.py              # 命令行：--tier 的档位来自实跑 result，代码里不留自宣言
│   ├── config.py           # YAML 加载 + Settings（含 yaml_lite 兜底）
│   ├── core.py             # 纯函数领域逻辑（数据加载/切分/LSTM/对照模型/拐点/绘图）
│   ├── io_utils.py         # CSV/JSON/原子写/表格渲染
│   ├── report.py           # 报告渲染
│   ├── stylecheck.py       # PEP 8 规范率实测引擎（pycodestyle，缺失走内置兜底）
│   ├── tiers.py            # 工单四档验收判定（纯函数，只比较实测值）
│   └── pipeline.py         # load → split → train/对照 → 拐点/敏感性 → 图表 → 判档
├── output/                 # report.txt / result.json / prediction_curve.png /
│                           # window_sensitivity.png(.csv)——全部为实测产物
├── tests/
│   ├── conftest.py         # macOS libomp 坑：收集前先导入 torch
│   ├── test_core.py        # 正常/边界/异常三档
│   ├── test_config.py      # 配置加载与校验
│   └── test_tiers.py       # 四档实测断言 + 反向证明（删能力必须降档）
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

## 五、验收口径（档位是算出来的，不是自称的）
工单《M2.2 轴承寿命预测系统》"四、验收标准"四档由 `src/rul_predict/tiers.py` 判定，
输入全部来自同一次运行的实测值（`output/result.json` 的 `tiers.measured`）：

| 档位 | 工单原文 | 机检实测项 |
|---|---|---|
| 及格(D) | MSE<0.15；能完成预测与可视化 | 留出设备 MSE；prediction_curve.png 磁盘字节 + 曲线数据点数 |
| 良好(C) | MSE≤0.12；对照基线说明LSTM增益 | MSE 线；同切分 Ridge 基线与 LSTM 的实测 MSE 差（正数才算增益） |
| 优秀(B) | MSE<0.10；对比≥2种模型并解读 | MSE 线；真实训练过的模型数与逐模型留出指标表 + 自动生成的解读行 |
| 优(A) | 达B且：预测曲线有拐点分析；对窗口长度做敏感性实验 | 平滑序列实测检出的拐点循环号（并进图画竖线）；逐窗口真重训真测的档数与 MSE 表 |

判不到的项一律传 None/False → 判缺 + 报告印 MISS（torch 缺失 → C 档增益判缺；
matplotlib 缺失 → D 档可视化判缺）。工单没给数字处（png 字节下限、窗口档数下限）
用的是"非空白图/能构成比较"的兜底口径，`config/rules.yaml` 与报告行都逐条标注了
"不是工单数字"。口头解读、图是否清晰可读、企业元师傅签认列在人工答辩项，绝不自动判达标。

- `python -m pytest -q` 全绿（28 用例：core 6 + config 6 + tiers 16）
- `python run.py --style-only` 零违规退出 0；规范率实测仅作答辩证据（本工单未逐档规定规范率）
- 配置修改不需改代码；同 seed 二次运行结果逐项一致（MSE/增益/拐点/窗口/图字节全部实测可复现）
- 数据用课程真实数据 `01-AI应用基础/data/bearing_rul.npz`（30 台设备 × 180 窗 × 20 列，
  设备级留出防泄漏）；npz 不在盘时走 `core.synth_devices` 同口径兜底并在报告标注来源
- 过程文档 8 份齐全，可直接用于期末答辩的材料链
