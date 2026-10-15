# 42-编辑器迁移（VS Code→PyCharm CE/Jupyter）与Jupyter文件关联报告

> 2026-09-12 ｜ 范围：02/03/05（排除01-AI16）

## 一、改造依据

用户要求："各个合适的阶段要求使用Jupyter或PyCharm-社区版而不是VS Code"。

## 二、改造方案

| 课程 | 主编辑器 | Jupyter用途 | 改动依据 |
|---|---|---|---|
| 02-程序设计基础 | **PyCharm CE**（.py编码全程） | **Jupyter**（每周notebook实训，24个ipynb全覆盖） | 24个notebook已存在但未被工单/PPT引用 |
| 03-项目实战 | **PyCharm CE**（工程化项目） | **Jupyter**（P2.1/P2.2数据探索，16个ipynb） | PP是工程项目课，PyCharm的工程功能更强 |
| 05-AI48 | **Jupyter**（全程实训主战场） | **PyCharm CE**（starter编码） | AI48已有Jupyter作主用，补PyCharm编码 |

## 三、落地范围

### 1. env_tools.py tool_for改造（PPT封面"本课主用"行+工单信息表"配套+工具"行数据源）
- PY：`PyCharm CE（全程主编辑器）+ Jupyter（每周notebook实训）`
- PY W8+：`PyCharm CE（编码）+ Jupyter（Pandas数据实验）`
- PP：`PyCharm CE + venv + Git（每周提交）`
- PP W3-4：`PyCharm CE（编码）+ Jupyter（Pandas/NumPy数据探索）`
- AI48：`Jupyter（全程实训）+ PyCharm CE（starter编码）`

### 2. VS Code引用全库清零
- 三课py/md文件：37个文件批量替换（VS Code/VSCode/vscode→PyCharm CE）
- _docx_work生成器层：meta3_py/cs_data/data_py/data_pp/sessions_meta/make_guides/env_tools共23处
- **结果**：PPT正文0处、工单0处、三课py/md 0处VS Code残留

### 3. PPT/工单PyCharm+Jupyter覆盖
- 工单含PyCharm/Jupyter：**41份**（三课全部分层工单"配套+工具"行）
- PPT含PyCharm/Jupyter：**102个**（封面"本课主用"meta行）

### 4. 通用指南加编辑器选择说明
`00-软件安装与使用完全指南`加："本套课程主用PyCharm CE和Jupyter，VS Code备选"

## 四、重建
PPT 72个 + 工单29份 + 课标docx×3+PDF×3 + 方案docx×3全部重建；env_tools/tool_for三课全覆盖

## 五、终验
- VS Code残留：PPT=0、工单=0、py/md=0 ✅
- PyCharm/Jupyter覆盖：工单41份、PPT 102个 ✅
- verify.sh ALL PASS ✅
- 三课课标/方案/计划表一致性8/8（37轮基线不受影响——编辑器变化在tool_for层，不涉及周次/学时/考核）
