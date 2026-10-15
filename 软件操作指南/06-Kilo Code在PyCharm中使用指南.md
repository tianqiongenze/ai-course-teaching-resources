# Kilo Code 在 PyCharm 中使用指南（课程版·详细）

> **适用课程**：02-Python编程基础 / 03-Python程序设计（项目实战）/ 05-AI应用基础（48课时版）
> **版本**：PyCharm Community Edition 2025.x + Kilo Code 插件最新版
> **前置条件**：已完成 PyCharm 安装配置（见 `05-PyCharm使用指南.md`）、已安装 Git（见 `03-Git与GitHub-Gitee使用指南.md`）

---

## 一、它是什么

**Kilo Code** 是一款**AI 编程助手插件**，集成在 PyCharm（及其他 JetBrains IDE）中，提供：
- **智能代码补全**：按 `Tab` 接受 AI 生成的整行/整块代码
- **内置聊天助手**：`Alt+L` / `⌘L` 唤起侧边栏，可问代码、改 Bug、写文档、生成测试
- **代码生成/重构**：选中代码 → 右键 Kilo Code → 解释/重构/补全/生成测试/添加类型注解
- **上下文感知**：自动读取项目结构、当前文件、Git 历史、依赖库，给出更贴合工程的建议
- **多模型支持**：可切换不同大模型（Kilo 自家模型 / DeepSeek / GPT-4o / Claude 等）

> **为什么要用**：比手写快 3-5 倍；生成的代码符合 PEP8、带类型注解、含 docstring；配合 PyCharm 静态分析，边写边查错；课程工单/项目实战/AI 实训全程可用。

---

## 二、安装插件

### 第1步：打开插件市场

1. 打开 PyCharm → 菜单 **File → Settings**（macOS：**PyCharm → Settings**）
2. 左侧点击 **Plugins** → 顶部选 **Marketplace** 标签

### 第2步：搜索并安装

1. 搜索框输入：**Kilo Code**
2. 找到 **Kilo Code**（发布者：Kilo Code，图标通常为紫色 K 字母）
3. 点击 **Install** → 等待下载安装完成
4. 点击 **Restart IDE** 重启 PyCharm

> ⚠️ **注意**：插件名必须是 **Kilo Code**，不要装同名山寨插件。官方插件 ID 通常为 `com.kilocode.kilocode`。

### 第3步：验证安装

重启后：
- 右侧工具栏出现 **Kilo Code** 图标（紫色 K / 机器人头像）
- 底部状态栏右侧显示 **Kilo Code: Ready**
- 菜单 **Tools → Kilo Code** 出现相关条目

---

## 三、配置 API Key（必做）

Kilo Code 需要 API Key 才能调用大模型。课程统一使用**课程专属 Key**（由教师分发），也可自备。

### 方式 A：使用课程统一 Key（推荐，零配置）

1. 教师会在群文件/课程网盘发放 `kilocode_apikey.txt`（或通过课程环境变量自动注入）
2. 打开终端，进入项目根目录：
   ```bash
   # Windows PowerShell
   $env:KILO_API_KEY = "sk-xxxxxxxxxxxxxxxx"
   
   # macOS / Linux / Git Bash
   export KILO_API_KEY="sk-xxxxxxxxxxxxxxxx"
   ```
3. 重启 PyCharm，Kilo Code 自动读取环境变量 → 状态栏显示 **Connected**

> 💡 **永久生效**：把上述命令加入 Shell 配置文件（`~/.bashrc` / `~/.zshrc` / PowerShell `$PROFILE`），以后开机即用。

### 方式 B：在插件设置中手动填入

1. **File → Settings → Tools → Kilo Code**
2. **API Key** 栏粘贴你的 Key（格式 `sk-...`）
3. **Model** 下拉选择推荐模型：
   - `kilo-code-latest`（默认，速度快、上下文长）
   - `deepseek-coder`（代码能力强、中文友好）
   - `gpt-4o` / `claude-3.5-sonnet`（需自备 Key，上限高）
4. 点击 **Test Connection** → 显示 ✅ Connected
5. **Apply → OK**

> ⚠️ **不要把 Key 提交到 GitHub！** 已在 `.gitignore` 中忽略 `*.env` `.kilorc` 等敏感文件。

