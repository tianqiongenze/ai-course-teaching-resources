# 60号报告：PyCharm指南GitHub/Gitee双仓操作重构

**日期**：2026-09-25
**触发**：用户要求"PyCharm软件操作指南中的有没有gitee的使用的详细操作的，需要支持github和gitee两种类型仓库的操作。请进行审查和重构"

---

## 一、审查结论（改造前）

| 文件 | 现状 | 缺口 |
|---|---|---|
| `05-PyCharm使用指南.md` 第七章 | 7.1克隆**只写GitHub地址**；7.3推送令牌"GitHub/Gitee"各一句带过；无PyCharm账号登录配置；无平台切换/双仓并推 | Gitee无详细操作 |
| `03-Git指南` 第六章（PyCharm中用Git） | 同样只写GitHub克隆地址；Gitee全章仅1处提及 | 双仓不平行 |
| `图/git.png` | 只标注gitee.com一处地址 | 无双仓对照 |

## 二、重构（三处）

### 1. 05-PyCharm指南第七章重写（7.1→7.10）
- **章首双仓对照表**：网址/仓库地址形如/推送密码/何时用四行——声明"操作完全平行，只是账号、仓库地址、令牌三处不同"
- **7.1克隆**：双地址并列（GitHub `github.com/用户名/仓库.git` / Gitee `gitee.com/用户名/仓库.git`），注明两平台都在网页"Code/克隆"按钮复制
- **7.2 PyCharm里登录GitHub账号**（新增）：Settings→Version Control→GitHub→+→Log In via GitHub / Use Token + 浏览器生成Token完整路径（头像→Settings→Developer settings→Personal access tokens→勾repo）
- **7.3 PyCharm里登录Gitee账号**（新增）：Settings→Version Control→Gitee→+→Use Token + 浏览器生成私人令牌完整路径（设置→私人令牌→勾projects）+ 提示"两账号可同时登录——推哪个平台取决于仓库远程地址"
- **7.5推送**：加"推错了平台/想换平台"——Git→Manage Remotes编辑origin URL（双地址对照+等价命令行）
- **7.9 双仓并推（进阶·A层选读）**（新增）：Manage Remotes加第二远程（gitee/github）→ `git push origin dev` + `git push gitee dev` 分别推——代码同时备份两平台
- **FAQ补双仓条目**：push 401双令牌口径 + GitHub连不上切Gitee三步

### 2. 03-Git指南第六章双仓化
- 6.1克隆双地址并列 + 超时两办法（终端clone / 第十节切Gitee）
- 6.6推送登录框双仓细化 + **"PyCharm账号登录双仓对照表"**（设置路径/获取令牌浏览器步骤/登录方式三行×两平台）
- **6.12 双仓并推与平台切换**（新增，速查表后）：Manage Remotes加第二远程 + origin URL编辑切换

### 3. 配图git.png升级双仓标注版（2032×1134，旧版单地址）
三区布局：
- **左上**仓库页线框（注明"GitHub与Gitee界面一致"）+ "点Code/克隆复制地址（两平台同一位置）"
- **右上**五步工作流（注明"两平台命令相同"）+ PyCharm等价快捷键条
- **下方双仓对照横条**：GitHub蓝卡（首选/Token）/ Gitee橙卡（不畅时用/私人令牌/国内快）/ 切换黑卡（`git remote set-url` + PyCharm Manage Remotes）+ 底部地址形如对照

## 三、验证

| 检查项 | 结果 |
|---|---|
| 05指南 GitHub/Gitee 均衡度 | 22处 / 24处 |
| 03指南 GitHub/Gitee 均衡度 | 33处 / 32处 |
| Manage Remotes（平台切换入口） | 05指南4处、03指南2处 |
| 双仓并推（7.9/6.12） | 两指南各1节 |
| git.png | 双仓对照版重新生成（2032×1134） |
| 登录配置（7.2/7.3） | PyCharm内GitHub+Gitee账号配置各1节含令牌浏览器获取全路径 |

## 四、设计口径
双仓不是"GitHub主教程+Gitee附录"，而是**平行写法**：每个操作步骤并列给两平台参数（地址/令牌/入口），共同操作（commit/branch/冲突）只写一次并标注"两平台相同"——学生用哪个平台都照着能走完全程。
