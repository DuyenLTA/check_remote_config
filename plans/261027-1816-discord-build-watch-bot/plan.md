---
title: "Discord build-watch bot: dev báo build → QA duyệt → cài từ App Tester → tự /rc-check"
status: done
created: 2026-10-27
blockedBy: []
blocks: []
---

# Discord build-watch bot

Dev đăng tin build (`Bản build AIP882---AI-Video v4.3.0 (40) …`) vào kênh build → bot **kiểm App Tester đã có bản cần cài chưa**
(chưa có thì báo đang chờ + tự kiểm lại mỗi 10 phút) → có rồi mới hỏi ở kênh QA kèm nút **Check**
→ người có role QA bấm → bot lái app **App Tester** trên máy Android đang cắm, cài đúng bản (ưu tiên bản debug) →
gọi `claude -p "/rc-check <pkg>"` → đăng kết quả + link artifact vào kênh QA.

## User đã chốt (27/10/2026)
- Nguồn build: **App Tester** (Firebase App Distribution) — link Drive chỉ chứa apk/aab để ASO submit; dev sẽ đẩy thêm **bản debug** lên App Tester
- Bot Discord thật: **user tự tạo** ở Developer Portal, token ở `~/.bashrc` (đầu file, trước guard `case $-`)
- Test: **Claude headless** chạy đủ workflow `/rc-check`
- Duyệt: **một role** (QA) mới bấm được Check

## Phases
| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 0 | [Spike rủi ro: claude -p publish artifact, tải + cài qua App Tester](phase-00-risk-spikes.md) | in-progress (headless OK, tải+cài OK; chưa có bản debug để thử đè release) | 1h |
| 1 | [Lấy build từ App Tester + cài (`rcr-cai-build`)](phase-01-app-tester-download-and-install.md) | done (`rcr-cai-build` chạy trên máy thật; tải tự động chạy thật ở build dev kế tiếp) | 5h |
| 2 | [Bot Discord: đọc kênh, nút duyệt theo role, hàng đợi](phase-02-discord-bot-watch-and-approve.md) | done (bot chạy thật ở `qa-auto`; hỏi ngay không kiểm App Tester trước; đọc tin chuyển tiếp + markdown; nhiều máy song song) | 4h |
| 3 | [Chạy Claude headless + đăng kết quả](phase-03-headless-claude-run-and-report.md) | done (prompt qua stdin — claude.CMD cắt tham số xuống dòng; trả lời tiếng Việt; chưa chạy trọn 1 lượt /rc-check thật) | 3h |
| 4 | [Vận hành: service, hướng dẫn tạo bot, README](phase-04-ops-service-and-docs.md) | done (Task Scheduler cài trên máy Windows; script systemd cho Ubuntu chưa chạy thật) | 2h |

## Phụ thuộc chính
- `discord.py` (mới, thêm vào extras `bot`), App Tester v0.133 trên máy (đã đăng nhập), `claude` CLI 2.1.311 (có sẵn)
- Dùng lại: `--preflight`, `rcr-check`, `rcr-sdk-check`, `discord_notify` (giữ webhook cho lượt tay), `ad_units_sheet` (mã app → package)

## Ràng buộc
- 1 máy điện thoại → **1 lượt tại một thời điểm**, hàng đợi FIFO; khoá file dùng chung với `/rc-check` tay
- Package lấy từ **mã app → sheet "Check thông số KT"** rồi khớp chính xác `bundle_id` trong App Tester; version khớp chính xác;
  sau khi cài xác nhận bằng `dumpsys`. Không khớp theo tên app, không ghép chữ trong tin vào prompt Claude
- Secret chỉ ở env (`DISCORD_BOT_TOKEN`), không in, không ghi repo
- Không commit/push trong lượt chạy (giữ luật §7 rc-check)

## Đã biết thêm (27/10/2026)
- Mẫu tin dev: `@QA… Bản build AIP882---AI-Video v4.3.0 (40) đã được hoàn thiện. Please check <ghi chú> <link Drive thư mục>`
  → bot chỉ cần **mã app** `AIP882` + **version** `4.3.0 (40)`; link Drive bỏ qua (chỉ để ASO submit)
- Bản release **không debuggable** → nhánh bộ TC (patch Remote Config) không chạy được → cần **bản debug trên App Tester**;
  không có bản debug thì chỉ chạy nhánh SDK 3.6.1, dòng cần đổi RC ra Đo tay — báo rõ trong kênh
- Hỏi duyệt + báo kết quả ở **kênh QA riêng**; đọc tin ở kênh build
- Bản debug = release **cùng app, cùng package** trên App Tester, release note có chữ `debug` → đổi debug ↔ release phải gỡ app (mất data)
- Dev ghi trong tin: `apply next-gen` → **cài bản release**; `revert next-gen` / không nhắc → **cài bản debug**
- **Next-Gen = tutorial 3.7.0** (user chốt 27/10/2026); 3.6.1 đã *revert next-gen* → bộ TC. Đã sửa `sdk_probe.NEXTGEN_SDK`
  sang 3.7.0 + docs + test (chưa commit). Bộ TC sắp có tab 3.6.1 / mới hơn — tool tự lấy khi tab có

## Đo trên máy (27/10/2026 tối)
- Luồng cài: Download (~2s) → hộp `Update this app?` (packageinstaller `button1`) → Play Protect `App scan recommended` → **Scan app** (~20s) → `This app looks safe` → **Install**
- App chưa test trên máy → màn **consent** của App Tester
- User chốt: bot **được bấm Scan app** (gửi APK lên Google quét) và **tự tick consent**
- Cùng version có nhiều release (vd 1.3.0 (13) ×2) → phân biệt bằng note; >1 bản cùng loại → dừng

## Đổi so với plan ban đầu (user chốt 27/10/2026 tối)
- **Bỏ bước kiểm App Tester trước** + lịch kiểm lại 10 phút: bot hỏi ngay; bấm Check mới vào App Tester tải đúng bản,
  chưa có bản → báo lỗi + nút **Thử lại**
- **Nhiều máy song song**, mỗi máy một build khác nhau; khoá `out/.may-<serial>.lock`; link report theo package,
  sheet ghi tạm rồi thay, proxy KT-02 lấy cổng trống
- Duyệt theo **user ID** (`DISCORD_DUYET_USER_IDS`), role tuỳ chọn
- Chạy được **Windows + Ubuntu**: cấu hình `~/.config/rcr/bot.env` (hoặc biến User Windows);
  `deploy/cai-bot-windows.ps1` (Task Scheduler) / `deploy/cai-bot-linux.sh` (systemd user)
- Tin dev có thể **không có tên app** (`Bản build AIP920 v1.6.0 (7)`) và **in đậm mã app** (`**AIP920**`)

## Câu hỏi còn mở
1. ~~Bot chưa được mời vào kênh build của dev~~ — 28/10/2026 bot đã vào kênh dev (server khác server QA);
   `DISCORD_BUILD_CHANNEL_ID` nhận nhiều ID → nghe kênh dev + `qa-auto` (vẫn nhận tin QA chuyển tiếp). Chưa thấy tin dev thật nào qua bot
2. Lượt bot có tắt webhook `rcr-notify` để kênh không nhận tin trùng không?
3. Chưa thử: cài bản debug đè release (App Tester chưa có bản debug), 2 máy chạy song song thật, script Ubuntu