### 方式 C：使用 `.env` 文件（项目级配置，推荐团队协作）

1. 在项目根目录新建 `.env` 文件：
   ```env
   KILO_API_KEY=sk-xxxxxxxxxxxxxxxx
   KILO_MODEL=kilo-code-latest
   ```
2. PyCharm 会自动读取 `.env`（需安装 **EnvFile** 插件：Settings → Plugins → 搜索 EnvFile → Install）
3. `.env` 已在课程 `.gitignore` 中，不会泄露

---

## 四、核心功能详解

### 4.1 智能代码补全（Inline Completion）

**触发方式**：写代码时自动出现灰色虚影建议 → 按 `Tab` 接受，`Esc` 取消

**适用场景**：
- 写函数签名 → 自动补全函数体
- 写 `for` 循环 → 自动补全循环体
- 写 SQL/正则/配置 → 自动生成正确语法
- 导入库后 → 自动补全常用调用链

**示例**：
```python
# 输入：
def calculate_bmi(weight: float, height: float) -> float:
    \"\"\"计算 BMI 指数\"\"\"
    
# 光标停在冒号后，等 0.5 秒 → 出现灰色建议：
#     bmi = weight / (height ** 2)
#     return round(bmi, 2)
# 按 Tab → 直接补全 ✅
```

**调整触发延迟**：Settings → Tools → Kilo Code → **Completion Delay (ms)**，默认 300ms，可改 150ms 更激进。

---

### 4.2 聊天助手（Chat Panel）

**打开方式**：
- 快捷键：`Alt+L`（Windows/Linux） / `⌘L`（macOS）
- 右侧工具栏点击 **Kilo Code** 图标
- 菜单 **Tools → Kilo Code → Open Chat**

**界面说明**：
```
┌─────────────────────────────────────┐
│  💬 Kilo Code Chat        [模型切换] │
├─────────────────────────────────────┤
│  用户：帮我写个冒泡排序             │
│  ┌───────────────────────────────┐  │
│  │ AI：def bubble_sort(arr):     │  │
│  │     n = len(arr)              │  │
│  │     for i in range(n):        │  │
│  │         for j in range(0,n-i-1):│ │
│  │             if arr[j]>arr[j+1]:│ │
│  │                 arr[j],arr[j+1]=...││
│  └───────────────────────────────┘  │
├─────────────────────────────────────┤
│  💡 @file 引用当前文件  @project 引用项目 │
│  输入框（Shift+Enter 换行，Enter 发送）  │
└─────────────────────────────────────┘
```

**常用指令前缀**（输入 `@` 触发菜单）：
| 前缀 | 作用 | 示例 |
|------|------|------|
| `@file` | 引用当前打开文件上下文 | `@file 解释这段代码的时间复杂度` |
| `@selection` | 引用选中代码片段 | 选中代码 → `@selection 重构为列表推导式` |
| `@project` | 引用整个项目结构 | `@project 帮我生成 README.md` |
| `@git` | 引用 Git 历史/变更 | `@git 总结最近 5 次提交的改动` |
| `@terminal` | 引用终端输出 | 运行报错后 → `@terminal 解释这个错误并修复` |
| `/explain` | 解释代码 | `/explain 递归函数原理` |
| `/refactor` | 重构代码 | `/refactor 提取公共方法` |
| `/test` | 生成单元测试 | `/test 为这个类生成 pytest 用例` |
| `/doc` | 生成文档字符串 | `/doc 给所有公开方法加 docstring` |
| `/fix` | 修复报错 | 选中报错代码 → `/fix` |

**聊天记录**：自动保存在项目 `.kilocode/chats/`，可随时回溯。

---

### 4.3 代码动作（Code Actions / 右键菜单）

**选中代码 → 右键 → Kilo Code** 出现以下菜单：

