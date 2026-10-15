# 69号报告 —— 全量代码实跑诊断与 PyCharm numpy 版本异常根治

> 日期：2026-09-29 ｜ 任务：用户指令"再次运行所有项目中的所有代码，为什么在PyCharm中执行代码时有点代码报Numpy版本异常导致程序异常呢？"
> 范围：02包+03包+05包（01包持续排除）

---

## 一、PyCharm numpy版本异常·根因实锤

对本机全部 conda 环境扫描 numpy 版本：

| 环境分组 | 环境 | numpy |
|---|---|---|
| ✅ 课程环境 | **py02**（02包）、anaconda-base | **2.5.3 / 2.4.6**（torch 2.14 兼容） |
| ❌ 历史环境 ×9 | py27/py37/py372/py38/py38-2/py38-tensorflow/py383/py383-mps/ds-playground | **1.16~1.26（全部 1.x）** |
| ⚠️ 缺失环境 | **pp03、ai48**（指南与requirements指名要求） | ——不存在，**新建于本轮** |

**根因链**：PyCharm 新建/打开项目时，解释器下拉列出全部 12 个环境；指南要求的 `pp03/ai48` 本机根本不存在 → 用户无从选起，PyCharm 自动关联（或用户误选）任意 numpy 1.x 旧环境 → 新课代码按 numpy 2.x 编写（`np.ptp` 口径、`numpy>=2.0` 依赖）→ 典型报错：

- `A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x...`（旧编译包×新 numpy）
- `AttributeError: module 'numpy' has no attribute 'float_'`（新代码×旧 numpy）

## 二、全量实跑结果（修复前 → 修复后）

| 代码资产 | 数量 | 修复前 | 修复后 |
|---|---|---|---|
| starter（学生代码框架） | 32 | 31 PASS（w09缺jieba） | **32/32 PASS** |
| 教师参考 solutions | 23 | 20 PASS | **23/23 PASS** |
| 教师版 notebook | 32 | 未跑（环境缺失） | **32/32 PASS**（inplace执行落盘） |

### 修 bug 三处（真代码级修复）

| # | 文件 | 症状 | 根因 | 修复 |
|---|---|---|---|---|
| 1 | `03包/教师参考/solutions.py` p41 | `TypeError: ModbusTcpClient.__init__() takes 2 positional arguments but 3 were given` | **pymodbus 3.15 API 变更**：位置参数→必须关键字 | `Client(host=..., port=...)`；并自动拉起 mini_modbus_server（atexit 清理） |
| 2 | `02包/教师参考/solutions.py` w11 | `ConnectionRefusedError [Errno 61]` | 依赖 5020 Modbus/1883 MQTT 服务未起 | 新增 `_ensure_local_sims()` 自动拉双服务，教师参考一键可跑 |
| 3 | py02 环境 | `ModuleNotFoundError: jieba/wordcloud` | requirements 未装 | `pip install jieba wordcloud`（已入环境） |

## 三、根治四件套

1. **补齐缺失环境**：新建 `pp03`、`ai48`（/opt/anaconda3/envs/，Python 3.14.6，numpy 2.5.3 全套依赖：pandas/sklearn/matplotlib/SQLAlchemy/streamlit/plotly/pymodbus/paho/litestar/granian/scipy/joblib/jupyter）。
   - 坑：conda create 本体报 `TypeError ... NoneType`（conda×python3.14 插件 bug）+ 官方源超时 → 绕过：`python -m venv` 建于 envs 目录（conda/PyCharm 均识别）+ 默认 PyPI 装（清华镜像反而 404 none）。
2. **check_env.py 三包统一加"解释器身份 + numpy≥2 门禁"**：
   - 首行打印 `[解释器] py02 (/opt/.../bin/python)` 与 `[numpy] 2.5.3 OK`；
   - 旧环境触发红字排障三步 + `sys.exit(1)`（03/05严格拦截，02包警告不拦截）；
   - 双向验证：py02 放行✓ / py38-2（numpy 1.23.5）拦截✓。
3. **PyCharm 指南新增"八、排障专题：numpy 版本异常"**（`软件操作指南/05-PyCharm使用指南.md`）：
   - 8.1 根因一句话；8.2 三步修复（右下角解释器→Conda→选 py02/pp03/ai48，附路径表）；8.3 两种报错对照表（1.x-compiled / AttributeError / multiarray 混装）；8.4 check_env 防呆 + **升包不降级铁律**。原"常见问题"顺延为第九节。
4. **依赖补装**：py02（jieba/wordcloud）、pp03/ai48（jupyter/nbconvert/ipykernel、litestar/granian）。

## 四、最终矩阵（全绿）

| 验证项 | 结果 |
|---|---|
| starter 32（py02/pp03/ai48 各自环境） | 32 PASS |
| solutions 23（w01-w12 + p11-p66 + multi×3） | 23 PASS |
| 教师版 notebook 32（inplace 执行） | 32 PASS |
| check_env 门禁（正确环境放行 / 旧环境拦截） | 双向通过 |

## 五、可重放清单

| # | 变更 | 路径/命令 |
|---|---|---|
| 1 | p41 修复 | `03包/教师参考/solutions.py`（Client(host=,port=)+auto sim） |
| 2 | w11 修复 | `02包/教师参考/solutions.py`（_ensure_local_sims） |
| 3 | 环境门禁 | 三包 `check_env.py` 头部 `_env_guard()`（strict: 02=False, 03/05=True） |
| 4 | 指南排障节 | `软件操作指南/05-PyCharm使用指南.md` 第八节 |
| 5 | 新环境 | `/opt/anaconda3/envs/pp03、ai48`（venv 方式；重放：`/opt/anaconda3/bin/python -m venv /opt/anaconda3/envs/<名>` + pip 装依赖） |
| 6 | 依赖 | py02: jieba/wordcloud；pp03/ai48: 全套+jupyter（pip 默认源） |

## 六、给用户的直接答复（问题复述）

**"为什么 PyCharm 里报 numpy 版本异常？"** —— 不是代码错，是 **PyCharm 当前解释器指向了 numpy 1.x 的历史环境**（本机 12 个环境里 9 个是旧环境），且指南要求的 pp03/ai48 课程环境此前不存在、无从选择。已四件套根治：**补建两个课程环境 + check_env 启动门禁（选错环境第一行就红字拦下并给三步指引）+ PyCharm 指南排障专节 + 全部 87 项代码/notebook 实跑归零**。今后遇到该报错：右下角换解释器到 py02/pp03/ai48 即愈（详见指南第八节对照表）。
