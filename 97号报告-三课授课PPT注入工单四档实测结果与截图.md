# 97号报告：三课 56 个授课 PPT 注入「工单四档实测结果 + 实跑截图 + 说明」

**日期**：2026-10-28
**范围**：`01-AI应用基础`（8 deck）、`02-程序设计基础`（24 deck）、`05-AI应用基础48课时版`（24 deck）
**03-Python程序设计-项目实战 按用户要求除外，未读未改。**
**触发**：96号轮把 32 个工程化项目的 D/C/B/A 四档改成「代码实测判定」之后，用户要求
「三课 32 个 deck 一次做完，将最新的 ABCD 层的各个运行结果不仅有数据还要有截图和相关说明详细的放置在 ppt 的相关位置」。

## 一、交付总览

| 项 | 数量 | 说明 |
|---|---|---|
| 处理 deck | **56 / 56** | 01:8｜02:24｜05:24，全部命中「本工单的工程化项目」页并解析出项目 slug |
| 新增页 | **130** | E1 实测验收页 56｜E2 实跑截图证据页 56｜E3 产出图证据页 18（12 个项目有落盘图，按 deck 计 6+6+6） |
| 四档任务卡实测标注 | **176 处** | 01:32｜02:96｜05:48（05 的 12 个「（下）」精简 deck 本身没有分层任务卡页，故为 0） |
| 「先看终点」预览页刷新 | **56 / 56** | 每 deck 恰好 1 页含「① 本次真跑实测输出（逐字取自 output/report.txt）」 |
| 越界/压页脚/页码不一致 | **0** | `工具/ppt97/check97.py` 全量程序化体检 |
| deck 体积 | 约 14MB → **29.6MB** | 截图与产出图内嵌进 PPTX（三课公开仓随之增大） |

## 二、三类新增页放了什么

- **E1「实测验收 · <项目 slug>」**（紧跟「本工单的工程化项目」页之后）
  顶部绿色/红色档位带＝`实测达成档位`；右侧最多 5 枚实测值卡（如「实测捕获异常 3 种」「日志 65 行」）；
  中部四行表＝**档位｜工单验收标准（原文）｜本次实测判定｜✓达标/✗未达标**；
  底部黄框＝人工答辩项条数与摘录 +「档位是算出来的」口径声明 +（如适用）档位取数来源、实测值超出 5 项的提示。
- **E2「实跑截图证据 · <slug>」**：① run.py 终端输出截图 ② pytest 终端输出截图
  ③ report.txt「验收档位判定（实测）」段截图 ④「采集口径（可复现）」说明卡（项目路径、命令、
  采集脚本与时间、渲染脚本、run/pytest 退出码）。
- **E3「产出图证据 · <slug>」**（仅 12 个有落盘图的项目）：最多 4 张 `output/` 图，每张标出
  相对路径 + 文件大小 +「run.py 本次落盘」；1 张时整幅通栏，3 张时补一格「其余产出图」清单，
  超过 4 张时页脚写明「本次共落盘 N 张，本页展示前 4 张」。
- **四张分层任务卡**：在原「✔ 达标标准」条下追加一行
  `✓ 本次实测达标 ｜ <该档实测判定原文>`；未达标则显示 `✗ 本次实测未达标`（本轮 176 处均为达标）。
- **预览页**：把原「① 参考实现真实运行输出」块换成 report.txt 里本次真跑的档位段（滤掉分隔线与段落标题）。

## 三、证据采集口径

| 脚本 | 作用 |
|---|---|
| `工具/ppt97/capture97.py` | 32 个项目逐个 `python run.py` + `python -m pytest -q`（3 worker，单项超时 900s），逐字捕获 stdout/stderr 与 `output/report.txt` 档位段，落 `evidence/<slug>/{evidence.json,run.txt,pytest.txt}` |
| `工具/ppt97/terminal_png.py` | PIL 终端窗口渲染（1280×560，ANSI 剥离、中英混排分段、达标/未达标着色） |
| `工具/ppt97/render97.py` | 每个 slug 出 `shot_run.png / shot_test.png / shot_report.png`（共 96 张） |
| `工具/ppt97/inject97.py` | 克隆母版页 + 回填素材注入 56 个 deck（幂等：已含 E1 页即跳过） |
| `工具/ppt97/check97.py` | 注入后体检：形状越界、压页脚（页脚分隔线顶边 7.10in）、新增页数、页码总数一致性 |

32/32 项目 `pytest` 退出码为 0；`run.py` 退出码 31 个为 0、1 个为 -6（`m32_yolo_dual`，见第四节第 3 条）。
共采集实测值 165 条。截图文字逐字取自捕获文件，排版只折行，**未改写任何数字**。

## 四、诚实性处理（本轮新增的几条规则）

