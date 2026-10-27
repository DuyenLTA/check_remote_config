---
phase: 2
title: "Bot Discord: đọc kênh, nút duyệt, hàng đợi"
status: pending
priority: P1
effort: "4h"
dependencies: [1]
---

# Phase 2: Bot Discord đọc kênh + nút duyệt theo role + hàng đợi

## Overview
`rcr-bot` chạy liên tục. Thấy tin `Bản build <MÃ>---<Tên> v<x.y.z> (<code>)` trong kênh build → **vào App Tester kiểm
trước** (`rcr-cai-build --chi-kiem`, không cài) xem đã có bản cần cài (debug/release theo SDK) chưa, rồi mới đăng ở **kênh QA**
(kèm link về tin gốc):

| Kết quả kiểm App Tester | Bot đăng ở kênh QA |
|---|---|
| có đúng bản cần | "Build AIP882 4.3.0 (40) — <package> — SDK <x> → bản <debug\|release> đã có. Check không?" + **Check** / **Bỏ qua** |
| cần debug, mới có release | "Chưa có bản debug trên App Tester, bot tự kiểm lại mỗi 10 phút" + nút **Chạy bản release (chỉ checklist Next-Gen)** |
| chưa có version đó | "App Tester chưa có 4.3.0 (40), bot tự kiểm lại mỗi 10 phút" |

Đang chờ: bot kiểm lại **mỗi 10 phút, tối đa 24 giờ**; bản xuất hiện → sửa chính tin đó thành câu hỏi Check; hết 24 giờ →
sửa tin thành "Hết giờ chờ" + nút **Kiểm lại**. Chỉ người có role QA bấm được mọi nút.

## Requirements
- Env: `DISCORD_BOT_TOKEN`, `DISCORD_BUILD_CHANNEL_ID`, `DISCORD_QA_ROLE_ID`, (tuỳ) `DISCORD_REPORT_CHANNEL_ID`
- Intents: guilds + guild_messages + **message_content**; chỉ nghe đúng kênh build, bỏ tin của bot
- Bấm nút: kiểm role → không có role thì trả lời ẩn (ephemeral) "Chỉ QA duyệt được", không làm gì
- Duyệt → vào hàng đợi FIFO (1 worker vì 1 máy); tin của bot sửa thành "Đang chờ (vị trí n)" / "Đang chạy" / "Xong"
- Cùng package + version duyệt 2 lần → không chạy trùng
- Lượt kiểm App Tester cũng lấy khoá máy; đang có lượt test chạy thì lượt kiểm hoãn tới khi máy rảnh (không chen vào giữa lượt)
- Danh sách tin đang chờ bản lưu cùng `out/bot-hang-doi.json` → bot khởi động lại vẫn kiểm tiếp
- Khoá file `out/.may-dang-chay.lock` dùng chung với lượt `/rc-check` tay: đang có lượt tay thì job chờ
- Bot khởi động lại không mất job đang chờ: lưu hàng đợi ra `out/bot-hang-doi.json`

## Architecture
```
discord_bot.py        client, on_message, View có 2 nút, kiểm role
bot_tin_build.py      tách mã app + version từ tin (thuần, dễ test; dùng build_ma_app của phase 1)
bot_hang_doi.py       queue + lock file + lưu/khôi phục JSON + danh sách tin đang chờ bản (lịch kiểm lại)
```
Job = `{msg_id, ma_app, package, version, sdk, loai_ban, nguoi_duyet, luc}`; worker gọi phase 1 (`cai`) rồi phase 3 (`chay_claude`).

## Related Code Files
- Create: `src/rcr/discord_bot.py`, `src/rcr/bot_tin_build.py`, `src/rcr/bot_hang_doi.py`
- Create: `tests/test_bot_tin_build.py`, `tests/test_bot_hang_doi.py`
- Modify: `pyproject.toml` (extras `bot = ["discord.py>=2.4"]`, script `rcr-bot`)

## Implementation Steps
1. Parser tin build theo mẫu thật (27/10/2026) → `{ma_app, ten, version, next_gen, tutorial}`; lệch mẫu → bot hỏi QA, không đoán

   | Tin (bỏ dòng mention) | ma_app | version | next_gen | tutorial |
   |---|---|---|---|---|
   | `Bản build AIP882---AI-Video v4.3.0 (40) đã được hoàn thiện. Please check` / `apply tutorial 3.6.1 (revert next-gen)` | AIP882 | 4.3.0 (40) | False | 3.6.1 |
   | `Bản build ADA895-AI-Photoshoot v3.0.0 (22) đã được hoàn thiện. Please check` / `apply next-gen, apply 3.7.0` | ADA895 | 3.0.0 (22) | True | 3.7.0 |

   - Dòng đầu: `Bản build\s+(?P<ma>[A-Z]{3}\d{3})-+(?P<ten>.+?)\s+v(?P<ver>\d+(?:\.\d+)+)\s*\((?P<code>\d+)\)` — dấu nối 1 hoặc 3 gạch
   - `next_gen`: có `revert next-?gen` → False; có `next-?gen` → True; không nhắc → None (coi như không next-gen)
   - `tutorial`: số `x.y.z` ở các dòng ghi chú (sau dòng đầu, bỏ link), không lấy số version build
   - 2 tin trên làm fixture test (bỏ mention tên người)
2. Hàng đợi + lock + persist, test không cần Discord
3. Bot discord.py: on_message → View; callback kiểm `interaction.user.roles`
4. Worker async: chạy job trong thread (subprocess dài), cập nhật tin trạng thái

## Success Criteria
- [ ] Đăng tin build mẫu, bản đã có trên App Tester → kênh QA nhận câu hỏi Check trong < 1 phút (gồm lượt kiểm App Tester)
- [ ] Bản debug chưa có → kênh QA nhận "đang chờ"; dev đẩy bản lên → trong ≤ 10 phút tin đổi thành câu hỏi Check
- [ ] Người không có role bấm → bị từ chối; QA bấm → job chạy
- [ ] 2 build duyệt liền nhau → chạy lần lượt, không đụng máy cùng lúc
- [ ] `pytest -q` xanh

## Risk Assessment
- Python 3.14 + discord.py: kiểm import được ở phase 0/đầu phase này (audioop đã bỏ khỏi stdlib)
- Token lộ → chỉ đọc env, không log; README nhắc reset token nếu lộ
