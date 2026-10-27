# 92号报告：全课程 Jupyter 教师版 TODO 与工程化项目工单全量审计与修复

**日期**：2026-10-28
**范围**：01-AI应用基础、02-程序设计基础、05-AI应用基础48课时版（03 课程按用户要求除外）
**触发**：用户要求逐一审核三课 Jupyter 实训全部教师版是否完成各课次 TODO 任务，工程化项目是否完成各层次工单任务；未完成的完善重构后同步各课独立仓库并更新整体仓库。

## 一、审计结论总览

| 对象 | 数量 | 审计基准 | 结果 |
|---|---|---|---|
| Jupyter 普通教师版（`*_教师版.ipynb`） | 32（01:8 / 02:12 / 05:12） | code 单元占位正则 `你的代码\|待补\|return 0$` + ast 语法 + executed 版对照 | **32/32 达标**（占位全部归零、ast 全过） |
| Jupyter 执行版（`*_教师版_executed.ipynb`） | 30 | 同上 | 全部为完成态（TODO 为「参考答案」docstring 标注，非缺口） |
| 工程化项目 | 32（01:8 / 02:12 / 05:12） | TODO/FIXME/NotImplemented 残留 + `output/report.txt` + 工单 D/C/B 层次映射 | **32/32 达标**（TODO=0、report 全存在、每项目有对应工单且含及格/优秀标准） |

## 二、教师版审计明细

- **审计定性**：普通教师版中 code 单元的 TODO 占位（`# === 你的代码 ===`、`return 0`、`raise NotImplementedError`）= 真未完成；markdown/docstring 中的 TODO 字样 = 任务描述，不算缺口；executed 版聚合脚本中的「TODO-N 参考答案」= 完成态标注。
- **修复方式**：以同课次 `_教师版_executed.ipynb`（完整可运行实现）为答案源，按函数名精确匹配回填至普通教师版占位单元，答案标注 `# 【参考答案】（与 executed 版一致）`；无 executed 的课次从对应工程化项目移植（同源逻辑）。
- **本轮实际修复**：
  - 02 包 12 个教师版（w01~w12，TODO 单元 1~5 个/文件）——回填自 executed 版；
  - 01 包 W05/W08/W09（回填自 executed）、**W10**（main() TODO-2 训练评估/TODO-3 新文本预测/TODO-4 每类Top10关键词/TODO-5 混淆矩阵，回填自 executed m41 实现）、**W11**（KnowledgeBase.retrieve 二元词重合检索 + Agent.ask 两步推理含阈值工具/RAG注入/防幻觉拒答 + main TODO-4 RAG对比/TODO-5 问答记录表，移植自工程化项目 m42_ops_rag core.py 同源逻辑）；
  - 05 包 W13（回填自 executed）；W19 的 `return 0` 为业务逻辑（无告警不派工）**非占位**，排除误报。
- **验证**：修复后 32 文件全部满足——json 可加载、code 单元占位=0、ast.parse 全过、修复函数与 executed/工程化项目逻辑同源。原始文件备份于 `/tmp/backup_jupyter/`。

## 三、工程化项目审计明细

- **TODO 残留**：01/02/05 三包 32 个项目源码 `TODO|FIXME|NotImplemented` 全部为 **0**（74号轮成果完好）。
- **实跑证据**：32/32 存在 `output/report.txt`（含输入口径、训练/测试划分、指标等）。
- **工单层次对照**：32/32 项目均能映射到对应分层工单（01: M1.1~M4.2；02: W01~W12；05: M1-1a~Z），工单内含 **及格(D)/良好(C)/优秀(B)** 分层标准（例：02 W06「及格(D) 处理≥2种异常+基本日志；优秀(B) ≥3种异常+完整finally+规范率≥90%」），项目 README/config/core 与 report 与之对应。
- **结论**：工程化项目层无需重构。

## 四、仓库同步

| 课程 | GitHub 仓库 | 本次推送 |
|---|---|---|
| 01-AI应用基础 | https://github.com/tianqiongenze/ai-application-foundations | ✔ +2 文件（W10/W11 手工修复；其余修复已随前次硬链接入仓） |
| 02-程序设计基础 | https://github.com/tianqiongenze/programming-fundamentals | ✔ +13 文件（12 教师版回填 + 杂项） |
| 05-AI应用基础48课时版 | https://github.com/tianqiongenze/ai-foundations-48h | ✔ 已是最新（W13 修复前次已入仓，本轮无新增变更） |
| 整体仓库 | gitee `ai-course-teaching-resources` | 本地已提交；远端推送需 gitee 凭据（本机无凭据，见 91号报告待办） |

同步方法：`gh repo clone` → `rsync -a`（不带 --delete 以保留 .git）→ add/commit/push。

## 五、过程记录与教训

1. **首轮通用回填引擎（正则启发式）失败**：按 TODO 标记行划区 + 调用点猜测，把文件名字符串误当函数名插入（02 包 12 文件一度 ast=FAIL）；已从备份恢复。教训：notebook 语义回填必须函数名精确匹配或 LLM 逐文件处理，不可用脆弱正则批量替换。
2. **子代理限流假象**：4 个并行修复 agent 返回 rate limit 错误，但实际已执行完成修复（备份时间戳与文件内容证实）；"恢复备份"操作恰好把引擎损坏改回 agent 正确修复态。教训：agent 报错≠未执行，恢复前先 diff 验证。
3. **rsync --delete 删 .git**：staging 同步误删仓库元数据，push 静默假成功（管道尾部退出码）。教训：同步脚本不得 --delete 含 .git 的目录；push 判定要看 git 退出码。

## 六、遗留（不阻塞本次交付）

1. gitee 整体仓库与 01/02 课程仓推送需 gitee 凭据（同 91号报告）。
2. 教师版修复为「源回填」，若需同步刷新 `_教师版_executed.ipynb` 的执行输出，需在配好依赖（sklearn/jieba/matplotlib/本地LLM）的环境重跑执行链（本轮 30 个 executed 已是完成态，仅 01 W10/W11 两课的 executed 不存在，可后续按需生成）。