1. **档位取数四级回退**，并在页脚注明实际用的哪一级：报告头「实测达成档位: X」29 个 →
   本次真跑输出的「达标档位」行 2 个（`m11_fault_diag`、`m12_data_quality` 的报告头未写档位行）→
   `output/result.json:tiers` 1 个（`w12_capstone`）→ 四档连判推出（本轮未触发）。
   全部取不到才显示红色「未达 D 档」。
2. **未达最高档如实呈现**：`m21a_classic_clf` 实测达成 **优秀(B)**，其 E1 表 A 档行判定列为
   `✗ 未达标`、档位带非绿色；其余 31 个项目实测达 优(A)。
3. **run.py 退出码非 0 不隐藏**：`m32_yolo_dual` 本次 `run_rc=-6`（进程收尾期 ONNX 解构抛
   `libc++abi: recursive_mutex lock failed`，档位判定与报告正文在此之前已完整产出）。
   该值同时出现在 E2 面板①标题、截图标题栏和「采集口径」卡的退出码行三处。
4. **人工答辩项不代判**：E1 黄框写明条数；捕获能拆出原文的（36 条）直接摘录前 3 条，
   报告里以单行「D·…；C·…」形式写出的拆不出条目，则写「逐条见下页 report.txt 截图」，
   不凭记忆补写。
5. **工单原文列的兜底**：某些报告该档只留了「本行只判准确率门，同档其余条目见下方人工答辩项」这类指向句，
   此时改用该 deck 分层任务卡上「✔ 达标标准」的工单原文（如 `m11_fault_diag` D 档显示「程序出结果 + 口述指标含义」）。
6. **兜底口径提示常驻**：E1 黄框固定一行「工单未给数字的门槛在报告里标注为『兜底口径·非工单数字』」。
7. **产出图不夸大**：只放 `output/` 下本次真跑落盘的文件，优先排除 `test_run/` 副本，逐张标路径与大小。

## 五、已知限制

- 05 的 12 个「（下）」deck 是 10 页精简结构，无分层任务卡页 → 只加 E1/E2(/E3) 页，卡片标注 0 处。
- E1 每页最多展示 5 枚实测值卡，超出部分指向下页 report.txt 截图（32 个项目里 19 个实测值 >5 条）。
- `evidence/*/shot_*.png`（8.2MB）不入 git：可由 `capture97.py + render97.py` 重跑再生，且已内嵌进各 deck；
  捕获文本 `run.txt / pytest.txt / evidence.json`（约 0.6MB）随仓入库作为可核对的原始凭证。
- 注入前的 56 个 deck 原件备份在 `/tmp/backup_ppt97/`，且可用 `git restore` 回到 96号轮状态。

## 六、仓库同步

| 目标 | 地址 | 推送后 `main` 头（`git ls-remote` 实测） | 本次变更文件 |
|---|---|---|---|
| 01 公开仓 | https://github.com/tianqiongenze/ai-application-foundations | `1c25717` | 80 个：8 deck + 8 项目证据文本 + 5 脚本 |
| 02 公开仓 | https://github.com/tianqiongenze/programming-fundamentals | `10d00a8` | 136 个：24 deck + 12 项目证据文本 + 5 脚本 |
| 05 公开仓 | https://github.com/tianqiongenze/ai-foundations-48h | `ae13955` | 95 个：24 deck + 12 项目证据文本 + 5 脚本 |
| 私有整库 | https://github.com/tianqiongenze/ai-course-teaching-resources | `ca04ecb`（`4da2f97..ca04ecb` 快进） | 161 个（03 课程工作区改动未纳入） |
| gitee 整库 | https://gitee.com/enze_tian_qiong/ai-course-teaching-resources | `ca04ecb`（`4da2f97..ca04ecb` 快进，不 force） | 同上 |

- 三门课公开仓各自只带**本课 8/12/12 个项目**的证据（`_index.json` 按 `course` 字段过滤后写入），
  公开仓之间不互相泄漏他课 slug；终端截图仍按 `.gitignore` 排除，仓内保留逐字捕获文本。
- 全程未使用 `--force` / `--no-verify`；`03-Python程序设计-项目实战` 的工作区改动（非本次产生）
  在本节初推时未 staged、未提交、未回退——**同日按用户口径改为全量纳入，见第七节**。
- 实测过程：推送期间 `github.com:443` 出现间歇性连接超时（同一时刻 `api.github.com` 可达），
  改为「先 `git ls-remote` 探活、通了才 push」的重试后三仓全部快进成功；gitee 一次通过。

## 七、追加：03 课全量同步 + 两处一致性修复（同日）

### 7.1 核查时查出的两处真实不一致

