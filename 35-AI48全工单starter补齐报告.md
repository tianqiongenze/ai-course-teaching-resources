# 35-AI48全工单starter补齐（12/12）报告

> 2026-09-11 ｜ 承34号轮建议：按w1模式逐周补齐其余10个starter

## 一、交付清单（`05包/学生代码框架/`，教学周命名）

| starter | 工单 | 双解/特色 | TODO数 |
|---|---|---|---|
| w2_feature_starter.py | M1-1b特征 | 时域三件套 vs 频域双特征→随机森林证"设计值钱"（a16指纹） | 2 |
| w3_classify_starter.py | M2-1a分类 | LR vs DT双解+**手写混淆矩阵**（不许调库） | 1 |
| w4_tuning_starter.py | M2-2调优 | GridSearch vs Randomized+**工时账计时**；无xgboost自动回退RF（环境也是选型） | 1 |
| w6_bidding_starter.py | M2-3b竞标 | **双线轻量基线**（图像块统计/时序滑窗RMS比）产出竞标数据表——"竞标书要证据不要形容词" | 2 |
| w7_transfer_starter.py | M3-1迁移 | **迁移思想实验**（冻结随机投影=预训练提取器 vs 原始像素训头，零torch） | 2 |
| w8_detect_starter.py | M3-2检测 | **手搓检测器**（滑窗分数图→阈值→定位框→IoU→FPS），YOLO调参的本质 | 2 |
| w9_prompt_starter.py | M4-1 LLM | 三版Prompt量化对比；call_llm三通道（真实API/规则兜底） | 1 |
| w10_rag_starter.py | M4-2 RAG | 切分→检索→引用三步；"查无依据敢说出口"；解B指向Chroma双解demo | 1 |
| w12_defense_starter.py | Z答辩 | 档案袋五层自检+**答辩提纲自动生成**（一图贯通） | 1 |
| （w1/w5/w11已有） | M1-1a/MLP/M5-1 | w1纯Py-Pandas双解；w5改占位提示不再exit(1) | — |

## 二、大一适配四原则（全部满足）
1. 合成数据自带（零数据准备）；2. 离线CPU零重依赖（torch/yolo级全用思想实验或轻量替身，真机版标注"教师演示"）；3. **TODO未填也能跑通占位流程**（烟测12/12退出0——第一次运行永远不报错，防止挫败感）；4. 每个starter尾部打印"目标：…"（对标工单达标线）。

## 三、联动更新
- README分级表补"Starter覆盖度12/12"行；课标资源行/教学方式大一适配条目落盘（34号轮该编辑因heredoc引号问题未生效，本轮合并修复）并重建docx+PDF
- 00-总索引新增35号轮条目

## 四、验证
- 烟测：12/12 starter语法通过、运行退出0、未填TODO输出引导语
- 课标docx抽验：starter全覆盖12/12、campus_skills、大一适配三要素齐
