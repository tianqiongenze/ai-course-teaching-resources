# 39-PPT教材行布局修复终审报告

> 2026-09-11 ｜ 范围：02/03/05（排除01-AI16）

## 一、根因定位

38号轮判断"PPT不受影响"是错误的。实际：37号轮把教材三行追加到WEEKS.content末尾，`build_ppts.py::split_sessions()`遍历`week["content"]`把教材行当作普通items分配到最后一次课的group，最终进了s24"课程总结与课后任务"页的正文shape——**三行长文本挤进正文shape导致整页布局混乱错位**。02包36处、03包24处命中。

## 二、修复方案（三层分离）

| 层 | 教材行位置 | 渲染方式 |
|---|---|---|
| **WEEKS.content** | ❌ 不含教材行（清出） | split_sessions不再误吞 |
| **week["textbook"]键** | ✅ 教材+预习+检查三行 | 独立键，各渲染器按需取 |
| **PPT正文shape** | ❌ 0处 | 不占正文版面 |
| **PPT演讲者备注** | ✅ 每课1处（d.note） | 教师可见，学生看投影不受干扰 |
| **计划表docx** | ✅ content副本+textbook | PlanBuilder填"授课内容"列时追加textbook行 |
| **方案docx** | ✅ "教材衔接"独立段 | SchemeBuilder块表后独立段（38号轮已修） |

### 具体改动
1. data_py/data_pp/data_ai48三文件：WEEKS注入从`content.append(...)`改为`week["textbook"]=[...]`键
2. gen_common.py PlanBuilder.build()：`fill_cell(cells[1], list(wk["content"])+wk.get("textbook",[]))`——计划表"授课内容"列追加教材行
3. build_ppts_v3.py：closing_tasks后`d.note("教材衔接："+" | ".join(week.get("textbook",[])))`——教材入演讲者备注
4. build_ai48_visual.py：同理`d.note`渲染教材（从D.WEEKS[w-4]取textbook键）

## 三、终验
- **AI视觉核验** s24（曾混乱页）：布局9/10整洁无错位；教材行不在正文；课后任务条目完整清晰
- **docx一致性** 8/8通过（三课课标/计划/方案教材+预习+检查全覆盖）
- **PPT正文教材行**：02=0处 03=0处 05=0处（正文shape零命中）
- **PPT备注教材衔接**：02=24处 03=16处 05=24处（每课1处，教师可见）
- 回归：verify.sh ALL PASS ✅

## 四、多角色终评
- 教授级高工：教材信息入课标info表+计划表授课内容列+方案独立段+PPT备注四层可达，不破坏任何版式
- 教育专家：预习/检查知识点对学生（计划表/方案）和教师（PPT备注）各就各位，不互相干扰
- 美工平面：PPT正文版面零侵入，s24页布局恢复9/10

## 五、再优化空间
无结构性缺口。教材信息已四层落盘且布局整洁；PPT正文/备注/计划表/方案/课标各司其职。
