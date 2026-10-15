#!/bin/sh
# ============================================================
# 两库自动同步脚本（81轮 · gitee 仓库改名英文后）
# 主库:  D:/Python编程实战/教学实施资料
#         → gitee.com/enze_tian_qiong/ai-course-teaching-resources
# 05库:  D:/Python编程实战/教学实施资料/05-AI应用基础48课时版
#         → gitee.com/enze_tian_qiong/ai-foundations-48h
#
# 作用：探测可用 proxy → 对两个仓库执行 add-commit-push
# 用法：sh auto_sync_gitee.sh
# ============================================================

# 1) 探测可用代理端口（WorkBuddy 动态代理通常 60785，但会变）
PROXY=""
for port in 60785 52404 62850; do
    if (echo > /dev/tcp/127.0.0.1/$port) 2>/dev/null; then
        PROXY="http://127.0.0.1:$port"
        break
    fi
done
if [ -z "$PROXY" ]; then
    echo "[WARN] 未探测到代理端口，使用系统默认(可能失败)"
    PROXY="http://127.0.0.1:60785"
fi
export HTTP_PROXY="$PROXY"
export HTTPS_PROXY="$PROXY"

# 2) 推送函数：先确保有远端，再 add-commit-push
sync_repo() {
    local dir="$1"
    local msg="$2"
    cd "$dir" || { echo "[SKIP] $dir 不存在"; return; }
    # 有变更？
    local n=$(git status --porcelain 2>/dev/null | wc -l)
    if [ -z "$n" ] || [ "$n" = "0" ]; then
        echo "[OK] $dir: 无变更，已是最新（up-to-date）"
        return
    fi
    git add -A 2>/dev/null
    # 若未配置user则用默认
    git -c user.name="mwenying" -c user.email="myuwei@126.com" \
        commit -m "$msg" 2>&1 | head -1
    echo "[PUSH] $dir ..."
    timeout 120 git push origin main 2>&1 | tail -1
}

sync_repo "D:/Python编程实战/教学实施资料" "auto-sync: 教学资源库变更"
sync_repo "D:/Python编程实战/教学实施资料/05-AI应用基础48课时版" "auto-sync: 05课程变更"

echo "[DONE] $(date '+%F %T') 同步完成"