# rc-check — kỹ thuật đo tay (chi tiết mục 5b bước 3)

Đọc khi: còn dòng `NEEDS_HUMAN` / `NOT_VERIFIABLE` phải tự đo trên máy. Mọi lệnh `adb` kèm `-s <serial>` của lượt.

## An toàn khi thao tác

- **Không gửi phím hay tap nào khi `AdActivity` đang hiện ad thật** — kể cả `input keyevent BACK`: 24/10/2026 (Piclux
  2.4.0) BACK trên inter …588, 2,2s sau log có 2 `ad_click`. Dòng "dismiss ad → sang màn X" đo tay thì: đổi `id_*` vị trí
  đó sang unit test của Google (ad test đóng an toàn), hoặc để tool lái (`fo_flow` chờ hết đếm ngược rồi mới đóng). Muốn
  qua ad thật thì `am force-stop`.
- Chỉ tap khi đã thấy node trong cây UI — tap mù theo tọa độ trúng ad (07/10/2026: mở Chrome).
- Canh giờ theo đồng hồ **máy** (`adb shell 'echo $EPOCHREALTIME'`), không theo máy tính (lệch ~0,8s).
- Luôn ghi `logcat -v epoch` và kiểm dòng fetch Firebase trước khi tin kết quả (fetch thật > ~400ms đè patch).

## Lấy bằng chứng theo loại dòng

- **Màn qua nhanh / bị ad che**: `screenrecord` rồi tách khung. Không có ffmpeg:
  `python -m venv <scratchpad>/fv && <scratchpad>/fv/<bin>/pip install imageio-ffmpeg pillow`. Splash thật thường chỉ
  đứng 1–2s trước "Loading Ads…".
- **Màu / chữ / vị trí**: `screencap -p` (PNG, không lấy màu từ video) + `uiautomator dump`. Màu chữ = pixel không đổi
  giữa hai khung khác nền.
- **Thời điểm, chớp trắng, animation**: timestamp từng khung thật (`-fps_mode passthrough` + `showinfo`), đừng đếm khung
  nội suy.
- **"Cold start lần 2", "kill app"**: `am force-stop` + `am start`, đo **ít nhất 3 lượt**.
- **Màn đứng quá ngắn** (GIF lặp, timeout, animation dài): giữ splash bằng Private DNS hỏng —
  `settings put global private_dns_specifier invalid-dns.example.invalid` + `private_dns_mode hostname`. Máy vẫn báo có
  Wi-Fi nên app không bỏ ads, request treo tới timeout → splash đứng ~18s. Xong **luôn** `settings delete global
  private_dns_mode` + `private_dns_specifier` rồi chờ ping tên miền thông. Ngắt hẳn wifi/data thì KHÔNG được (app bỏ ads,
  splash còn ngắn hơn). GIF lặp: khớp từng khung quay được với khung của file GIF gốc (centerCrop + autocontrast) — chỉ số
  khung tăng rồi rơi về đầu = một lần lặp.
- **Log app trả lời thẳng**: `adb logcat -d | grep <Activity>` (vd `Splash media ready … source=DATA_DISK_CACHE`).
- **"Xem logcat tag X"** (version Lib Ads, Adjust, FB ID…) **là chấm được**: lọc đúng tag, tìm theo **nhãn**
  (`Version Lib Ads`) chứ không theo giá trị kỳ vọng (AIP805: tìm `1.2.9` không thấy, thật ra build là 1.2.10). Tag
  `FOR_TESTER_CONFIG` chỉ in khi bật tester mode: `pm clear` → `pm grant <pkg> android.permission.POST_NOTIFICATIONS` →
  mở app, chờ ~1,5s → bấm `splashAppIcon` 25 lần, có toast "Change to tester ad mode". Tab "các tag check" của sheet TC
  ghi tag nào check gì.
- **Resume / ẩn app**: bấm **Home** rồi mở lại bằng **icon** (`monkey -p <pkg> -c android.intent.category.LAUNCHER 1`),
  không qua Recent. Android 11 không có `topResumedActivity`, đọc `mResumedActivity`.
- **Inter có full màn / lộ nền app không**: `screencap` liên tục ~0,15s/khung từ lúc bấm tới khi inter đứng yên. Dải trắng
  status bar được; thấy màn app phía sau là lỗi.
- **Cursor / mốc 0–4s**: chụp liên tục (~0,4s/khung); `uiautomator dump` ~2,5s/lần quá thô.
- **Precondition đòi máy khác** (OPPO, Samsung…): nhắn qa-auto (trả lời dưới tin build) nhờ cắm máy, máy lên tự chạy tiếp.
  Máy mới chưa có đúng bản build → gỡ app rồi cài lại bản release từ App Tester (`rcr-cai-build`), không pull APK từ máy
  cũ, không dùng nút "Mở"/xoá data. Không có máy → case BLOCKED (mục 5d2).

## Tab rating — cách đo đã chốt (AIP892 2.2.0, 13/11/2026: 3/3 PASS theo TC sửa)

Tool chưa lái được nhóm R01/R02 (bước "Gen ảnh, chờ popup" ra `NEEDS_HUMAN`) → đo tay theo đây, app khác dùng lại.
Bật event FA trước: `setprop debug.firebase.analytics.app <pkg>`, đọc `FA-SVC` "Logging event" trên `logcat -v epoch`;
xong trả `debug.firebase.analytics.app` về giá trị cũ.
- **Thứ tự popup ở Home** (session 2 của old user: force-stop, mở bằng icon, qua Question + Billing rồi mới tới Home):
  so timestamp `widget_view` với `rating_placement_viewed placement_name=home`. TC: Widget → Daily Checkin → Rating,
  popup không đủ điều kiện (Checkin đã làm trong ngày ở session 1) thì bỏ qua. Mỗi lần dump UI chỉ có một popup = không chồng.
- **App Shortcut**: nhấn giữ icon trên launcher → "Rate Us"; `ActivityTaskManager START` ra thẳng `VslRatingActivity`
  (shortcut `vsl_rating_shortcut`, xem `dumpsys shortcut`) + `rating_placement_viewed placement_name=app_shortcut`.
  4 sao → "Rate on Google Play" mở `market://details?id=<pkg>`; BACK từ Play → `START … FoSplashActivity`.
- **Feedback** (Submit mở Gmail soạn sẵn tới `feedback_email`): **không gửi vào hộp thư store** — đổi người nhận về tài
  khoản test trên máy, giữ tiêu đề / nội dung / ảnh, Send, mở Inbox trên máy kiểm mail + ảnh; toast "Feedback sent
  successfully" và app quay về màn result.
- **Bẫy bàn phím**: Gboard đang tiếng Việt Telex thì `input text "test"` thành "tét" (cả địa chỉ email) → bấm nút quả địa
  cầu sang EN trước. Trước khi gửi DEL, dump `focused="true"` để khỏi xoá chữ ở ô khác.
