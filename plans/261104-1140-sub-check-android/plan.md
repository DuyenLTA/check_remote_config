# Check sub Android (`/check-sub`) — plan

**Mục tiêu:** chạy bộ TC sub chung (sheet `SUB_Android`, tab `TC Sub Android`, 45 TC) trên mọi app Android:
`/check-sub <mã app> <version>` trên Discord (và lệnh terminal) → cài build → chạy case → report + menu log bug như Check.

**User chốt (04/11/2026):**
- Build: bản release từ App Tester (team đã mua sub được trên bản này)
- Chạy từ: lệnh `/check-sub` trên Discord, qua hàng đợi như Check; có thêm lệnh terminal
- Case cần máy thứ 2 / tài khoản thứ 2: tự chạy nếu đủ máy/tài khoản, thiếu thì ghi "Cần test tay"
- Thông tin riêng từng app (đường vào Paywall, nút, quyền lợi Premium): tool tự dò lần đầu rồi lưu, QA sửa nếu sai

## Kiến trúc
Giống `rc-check`: phần tất định là Python (`rcr-sub`), phần phán đoán do Claude headless chạy `/sub-check`.

| Khối | Việc | Ghi chú |
|---|---|---|
| `sub_tc` | tải sheet sub → danh sách case (N°, nhóm, precondition, action, expected) | dòng `▌` là tiêu đề nhóm, cột Feature/Test Description kế thừa dòng trên |
| `sub_profile` | `data/sub-profiles/<package>.json`: đường vào Paywall, nút gói/Continue/Continue with ads, entry Settings > quản lý sub, quyền lợi Premium | lần đầu Claude dò rồi ghi; lần sau dùng lại |
| `sub_billing` | nhận popup Google Play (`com.android.vending`), đọc giá + chu kỳ, chọn thẻ test (approves / declines / slow), bấm Subscribe, đóng popup | dump uiautomator, chọn theo chữ hiển thị |
| `sub_play_store` | mở trang Subscriptions (deep link), đọc trạng thái gói, Cancel, Resubscribe, đổi phương thức thanh toán | |
| `sub_trang_thai` | app Premium hay free: ads có load không (ad_log), Paywall còn hiện không, Play Store có sub Active | ba nguồn phải khớp nhau |
| `sub_lich` | xếp case theo trạng thái tài khoản để đỡ chờ: nhóm "chưa mua" → mua → nhóm "đang Active" → cancel → chờ hết kỳ… | gia hạn test: Weekly/Monthly 5 phút, Yearly 30 phút |
| `/sub-check` (Claude) | chạy từng case theo lịch, chấm Expected, ra FAIL giả như rc-check 5d, ghi report | |
| Bot | `/check-sub` → job `loai_job: "sub"` → cài build → Claude `/sub-check` → kết quả + menu bug | dùng lại hàng đợi, nút Dừng/Huỷ, log Jira |

## Phân loại 45 TC
- **Tự chạy 1 máy (~32):** 1, 2, 89, 52, 90, 91, 8, 10, 12, 55, 23, 28, 59, 60, 61, 62, 63, 36, 67, 71, 43, 73, 44, 45, 74–78, 80, 82, 47, 49
- **Tự chạy, cần chọn thẻ test / Play Console bật sẵn (6):** 6, 56, 32, 65, 33, 64
- **Cần máy B / tài khoản 2 (3):** 38, 41 (máy thứ 2 cùng tài khoản), 40 (tài khoản Google thứ 2 trên máy) → tự chạy nếu đủ, thiếu ghi "Cần test tay"
- **Cần người:** 35 (refund qua ASO), 7 (mất mạng đúng lúc popup xử lý — chạy thử, không ổn định thì NEEDS_HUMAN)
- **Riêng app:** 16 (quyền lợi Premium) — lấy từ profile app

## Phases
| # | Phase | Trạng thái |
|---|---|---|
| 1 | Spike trên máy thật: popup billing, Play Store Subscriptions, nhận Premium — chốt selector | Xong ([kết quả](phase-01-spike-ket-qua.md)) |
| 2 | `sub_tc`, `sub_doc_man` (Paywall / popup / Play Store), `sub_log` (PurchaseEG), `sub_thao_tac` (lái máy + profile) | Xong, chạy thật trên Pixel 4: mua, đóng popup, cancel, resubscribe, chờ hết kỳ |
| 3 | Lịch (`sub_tc.lich`) + CLI `rcr-sub` + report HTML (`sub_report`) | Xong |
| 4 | Lệnh Claude `/sub-check` (dò profile lần đầu, chấm, rà FAIL giả) | Xong — chưa chạy cả bộ đầu-cuối |
| 5 | Bot: `/check-sub`, job sub, prompt, kết quả + log bug, verify bug `sub#<số>` | Xong |
| 6 | Chạy thật 1 app đầu-cuối, sửa, docs (README, usage-log) | README xong; chờ lượt đầu-cuối AIP936 |

## Rủi ro
- **Mua thật bằng tiền:** chỉ mua khi tài khoản Google trên máy là License Tester (popup ghi "Test card"); không thấy chữ đó → dừng, không bấm Subscribe.
- Popup billing / Play Store đổi giao diện theo bản Play Store → chọn theo chữ, có ảnh chụp mỗi bước.
- Lượt dài (gia hạn nhiều kỳ, Grace Period): cả bộ ước 2–3 giờ/app → lưu lượt sau mỗi case, chạy tiếp được.
- TC có `[Inferred — cần confirm với spec]` (56, 71, 73): chấm theo hành vi hợp lý, ghi rõ trong report.

## Câu hỏi chưa giải quyết
- Máy nào đăng nhập tài khoản License Tester? Tài khoản thứ 2 / máy thứ 2 cùng tài khoản có sẵn không?
- Play Console các app đã bật Grace Period / Account Hold chưa (TC32, 33, 64, 65)?
