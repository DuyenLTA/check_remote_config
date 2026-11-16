# rc-check — tab gen ngầm tự lái (`rcr-gen-ngam`)

Đọc khi: chạy bộ TC gen ngầm (`/check` ô `tinh_nang` = `gen ngầm`), app mới cần khai chữ trên màn, hoặc nhóm báo
`lai_hut`.

## Chạy

```
<bin>/rcr-gen-ngam chay --package <pkg> --serial <S> --app-label "<app> <bản>"      # cả tab, ~25–30 phút
<bin>/rcr-gen-ngam chay ... --nhom r06 --tiep --luot <file .luot.json>                # chạy lại một nhóm
<bin>/rcr-gen-ngam cham --package <pkg> --luot <file>                                 # chấm lại từ số đo đã lưu
```

Mỗi lần `chay` / `cham` tool **tải lại sheet TC** trước (QA hay sửa giữa các lượt), case đổi chữ thì cập nhật file lượt và in ra. Không `--luot` thì tool dựng khung 37 case thẳng từ sheet TC (vài giây, meta chép từ lượt gen ngầm gần nhất của app).
`rcr-check --tc gen-ngam --no-actions` vẫn đặt config + clear data + lái FO từng case (6+ phút) — đừng dùng để dựng khung.
Số đo lưu ở `out/gen-ngam-<pkg>-so.json`, video màn chờ ở `out/gen-ngam-video/`.

## Nhóm config (mỗi nhóm một lần đặt config + clear data + lái FO)

| Nhóm | Case | Ghi chú |
|---|---|---|
| r01 | R01 | ép `generating_wait_image_seconds=45`: ảnh server 30–34s phải xong TRƯỚC mốc popup (user chốt 16/11/2026), report ghi điều kiện ép |
| chung | S01 → R02–R05 → R08, R01-06 | mở lần đầu bấm Don't allow cho S01; Allow ở S01-02 là cấp quyền cho phần còn lại. Ảnh S01 được mở hết trước R02 (badge = 1). R01-06 đếm hết lượt ở đây (cùng Test Data R01) |
| r06 | R06 | đếm hết lượt video (max_concurrent=3 nhanh nhất) cho R06-03 |
| r07 | R07 | mua gói test; đếm ảnh / video tới khi bị chặn theo `limit_gen_*_sub_per_day` của Test Data nhóm (TC 16/11: 3 / 2), bấm lần 4 kiểm chữ chặn |
| dem_r01 | R01-06 | chỉ đếm hết lượt ảnh (khi nhóm chung hỏng ở bước cuối) |

Mỗi nhóm: gói test weekly gia hạn 5 phút/lần — log billing chưa rõ thì mở lạnh đọc lại, chỉ mua khi chắc hết hạn.

## Cách đo (đã kiểm trên AIP892 Pixel 6)

- **Mốc giây** (popup giây 12 / 5, về Home giây 15 / 8): `logcat -v epoch` START ProcessingActivity → START màn kế.
- **Popup đếm 3 → 2 → 1**: `uiautomator dump` mất ~2,1s/lần, `uiautomator events` của app Compose không mang chữ →
  quay màn hình 540x1200, tách 10 khung/s (imageio-ffmpeg), so vùng tiêu đề popup (popup hiện) và đếm điểm ảnh đổi hẳn
  ở dòng đếm (đổi số); neo giờ khung vào START MainActivity. Đo được: hiện 12,0s, đổi 12,9 / 13,9, về Home 15,0.
- **Bấm OK "ngay"**: nhìn UI không kịp → canh vào màn chờ bằng `dumpsys window` (0,02s), tới giây 12,6 bấm toạ độ nút
  OK đọc ở popup trước cùng lượt (màn chờ Premium không có ad).
- **Toast tự ẩn 8s**: mọi lần nhìn UI đều ghi có toast không; thời gian toast đứng = [lần thấy cuối − lần thấy đầu, lần
  mất − lần chưa thấy trước đó] (tính từ lúc TOAST HIỆN — app có thể hiện toast trễ hơn worker vài giây); PASS khi khoảng
  đó chạm 7–9s.
- **Toast hệ thống** ("Generating, please wait", "2 items deleted"): KHÔNG có trong `uiautomator dump`, `uiautomator
  events` cũng không mang chữ → soi `dumpsys notification` mục "Toast Queue" (có pkg app) liên tục 3s sau khi bấm.
- **Popup đếm ngược là dialog**: lúc nó giữ focus `dumpsys window` có thể không ra tên activity → vẫn coi là ở màn chờ.
  Khung chữ popup / nút OK lấy từ lần nhìn đúng giây `popup_anh_giay` / `popup_video_giay`, dự phòng `popup_hop_*` trong
  công thức app.
- **Quyền thông báo (S01)**: mua lại gói → mở lạnh → app hỏi quyền lần nữa, bộ lái FO bấm Cho phép → tool thu hồi lại
  (pm revoke + cờ user-set) để giữ trạng thái đã từ chối.
- **2 lượt chạy chồng (R05)**: tạo VIDEO trước (≥45s) rồi ảnh — ảnh trước thì xong trước khi kịp mở History.
- **Đếm lượt/ngày**: tạo tới khi app chặn; tổng lần vào màn chờ trong nhóm = limit → mỗi lần trừ đúng 1. Bị chặn vì
  đủ `max_concurrent` (không phải hết lượt) thì chờ một lượt xong rồi thử lại.

## Dòng bỏ khỏi report

`bo_dong` trong `src/rcr/data/gen_ngam_cong_thuc.yaml`: dòng T2I / vùng mô tả / copy prompt với app không có T2I
(user chốt 16/11/2026: bỏ khỏi report, không chấm).
