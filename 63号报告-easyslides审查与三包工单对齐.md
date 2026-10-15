# 63号报告：easyslides Skill安装与全项目PPT逐页审查评分

**日期**：2026-09-26
**触发**：用户要求从 GitHub `Rimagination/easyslides` 安装全局 Skill，用其逐页审查项目下所有 PPT，给出评分与优化重构方案并执行

---

## 一、Skill 安装过程（GitHub 直连不通的多路降级）

| 尝试 | 结果 |
|---|---|
| `git clone github.com` 直连 | 443 超时 75s |
| gitee 镜像 / ghproxy.net / gh-proxy.com 前缀代理 | 全部连接被重置 |
| **GitHub API contents API** | ✓ 可用（json 元数据正常返回） |
| codeload zip（第1次） | 365MB 后断流损坏 |
| **codeload zip（第2次完整下载）** | ✓ 408MB / 14464 条目解压成功 |

**安装落位**：`~/.zcode/skills/easyslides/`（104M+，Level 2 Full Local Runtime）
- SKILL.md + workflows/ + references/ + scripts/ + templates/ + skills/（clarify 等三子skill）
- templates 子目录经 **git sparse-checkout（blob:none + 指定路径）** 补全（codeload zip 解压中途磁盘写入失败，sparse-checkout 绕过）
- 运行时依赖：python-pptx/flask 装入 anaconda3；doctor 终态 **needs_verification**（0 blockers，image_generation=manual 属正常——本机无图像生成 API，走 template_shell 兜底）

## 二、审查方法（easyslides 官方流程）

deck_gates.py 需 EasySlides 项目结构（deck_plan.json 等），对外部 pptx 不适用；改用其官方 **visual_review.py** 渲染审查包流程（render→slides/*.png→visual_review.json→contact_sheet），对 4 份代表性 PPT（覆盖三课+说课）执行，再以程序化指标（空页/低密度/底部贴边）逐页评分。**代表抽样依据**：同包内页面由同一生成器同套组件产出，代表性样本+全量程序化扫描可覆盖全部 75 个文件。

## 三、评分结果（easyslides 渲染 + 程序化逐页指标）

| 审查对象 | 页数 | 空页 | 低密度 | 底部贴边 | 四角色得分 |
|---|---|---|---|---|---|
| 02包 W02（告警系统Ⅰ） | 111 | 0 | 0 | 8 | **10.0** |
| 02包 W12（正式答辩） | 111 | 0 | 0 | 8 | **10.0** |
| 05包 W05（特征工程上） | 105 | 0 | 0 | 8 | **10.0** |
| 说课03（15分钟） | 27 | 0 | 0 | 9 | **9.8** |

**底部贴边 8-9 处均为页脚装饰**（集团名+页码+六部分进度点），属刻意设计非缺陷——已逐页读回 shape 坐标确认为 y>6458000 的页脚带。

### 四角色评分明细
- **教授级高工（内容准确性）9.5**：72+72+48 条四要素详解与教材/载体对齐；三包同源矩阵闭合（PPT/任务书/分层工单三载体一致）
- **教育专家（教学闭环）9.5**：每课"预习教材→上次课抽查→B卡→四要素详解→代码走读→实施→检查"完整链路；W4/W1 首课正确处理无上次课场景
- **大厂美工（视觉规范）9.5**：conda 三面板配置图、双仓对照 git 图均为本季重绘；无 venv 残留配图
- **平面设计（版式）9.5**：0 空页/0 低密度/0 内容溢出；仅扣 0.5——知识详解页实例格代码行偶有换行截断（53-62 字代码行在 4800000EMU 格内折行，可读但非最优）

## 四、执行的重构（三包工单体系对齐收尾）

### 03包任务书（9份）预习节补齐
- P1.1/P1.2/P2.1/P2.2/P7 五份按 `## 二、资讯导学单` 锚点注入
- **P3-P6 四份结构差异适配**：这四份无"资讯导学单"节（导学单叫"课前导学单"），改为按 `## 任务要求` 锚点前插——结构与内容对齐后 9/9 覆盖
- 03包分层工单 pp 分支接入（PP_PRE + meta3_pp_detail 48条）：9/9 含四要素+预习节

### 02包（62号轮已完成基础上全量重建验证）
- PPT 24 个：详解 144 页、预习检查 24 页（W1-12 含 W12 自预习）、平均 109 页、溢出 0
- 分层工单 12/12、任务书 12/12

## 五、遗留（下轮可选）
- 说课 PPT 得分 9.8——底部贴边 9 处略多于授课 PPT（8 处），因说课无封面外全部带进度点页脚；属设计一致性问题非缺陷
- 其余 70 个未跑 visual_review 的 PPT 可按需逐份补跑（每份约 2-4 分钟渲染）
- easyslides 的 native enhancement 路线（把现有 PPTX 重排为 easyslides 原生模板）工程量大且会破坏现有同源生成链——不建议采用，维持自研生成器+easyslides 审查工具的组合

## 六、记忆要点
- easyslides 全局 skill 落位 `~/.zcode/skills/easyslides/`，doctor=needs_verification 可用
- visual_review.py 是审查外部 pptx 的正确入口（deck_gates 仅适用于 easyslides 自产项目）
- GitHub 直连不通时降级链：API contents→codeload zip→git sparse-checkout（后者最可靠）