| 动作 | 说明 | 适用场景 |
|------|------|----------|
| **Explain** | 逐行解释代码逻辑 | 看不懂别人代码/复习算法 |
| **Refactor** | 重构：提取函数/消除重复/改名/加类型注解 | 代码变臭时 |
| **Generate Tests** | 生成 pytest/unittest 测试用例 | 提交前补测试 |
| **Add Docstrings** | 批量添加 Google/NumPy/Sphinx 风格 docstring | 规范代码 |
| **Fix Issues** | 自动修复静态分析报错（红波浪线） | 解决 PyCharm 报红 |
| **Optimize** | 性能优化建议（算法/数据结构/缓存） | 处理大数据/慢查询 |
| **Convert** | 语言互转/风格转换 | Python ↔ JavaScript，同步/异步转换 |
| **Custom Prompt** | 自定义指令 | 团队统一代码风格 |

**示例——生成测试**：
```python
# 选中这个类：
class Calculator:
    def add(self, a: float, b: float) -> float:
        return a + b
    
    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ValueError("除数不能为 0")
        return a / b

# 右键 → Kilo Code → Generate Tests → 选择 pytest
# 自动在 tests/ 目录生成：
# test_calculator.py
import pytest
from calculator import Calculator

class TestCalculator:
    def test_add(self):
        calc = Calculator()
        assert calc.add(1, 2) == 3
        assert calc.add(-1, 1) == 0
    
    def test_divide(self):
        calc = Calculator()
        assert calc.divide(6, 2) == 3
        with pytest.raises(ValueError):
            calc.divide(1, 0)
```

---

### 4.4 终端集成（Terminal Assistant）

PyCharm 底部 **Terminal** 标签页中：
- 运行命令报错后，终端上方出现 **💡 Kilo Code: Explain & Fix** 按钮
- 点击 → 自动分析错误、给出修复命令/代码
- 也可在终端直接输入 `kilo "你的问题"`（需配置别名）

**配置终端别名**（一次性）：
```bash
# ~/.bashrc / ~/.zshrc
alias kilo='python -m kilocode.cli'
```
然后终端直接用：
```bash
kilo "帮我写个爬虫抓取豆瓣Top250"
```

---

### 4.5 Git Commit Message 生成

1. 按 `Ctrl+K` / `⌘K` 打开 Commit 对话框
2. 暂存文件后，点击 Commit Message 输入框右侧 **🤖 Kilo Code** 图标
3. 自动根据 diff 生成规范提交信息（`feat:`/`fix:`/`refactor:`/`docs:`...）
4. 微调后直接 Commit

> 配合 `03-Git与GitHub-Gitee使用指南.md` 第七节“提交规范”使用，commit 质量秒过教师审查。

---

## 五、课程实战场景速查

| 场景 | 操作步骤 | 预期产出 |
|------|----------|----------|
| **W2 基础语法：写函数** | 输入函数签名+docstring → `Tab` 补全函数体 | 规范函数、含类型注解、边界处理 |
| **W5 面向对象：设计类** | Chat: `@project 根据需求文档生成类图代码` | 完整类定义、继承关系、魔术方法 |
| **W7 文件操作：批量处理** | 选中目录结构 → Chat: `@project 写脚本遍历所有 CSV 合并` | 可跑通的脚本、异常处理、进度条 |
| **W9 数据分析：Pandas 操作** | Chat: `@file 这段代码用 vectorized 写法优化` | 无循环、高性能 Pandas 代码 |
| **W11 网络编程：Socket/HTTP** | Chat: `@selection 封装成可复用的 Client 类` | 带重试/超时/上下文管理器的客户端 |
| **03 课项目：数据库建模** | Chat: `@project 生成 SQLAlchemy ORM 模型 + Alembic 迁移` | models.py + migrations/versions/ |
| **03 课项目：API 开发** | 右键 → Generate Tests → 选 FastAPI TestClient | 覆盖率 >80% 的测试套件 |
| **05 课 AI：数据预处理** | Terminal 报错 → 点 💡 Explain & Fix | 修复版预处理管道 |
| **05 课 AI：模型训练** | Chat: `@file 加上 TensorBoard 回调 + 早停 + 模型保存` | 生产级训练脚本 |
| **期末大作业：全栈** | `@project 生成 Dockerfile + docker-compose + GitHub Actions CI` | 一键部署、自动测试流水线 |

---

## 六、进阶配置与技巧

### 6.1 自定义提示词模板（Prompt Templates）

