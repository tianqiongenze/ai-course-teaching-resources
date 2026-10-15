# 48号报告：GitHub/Gitee操作指南生成与全课程关联

**日期**：2026-09-14
**触发**：用户要求"以上所有课程都要使用到GitHub（如果GitHub不能正常使用，切换至Gitee），请生成详细的GitHub操作指南（要包括在PyCharm中的详细使用细节），并将其关联进各个课程的软件与环境配置完全指南中和其他相关的资料中"

---

## 一、改造前现状

| 资产 | Git提及情况 | 问题 |
|---|---|---|
| `03-Git与GitHub-Gitee使用指南.md` | 33行简版（五步工作流+常见问题） | 缺PyCharm集成步骤、缺注册细节、缺切换Gitee流程、缺ABCD评分关联 |
| `05-PyCharm使用指南.md` | 25行简版 | 无Git章节 |
| `00-软件安装完全指南`第四部分 | 标题"02课W11/03课W2起用" | 限定为02 W11/03 W2，非"所有课程" |
| 01完全指南 | 1行"选做：工单留档" | Git=选做，不符合用户要求 |
| 02完全指南 | 1行"选做：综合项目代码留档W11-12" | Git=选做，不符合用户要求 |
| 05完全指南 | 1行"选做：IDE备选/项目化留档" | Git=选做，不符合用户要求 |
| 03完全指南 | 18处深入（W2核心周） | 唯一已深入的课程，但文件名引用有断链 |
| `00-资源库总索引.md`总地图 | Git行：01选做/02选做/03★★★/05选做 | 三课标"选做"不符合用户要求 |
| `env_tools.py` tool_for | 仅03课(pp)返回git指南 | 01/02/05不返回git指南→工单/PPT封面不含Git引用 |
| 工单"配套+工具"行 | 仅03课工单含Git | 01/02/05工单不含Git引用 |
| PPT封面"本课主用"行 | 仅03课PPT含Git | 01/02/05 PPT不含Git引用 |

## 二、改造内容

### 1. Git指南重写（33行→约350行）
`软件操作指南/03-Git与GitHub-Gitee使用指南.md` 全文重写，十二章：
- 一、它是什么（GitHub vs Gitee对照表+切换策略）
- 二、安装与配置（Git安装/验证/user.name+email/init.default branch/credential.helper五步）
- 三、注册GitHub与建仓（注册/建仓/获取地址/克隆四步）
- 四、五步工作流（逐步详解clone→branch→add→commit→push+合并）
- 五、commit前缀规范（feat/fix/docs/test/refactor五类表）
- 六、**在PyCharm中使用Git**（11小节：克隆/分支/查看改动/暂存提交Ctrl+K/推送Ctrl+Shift+K/拉取Ctrl+T/查看历史/解决冲突三窗合并/.gitignore/快捷键速查表）
- 七、各课程使用场景（02 W1-12/03 W1-9/05 W4-12逐周表）
- 八、ABCD四层评分关联（A规范+分支+冲突/B帮带/C完成提交/D至少一次push）
- 九、常见问题（Token/venv误提交/冲突/撤销/rejected/慢 六题）
- 十、**切换到Gitee**（两步：建仓+`git remote set-url`，含PyCharm VCS→Remotes方法）
- 十一、.gitignore模板（三课通用）
- 十二、命令速查表

### 2. PyCharm指南扩展（25行→约180行）
`软件操作指南/05-PyCharm使用指南.md` 扩展，加：
- 安装详解（下载/启动/Windows勾选项）
- 首次配置三步（New Project/确认解释器/运行）
- 调试三板斧（断点/调试/Step Over/Into/Out/Resume）
- Jupyter Notebook在PyCharm中
- 常用快捷键速查表
- **第七章：在PyCharm中使用Git**（7小节：克隆/提交Ctrl+K/推送Ctrl+Shift+K/拉取Ctrl+T/分支管理/查看历史/解决冲突三窗合并/快捷键速查）
- FAQ增commit灰色/push 403/rejected三题

### 3. 00总指南第四部分升级
标题从"安装Git（02课W11/03课W2起用）"改为"安装Git与注册GitHub（所有课程第1周装机即完成）"——去掉课程限定，加credential.helper配置和"所有课程必用"说明

### 4. 四课完全指南升级（01/02/03/05）
| 课程 | 改造前 | 改造后 |
|---|---|---|
| 01-AI应用基础 | "版本管理（选做：工单留档）Git+Gitee 课后" | **"代码版本管理（每周必提交）Git+GitHub/Gitee W4起每周"** |
| 02-Python编程基础 | "综合项目代码留档（选做）Git+Gitee W11-12" | **"代码版本管理（每周必提交）Git+GitHub/Gitee W1起每周"** |
| 03-项目实战 | 已深入（18处），修文件名断链 | 修`03-GitHub与Gitee图解指南.md`→`03-Git与GitHub-Gitee使用指南.md`；修`06-PyCharm CE使用指南.md`→`05-PyCharm使用指南.md` |
| 05-AI应用基础48 | "IDE备选/项目化留档 PyCharm/Git+Gitee 选做" | **"代码版本管理（每周必提交）Git+GitHub/Gitee W4起每周"** |

02完全指南额外加W1装机课"注册GitHub账号+建仓+clone+首次Git提交"步骤；02/05加"每周Git提交惯例"段。

### 5. 00总索引总地图升级
Git行从"01选做留档/02 W11-12选做/05选做"→**"01 W4起每周提交/02 W1起每周提交/05 W4起每周提交"**；同时总地图VS Code行→PyCharm CE行（42号轮迁移后总地图未同步）。

### 6. env_tools.py tool_for升级
所有课程所有周次返回的工具短语+指南列表均加`GUIDE["git"]`：
- ai(01)：`"Jupyter+PyCharm CE+Git/GitHub（每周提交）"` + git指南
- py(02)：`"PyCharm CE+Jupyter+Git/GitHub（每周提交）"` + git指南
- pp(03)：保持已含git（短语从"Git/Gitee"统一为"Git/GitHub"）
- ai48(05)：`"Jupyter+PyCharm CE+Git/GitHub（每周提交）"` + git指南

### 7. 重建产物验证
- 工单29份重建 → 02 W1工单"配套+工具"行确认含"Git/GitHub（每周提交）"
- PPT 72个重建（02=24/03=16/05=24/01=8）→ 02/05 PPT封面"本课主用"行确认含Git引用

## 三、文件清单

| 文件 | 改动 |
|---|---|
| `软件操作指南/03-Git与GitHub-Gitee使用指南.md` | 重写（33行→350行） |
| `软件操作指南/05-PyCharm使用指南.md` | 扩展（25行→180行，加第七章Git） |
| `软件操作指南/00-软件安装与使用完全指南（文科生照做版）.md` | 第四部分升级 |
| `01-AI应用基础/课程软件与环境配置完全指南.md` | Git选做→必用 |
| `02-程序设计基础/课程软件与环境配置完全指南.md` | Git选做→必用+W1步骤+提交惯例 |
| `03-Python程序设计-项目实战/课程软件与环境配置完全指南.md` | 修文件名断链+强化 |
| `05-AI应用基础48课时版/课程软件与环境配置完全指南.md` | Git选做→必用+提交惯例 |
| `00-资源库总索引.md` | 总地图Git行升级+VS Code→PyCharm CE |
| `_docx_work/env_tools.py` | tool_for全课加git指南 |
| 工单29份 | 重建（tool_for注入"Git/GitHub"到"配套+工具"行） |
| PPT 72个 | 重建（tool_for注入"Git/GitHub"到封面"本课主用"行） |
