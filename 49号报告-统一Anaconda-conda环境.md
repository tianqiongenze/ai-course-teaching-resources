# 49号报告：统一使用Anaconda conda环境（venv全清零）

**日期**：2026-09-14
**触发**：用户要求"每门课都要使用Anaconda，在软件安装和环境配置中使用Anaconda及相关命令创建和切换相关python环境，全部更新所有相关资料达到统一要求"

---

## 一、改造前现状

| 课程/资料 | 环境创建方式 | 问题 |
|---|---|---|
| 01-AI应用基础 | 无独立环境，直接pip到base | 不符合"每门课独立环境" |
| 02-Python编程基础 | 无独立环境，口径提"课堂仍用venv+requirements"但无venv命令 | 含venv残留引用 |
| 03-项目实战 | **venv**（`python -m venv .venv`+`.venv\Scripts\activate`） | 唯一用venv的课程，与统一口径冲突 |
| 05-AI应用基础48 | 无独立环境，直接pip到base | 不符合"每门课独立环境" |
| Anaconda指南 | 35行简版，有conda create/activate但太简 | 缺PyCharm集成、缺环境管理命令、缺切换/导出教学 |
| PyCharm指南 | 教"New environment using Virtualenv" | 与conda统一口径冲突 |
| VSCode指南 | 教`python -m venv venv` | 与conda统一口径冲突 |
| 00总指南第五部分 | `pip install` 无conda activate | 无环境创建步骤 |
| 00总索引总地图 | 03="全程+venv"、Anaconda="可选/开课前总管" | venv口径 |
| env_tools.py | 03课返回"PyCharm CE + venv + Git/GitHub" | 工单/PPT注入venv |
| 03 check_env.py | `check("venv模块", ...)` | 检测venv而非conda |

## 二、改造内容

### 1. Anaconda指南重写（35行→200行）
`软件操作指南/01-Anaconda安装与使用指南.md` 全文重写，九章：
- 一、它是什么（conda vs venv对照表+为什么统一用conda）
- 二、安装（下载/安装/验证/镜像配置四步）
- 三、**为每门课创建独立环境**（conda create -n py02/pp03/ai48 + conda activate + pip install + 验证四步）
- 四、conda环境管理命令速查（创建/激活/退出/查看/装包/导出/删除7类）
- 五、Anaconda Navigator（图形界面）
- 六、**在PyCharm中使用conda环境**（新建项目选conda环境/已有项目切换/终端激活/验证路径4小节）
- 七、各课程环境配置对照表（02=py02/03=pp03/05=ai48+核心依赖+每次课前操作+换课切换）
- 八、常见问题（7题：conda不是内部命令/pip装了import不到/numpy冲突/torch失败/空间大/Navigator白屏/环境间冲突）
- 九、命令速查表

### 2. PyCharm指南改（Virtualenv→conda环境）
`软件操作指南/05-PyCharm使用指南.md` 第三章"首次配置"：
- 旧：选"New environment using Virtualenv"+Base interpreter选Anaconda
- 新：选"Previously configured interpreter"→Add Interpreter→**Conda Environment**→选已有环境（py02/pp03/ai48）
- 加"⚠️不要选New environment using Virtualenv"警告
- 加第4步验证conda环境（`python -c "import sys; print(sys.executable)"`看路径含`envs\py02`）
- FAQ改"venv"→"conda环境"

### 3. VSCode指南改（venv→conda）
`软件操作指南/06-VSCode使用指南.md`：
- 标题"轻量首选"→"备选"（42号轮已迁移到PyCharm CE）
- 第4步：`python -m venv venv`→`conda activate 课程环境名`
- FAQ：Select Interpreter→选venv→选conda环境

### 4. 00总指南升级
`软件操作指南/00-软件安装与使用完全指南（文科生照做版）.md`：
- 第一部分加第4步"为每门课创建conda环境"（conda create -n py02/pp03/ai48+conda env list验证）+第5步"激活环境并装基础包"（conda activate py02+pip install）
- 第五部分标题从"安装课程所需Python包"→"为每门课创建conda环境并安装Python包"
- 装包表加"先激活"列（conda activate py02/pp03/ai48）

