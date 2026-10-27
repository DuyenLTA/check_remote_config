#!/usr/bin/env bash
# Cai rcr-bot thanh systemd USER service tren Ubuntu: tu bat khi dang nhap, tu chay lai khi loi.
# Chay: bash deploy/cai-bot-linux.sh   (khong can sudo)
# Cau hinh doc tu ~/.config/rcr/bot.env (KEY=VALUE) - systemd khong doc ~/.bashrc.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$REPO/.venv/bin/rcr-bot"
CFG="$HOME/.config/rcr/bot.env"
UNIT="$HOME/.config/systemd/user/rcr-bot.service"

if [ ! -x "$BIN" ]; then
  echo "Chua co $BIN. Chay: cd $REPO && .venv/bin/python -m pip install -e '.[dev,bot]'" >&2
  exit 1
fi
if [ ! -f "$CFG" ]; then
  echo "Chua co $CFG. Tao file voi cac dong:" >&2
  echo "  DISCORD_BOT_TOKEN=... / DISCORD_BUILD_CHANNEL_ID=... / DISCORD_QA_CHANNEL_ID=... / DISCORD_DUYET_USER_IDS=..." >&2
  exit 1
fi
chmod 600 "$CFG"
command -v claude >/dev/null || { echo "Khong thay 'claude' trong PATH" >&2; exit 1; }
command -v adb >/dev/null || { echo "Khong thay 'adb' trong PATH" >&2; exit 1; }

mkdir -p "$(dirname "$UNIT")"
# PATH cua shell luc cai: systemd khong co nvm (claude) / platform-tools (adb).
# '%' la ky tu dac biet cua systemd -> nhan doi.
cat > "$UNIT" <<EOF
[Unit]
Description=rcr-bot: Discord build-watch -> App Tester -> /rc-check
After=network-online.target

[Service]
WorkingDirectory=$REPO
EnvironmentFile=$CFG
Environment=PATH=${PATH//%/%%}
Environment=PYTHONIOENCODING=utf-8
ExecStart=$BIN
Restart=on-failure
RestartSec=30

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now rcr-bot
systemctl --user --no-pager status rcr-bot | head -5
echo
echo "Xem log: journalctl --user -u rcr-bot -f"
echo "Muon bot chay ca khi chua dang nhap: sudo loginctl enable-linger $USER"
