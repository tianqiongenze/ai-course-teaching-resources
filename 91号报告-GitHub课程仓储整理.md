# 91号报告：课程分组 GitHub 仓储整理（四门课各建独立公共课程仓）

**日期**：2026-10-20
**触发**：用户要求「目录下每个课程单独建 github 仓库（已有相关课程仓库则不再建），命名不用拼音，同步各自远程仓库，并把 GitHub/gitee 仓库地址整理进相关资料」。

## 一、本次已建/已推送 GitHub 课程仓库（public，非拼音英文名）

| 课程目录 | 仓库名（英文·非拼音） | GitHub 地址 | 说明 |
|---|---|---|---|
| 01-AI应用基础 | `ai-application-foundations` | https://github.com/tianqiongenze/ai-application-foundations | 新建 · 已推送 1165 文件 |
| 02-程序设计基础 | `programming-fundamentals` | https://github.com/tianqiongenze/programming-fundamentals | 新建 · 已推送 549 文件 |
| 03-Python程序设计-项目实战 | `industrial-IoT-python-programming` | https://github.com/tianqiongenze/industrial-IoT-python-programming | 新建专属仓 · 已推送 459 文件 |
| 05-AI应用基础48课时版 | `ai-foundations-48h` | https://github.com/tianqiongenze/ai-foundations-48h | 新建 · 已推送 523 文件 |

> 账号：GitHub `tianqiongenze`；gitee `enze_tian_qiong`。

已核实 4 仓均为 PUBLIC、内容为当前课程目录全量（用 `cp -al` 硬链接共享源 inode，未复制消耗，仅 .git/ 独立）。

## 二、03 专属仓取舍（按用户的「已有则不建」+「干净专属」双向意愿）
- GitHub 原本已有 `python-programming-practice`，但它是**包含 03+AI+CAD 多门课的混合源仓**（顶层含 LS 教学方案、4 份课标、历史版本等），不是 03 单科仓库。
- 按「每门课一个干净独立仓」决定**另建 `industrial-IoT-python-programming` 专属仓**，避免继续污染混合仓；原混合仓不动。

## 三、gitee 课程仓库（沿用已有，暂不同步）
本机无 gitee 推送凭据（https 无 keychain 记录、ssh 未注册公钥），按用户「gitee 仅整理地址、暂不建/不同步」处理：

| 课程目录 | gitee 仓库 | gitee 地址 |
|---|---|---|
| 03-Python程序设计-项目实战 | `03-Python程序设计-项目实战` | https://gitee.com/enze_tian_qiong/03-python-practice |
| 05-AI应用基础48课时版 | `ai-foundations-48h` | https://gitee.com/enze_tian_qiong/ai-foundations-48h |
| 整库（含全部课程） | `ai-course-teaching-resources` | https://gitee.com/enze_tian_qiong/ai-course-teaching-resources |

> 01/02 在 gitee 尚无独立课程仓，需在 gitee 手动建仓后，以同一英文名
> `ai-application-foundations` / `programming-fundamentals` 推送即可与 GitHub 对齐。
> 这些地址已整理进 `00-资源库总索引.md`（91号轮）。

## 四、大文件与净化
- 全库扫描：**无 >100MB 单文件**，可直接进 GitHub（100MB 单文件上限）与 gitee。
- 课程内最大文件为共享字体 `ZH_Font.ttf`（22.2MB）与模型权重（yolov8n.onnx/pt，≤12.3MB），均正常进仓。
- 每仓 `.gitignore` 排除 venv/__pycache__/中间产物（*.db/*.kuzu/*.duckdb/*.onnx/*.pt 可选，03 仓已加）。

## 五、方法
- 复用已有：`python-programming-practice`（混合仓）未重刷；`ai-foundations-48h`（gitee 已有回溯）未冲突。
- 推送链路：本机 ssh 未注册 GitHub 公钥 → 切 https + `gh auth setup-git`（gh token 作 git 凭据，scopes 含 repo/workflow）成功推送；建仓用 `gh repo create --public`。
- 本地副本在 `/tmp/course_repos/`（`cp -al` 硬链接，磁盘占用≈0，随 /tmp 清空不影响源仓）。

## 六、待办（需用户或手动）
1. **gitee 01/02 建仓并推送**（需 gitee 个人访问令牌，或网页端手动建仓后本机补 push）。
2. 若要让各课程仓保持「次课/轮次」更新，可在根仓提交后对 4 个课程仓执行同样的 add-commit-push。