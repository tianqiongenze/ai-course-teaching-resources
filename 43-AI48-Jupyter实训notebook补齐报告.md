# 43-AI48 Jupyter实训notebook补齐报告

> 2026-09-12 ｜ 范围：05-AI应用基础48课时版

## 一、问题

05-AI48仅有4个notebook（W5 MLP / W11多智能体各师生版），覆盖48课时中的2/12周——远不足以支撑全程教学。对比：02有24个（12周×师生版）、03有16个（8周×师生版）。

## 二、修复

### 1. build_ipynb.py改造
- COURSES加`"ai48"`条目（folder/name/sol_file/starter_dir映射）
- TASKS追加AI48_TASKS：12周×(教学周,工单号,工单名,starter文件,solutions函数名)
- get_meta加ai48分支：从meta3_ai48.AI48取basics/skills/abcd/code/errors，从sessions_ai48.SESSIONS取quiz/sp/sg/steps（sp/sg是list→取[0]转str适配模板）
- AI TASKS周次修正：6-13→4-11（31轮AI_META键平移后build_ipynb未同步，导致W12=M4.1时AI_META[12]不存在报NoneType）

### 2. 生成结果
- AI48 Jupyter实训：**4→24个**notebook（12周×师生版全覆盖）
- 三课notebook总数：02=24 + 03=16 + 05=24 = **64个**（此前05仅4个→64）
- 旧的4个手工notebook（W5_MLP神经网络/W11_多智能体调度旧命名）已清理

### 3. notebook内容结构（与02/03同构）
- 学生版：工单信息/ABCD分层表 → 课前资讯(Predict预习快问) → 环境与数据准备(可运行) → 任务与PRIMM引导 → starter分cell → 提交要求与避坑
- 教师版：简版说明 → 环境与数据准备 → 参考实现(inspect取源码) → 执行与验证

## 三、覆盖度对照
| 课程 | 教学周 | notebook数 | 覆盖率 |
|---|---|---|---|
| 02-程序设计基础 | 12周 | 24 | 100%（12周×师生版） |
| 03-项目实战 | 8+1周 | 16 | 100%（8周×师生版） |
| 05-AI48 | 12周 | 24 | **100%（12周×师生版）** ← 从4→24 |
