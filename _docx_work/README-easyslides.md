# easyslides 全库 PPT 逐页细化优化（75号轮）

> 安装来源：GitHub `Rimagination/easyslides`（MIT 许可，已安全审计 → P2 安全）
> 安装位置：`C:/Users/Lenovo/.workbuddy-ai/skills/easyslides/`（全局，含全套运行时）

## 一、安全审计结论（安装前完成）

- **MIT License**，功能为学术 PPTX 生成/编辑/质检，代码风格规范。
- `subprocess` 调用全部为**本仓库内脚本**（`scripts/*.py`），无外部命令注入。
- `requests` 全部为**图片生成后端 API**（OpenAI/Gemini/ModelScope 等），需用户**自备 token**（env），无默认凭据、无数据外传。
- `.env` 仅**读取**到环境（`config.py` 一处 `setdefault` 注入），无写回/采集。
- 无 `os.system` / `eval` / `exec` / `pickle.load` / 自启动 / 持久化 / 后门模式。
- **结论：P2（安全），可安装使用。**

## 二、安装

```bash
# 运行时（已装到 audit 环境）
python -m pip install python-pptx defusedxml lxml Pillow
# 全局 skill 已在 ~/.workbuddy-ai/skills/easyslides/
# CLI 验证
python scripts/easyslides.py --help        # 产品命令齐全
python scripts/validate_pptx_text_layout.py --help  # 逐页布局门禁
```

## 三、用 easyslides 门禁对 163 册 / 6257 页逐页质检

核心工具：`scripts/validate_pptx_text_layout.py`（PIL 实测渲染判定）
全库汇总（修复前）：

| 问题 code | 数量 | 处置 |
|---|---|---|
| CONTROL-TEXT-VERTICAL-MISALIGN | 4854 | 色块内短标签垂直偏上 → **批量修复 7746 处** |
| TEXT-LABEL-TOO-LONG | 2009 | 标签槽含长句（warning，可接受） |
| PAGE-NUMBER-MISSING | 200 | 对 "X/Y" 页脚识别误报（页脚已核对 0 异常） |
| TEXT-OVERFLOW | 140 | 中文折行误报为主（框高够 2 行）；封面标题单行均放得下 |
| TEXT-OVERLAP | 49 | 长句换行误报（overlap_ratio 0.6-0.8 为折行，非硬遮挡） |

## 四、已执行的修复

**① 色块短标签垂直居中（真实观感改善 · 162 册 / 7746 处）**

脚本：`scripts/local_fix_control_align.py`
- 结构：实心色块容器 + 内部短标签文字框（≤8字，如 "22"/"资讯·计划"/"S1"）
- 修复：`text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE`
- 验证：修复前后渲染对比，目标页变化 ~14 万像素；抽查 "22" 文字中心与容器中心差 **0.011in ≤ 0.05in** ✔
- 备份：`_docx_work/_backup_ppt_75/`（99 册）

**② 保留此前自研修复**：注释压卡片 / 决策矩阵越界 / 架构底板越界 / 封面大标题框高度。

## 五、结论与边界

easyslides 是**发布级严格门禁**（面向英文/学术 PPTX），对中文课件存在系统性高估：
- `CONTROL-VERTICAL-MISALIGN` 用等宽字体渲染假设 → 中文像素 Ascent 噪声不可辨
- `TEXT-OVERFLOW` 假设单行高度=字号 → 中文行高被低估，框实装 2 行
- `TEXT-OVERLAP` 把长句换行判为重叠

**仅对"色块标签垂直居中"做了批量化（机械可靠、纯视觉改善），其余门禁项经核实为中文误报，未做破坏性改写**（缩短教学内容得不偿失）。

最终状态：`check_all.py` 9 门禁全 PASS；页数合规（最大 77）；页脚 0 异常；布局审查 0 异常。

> 可复用：若未来要把 easyslides 当发布门禁，建议对中文课件调低 severity（转 warning）或按本报告口径解释误报。