# 项目长期记忆 · Python编程实战/教学实施资料

## 项目性质
重庆现代制造职业学院 智能控制学院 · 工业互联网专业 **AI课程群教学资源库**。
统一虚构项目载体：**重庆两江智造集团**（细分：精密制造事业部 / 设备智能运维中心 / 数字化转型办公室）。
四门课程包：01-AI应用基础（阶段A 16课时）/ 02-Python编程基础（48课时）/ 03-Python程序设计-项目实战（32课时）/ 05-AI应用基础48课时版（阶段B 32课时）。

## 工作方式约定（用户偏好）
用户以「**多重视角审查 → 打分 → 提方案 → 立即执行 → 出编号报告**」的循环推进，已至 **72 号报告**。
每轮产出：① 顶层编号报告（`NN号报告-*.md`）；② 同步更新 `00-资源库总索引.md` 与各包 `README.md`；③ 诚实声明遗留项。
用户重视**量化实测证据**（页数/命中数/通过率），反感"编造实测数字"（71g 轮明确要求诚实化）。

## PPT 体系口径（72 轮定稿）
| 档 | 用途 | 页数 |
|---|---|---|
| V1授课PPT | 精讲骨架 | 19-25 |
| V2授课PPT | 课堂投屏（上节全量 / 下节精简实操） | 55-66（下节6-8） |
| 授课PPT | 深度讲义参考 | 67-75 |
**硬约束：单册 ≤80 页。**

## 三种代码形态（74 轮定稿 · 每课每周次全覆盖）
| 形态 | 目录 | 定位 |
|---|---|---|
| ① starter | `<包>/学生代码框架/` | 学生填空起步（TODO 骨架） |
| ② 教师参考 | `<包>/教师参考/` | 完成态参考（单文件示意） |
| ③ **工程化项目** | `<包>/工程化项目/<slug>/` | **企业级工程结构 + 全套流程资料** |

**40 个项目**（01包8 / 02包12 / 03包8 / 05包12），每项目 **23 文件**：
`run.py` + `config/rules.yaml`（规则外置）+ `src/<pkg>/{__init__,config,core,io_utils,report,pipeline}.py`
+ `tests/{__init__,test_core,test_config}.py` + `docs/01~08`。
标准：GB/T 8566（docs/08 过程组映射）/ 9385（docs/01）/ 15532（docs/04）/ 8567（全套）+ TOGAF 四域（docs/02）+ ADR-001（docs/07）。
源码文档 **924** 文件（23×40 + 4 索引）+ output 产物 98 = 1022。

## 工具链
- `check_all.py`（根级）— **全量自检总脚本**（7 门禁：页数≤80/页脚编号/效果图覆盖/代码0漂移/依赖锁定/根目录整洁/索引齐备）；公开分享前必跑。
- `_docx_work/eng/` — **工程化项目生成器**（74轮新建）：
  `eng_gen.py`（模板层+`write_project()`，用 `<key>` 标记替换避花括号转义）、
  `eng_helpers.py`（MD 片段助手+`finalize()`，与 specs 解耦防循环导入）、
  `eng_specs.py` + `specs_01/02/03/05.py`（40 项规格）、
  `verify_projects.py`（pytest+run.py 双门禁终验）、`make_index.py`（四包索引 README）。
  重放：`python _docx_work/eng/eng_gen.py --build`；验证：`python _docx_work/eng/verify_projects.py`。
