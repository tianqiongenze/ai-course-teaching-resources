# 51号报告：VS Code全面清除（编辑器统一PyCharm CE）

**日期**：2026-09-14
**触发**：用户要求"再次一一审查每个课程所有资料，是否还有VS Code的安装使用，我们已经使用PyCharm替换了，就不要再出现VS Code了，特别要修改00-软件安装与使用完全指南（文科生照做版）.md文件中关于VS Code的安装部分改为PyCharm"

---

## 一、改造前VS Code残留分布（全资料扫描）

| 文件 | 残留数 | 性质 |
|---|---|---|
| `00-软件安装与使用完全指南（文科生照做版）.md` | 9处 | **第二部分"安装VS Code"整段**（下载/装扩展/选解释器/验证）+第5步"在VS Code中用Jupyter"+故障排查表 |
| `软件操作指南/06-VSCode使用指南.md` | 整个文件 | 独立VS Code指南（42号轮标记"备选"保留） |
| `软件操作指南/图/vscode.png` | 图文件 | VS Code界面线框图 |
| 01包工单任务书×8（M1.1-M4.2） | 各1处 | "本课主用工具：Jupyter+VS Code（编码）+06-VSCode使用指南.md引用" |
| `01-AI应用基础/课程软件与环境配置完全指南.md` | 1处 | 软件清单表"\| VS Code + Python扩展 \|编码（或PyCharm）\|" |
| `01-AI应用基础/环境搭建指南.md` | 1处 | "基础环境：Python 3.12+、VS Code + Python扩展" |
| `00-资源库总索引.md` | 1处 | "Anaconda+VS Code+Jupyter+Git六部分" |
| `版权与合规声明.md` | 1处 | 商标说明提及VS Code |
| `_docx_work/make_guides.py` | 1段 | 第6段VS Code界面线框插图生成（保存为vscode.png） |
| `_docx_work/env_tools.py` | 1处 | GUIDE字典"vscode"键映射06-VSCode使用指南.md |

**保留正确的3处**（说明性提及，非使用内容）：
- 05-PyCharm指南"为什么不用 VS Code"对比说明（42号轮迁移理由）
- 03-Git指南 `.vscode/`（.gitignore标准目录名）
- env_tools.py注释"VS Code指南已归档"（变更记录）

## 二、改造内容

### 1. 00总指南第二部分重写（VS Code安装→PyCharm CE安装）
- 标题："安装VS Code（代码编辑器）"→"安装PyCharm CE（代码编辑器）"
- 编辑器选择说明：删"VS Code也可用但非主推——安装步骤保留作为备选"→"统一使用PyCharm CE"
- 第1步下载：code.visualstudio.com→jetbrains.com/pycharm/download（Community Edition，勾选PATH+.py关联）
- 第2步：删"安装Python扩展"（VS Code特征）→"首次启动与新建项目"（New Project→Conda Environment→选conda环境，加"不要选New environment using Virtualenv"警告）
- 第3步：命令面板Select Interpreter→File→Settings→Python Interpreter→确认conda环境
- 第4步：验证运行hello.py（VS Code打开文件夹→PyCharm项目树右键Run）
- 第5步："在VS Code中也能用Jupyter"→"在PyCharm中也能用Jupyter"（Jupyter插件+conda内核）
- 故障排查表："VS Code运行.py提示没有Python解释器"→"PyCharm运行.py提示"（Conda Environment→选课程conda环境）

### 2. 06-VSCode使用指南归档
`教学实施资料/软件操作指南/06-VSCode使用指南.md` → `_docx_work/_local_only/归档_VSCode指南/`（旧口径归档不删，符合工作流；VS Code不再出现在教学资料中）
`图/vscode.png` → 同目录归档

### 3. env_tools.py GUIDE字典
删"vscode"键（"06-VSCode使用指南.md"映射）。验证：tool_for全课全周（ai/py/pp/ai48）4/4正常——tool_for从不引用GUIDE["vscode"]，删键安全

### 4. 01包工单任务书×8批量替换
"Jupyter（实训/演示）+ VS Code（编码）+06-VSCode使用指南.md引用"→**"Jupyter（实训/演示）+ PyCharm CE（编码）+ Git/GitHub（每周提交）+05-PyCharm使用指南.md+03-Git指南引用"**（与env_tools ai分支口径一致）

### 5. 01完全指南+环境搭建指南+总索引+版权声明
- 01完全指南软件清单表："VS Code + Python扩展（编码或PyCharm）"→"PyCharm CE 2025.x（统一编辑器，Community免费版）"
- 01环境搭建指南："VS Code + Python扩展"→"Anaconda+PyCharm CE"
- 00总索引："Anaconda+VS Code+Jupyter+Git六部分"→"Anaconda+PyCharm CE+Jupyter+Git六部分"
- 版权声明：商标说明"Anaconda/VS Code/GitHub"→"Anaconda/PyCharm/GitHub/Gitee"

### 6. make_guides.py删旧VS Code插图段
第6段（PyCharm CE标题但内容VS Code风格线框+vscode.png保存）删除→print"5张指南配图已生成"

## 三、重建与验证

| 项 | 结果 |
|---|---|
| 工单docx重建 | 29份（用`_docx_work/venv/bin/python`，venv含python-docx+pptx；anaconda3无docx） |
| 03工单"配套+工具"行验证 | "PyCharm CE + conda环境(pp03) + Git/GitHub（每周提交）"——无VS Code ✓ |
| tool_for验证 | ai/py/pp/ai48全周次4/4正常 |
| 最终扫描 | 教学资料+数据文件VS Code残留=0（保留3处正确说明性提及） |
| 软件操作指南目录 | 00/01/02/03/04/05六份指南（06-VSCode已归档），图/5张（vscode.png已归档） |

## 四、注意：docx生成器解释器
- `_docx_work`的docx/pptx生成器（build_worksheets/build.py等）须用**`_docx_work/venv/bin/python`**跑（venv含python-docx+python-pptx）
- `/opt/anaconda3/bin/python`无python-docx（只有python-pptx）——build_shuoke.py等纯pptx生成器可用anaconda3
- 此前各轮部分生成用anaconda3跑docx成功存疑，本轮起统一用venv解释器跑docx生成器

## 五、终态
- **编辑器统一**：PyCharm CE（编码）+ Jupyter（实训）——VS Code全库清零完成（42号轮清使用、51号轮清安装与残留）
- VS Code资产归档：`_docx_work/_local_only/归档_VSCode指南/`（06-VSCode使用指南.md+vscode.png）
