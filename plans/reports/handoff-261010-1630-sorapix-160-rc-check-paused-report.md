# Handoff — /rc-check Sorapix 1.6.0 (dừng giữa chừng)

- App: `com.ai.aiimage.aivideogenerator` 1.6.0 (vc10, DEBUGGABLE), máy Pixel 6 `18311FDF60085N`
- SDK FO 3.5.3 (logcat) → tab `TC SDK 3.5.3`, 54 case, 54 tool chạy được
- RC: 177 key, 109 mirror, ghi qua run-as. Sheet ID ads: 46 vị trí
- Chạy 10/10/2026 14:25–16:22, 4 nhóm × ~14 case
- Dữ liệu: `out/sorapix-1.6.0-261010/` (`rc-g0..3.json` = stdout từng nhóm, `rc-all.json` = 54 record gộp, `rc-keys.txt` = danh sách key). Report từng nhóm: `out/run-com.ai.aiimage.aivideogenerator-g0..3.html`
- Chưa publish artifact (còn case chưa chấm xong — mục 5b/5d)

## Kết quả thô của tool

35 PASS · 11 FAIL · 4 BLOCKED · 4 NOT_VERIFIABLE. PASS chưa rà PASS giả (mục 5c).

| Nhóm | Case | Ghi chú |
|---|---|---|
| Nút X OB3 | OB3X-001/002/004/005/013 (FAIL ×2 lần) | Nghi FAIL giả: ad 303 `…826` show, OB3 đứng 8,6s nhưng `ob3.khung` chỉ có **1 khung** (0,27s). Nút X app này là `btnSkip`/`btnTimeoutSkip` (đã có trong `data/ui_names.yaml`) |
| Timer OB3 | OB3A-002/004/006 FAIL, OB3A-003 BLOCKED, OB3A-005 NV | 002: ad 303 fill nên vùng ad không trống (điều kiện no-fill không thành). 004: rời OB3 sau 3,6s kể từ ad fail (timer=3). 003: cần throttle/chặn ad server |
| Hứng ad 202 | H202-004/005/007 FAIL, H202-006/008/009 BLOCKED | Điều kiện "202 chưa kịp show ở LFO2" chưa tạo được; 008/009 record rỗng (`overrides {}`) |
| Màu chữ OB2 | OB2-001/002/003 NV | Cần screencap + đo màu |

## Việc làm tiếp (đã chọn hướng: dừng)

1. Sửa tool: OB3 chỉ quan sát được 1 khung → tìm vì sao vòng nhìn dừng sớm, rồi chạy lẻ 10 case OB3X/OB3A, gộp vào `rc-all.json`
2. Rà 5b/5d các case còn lại; build này **dùng ad thật** (interstitial splash không đóng bằng BACK) → xin dev bản ad test trước khi lái tay
3. Rà PASS giả 35 case từ `cases[].ads` offline
4. Gộp + publish bằng `report_html.build(report_data.page_data(...))`, ghi link `rcr-artifact --generated-at`

## Trạng thái máy / repo

- Config đã `--restore`, mạng bình thường. App bị `pm clear` nhiều lần
- Sửa tool chưa commit: `src/rcr/device_reset.py` cấp `POST_NOTIFICATIONS` sau `pm clear` (dialog quyền làm 20/23 case kẹt foreground ở lượt đầu) + 2 test `tests/test_device_reset.py`; 570 test pass

## Câu hỏi chưa giải quyết

- Có bản Sorapix dùng ad test không?
- Lệnh nền bị Claude Code dừng 2 lần vì thiếu RAM — chạy lượt dài nên đóng bớt app nặng, hoặc bật `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1`