| 缺口 | 表现 | 处理 |
|---|---|---|
| 整库落后公开仓 | 本次真跑落盘的 `output/report.txt`、`result.json` 等 50 个文件只进了三课公开仓，整库还是 96 号轮旧产物（如 m11 生成时间 `09:49:45` vs `10:42:58`） | `ee34f8d` 补进整库；比对确认只变生成时间与训练耗时，**精度指标逐字不变** |
| 公开仓混入临时产物 | 三门课公开仓共 **88 个** `工程化项目/*/output/test_run/`（pytest 实跑临时目录，非交付证据）被跟踪；原因是 `.gitignore` 写成 `*/工程化项目/...` 在「课程目录＝仓根」的镜像布局下永不命中 | 三仓各一提交 `git rm --cached` 摘出（磁盘保留）+ 规则改课程内相对路径；整库同步落一份课程级 `.gitignore`（`7dbe492`）使两侧逐字节一致 |

修复后 **整库 ↔ 三课公开仓文件树差异 0**：01 `1237↔1237`｜02 `634↔634`｜05 `594↔594`（公开仓另有本课 `工具/ppt97` 证据 30/42/42 个文件）。

### 7.2 03 课全量入库（377 项）与「试卷类不上交」口径

- `f8c3afd`：03 工作区改动全量入整库 = **236 改 / 134 新增 / 4 改名 / 3 删除**（p11-p77 各项目新落盘的 `src/tests/output/docs`、W09 三版 notebook、教师参考与工具脚本）。
- 新增 `03-Python程序设计-项目实战/.gitignore`：A/B/C 三类试卷与参考答案、电气制图 CAD 卷、
  期末考试模拟数据、`工具/期末试卷生成/`、误建的 `--help`/`.workbuddy` **全部 ignore**；
  逐条 `git check-ignore` 复核命中，本次 03 提交清单 **0 处试卷类路径**。
- `c11d8c5` 追加 `*.onnx`/`*.pt` 排除（与 03 公开仓既有规则取并集）；
  `e957797` 把 rsync 用的排除清单以 `工具/03同步排除清单.txt` 存进整库（该目录不进任何课程公开仓）。
- 4 个**早期轮次已入库**的考核类文件（`必答题库-答辩与期末（四类40题）.md`、
  `期末工业级项目册-20选1.docx/md/pdf`）本轮未改动、未重写历史，保留在整库；
  其中 4 个已存在于 03 的 GitHub 公开仓（详见 7.4 待确认项）。

### 7.3 03 两个课程仓同步

| 目标 | 分支 | 推送 | 内容 |
|---|---|---|---|
| [03 GitHub 公开仓](https://github.com/tianqiongenze/industrial-IoT-python-programming) | `main` | `ed84a8e..543e4e8` 快进 | 21 个文件更新（15 个 V2 授课 PPT + 3 个项目内 `.gitignore` + 2 个 runtime json） |
| [03 gitee 课程仓](https://gitee.com/enze_tian_qiong/03-python-practice) | `master` | `c0c7eff..95ded29` 快进 | **首次真正入库**：574 个文件 / 157MB（此前该仓只有一个 LICENSE） |

- 镜像法同前三课：`clone → rsync -a --delete（带排除清单，保住仓根 LICENSE）→ 提交 → HEAD:<分支> 推送`，
  无 force、无 `--no-verify`；gitee 侧 `develop/feature/hotfix/release` 四个占位分支未动。
- 树比对（整库 03 目录 ↔ 公开仓 HEAD）：**内容不同 0 处**；
  仅整库有的 9 项全部是 `*.db / *.kuzu / *.duckdb` 运行库（公开仓按规则本就不收）；
  仅 GitHub 03 仓还有 1 个本地已不存在的早期残留 `工程化项目/p66_ml_service/runtime/train_timing.json`。

### 7.4 最终五仓状态（`git ls-remote` 实测）

| 仓 | 头 |
|---|---|
| [01 ai-application-foundations](https://github.com/tianqiongenze/ai-application-foundations) | `5e75c07` |
| [02 programming-fundamentals](https://github.com/tianqiongenze/programming-fundamentals) | `486dc1b` |
| [05 ai-foundations-48h](https://github.com/tianqiongenze/ai-foundations-48h) | `e87a4d7` |
| [03 industrial-IoT-python-programming](https://github.com/tianqiongenze/industrial-IoT-python-programming) | `543e4e8` |
| [GitHub 私有整库](https://github.com/tianqiongenze/ai-course-teaching-resources) / [gitee 整库](https://gitee.com/enze_tian_qiong/ai-course-teaching-resources) | `e957797`（含文档回填提交） |
| [03 gitee 课程仓](https://gitee.com/enze_tian_qiong/03-python-practice) | `95ded29`（`master`） |

**待你确认一件事**：`必答题库-答辩与期末（四类40题）.md` 与 `期末工业级项目册-20选1`（docx/md/pdf）
这 4 个考核类文件是**早期轮次就已公开**在 03 GitHub 仓里的，本轮没有改动它们。
如果按「试卷之类不上传」要一并从公开仓撤下，我可以再做一次删除提交（正常快进，不动历史、不 force）；
文件仍保留在本地与整库。
