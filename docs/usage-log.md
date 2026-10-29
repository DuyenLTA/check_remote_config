# Log sử dụng — rc-check

Mỗi lượt chạy thật thêm một dòng. "Test tay (TB)" là thời gian tester ước tính nếu làm cùng việc bằng tay, lấy trung bình; spec dài hay ngắn thì lệch lên xuống. "Tiết kiệm" = Test tay − Thời gian tool. Thời gian tool là thời gian máy chạy; trong lúc đó tester làm việc khác được, nên con số tiết kiệm là mức thấp nhất.

Test tay (TB): **3 giờ** cho một bộ testcase Remote Config của một app (tester ước tính 22/10/2026).

| Ngày | App | Version | Số case | Kết quả | Bug app xác nhận | Report | Thời gian tool | Test tay (TB) | Tiết kiệm |
|---|---|---|---|---|---|---|---|---|---|
| 10/10/2026 | Sorapix com.ai.aiimage.aivideogenerator | 1.6.0 | 54 (4 nhóm) | 35 PASS · 11 FAIL · 4 BLOCKED · 4 không kiểm được | 0, 11 FAIL chưa audit | `out/run-com.ai.aiimage.aivideogenerator-g0..g3.html` (chưa publish) | ~2 giờ (14:25–16:22) | 3 giờ | ~1 giờ, chưa tính thời gian xử lý 19 case còn lại |
| 10/10/2026 | com.hairai.hairstyletryon.haircolorchanger | — | 0 | Mới kiểm DEX, chưa chạy case | — | `out/dex-…-21.json` | — | — | — |
| 24/10/2026 | Sorapix com.ai.aiimage.aivideogenerator | 1.6.0 | 54 (gộp 10/10 + chạy lại 23–24/10) | 45 PASS · 1 FAIL · 8 BLOCKED | 0 bug logic; 1 FAIL giao diện chờ design/PO (OB2-002 chữ Swipe to Next tương phản thấp khi có ad) | https://claude.ai/artifact/WN3x6ecwSyNivwRsaqB3TP | ~5,5 giờ máy chạy cộng dồn (10/10 ~2 giờ, 23/10 ~3 giờ, 24/10 26 phút) + ~30 phút Claude chấm tay 6 case | 3 giờ | chưa tiết kiệm: lượt đầu chạy đủ bộ, tool được sửa giữa chừng (bắt khung OB3, vuốt kẹt, chấm OB3A) nên phải chạy lại nhiều lần |
| 24/10/2026 | Piclux: AI Photo Studio | 2.4.0 | 22 (TC SDK 3.4.0) | 2 PASS · 1 FAIL · 3 BLOCKED · 16 chưa chấm (bản tạm) | chưa có bug xác nhận | https://claude.ai/artifact/J5GwJpP99ddhPjgSz1Hs3S | 50 phút | 3 giờ | 130 phút |
| 28/10/2026 | AI Song | 2.2.0 (13) | 41 dòng (4 mục) | 35 Khớp · 0 Sai · 6 còn đo tay · 24 không áp dụng | — | https://claude.ai/artifact/R8mKMjwPDChDxHzEcLtxP6 | ? | 3 giờ | ? |
| 29/10/2026 | Cast to TV | 1.4.0 (14) | 23 (TC SDK 3.6.1) | 20 PASS · 0 FAIL · 3 chờ máy OPPO | — | https://claude.ai/artifact/GtBN7SHzZg1GFn1i6h2kMb | ? | 3 giờ | ? |
| 29/10/2026 | Cast to TV | 1.4.0 (14) | 23 (TC SDK 3.6.1) | 22 PASS · 0 FAIL · 1 chưa đo (306 no fill) | — | https://claude.ai/artifact/GtBN7SHzZg1GFn1i6h2kMb | ? | 3 giờ | ? |

Lượt Sorapix có 20/23 case bị kẹt vì hộp thoại xin quyền thông báo che app sau `pm clear`, mỗi
case hết giờ chờ rồi chạy lại. Đã sửa ở commit `66ca8ec`; lượt sau sẽ bớt thời gian chờ này, chưa đo lại.

Các lượt Piclux 2.8.0 (06/10) và Photomaker (05/10, 28/09) có nhắc trong `.claude/commands/rc-check.md`
nhưng report không còn trên máy này.
