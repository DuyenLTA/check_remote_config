#!/usr/bin/env bash
# Phien Claude Code publish report thanh artifact cho rcr-bot (bot khong gui file HTML nua).
# Chay tren may bot chinh (Ubuntu), SAU deploy/cai-24-24-ubuntu.sh:
#   bash deploy/cai-phien-publish-ubuntu.sh       (chay lai nhieu lan khong sao)
# Lam:
#   1. cai tmux neu thieu
#   2. systemd user service `rcr-publish`: mo tmux session `rcr-publish` chay
#      `claude "/loop 5m /publish-report"` trong thu muc repo; phien chet thi tu mo lai
#   3. timer mo lai phien moi 6 ngay (lich /loop het han sau 7 ngay)
#   4. in cach lam LAN DAU (bat buoc co nguoi): attach tmux, xac nhan tin cay thu muc / dang nhap
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
UNIT="$HOME/.config/systemd/user/rcr-publish.service"
CLAUDE_BIN="$(command -v claude || true)"
ok()   { echo "  [OK] $*"; }

[ "$(uname -s)" = "Linux" ] || { echo "Script nay chi chay tren Ubuntu/Linux." >&2; exit 1; }
[ -n "$CLAUDE_BIN" ] || { echo "Khong thay lenh claude trong PATH - cai Claude Code truoc." >&2; exit 1; }
[ -x "$REPO/.venv/bin/rcr-publish" ] || { echo "Chua co $REPO/.venv/bin/rcr-publish - chay: $REPO/.venv/bin/pip install -e $REPO" >&2; exit 1; }

echo "1. tmux"
command -v tmux >/dev/null 2>&1 || sudo apt-get install -y -qq tmux >/dev/null
ok "$(tmux -V)"

echo "2. Service rcr-publish"
mkdir -p "$(dirname "$UNIT")"
# Chi mo dung tool can dung: Artifact (publish) + Read (xem dau file) + Bash rcr-publish.
cat > "$UNIT" <<EOF
[Unit]
Description=Claude Code publish report rcr-bot thanh artifact
After=network-online.target
StartLimitIntervalSec=0

[Service]
Type=forking
WorkingDirectory=$REPO
Environment=PATH=$(dirname "$CLAUDE_BIN"):$REPO/.venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/tmux new-session -d -s rcr-publish -c $REPO "$CLAUDE_BIN --allowedTools Artifact Read 'Bash($REPO/.venv/bin/rcr-publish:*)' -- '/loop 5m /publish-report'"
ExecStop=/usr/bin/tmux kill-session -t rcr-publish
Restart=always
RestartSec=60

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable rcr-publish >/dev/null 2>&1
systemctl --user restart rcr-publish
ok "service rcr-publish: $(systemctl --user is-active rcr-publish)"

# Lich `/loop` cua Claude Code tu het han sau 7 ngay ma phien van song -> service khong tu mo lai, report nam cho.
# Timer mo lai phien moi 6 ngay de lich luon duoc tao lai (Claude Code da nho tin cay thu muc, khong hoi lai).
echo "3. Timer mo lai phien moi 6 ngay"
cat > "$(dirname "$UNIT")/rcr-publish-restart.service" <<EOF2
[Unit]
Description=Mo lai phien rcr-publish (lich /loop cua Claude Code tu het han sau 7 ngay)

[Service]
Type=oneshot
ExecStart=/usr/bin/systemctl --user restart rcr-publish
EOF2
cat > "$(dirname "$UNIT")/rcr-publish-restart.timer" <<EOF2
[Unit]
Description=Moi 6 ngay mo lai phien rcr-publish truoc khi lich /loop 7 ngay het han

[Timer]
OnActiveSec=6d
OnUnitActiveSec=6d
Unit=rcr-publish-restart.service

[Install]
WantedBy=timers.target
EOF2
systemctl --user daemon-reload
systemctl --user enable --now rcr-publish-restart.timer >/dev/null 2>&1
ok "timer rcr-publish-restart: $(systemctl --user is-active rcr-publish-restart.timer)"

cat <<EOF

4. LAN DAU - can nguoi ngoi may (chi mot lan):
   tmux attach -t rcr-publish
   - Claude Code hoi tin cay thu muc $REPO -> chon Yes. Chua dang nhap thi dang nhap.
   - Thay vong /loop bat dau ("Khong co report chờ." hoac dang publish) la xong.
   - Thoat ra ma KHONG tat phien: bam Ctrl+B roi D.
   Kiem lai bat cu luc nao: tmux attach -t rcr-publish  |  systemctl --user status rcr-publish
EOF
