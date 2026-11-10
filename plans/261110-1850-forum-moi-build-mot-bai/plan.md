# Forum: mỗi build một bài

User chốt 10/11/2026: qa-auto khó nhìn — tin build mới lẫn kết quả, nhiều build thì vuốt lên tìm. Chọn Forum
(`qa-builds`, id 1569677169758699560) thay vì tách 2 kênh.

## Thiết kế
- `DISCORD_FORUM_CHANNEL_ID` (rỗng = như cũ, mọi tin gốc ở qa-auto).
- Build mới có SDK → tạo **bài** (tên `AIP916 · 1.3.0 (5) · Tên app`), tin đầu bài = tin gốc (nút Check…),
  tag người duyệt để có thông báo. Id tin đầu bài == id thread → `msg_id` giữ nguyên ý nghĩa.
- Tin gốc khác của CÙNG build (verify, hỏi lại /check, check-sub) → gửi vào bài đó; build chưa có bài → tạo bài.
- `tin[msg_id].kenh_id` = id thread. `_tin_qa` đọc kenh_id, không có thì qa-auto (job cũ).
- Nhãn (QA tạo tay trong kênh, bot khớp theo tên, thiếu thì bỏ qua): Chờ duyệt → Đang chạy → PASS / FAIL /
  Cần xem (DUNG, LOI, HET_GIO, cài hỏng, thiếu testvsl). Chỉ lượt check/sub đổi nhãn, verify không.
- Thông báo chung (không đọc được tin build, build không SDK, sprint, lỗi bot) vẫn ở qa-auto.
- Bài tự archive sau 7 ngày không hoạt động.

## Việc
- [x] module `bot_forum.py`: gui_goc, kenh_cua, dat_nhan, nhan_ket_qua
- [x] `_tin_qa` theo kenh_id
- [x] hoi_build_moi, hoi_lai_build (+ hoi_lai báo link ở qa-auto), verify, check-sub dùng gui_goc
- [x] nhãn ở lúc chạy / cài hỏng / kết quả
- [x] test, README
- [ ] Ubuntu: thêm `DISCORD_FORUM_CHANNEL_ID` vào bot.env, pull, restart
