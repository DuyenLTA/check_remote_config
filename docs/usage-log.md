# Log sử dụng — rc-check

Mỗi lượt chạy thật thêm một dòng. "Test tay (TB)" là thời gian tester ước tính nếu làm cùng việc bằng tay, lấy trung bình; spec dài hay ngắn thì lệch lên xuống. "Tiết kiệm" = Test tay − Thời gian tool. Thời gian tool là thời gian máy chạy; trong lúc đó tester làm việc khác được, nên con số tiết kiệm là mức thấp nhất.

Test tay (TB): **3 giờ** cho một bộ testcase Remote Config của một app (tester ước tính 22/10/2026).

| Ngày | App | Version | Số case | Kết quả | Bug app xác nhận | Report | Thời gian tool | Test tay (TB) | Tiết kiệm |
|---|---|---|---|---|---|---|---|---|---|
| 10/10/2026 | Sorapix com.ai.aiimage.aivideogenerator | 1.6.0 | 54 (4 nhóm) | 35 PASS · 11 FAIL · 4 BLOCKED · 4 không kiểm được | 0, 11 FAIL chưa audit | `out/run-com.ai.aiimage.aivideogenerator-g0..g3.html` (chưa publish) | ~2 giờ (14:25–16:22) | 3 giờ | ~1 giờ, chưa tính thời gian xử lý 19 case còn lại |
| 10/10/2026 | com.hairai.hairstyletryon.haircolorchanger | — | 0 | Mới kiểm DEX, chưa chạy case | — | `out/dex-…-21.json` | — | — | — |

Lượt Sorapix có 20/23 case bị kẹt vì hộp thoại xin quyền thông báo che app sau `pm clear`, mỗi
case hết giờ chờ rồi chạy lại. Đã sửa ở commit `66ca8ec`; lượt sau sẽ bớt thời gian chờ này, chưa đo lại.

Các lượt Piclux 2.8.0 (06/10) và Photomaker (05/10, 28/09) có nhắc trong `.claude/commands/rc-check.md`
nhưng report không còn trên máy này.