### 5. 四课完全指南统一（venv→conda）

| 课程 | 环境名 | 改造内容 |
|---|---|---|
| 01-AI应用基础 | `ai01` | 基础环境三步装：python.org→Anaconda+conda create+conda activate |
| 02-Python编程基础 | `py02` | W1装机课加conda环境创建步骤；每周加conda activate；基础环境段改conda；附录新工具博览venv→conda |
| 03-项目实战 | `pp03` | **venv全清**：软件地图"venv管理"→"conda环境管理"；W1/W2步骤改conda create+activate；基础环境段venv→conda；逐周表/故障排查/check_env全改 |
| 05-AI应用基础48 | `ai48` | 基础环境三步装：加conda create+conda activate |

### 6. 00总索引总地图升级
Anaconda行从"可选环境管理/开课前总管/推荐按周装包"→**"创建ai01/py02/pp03/ai48环境·全程"**；PyCharm CE行03列"全程+venv"→"全程"

### 7. env_tools.py升级
03课(pp)返回短语从"PyCharm CE + venv + Git/GitHub"→**"PyCharm CE + conda环境(pp03) + Git/GitHub"**

### 8. 03 check_env.py升级
`check("venv模块", ...)` → `check("conda环境(需先conda activate pp03)", ...)`——检测sys.executable路径含conda/envs

### 9. 重建验证
- 工单29份重建→03工单"配套+工具"行确认"PyCharm CE + conda环境(pp03) + Git/GitHub"
- PPT 72个重建→封面"本课主用"行含conda环境
- 全资料venv残留扫描=0（仅保留Anaconda指南conda vs venv对比表+PyCharm"不要选Virtualenv"警告）

## 三、课程环境对照表（终态）

| 课程 | conda环境名 | Python版本 | 创建时间 | 核心依赖 |
|---|---|---|---|---|
| 02-Python编程基础 | `py02` | 3.10 | W1装机课 | numpy/pandas/matplotlib/scikit-learn/scipy |
| 03-项目实战 | `pp03` | 3.10 | W1 | numpy/pandas/matplotlib/scikit-learn/streamlit/plotly/sqlalchemy |
| 05-AI应用基础48 | `ai48` | 3.10 | W4开课前 | numpy/pandas/scikit-learn/xgboost/torch(CPU)/onnxruntime/opencv |
| 01-AI应用基础16 | `ai01` | 3.10 | W4开课前 | numpy/scikit-learn/torch(CPU)/onnxruntime |

## 四、文件清单

| 文件 | 改动 |
|---|---|
| `软件操作指南/01-Anaconda安装与使用指南.md` | 重写（35行→200行） |
| `软件操作指南/05-PyCharm使用指南.md` | 第三章Virtualenv→conda+FAQ |
| `软件操作指南/06-VSCode使用指南.md` | venv→conda+标题改备选 |
| `软件操作指南/00-软件安装与使用完全指南（文科生照做版）.md` | 第一部分加conda环境创建+第五部分改conda |
| `01-AI应用基础/课程软件与环境配置完全指南.md` | 基础环境段conda |
| `02-程序设计基础/课程软件与环境配置完全指南.md` | W1加conda+每周activate+基础段+附录 |
| `03-Python程序设计-项目实战/课程软件与环境配置完全指南.md` | venv全清→conda |
| `05-AI应用基础48课时版/课程软件与环境配置完全指南.md` | 基础环境段conda |
| `00-资源库总索引.md` | 总地图Anaconda行+PyCharm CE行 |
| `_docx_work/env_tools.py` | pp返回conda环境 |
| `03-Python程序设计-项目实战/check_env.py` | venv检测→conda检测 |
| 工单29份+PPT 72个 | 重建（tool_for注入conda环境） |
