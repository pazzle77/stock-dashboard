#!/bin/bash
# 台美股 Dashboard 排程設定
# 使用 crontab 自動執行

PYTHON="/Users/jacky/.pyenv/versions/3.11.7/bin/python3"
SCRIPT="/Users/jacky/claude/stock dashboard/dashboard.py"
LOG="/Users/jacky/claude/stock dashboard/dashboard.log"

echo "設定 crontab 排程..."
echo "台股：09:00（開盤）、13:30（收盤）"
echo "美股：21:30（開盤）、04:00（收盤）"
echo ""

# 寫入 crontab（保留現有設定）
(crontab -l 2>/dev/null | grep -v "dashboard.py"; cat <<EOF
# 台美股 Dashboard
0 9    * * 1-5 $PYTHON "$SCRIPT" >> "$LOG" 2>&1
30 13  * * 1-5 $PYTHON "$SCRIPT" >> "$LOG" 2>&1
30 21  * * 1-5 $PYTHON "$SCRIPT" >> "$LOG" 2>&1
0 4    * * 2-6 $PYTHON "$SCRIPT" >> "$LOG" 2>&1
EOF
) | crontab -

echo "排程設定完成！目前 crontab："
crontab -l | grep dashboard