- `_docx_work/slim/slim_ppt.py` — PPT 精简融合（并查集聚类去重 + 15 条填充页规则 + KEEP 保护 + 页脚重编）；`--profile deep|v2`。
- `_docx_work/slim/inject_shots.py` — 01/02 包真实运行效果图注入（`--run`/`--inject`/`--refresh`，幂等）。
- `_docx_work/slim/inject_shots_ai48.py` — 05 包效果图新建（克隆模板页→三卡→插入；`--refresh` 支持重建）。
- `_docx_work/README.md` — 工具清单 + 灾备重建流程 + 踩坑记录（**目录被删后按此重建**）。
- `05包/教师参考/solutions.py` — 12 工单完成态参考实现（m11a…z，`all` 一键全跑）。
- 备份：`_docx_work/_backup_ppt_72/`（163册精简前）、`_backup_ppt_73/`（05包48册注入前）；隔离区 `_artifacts_quarantine/`。
- 四包 `requirements.lock` — 精确版本锁定（未安装项标 `# 待核验`）。
- 环境：三包各自 conda 环境（ai01/py02/pp03/ai48）；本机可用 `/c/miniconda3`、`C:/Python314`（含 sklearn/torch）。

## 关键约定
- 课程思政三融入 / 岗课赛证创 / ABCD 四层分层（D学徒≥60 / C操作员≥70 / B组长≥80 / A师傅≥90）/ 双元制（学校元70% + 企业元30%）。
- 教学法：第1-6周"三步式四步法"（讲→演→模仿→练习）→ 第7-12周完整"六步法"。
- 环境统一：Anaconda + conda 环境 + PyCharm CE + Jupyter + Git（**已全面清除 VSCode**）。
- 实训室：双创中心 302。
- 版权：建议整体 CC BY-NC-SA 4.0；见《版权与合规声明.md》。

## 反复踩坑（务必避免）
1. **`_docx_work/` 三次被外部整目录删除** → 生成器逻辑务必保持简单+文档化，重要产物双写；已补 `_docx_work/README.md` 灾备流程。
2. **PPT 去重禁用两两比较**（链式误删）→ 用并查集聚类。
3. **后台服务随 shell 退出被回收** → 同进程线程启动。
4. granian 在 Windows 多 worker 报 `upstream connect failed` → 用 uvicorn 或 workers=1。
5. 生成器旧脚本依赖 macOS 路径（`/opt/anaconda3`），Windows 环境不可直接重放。
6. **refresh 删除旧页必须"删全部"** —— 只删首个会残留重复页（05包曾出现每册 2 个效果图页）。
7. **卡片识别须排除页脚横线** —— 页脚线宽 12.14in/高 0.02in 会被 `width>=4.5` 误判为卡片。
8. **自检脚本须排除自身** —— 其正则字面量会自我匹配产生假阳性。
9. **numpy 固定宽度字符串会静默截断** —— `np.array(["正常"]*n)` dtype=`<U2`，赋 `"轴承磨损"` 变 `"轴承"`（不报错，最难查）。
10. **requests 走代理连不上本地服务** → 设 `NO_PROXY=127.0.0.1,localhost`。
11. **Python 闭包作用域陷阱**：推导式/生成器循环变量**不得与函数后续变量同名**（抛 `NameError: cannot access free variable`）；渲染逻辑抽成内部函数可解。
12. **中文等宽表按"显示宽度"（CJK=2）而非 `len()`**，测试断言同样要用宽度函数。
13. **自研 `yaml_lite` 支持块状 list 须"双帧"**：`key:` 空值时同时压入(列表父级帧 + 子字典帧+0.5缩进)，遇 `- ` 先弹子字典帧。
14. **YAML 禁"一行多键"与内嵌双引号 JSON**（转义会被吞）→ 改多行键 + 单引号。
15. **pandas 新版 `df.loc[...] = None` 转 NaN**，造缺失值直接用 `np.nan`。
16. **heredoc 写 Python 时 `\n` 易被污染为 `/n`** → 复杂模板用 `chr(10)` 拼接或用 Write 工具直接落盘。
17. **pipeline 必须 `from . import core, io_utils, report` 三件套齐全并调 `report.save`**，否则 run.py 无产物。

## 评分基线（四视角，74轮）
架构师 **97** / 高级美工 96 / 教育专家 96 / 教授级高工 96（平均 **96.3**；73轮 96.0，72轮 90.0）。
