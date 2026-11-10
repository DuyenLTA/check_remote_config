#!/usr/bin/env bash
# Cho rcr-bot tren Ubuntu chay 24/24 (bot chinh). Chay SAU deploy/cai-bot-linux.sh:
#   bash deploy/cai-24-24-ubuntu.sh        (se hoi mat khau sudo; chay lai nhieu lan khong sao)
# Lam:
#   1. linger: bot tu bat khi may khoi dong lai, khong can dang nhap
#   2. chan sleep / suspend / hibernate, GNOME khong tu suspend, gap nap laptop van chay
#   3. systemd: bot thoat kieu gi cung tu bat lai, khong bao gio "bo cuoc"
#   4. adb: udev rule + nhom plugdev (khong bi "no permissions")
#   5. token Claude dai han trong bot.env (luot chay dem khong chet vi het phien)
#   6. dien thoai dang cam: man hinh luon sang khi cam sac
#   7. kiem bot.env khong co RCR_VAI_TRO=phu, restart bot, in trang thai
set -euo pipefail

CFG="$HOME/.config/rcr/bot.env"
UNIT_DIR="$HOME/.config/systemd/user/rcr-bot.service.d"
ok()   { echo "  [OK] $*"; }
canh() { echo "  [!]  $*"; }

[ "$(uname -s)" = "Linux" ] || { echo "Script nay chi chay tren Ubuntu/Linux." >&2; exit 1; }
[ -f "$CFG" ] || { echo "Chua co $CFG - chay deploy/cai-bot-linux.sh truoc." >&2; exit 1; }
systemctl --user cat rcr-bot >/dev/null 2>&1 || { echo "Chua co service rcr-bot - chay deploy/cai-bot-linux.sh truoc." >&2; exit 1; }

echo "1. Tu bat bot khi khoi dong lai may (linger)"
sudo loginctl enable-linger "$USER"
ok "linger: $(loginctl show-user "$USER" -p Linger --value)"

echo "2. Chan sleep / suspend"
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target >/dev/null 2>&1
ok "da mask sleep/suspend/hibernate"
if command -v gsettings >/dev/null 2>&1 && gsettings list-schemas 2>/dev/null | grep -qx org.gnome.settings-daemon.plugins.power; then
  gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
  gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'
  ok "GNOME khong tu suspend khi de lau (lock man hinh van giu, khong anh huong bot)"
fi
# Drop-in thay vi sua logind.conf goc. Reload bang HUP: restart systemd-logind co the da ca phien do hoa.
sudo mkdir -p /etc/systemd/logind.conf.d
printf '[Login]\nHandleLidSwitch=ignore\nHandleLidSwitchExternalPower=ignore\nHandleLidSwitchDocked=ignore\n' \
  | sudo tee /etc/systemd/logind.conf.d/rcr-24-24.conf >/dev/null
sudo systemctl kill -s HUP systemd-logind
ok "gap nap laptop: khong lam gi"

echo "3. Bot thoat kieu gi cung tu bat lai"
mkdir -p "$UNIT_DIR"
# Restart=always: ca khi bot thoat ma 0. StartLimitIntervalSec=0: loi lien tuc (mat mang) van thu mai.
printf '[Unit]\nStartLimitIntervalSec=0\n\n[Service]\nRestart=always\nRestartSec=30\n' > "$UNIT_DIR/24-24.conf"
systemctl --user daemon-reload
systemctl --user enable rcr-bot >/dev/null 2>&1
ok "Restart=always, RestartSec=30"

echo "4. Quyen adb"
if ! dpkg -s android-sdk-platform-tools-common >/dev/null 2>&1; then
  sudo apt-get install -y -qq android-sdk-platform-tools-common >/dev/null
fi
getent group plugdev >/dev/null || sudo groupadd plugdev
if id -nG "$USER" | tr ' ' '\n' | grep -qx plugdev; then
  ok "da o nhom plugdev"
else
  sudo usermod -aG plugdev "$USER"
  canh "vua them vao nhom plugdev - can khoi dong lai may 1 lan de co hieu luc"
fi
sudo udevadm control --reload-rules && sudo udevadm trigger
ok "udev rule adb"

echo "5. Token Claude dai han"
if grep -q '^CLAUDE_CODE_OAUTH_TOKEN=.' "$CFG"; then
  ok "bot.env da co CLAUDE_CODE_OAUTH_TOKEN"
else
  echo "  Mo terminal KHAC, chay: claude setup-token   -> dang nhap -> copy token no in ra."
  read -r -s -p "  Dan token vao day (Enter de bo qua): " TOKEN; echo
  if [ -n "${TOKEN:-}" ]; then
    echo "CLAUDE_CODE_OAUTH_TOKEN=$TOKEN" >> "$CFG"
    ok "da ghi token vao bot.env"
  else
    canh "chua co token: phien claude het han thi moi luot se loi"
  fi
fi
chmod 600 "$CFG"

echo "6. Dien thoai dang cam"
if command -v adb >/dev/null 2>&1; then
  SERIALS=$(adb devices | awk 'NR>1 && $2=="device" {print $1}')
  [ -n "$SERIALS" ] || canh "khong co may nao o trang thai device (cam may moi thi chay lai script)"
  for s in $SERIALS; do
    adb -s "$s" shell svc power stayon usb >/dev/null 2>&1 && ok "$s: man hinh luon sang khi cam sac" \
      || canh "$s: khong dat duoc stayon"
    # Chi tat duoc khoa vuot; may co PIN/mat khau thi phai tat tay trong Cai dat.
    adb -s "$s" shell locksettings set-disable true >/dev/null 2>&1 || canh "$s: con khoa man hinh co mat khau - tat tay"
  done
else
  canh "khong thay adb trong PATH"
fi

echo "7. Vai tro + restart bot"
if grep -q '^RCR_VAI_TRO=phu' "$CFG"; then
  canh "bot.env dang co RCR_VAI_TRO=phu -> Ubuntu se KHONG doc tin build. Xoa dong do neu Ubuntu la bot chinh."
else
  ok "vai: chinh"
fi
systemctl --user restart rcr-bot
sleep 5
systemctl --user --no-pager status rcr-bot | head -4
echo
echo "Xong. Log: journalctl --user -u rcr-bot -f"
echo "Thu that: sudo reboot -> KHONG dang nhap -> tha tin build -> bot van tra loi o qa-auto."
