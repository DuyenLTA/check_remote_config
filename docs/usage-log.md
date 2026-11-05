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
| 31/10/2026 | AIP886 AI Photo Video Maker (release) | 2.7.0 (20) | 23 (8 nhóm) | 19 PASS · 0 FAIL · 4 chờ (3 cần máy OPPO, 1 chờ kho fill inter resume 503) | không | https://claude.ai/artifact/HboJXYApcM4FjxX3fzAphC | 31 phút | 3 giờ | 149 phút |
| 31/10/2026 | AIP886 AI Photo Video Maker (release, tool tự chấm) | 2.7.0 (20) | 23 (8 nhóm) | 20 PASS · 0 FAIL · 3 BLOCKED (cần máy OPPO) | không | https://claude.ai/artifact/LCwN9MDx2uFf3zA5rgMEpi | ? | 3 giờ | ? |
| 02/11/2026 | AIHomeDesign | 1.9.0 (11) | 61 (TC SDK 3.6.1) | 53 PASS · 4 FAIL · 4 BLOCKED (S03 cần máy OPPO, SG04-01 cần throttle mạng) | splash_inter_change=false vẫn dùng chuỗi 102_n (RG02-01/02); LFO1 enable_btn_lfo=true không focus ngôn ngữ đầu (RG02-03); 305 vẫn load khi tắt OB5+Question (RG04-02) | https://claude.ai/artifact/6W7Xturyuzr3g7VqBDrqTz | 270 phút | 3 giờ | -90 phút |
| 02/11/2026 | AI Photo Video Maker | 2.7.0 | 61 (SDK 3.6.1) | 48 PASS · 13 FAIL | 13 FAIL (resume ad sai màn, 102_a trùng ID, LFO1 Next, 305 preload, 302 ở OB2, 301_o khi tắt OB Old; SG04 cần PO xác nhận) | https://claude.ai/artifact/BkdQWpEJQfCtGRZYTP9hf1 | 120 phút | 3 giờ | 60 phút |
| 03/11/2026 | AIP936 AIHomeDesign (release, chạy lại full, chế độ chuỗi) | 1.9.0 (11) | 55 (TC SDK 3.6.1, sheet 03/11) | 51 PASS · 0 FAIL · 4 BLOCKED (S03 cần máy OPPO, SG04-01 cần throttle mạng, RG08-04 native full 303 không fill) | không (RG04-02 305 preload đã bị xoá khỏi sheet) | https://claude.ai/artifact/6W7Xturyuzr3g7VqBDrqTz | 48 phút (TB 54s/case) | 3 giờ | 132 phút |
| 05/11/2026 | AI Photo Video Slideshow (AIP893) | 2.5.0 | 52 (12 nhóm) | 39 PASS · 10 FAIL · 3 BLOCKED (S04/S05 cần throttle mạng) | ob3_show_button_skip=false vẫn có X; tắt OB1/OB2/OB4 thì ad màn tắt không load (301/302/303, 305 mất preload); đi nhanh qua LFO2 thì OB1 trắng, 202 sang OB2; màu chữ swipe không theo primary; thứ tự list_language sai từ vị trí 4; tiêu đề LFO2 không đổi ngôn ngữ; OB3 native full reload sau resume | https://claude.ai/artifact/Mjf4SQZTBw5pt6XqmGzvRo | 46 phút | 3 giờ | 134 phút |

Lượt Sorapix có 20/23 case bị kẹt vì hộp thoại xin quyền thông báo che app sau `pm clear`, mỗi
case hết giờ chờ rồi chạy lại. Đã sửa ở commit `66ca8ec`; lượt sau sẽ bớt thời gian chờ này, chưa đo lại.

Các lượt Piclux 2.8.0 (06/10) và Photomaker (05/10, 28/09) có nhắc trong `.claude/commands/rc-check.md`
nhưng report không còn trên máy này.
