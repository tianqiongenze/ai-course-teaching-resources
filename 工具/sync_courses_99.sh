#!/bin/bash
# ============================================================
# 99号轮课程仓镜像同步（沿用98号报告口径）
#   clone --depth 1 → 清空工作区(保 .git/LICENSE) → rsync 课程目录
#   → commit → push → ls-remote 复核
# 03 课程按 工具/03同步排除清单.txt 排除试卷/期末类（含期末项目册三格式）
# ============================================================
set -u
ROOT="/Users/joelgong/PycharmProjects/ai-course-teaching-resources"
WORK="/tmp/sync_courses_99"
EXCL="$ROOT/工具/03同步排除清单.txt"
MSG="sync(99): V2授课PPT注入重难点细化包（重难点地图/难点击破/避坑清单，99号轮）"

# 仓地址 → 课程目录
TASKS=(
  "https://github.com/tianqiongenze/ai-application-foundations.git|01-AI应用基础"
  "https://github.com/tianqiongenze/programming-fundamentals.git|02-程序设计基础"
  "https://github.com/tianqiongenze/industrial-IoT-python-programming.git|03-Python程序设计-项目实战"
  "https://gitee.com/enze_tian_qiong/03-python-practice.git|03-Python程序设计-项目实战"
  "https://github.com/tianqiongenze/ai-foundations-48h.git|05-AI应用基础48课时版"
  "https://gitee.com/enze_tian_qiong/ai-foundations-48h.git|05-AI应用基础48课时版"
)

rm -rf "$WORK"; mkdir -p "$WORK"
RESULT_LOG="$WORK/result.txt"; : > "$RESULT_LOG"
HOST_FILTER="${1:-}"   # 可选：只同步包含该关键字的仓（如 github.com / gitee.com）

git_clone() {  # $1=url $2=dir → 0 ok
  for i in 1 2 3 4 5; do
    if git clone --depth 1 --quiet "$1" "$2" 2>/dev/null; then return 0; fi
    rm -rf "$2"; sleep $((i * 2))
  done
  return 1
}

git_push() {  # $1=dir → 0 ok
  for i in 1 2 3 4 5; do
    if git -C "$1" push --quiet 2>/dev/null; then return 0; fi
    sleep $((i * 2))
  done
  git -C "$1" push 2>&1 | tail -2
  return 1
}

for task in "${TASKS[@]}"; do
  url="${task%%|*}"; course="${task#*|}"
  if [ -n "$HOST_FILTER" ] && [[ "$url" != *"$HOST_FILTER"* ]]; then continue; fi
  name=$(basename "$url" .git)
  host=$(echo "$url" | cut -d/ -f3)
  dir="$WORK/${host}__${name}"
  echo "====[$course → $host/$name]"
  if ! git_clone "$url" "$dir"; then
    echo "FAIL clone $url" | tee -a "$RESULT_LOG"; continue
  fi
  branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD)
  # 清空工作区，保留 .git 与仓根 LICENSE
  find "$dir" -maxdepth 1 -mindepth 1 ! -name '.git' ! -name 'LICENSE' -exec rm -rf {} +
  # 镜像课程目录（03 用排除清单）
  if [ "$course" = "03-Python程序设计-项目实战" ]; then
    rsync -a --exclude-from="$EXCL" "$ROOT/$course/" "$dir/"
  else
    rsync -a "$ROOT/$course/" "$dir/"
  fi
  git -C "$dir" add -A
  n=$(git -C "$dir" status --porcelain | wc -l | tr -d ' ')
  if [ "$n" = "0" ]; then
    echo "OK(无变更) $host/$name [$branch] $(git -C "$dir" rev-parse --short HEAD)" | tee -a "$RESULT_LOG"
    continue
  fi
  if git -C "$dir" commit --quiet -m "$MSG"; then
    old=$(git ls-remote "$url" "$branch" | cut -f1 | cut -c1-7)
    if git_push "$dir"; then
      new=$(git ls-remote "$url" "$branch" | cut -f1 | cut -c1-7)
      echo "OK $host/$name [$branch] 变更${n}文件 ${old}..${new}" | tee -a "$RESULT_LOG"
    else
      echo "FAIL push $host/$name" | tee -a "$RESULT_LOG"
    fi
  else
    echo "FAIL commit $host/$name" | tee -a "$RESULT_LOG"
  fi
done

echo "======== 汇总 ========"
cat "$RESULT_LOG"
