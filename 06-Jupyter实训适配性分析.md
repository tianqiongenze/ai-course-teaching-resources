# 三门课程 Jupyter 实训适配性分析与使用说明

## 一、结论（先说答案）

**三门课程全部28个工单任务均可"只使用Jupyter"完整完成**，无需安装任何外部服务：
- 数据：全部由本地生成器/内置样例产生（无外网下载）；
- 深度学习：CPU版PyTorch训练tiny模型（M2.1约40秒、M2.2约60秒）；
- YOLO：本地ONNX权重推理（无需GPU、无需在线下载）；
- 大模型：本地模拟LLM服务在notebook内以线程启动（无需外网API）；
- 工业协议：Modbus/MQTT模拟器以子进程启动（无需Docker/真实设备）。

## 二、逐任务适配矩阵

| 课 | 任务 | 纯Jupyter可行性 | 说明 |
|----|------|----------------|------|
| AI | M1.1/M1.2 分类与特征工程 | ✅ 完全 | sklearn+NumPy；数据本地生成 |
| AI | M2.1 CNN缺陷检测 | ✅ 完全 | CPU训练tiny-CNN约40s（实测acc 0.875） |
| AI | M2.2 LSTM寿命预测 | ✅ 完全 | CPU训练约60s（实测MSE 0.074） |
| AI | M3.1 尺寸测量 | ✅ 完全 | OpenCV本地图像 |
| AI | M3.2 YOLO检测 | ✅ 完全 | ONNX本地权重CPU推理（实测FPS 160档≈19） |
| AI | M4.1 文本分类 | ✅ 完全 | jieba+TF-IDF本地语料 |
| AI | M4.2 智能决策助手 | ✅ 完全 | 模拟LLM以线程在notebook内启动 |
| PY | W1-W10 | ✅ 完全 | 纯Python+轻量库，样例数据内嵌 |
| PY | W11 数据采集 | ✅ 完全 | 模拟器以subprocess启动，采集完自动清理 |
| PY | W12 综合项目 | ✅ 完全 | 上述能力组合 |
| PP | P1.1/P1.2 | ✅ 完全 | 纯Python+Git命令 |
| PP | P2.1/P2.2 | ✅ 完全 | Pandas/NumPy本地数据 |
| PP | P3 仪表盘/日报 | ⚠️ 两种方式 | 日报(HTML/PDF)完全可；Streamlit仪表盘在Jupyter内以`%run`嵌入或命令行启动（见notebook说明） |
| PP | P4.1 多源采集 | ✅ 完全 | 三台PLC模拟器子进程+线程采集（notebook内演示版） |
| PP | P5 数据库 | ✅ 完全 | SQLite文件库零安装 |
| PP | P6 模型与部署 | ✅ 完全 | sklearn训练+http.server推理服务（线程） |

## 三、Jupyter实训包结构（每课程包/Jupyter实训/）

- `任务码_工单号_名称_学生版.ipynb` ×28：工单信息+ABCD分层表 → 资讯导学（PRIMM之Predict） → 环境与数据准备（可运行） → 任务要求 → starter分cell（Investigate→Modify→Make） → 提交要求与避坑
- `任务码_工单号_名称_教师版.ipynb` ×28：参考实现源码+执行验证cell，**已全部用本地Anaconda Jupyter（nbconvert --execute）实跑验证**
- 运行约定：首个cell自动把工作目录切到课程包根（`data/`、`fonts/`、权重路径与桌面版完全一致）

## 四、教师使用建议

1. **课堂模式**：投影教师版逐步执行；学生开学生版跟做——Jupyter的"cell级执行"天然契合六步法的"决策→实施→检查"循环与PRIMM"预测→运行"环节。
2. **提交方式**：学生提交**带输出的ipynb**（相当于自带运行证据），配合`jupyter nbconvert --to html`可归档为网页报告。
3. **环境**：机房统一Anaconda（含requirements）；本机验证环境为Anaconda 3.12 + Jupyter（ipykernel 6.28）。
4. **与传统.py的关系**：Jupyter版与`学生代码框架/*.py`内容同源，二选一或混用均可；期末交付建议回归.py+Git（工程规范）。