Settings → Tools → Kilo Code → **Prompt Templates** → **Add**：

| 名称 | 模板内容 | 触发方式 |
|------|----------|----------|
| `course_style` | `请按课程规范生成代码：PEP8、类型注解、Google docstring、日志用 loguru、配置用 pydantic-settings、错误用自定义异常类` | Chat 输入 `/course_style` |
| `test_pytest` | `生成 pytest 测试：覆盖正常/边界/异常三类用例、用 fixture 复用 setup、mock 外部依赖、assert 写清晰 message` | 右键 Generate Tests 前选中 |
| `refactor_clean` | `重构目标：降低圈复杂度<10、消除重复代码、单一职责、变量名语义化、加类型注解、不改变对外接口` | 右键 Refactor 前选中 |

---

### 6.2 模型切换策略

| 任务类型 | 推荐模型 | 原因 |
|----------|----------|------|
| 日常补全/简单重构 | `kilo-code-latest` | 极快、免费、上下文 128k |
| 算法/数据结构/LeetCode | `deepseek-coder` | 代码推理强、中文解释清晰 |
| 架构设计/复杂重构/文档 | `gpt-4o` / `claude-3.5-sonnet` | 推理深、长上下文、工程感强 |
| 离线/隐私敏感 | 本地模型（Ollama + CodeLlama） | 数据不出本机、无网也能用 |

**快速切换**：Chat 顶部下拉菜单，或 `Ctrl+Shift+P` → `Kilo Code: Switch Model`。

---

### 6.3 上下文控制（Context Control）

聊天面板右上角 **齿轮图标** → **Context Settings**：

- **Max Context Tokens**：默认 8000，大项目可改 16000/32000
- **Include**：
  - ✅ Current File（当前文件）
  - ✅ Open Tabs（打开的标签页）
  - ✅ Project Structure（项目目录树）
  - ☐ Git History（Git 历史，费 token，按需开）
  - ☐ Terminal Output（终端输出，按需开）
- **Exclude Patterns**：排除大文件/二进制/生成文件：
  ```
  **/__pycache__/**, **/*.pyc, **/venv/**, **/.venv/**, **/env/**, **/.env, **/node_modules/**, **/dist/**, **/build/**, **/*.log, **/*.db, **/*.sqlite, **/data/**, **/*.csv, **/*.parquet, **/*.pkl, **/*.model
  ```

---

### 6.4 快捷键自定义（Keymap）

Settings → Keymap → 搜索 "Kilo Code"，推荐绑定：

| 动作 | 建议快捷键 (Win) | 建议快捷键 (Mac) | 说明 |
|------|------------------|------------------|------|
| Open Chat | `Alt+L` | `⌘L` | 默认 |
| Accept Completion | `Tab` | `Tab` | 默认 |
| Next Completion | `Alt+]` | `⌘]` | 循环备选 |
| Prev Completion | `Alt+[` | `⌘[` | 循环备选 |
| Explain Selection | `Alt+E` | `⌘E` | 选中代码解释 |
| Refactor Selection | `Alt+R` | `⌘R` | 选中代码重构 |
| Generate Tests | `Alt+T` | `⌘T` | 选中代码生成测试 |
| Fix Issues | `Alt+F` | `⌘F` | 修复当前文件报错 |

> ⚠️ 避免与 PyCharm 默认快捷键冲突（如 `Ctrl+Shift+T` 是打开测试文件）。

---

