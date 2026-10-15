# 59号报告：PyCharm指南配图conda版重绘与全库venv残留清零

**日期**：2026-09-25
**触发**：用户指出"PyCharm软件操作指南中的配图还是venv而不是使用conda方式，请再次审查项目目录下所有文档资料进行相关替换（涉及到配图的要更加真实详细可操作）"

---

## 一、排查结果

| 位置 | 现状 | 处理 |
|---|---|---|
| `make_guides.py` PyCharm段"首次配置三步" | **"New Project→选venv / Settings→解释器选venv"** ——venv配图唯一源头 | 重绘 |
| `图/pycharm.png` | 8月22日旧版（venv内容已烧进图片） | 重新生成 |
| 全库其他md/py | 03包8份工单任务书"主用工具：PyCharm CE + venv"、载体手册P1.2"venv+Git"、03包README、textbook_map.py PP_PRE W1"venv虚拟环境" | 一并清零 |
| 编号报告（27/28/33/37/41/42号等） | 历史档案记录当时状态 | **不改**（审计工作流：报告是时点快照） |

## 二、配图重绘（核心：更真实详细可操作）

按用户要求升级为**三面板大图**（旧版仅两面板、右栏只有三步文字条）：

### 面板1（左上）：PyCharm CE 界面线框——快捷键标注版
菜单栏（运行▶Shift+F10 / 调试🐛Shift+F9）、项目树（用05包真实目录"学生代码框架/工单任务书/"）、编辑器（Tab补全/Ctrl+Alt+L格式化/断点）、Run窗口（F8逐行F7进函数）、**底部Terminal标出"(py02/pp03/ai48)提示符确认位"**、右下角状态栏"Python 3.12 (环境名) ← conda环境确认位"

### 面板2（中）：首次配置五步（conda环境·照做）——竖流程带真实路径
1. New Project→Location选课程包目录
2. Interpreter下拉→Previously configured→**Add Interpreter→Conda Environment**（蓝色高亮）
3. 列表选已建环境 **py02 / pp03 / ai48**（注明"Anaconda里conda create建的"）
4. Settings(Ctrl+Alt+S)→Project→Python Interpreter→**路径含 envs\py02\python.exe**（蓝色高亮）
5. 右键main.py→Run→看到输出=成功✓

### 面板3（右）：验证三查（90秒防呆）——绿框检查清单
- 查①终端提示符显示(py02)/(pp03)/(ai48)，没有括号=环境没激活
- 查②`import sys; print(sys.executable)`输出含envs\环境名\
- 查③IDE右下角显示Python 3.12(环境名)，显示base=选错重做④
- ⚠橙色警示框：**别选New environment using Virtualenv——本课程统一conda**
- 底部导航：卡住先查01-Anaconda指南第六章

### 技术规格
2053×1203px（旧版约1890×660）· 222KB · 思源黑体渲染 · matplotlib三Axes布局

## 三、验收（judge通道受限，程序化双验）

- **judge会话**：visual-judge周限额已满（2026-09-28重置）+主线程PNG视觉通道故障——按既有兜底规则转程序化
- **源码级验证**：make_guides.py PyCharm段venv出现=0处（唯一"Virtualenv"=警示框）、conda=13处（Conda Environment选项/py02×4/pp03×3/ai48×3/envs路径）
- **像素级验证**：非白像素24%（内容充实，阈值8%）、RGBA模式、新生成时间戳
- md引用为路径引用（`图/pycharm.png`）非内嵌——图更新即全库生效，同时更新05指南的图alt文字

## 四、全库venv残留清零（连带发现）

| 文件 | 修正 |
|---|---|
| 03包8份工单任务书 | "PyCharm CE + venv + Git"→"conda环境(pp03) + Git"；P1.2微课名/虚拟环境要求/及格标准/易错项/`python -m venv`命令全部conda化（并修正指向断链`06-PyCharm CE使用指南.md`→`05-PyCharm使用指南.md`） |
| `14-项目载体手册` | P1.2"venv+Git+目录规范"→"conda环境+Git+目录规范" |
| 03包README | "Python 3.12+ + venv + Git"→"+ conda环境(pp03) + Git" |
| `textbook_map.py` PP_PRE W1 | 教材预习映射"venv虚拟环境/能创建venv"→"conda环境创建与激活/能conda activate pp03" |

**终态**：教学资料现行文件（md/py/配图）venv操作内容=0；仅存编号报告（历史档案）与Anaconda指南的conda vs venv对比表、PyCharm指南"别选Virtualenv"警示（合法保留）。

## 五、坑（入记忆）
matplotlib装饰器画图中**元组内不能用`fc=BLUE`关键字语法**（`SyntaxError: Maybe you meant '=='`）——色值作元组第三元素传入循环解包。
