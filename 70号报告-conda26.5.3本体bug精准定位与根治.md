# 70号报告 —— conda 26.5.3 "本体bug"精准定位与根治（含官方issue回报文本）

> 日期：2026-09-29 ｜ 任务：用户指令"conda本体有bug是什么意思？精准定位问题，联网搜索最佳方案并彻底解决问题"
> 前情：69号轮曾以"conda本体bug"一笔带过并用venv绕过——本轮按要求彻底交代与根治。

---

## 一、"conda本体有bug"的准确含义（一句话）

**conda 26.5.3 自身代码缺陷**：`conda/cli/common.py` 的 `validate_subdir_config()` 在
"**未激活任何conda环境、直接用绝对路径调用conda**"时，把 `context.active_prefix`（此时为 `None`）
直接传入 `os.path.abspath(None)` → `TypeError: expected str, bytes or os.PathLike object, not NoneType`，
任何 `conda create/install` 全部崩——不是我们环境配置坏，是这一版conda的代码漏了判空。

## 二、精准定位过程

### 2.1 完整traceback（复现条件：无CONDA_PREFIX环境变量 + 绝对路径调用）

```
conda/cli/main_create.py  line 209  execute → validate_subdir_config()
conda/cli/common.py       line 225  elif not paths_equal(context.active_prefix, context.root_prefix):
conda/common/path/__init__.py:119   return abspath(path1) == abspath(path2)
TypeError: expected str, bytes or os.PathLike object, not NoneType
```

### 2.2 铁证（同文件双重标准）

`conda/cli/common.py` 第48行的 `is_active_prefix()` 明确写了
`if context.active_prefix is None:` 的判空分支——**同一个文件里一处判了None、一处没判**，
即回归性漏判，而非设计如此。

### 2.3 两个干扰因素（此前掩盖真相）

| 干扰 | 真相 |
|---|---|
| `CONDA_NO_PLUGINS=true`（排障时加的） | 它会**禁用libmamba求解器插件**→报"non-default solver not recognized"，制造了第二个假错误 |
| repo.anaconda.com 超时 | 网络层真实存在（notices拉取失败），但重试后能过，非崩溃根因 |

## 三、联网检索结论

| 来源 | 发现 |
|---|---|
| [conda/conda #15020](https://github.com/conda/conda/issues/15020) | 同函数同类崩溃：`active_prefix` 为 **str**（非Path）时 `.parent` 崩 |
| [conda release notes](https://docs.conda.io/projects/conda/en/latest/release-notes.html) | 该str形态经 **#15038 修复于 conda 25.9.0**："Fix validate_subdir_config cli validation" |
| 全网检索 | **None形态（未激活态）无已报告issue、无修复记录** → 本机遇到的是25.9.0修复时遗漏的第三种形态（None），疑似未公开回归 |

## 四、根治方案（三层）

1. **立即可用的workaround（验证有效）**：调用前 `export CONDA_PREFIX=/opt/anaconda3`
   （active_prefix 变非None，绕过崩点；实测 conda create 成功）。
2. **根治补丁（已实施）**：直改 `/opt/anaconda3/lib/python3.14/site-packages/conda/cli/common.py`
   （conda纯Python包，改动一行，升级conda时自然被新版覆盖）：
   ```diff
   -        elif not paths_equal(context.active_prefix, context.root_prefix):
   +        elif context.active_prefix is not None \
   +                and not paths_equal(context.active_prefix, context.root_prefix):
   ```
   语义与同文件 `is_active_prefix` 的None处理一致（无活动环境→按base/全局配置处理）。
3. **回报上游（彻底）**：issue文本已备好 → [conda-issue回报文本-26.5.3-active_prefix-None.md](conda-issue回报文本-26.5.3-active_prefix-None.md)
   （含复现条件/traceback/根因/补丁diff，可直接提交 github.com/conda/conda）。

## 五、修复验证（全绿）

| 验证 | 结果 |
|---|---|
| **裸调**（无任何conda环境变量）`conda create -n _condatest2 python=3.12 -y` | ✅ 成功（补丁前必崩） |
| `conda install -n pp03/ai48 jupyter nbconvert ipykernel` | ✅ 成功（install路径同崩点，双重验证） |
| pp03/ai48 **重建为真conda环境**（替换69轮venv版，Python 3.12.11+全套依赖+jupyter栈） | ✅ 与指南"conda create"口径100%一致 |
| 三包 `check_env.py`（各自专属环境） | ✅ `[解释器] py02/pp03/ai48` + `[numpy] 2.5.3 OK` |
| 回归：starter 32 + 教师notebook抽验3（真conda环境） | ✅ 35/35 PASS |
| 旧venv备份清理 | ✅ 已删除；`conda env list` 干净 |

## 六、可重放清单

| # | 动作 | 命令/路径 |
|---|---|---|
| 1 | conda补丁 | `/opt/anaconda3/lib/python3.14/site-packages/conda/cli/common.py` L225 None-guard（升级conda即被覆盖） |
| 2 | 重建pp03/ai48 | `conda create -n pp03 python=3.12 -y` + `pip install pandas numpy …`（核心批） + `conda install -n pp03 jupyter nbconvert ipykernel -y` |
| 3 | issue回报 | `教学实施资料/conda-issue回报文本-26.5.3-active_prefix-None.md` |

## 七、遗留与建议

1. **conda升级窗口**：`conda update -n base conda` 到最新版后请复跑
   `conda create -n _t python=3.12 -y`（不带CONDA_PREFIX）——若上游已修，本地补丁被覆盖也无妨；若仍崩，补丁需重打（重放清单#1）。
2. argon2-cffi-bindings 在 pip 整组安装时偶发构建失败回滚——**分批装核心依赖 + jupyter栈走conda install** 是稳妥路径（本轮实证）。
3. 联网来源：[#15020](https://github.com/conda/conda/issues/15020) · [conda release notes](https://docs.conda.io/projects/conda/en/latest/release-notes.html) · [#13472](https://github.com/conda/conda/issues/13472)（另类init崩溃，对照参考）