## 七、常见问题（FAQ）

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| **状态栏显示 "No API Key"** | 未配置 Key | 见第三章配置 API Key |
| **补全不出现 / 很慢** | 网络/模型负载/上下文过长 | 1) 检查网络 2) 切换 `kilo-code-latest` 3) 清理上下文（聊天面板右上角🗑️） |
| **生成代码有语法错误** | 模型幻觉 / 上下文不全 | 1) 选中报错代码 → `/fix` 2) 补充 `@file` 或 `@project` 上下文 3) 手动微调后再让 AI 继续 |
| **Chat 说"超出上下文窗口"** | 对话太长/项目太大 | 1) 点🗑️清空历史 2) 调小 Context Settings 的 Max Tokens 3) 用 `@file` 代替 `@project` |
| **插件报错 "Connection refused"** | 代理/防火墙/公司网络拦截 | 1) Settings → Appearance → System Settings → HTTP Proxy 配置代理 2) 或用本地模型（Ollama） |
| **生成的测试跑不通** | 依赖未装 / 路径不对 | 1) 终端 `pip install pytest pytest-mock` 2) 确认 `tests/` 在 `PYTHONPATH`（PyCharm 自动标记） |
| **中文注释乱码** | 编码问题 | Settings → Editor → File Encodings → Global/ Project 都选 UTF-8 |
| **想用本地模型（离线/隐私）** | 无外网/数据敏感 | 1) 装 Ollama：`curl -fsSL https://ollama.com/install.sh \| sh` 2) `ollama pull codellama:13b` 3) Settings → Kilo Code → Model → `ollama/codellama:13b` → Base URL `http://localhost:11434/v1` |

---

## 八、最佳实践清单（每次编码前核对）

- [ ] **环境就绪**：conda 环境激活、解释器选对、Kilo Code 状态栏显示 Connected
- [ ] **上下文干净**：聊天记录过长时清空（🗑️），避免污染新任务
- [ ] **任务拆解**：大需求拆成小步骤，逐步让 AI 完成（单次对话 < 10 轮）
- [ ] **人工审核**：AI 代码**必须**人工阅读、跑测试、过静态分析（PyCharm 绿色再提交）
- [ ] **版本控制**：AI 生成代码先 `git add -p` 分块暂存，写清晰 commit message
- [ ] **敏感数据**：绝不把密码/Key/真实数据发给 AI（用 `@file` 引用占位符文件）
- [ ] **学习为主**：**先自己想、再让 AI 辅助、最后自己能讲清原理**——考试/面试靠自己

---

## 九、快捷键总览表（打印贴显示器边）

| 功能 | Windows / Linux | macOS | 备注 |
|------|-----------------|-------|------|
| 打开/关闭 Chat | `Alt+L` | `⌘L` | 核心入口 |
| 接受补全 | `Tab` | `Tab` | 灰色虚影时 |
| 拒绝补全 | `Esc` | `Esc` | |
| 下一个补全建议 | `Alt+]` | `⌘]` | |
| 上一个补全建议 | `Alt+[` | `⌘[` | |
| 解释选中代码 | `Alt+E` | `⌘E` | 需自定义 Keymap |
| 重构选中代码 | `Alt+R` | `⌘R` | 需自定义 Keymap |
| 生成测试 | `Alt+T` | `⌘T` | 需自定义 Keymap |
| 修复报错 | `Alt+F` | `⌘F` | 需自定义 Keymap |
| 切换模型 | `Ctrl+Shift+P` → Kilo:Switch | `⇧⌘P` → Kilo:Switch | |
| 清空聊天历史 | Chat 面板右上角 🗑️ | Chat 面板右上角 🗑️ | |
| 终端 Explain & Fix | 鼠标点 💡 按钮 | 鼠标点 💡 按钮 | 报错后自动出现 |

---

## 十、参考资料与扩展阅读

- **Kilo Code 官方文档**：https://docs.kilocode.ai（最新功能、API 参考、故障排查）
- **PyCharm 官方帮助 - AI Assistant**：https://www.jetbrains.com/help/pycharm/ai-assistant.html（原生 AI 对比）
- **提示词工程指南**：https://promptingguide.ai/zh（写好 Prompt 的通用技巧）
- **课程配套仓库**：`git@github.com:课程组/kilocode-course-examples.git`（含各周实战 Prompt 模板）
- **隐私合规**：课程代码含学生信息/业务数据时，**禁止**发送给云端模型 → 用本地模型（Ollama）或脱敏后再问

---

> **版本记录**：
> - v1.0 (2025-09) 初版：安装、配置、核心功能、课程场景、FAQ
> - 维护者：教学组 | 反馈群：课程 QQ 群/钉钉群 | 更新频率：每学期迭代

> **下一步**：完成配置后，打开任意 `.py` 文件，输入 `def quick_sort(arr):` 体验补全 → 再按 `Alt+L` 问“我要对 100 万整数排序，用什么算法最快？” → 开启 AI 编程之旅 🚀