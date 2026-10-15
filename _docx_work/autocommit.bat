@echo off
REM 74号轮·_docx_work/ 生成器自动提交脚本
REM 用法：双击执行（或加到 Windows 任务计划程序，每日定时）
REM 行为：add -A → 若有变更则 commit + 打印提交摘要

cd /d "%~dp0"
git add -A
git diff --cached --quiet
if %errorlevel%==0 (
    echo [%date% %time%] 无变更，跳过
    exit /b 0
)
git -c user.email=workbuddy@local -c user.name=workbuddy commit -m "auto: %date:~0,10% %time:~0,8% 生成器变更"
echo [%date% %time%] 已提交：%errorlevel%
git log --oneline -1
