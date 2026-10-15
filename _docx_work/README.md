# `_docx_work/` —— 生成器与工具基础设施（74号轮·已纳入版本控制）

> ✅ **本目录已纳入 Git 版本控制**（74号轮）——历史三次被外部整目录删除的悲剧不再重演。
> 自动提交：双击 `autocommit.bat`；详见文末"七、版本控制"。

> ⚠ **重要**：本目录历史上被外部整目录删除过 **3 次**（01包事故模式）。为此本轮做了三件事：
> ① 所有工具**逻辑保持简单、单文件、零魔法**，可据本 README 重建；
> ② 关键产物**双写**（数据落 `_shots*.json`，报告落顶层 md）；
> ③ 本 README 即**灾备说明书**——即使目录被删，按此清单可在 30 分钟内重建。

---

## 一、工具清单

| 工具 | 作用 | 关键参数 |
|---|---|---|
| `slim/slim_ppt.py` | **PPT 精简融合**：并查集聚类去重 + 15 条填充页规则 + KEEP 保护 + 页脚重编号 | `--dry` 空跑 / `--apply --target 80 --profile deep\|v2 <pptx...>` |
| `slim/inject_shots.py` | **01/02 包效果图注入**：把参考实现真实输出写入"（教师课后替换）"占位页 | `--run`（跑解缓存）/ `--inject` / `--refresh`（重排+刷新） |
| `slim/inject_shots_ai48.py` | **05 包效果图新建**：克隆模板页 → 重建三卡内容 → 插入"工单页"之后 | `--run` / `--inject` / `--refresh` / `--dry` |
| `slim/_shots.json` | 01/02 包参考实现真实输出快照（数据层，双写产物） | 自动生成 |
| `slim/_shots_ai48.json` | 05 包 12 工单完成态输出快照 | 自动生成 |

**依赖**：`python-pptx`、`lxml`（`pip install python-pptx lxml`）。
运行参考实现另需各包业务依赖（见各包 `requirements.lock`）。

---

## 二、备份与隔离区

| 目录 | 内容 | 说明 |
|---|---|---|
| `_backup_ppt_72/` | 163 册 PPT **精简前**原件（49MB） | 72号轮备份；需回滚时按原路径覆盖 |
| `_backup_ppt_73/` | 05 包 V1/V2 共 48 册**注入前**原件 | 73号轮备份 |
| `_artifacts_quarantine/` | 根目录 10 个运行产物 + 2 个冗余工程副本 | **非删除**，附还原说明（见其 README.md） |

---

## 三、灾备重建流程（若本目录被删）

```bash
# 1) 重建目录
mkdir -p _docx_work/slim

# 2) 重建精简工具（逻辑见 72号报告 第五节"可重放清单"，约 200 行）
#    slim_ppt.py 三要素：FILLER 规则表 + KEEP 保护表 + 并查集聚类去重
# 3) 重建效果图工具（逻辑见 73号报告 第四节）
#    inject_shots.py：run_solutions → clean_lines → set_frame
#    inject_shots_ai48.py：clone_slide → build_page → move_slide

# 4) 重跑
python _docx_work/slim/slim_ppt.py --apply --target 80 --profile deep <pptx...>
python _docx_work/slim/inject_shots.py --run && python _docx_work/slim/inject_shots.py --inject
python _docx_work/slim/inject_shots_ai48.py --run && python _docx_work/slim/inject_shots_ai48.py --inject
```

> **原件不丢**：`_backup_ppt_72/` 与 `_backup_ppt_73/` 是最终防线；即使工具与产物全丢，
> 用备份 + 各包 `教师参考/solutions*.py` 即可完全重建。

---

## 四、踩坑记录（务必避免）

1. **PPT 去重禁用两两比较** —— 会链式误删（ABCD 四层任务卡互相误删、删除者自身也被删）。**必须用并查集聚类**。
2. **保护规则必须兼容前导页码** —— `"21知识口袋书"` 用 `startswith("知识口袋书")` 匹配不到，须 `re.match(r"^\d*\s*知识口袋书")`。
3. **卡片识别要排除页脚横线** —— 页脚线宽 12.14in、高 0.02in，会被 `width>=4.5` 误判为卡片；须加 `height>=0.5`。
4. **后台服务随 shell 退出被回收** —— mock LLM 服务改为**同进程线程启动**。
5. **granian 在 Windows 多 worker 报 `upstream connect failed`** —— 用 `--workers 1` 或改 uvicorn。
6. **numpy 固定宽度字符串静默截断** —— `np.array(["正常"]*n)` dtype=`<U2`，赋 `"轴承磨损"` 会变成 `"轴承"`；须一次性构造标签列表。
7. **requests 走代理导致本地服务连不上** —— 设 `NO_PROXY=127.0.0.1,localhost`。

## 七、版本控制（74号轮新增）

- **仓库位置**：`_docx_work/` 自身为 git 仓库（`.git/`），与上级 `D:/Python编程实战/` 仓库独立，避免污染。
- **已入库（18 个文件）**：
  - `slim/` 4 个脚本 + 2 个缓存（`slim_ppt.py` / `inject_shots.py` / `inject_shots_ai48.py` / `ppt_eng_pages.py` + 缓存）
  - `eng/` 7 个脚本（`eng_gen.py` / `eng_helpers.py` / `eng_specs.py` / `specs_01/02/03/05.py` / `make_index.py` / `verify_projects.py` / `check_parity.py`）
  - `README.md`（本文）
  - `.gitignore`（排除 `_backup_ppt_*/`、`__pycache__/`、`.pytest_cache/` 等大体积产物）
- **自动提交**：`autocommit.bat`（双击或加入 Windows 任务计划每日定时）；手动：
  ```bash
  cd _docx_work
  git add -A
  git commit -m "描述本次变更"
  ```
- **首次重建**：克隆/重装环境后，从本目录 + 上层 `教学实施资料/` 即可按 README 重建全部生成器与产物。
