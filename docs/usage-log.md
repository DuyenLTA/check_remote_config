# Log sử dụng — rc-check

Mỗi lượt chạy thật thêm một dòng. Cột "Test tay" là thời gian tester ước tính nếu làm cùng việc bằng tay; điền cột này thì tính được thời gian tiết kiệm. Dấu `?` là chưa điền.

| Ngày | App | Version | Số case | Kết quả | Bug app xác nhận | Report | Thời gian tool | Test tay |
|---|---|---|---|---|---|---|---|---|
| 10/10/2026 | Sorapix com.ai.aiimage.aivideogenerator | 1.6.0 | 54 (4 nhóm) | 35 PASS · 11 FAIL · 4 BLOCKED · 4 không kiểm được | 0, 11 FAIL chưa audit | `out/run-com.ai.aiimage.aivideogenerator-g0..g3.html` (chưa publish) | 14:25–16:22, ~2 giờ | ? |
| 10/10/2026 | com.hairai.hairstyletryon.haircolorchanger | — | 0 | Mới kiểm DEX, chưa chạy case | — | `out/dex-…-21.json` | — | — |

Các lượt Piclux 2.8.0 (06/10) và Photomaker (05/10, 28/09) có nhắc trong `.claude/commands/rc-check.md`
nhưng report không còn trên máy này.
