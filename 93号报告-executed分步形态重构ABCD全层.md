# 93号报告：教师版 executed 从「聚合脚本形态」重构为「分步执行形态」（ABCD 全层完成态）

**日期**：2026-10-28
**范围**：01/02/05 三课程 Jupyter 实训（03 除外）；33 个 `_教师版_executed.ipynb`（30 个重构 + 01 包 W06/W07/W11 三个原缺失新建）
**触发**：用户要求 executed 版不要聚合脚本形态，要能完整完成 ABCD 四层全部任务。

## 一、重构前问题

旧 executed 形态：`[md头] → [code 环境准备] → [md 参考实现] → [code 聚合大脚本(无输出)] → [md 对照/多解] → [code w01()]`——实现聚在 1 个大 cell 且**无执行输出**（out=0，纯源码展示），与学生看到的分步教学结构脱节；且 A·师傅层扩展任务（多解互验/帮带）只是文本没有执行证据。

## 二、新形态（重建器 `/tmp/rebuild_executed.py`，数据驱动）

```
[md] 课头 + 工单验收标准表（ABCD，从 工单任务书/*.md 提取）
[md+code…] 普通教师版分步教学骨架（情境→任务→分层提示→分步 Starter+【参考答案】）
[md] A·师傅层：多解对比与帮带要点（继承旧 executed 的实跑互验记录）
[md] ABCD 验收对照（D/C=分步单元执行输出；B=(优秀)扩展单元；A=多解互验+费曼展示）
```

执行：nbclient（python3 kernel）全量真实运行，输出落进每个 cell。

## 三、结果（最终验收 32/32 ✔）

| 包 | 文件数 | 结果 | cells 范围 | 有输出cell | 执行错误 |
|---|---|---|---|---|---|
| 01-AI应用基础 | 8 | 8/8 ✔（含新建 W06/W07/W11） | 21~29 | 2~3 | 0 |
| 02-程序设计基础 | 12 | 12/12 ✔ | 19~27 | 2~3 | 0 |
| 05-AI应用基础48课时版 | 12 | 12/12 ✔（LLM/RAG 课次走降级路径正常出证） | 19~25 | 3 | 0 |

验收标准（逐文件）：分步形态（≥19 cells）+ 「ABCD 验收对照」单元存在 + 无旧「参考实现」聚合 cell + 有输出 cell≥2 + error=0 + 全部 code 单元 ast.parse 通过。

## 四、过程依赖修复（环境层）

| 问题 | 根因 | 处置 |
|---|---|---|
| 02 w09 缺 jieba | pp03 未装 | `pip install jieba` |
| 01 W08/W09 缺 cv2 | pp03 未装 | `pip install opencv-python`（5.0.0） |
| 01 W06/W07 torch 报 `Could not infer dtype of numpy.float32` | 本机 Python 为 **x86_64**（Rosetta），PyPI 对该平台 torch 最高仅 2.2.2，不兼容 numpy 2.5.3 | ①不降 numpy（scipy1.18/contourpy1.4 强依赖 numpy2，连锁太深）；②改 W06/W07 教师版 8 处 `torch.tensor(np数组)` → `.tolist()+显式dtype` 纯 Python 路径（语义不变，行级缩进对齐，ast 验证后写盘），torch-numpy 桥不再被触发 |

> 注：W06/W07 的 tensor 转换写法修复同时回写了普通教师版（源与 executed 同构），备份于 `/tmp/backup_jupyter/*.pre_torchfix`。

## 五、同步

| 仓库 | 结果 |
|---|---|
| 01 → github `ai-application-foundations` | ✔（executed 重建 + W06/W07 torch 兼容修复） |
| 02 → github `programming-fundamentals` | ✔（12 个 executed 重构 + jieba） |
| 05 → github `ai-foundations-48h` | ✔（12 个 executed 重构） |
| 整体仓 gitee `ai-course-teaching-resources` | ✔（本报告 + 全部变更） |

## 六、遗留

1. 05 包分步单元的答案标注形态与 01/02 不同（参考答案在 docstring「TODO-N 参考答案」，无【参考答案】行内标注）——功能等价，形态统一可作后续小迭代。
2. W17/W18（LLM/RAG）的执行输出基于降级路径（本地 LLM 服务未起时返回「[降级] 转人工」文本）——教学语义正确；如需真实 LLM 输出，起本地服务后重跑 rebuild 即可。
