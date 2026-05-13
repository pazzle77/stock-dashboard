#!/bin/bash
# 自動更新 Dashboard 並 push 到 GitHub
# 由 Mac crontab 呼叫

PYTHON="/Users/jacky/.pyenv/versions/3.11.7/bin/python3"
DIR="/Users/jacky/claude/stock dashboard"
LOG="$DIR/dashboard.log"
GIT="/usr/bin/git"
export PATH="/opt/homebrew/bin:$PATH"  # 讓 crontab 找得到 gh

cd "$DIR" || exit 1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 開始更新..." >> "$LOG"

# 更新 dashboard.html
$PYTHON "$DIR/dashboard.py" >> "$LOG" 2>&1

# push 到 GitHub
$GIT add dashboard.html
if ! $GIT diff --staged --quiet; then
    $GIT commit -m "Auto update $(date '+%Y-%m-%d %H:%M') TW"
    $GIT pull --rebase origin main >> "$LOG" 2>&1
    $GIT push origin main >> "$LOG" 2>&1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Push 完成" >> "$LOG"
    # 通知 Vercel 重新部署
    curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_7c3XpuRMC1YaOY8H4ueoHAW0FH0C/UbLWjeWt4F" >> "$LOG" 2>&1
    echo "" >> "$LOG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Vercel 部署觸發完成" >> "$LOG"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 無變動，跳過 push" >> "$LOG"
fi
