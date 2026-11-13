# rc-check — bộ IAA (`--tc iaa`): chạy theo nhóm biến thể, tự chấm phần đọc được từ log

Đọc khi: chạy bộ IAA cho app bất kỳ (bot `/check` ô `tinh_nang = iaa`, hoặc `--tc iaa`). Đóng gói 13/11/2026 sau lượt
AIP893 AI Photo Video Slideshow 2.6.0 (9 vị trí × 4 biến thể = 36 case, 35 PASS · 1 FAIL — trước đó Claude lái app 36 lần).

## Bộ case

Tool dựng từ mục **"3. ID ads inapp"** của tab app trong sheet "Check thông số KT" (`tc_iaa_tu_sheet_kt`). Vị trí thứ
`ii` (thứ tự trên sheet) ra 4 case: `IAA-ii-01` bật high + thường (Expected = nguyên văn từng dòng cột Ad description +
dòng ID), `-02` chỉ thường, `-03` chỉ high, `-04` tắt. Tool **không lái được** câu "Đi tới vị trí X đúng như mô tả".

## Quy trình — tool tự lái (4 lượt lái thay vì 36 case)

1. `rcr-check --package P --serial S --tc iaa --case all --no-actions --report out/run-P-S-iaa-<hhmmss>.html --app-label "<tên> <ver>"`
   — dựng case + file lượt + report khung (tool chỉ đặt / trả config từng case, không lái; chưa đo thời gian lượt này).
2. App **đã có đường lái** trong `src/rcr/data/iaa_duong_lai.yaml`:
   ```
   <bin>/rcr-iaa chay --package P --serial S --luot out/run-…luot.json
   ```
   Lần lượt `bat` → `thuong` → `high` → `tat`: đặt config biến thể cho **mọi vị trí** (pm clear), tool **tự lái** đường IAA
   của app vừa ghi `logcat -v epoch -s FA-SVC:V` (`out/iaa-P-<biến thể>.log`), trả config, cuối cùng tự chấm: dòng ID của
   `-01`, cả hai dòng `-02`/`-03`/`-04`. In từng đoạn lái `xong`/`HỎNG` + `con_cham_tay`.
3. Claude chấm tay các dòng mô tả của `-01` từ log lượt `bat` (`out/iaa-P-bat.log`) + ảnh, bằng `rcr-check --cham-tay`
   (mỗi vế câu mô tả một kết luận; không đo được thì không PASS). Đoạn nào `HỎNG` thì đọc lý do, sửa đường lái
   (`rcr-iaa` chạy lại được từng biến thể: `--bien-the-ds bat`).
4. Lệnh lẻ khi cần: `rcr-iaa dat|tra --bien-the …` (đặt / trả config), `rcr-iaa cham --log bat=… --log tat=…`.

Tool chấm "0 request" là PASS **chỉ khi** lượt `bat` (cùng đường lái) có request của vị trí đó — lượt lái chưa tới màn
thì không tính. Log chung cả máy: tool lọc theo ID unit đầy đủ của sheet, app khác chạy song song không lẫn vào.

## Dò đường lái cho app mới (một lần / app, ~20 phút)

Lái tay một lượt theo kịch bản mục 3 (Home → từng tính năng → upload / prompt → Generate → xem ads → loading →
result → về Home → style → luồng uninstall), mỗi màn `uiautomator dump` lấy **chữ** của nút. Khai vào
`iaa_duong_lai.yaml` theo **đoạn** (mỗi đoạn bắt đầu `ve_chu: <chữ chỉ có ở Home>`), loại bước ở đầu `src/rcr/iaa_lai.py`:
- App Compose (mọi màn chung một activity, như AIP893): nhận màn bằng chữ (`ve_chu`, `cho_chu`, `toi_chu`), không bằng
  activity. Màn loading nhận bằng chữ `"<số>%"`.
- Inter hiện trễ 1–2s sau khi bấm → `dong_ad: 6` sau bước bấm; các bước tap/chờ chữ tự đóng ad (cả app open khi quay
  về app) mỗi ~5s.
- Nút có chữ mà uiautomator trả bounds rỗng (AIP893 `Watch Ads (0/2)` ở đáy sheet) → `tap_tai: [0.5, 0.935]`.
- Ô nhập prompt → `nhap: "<chữ>"` + `o: "<chữ gợi ý trong ô>"` (vị trí ô đổi sau khi upload ảnh, đừng tap toạ độ).
- Luồng uninstall mở bằng shortcut launcher **theo id** (`dumpsys shortcut`, vd `uninstall`): activity không export
  nên `am start` bị chặn; nhãn trên máy tiếng Việt là "Gỡ cài đặt" — trùng chữ lệnh gỡ của launcher, tool chọn theo
  id và gặp trình gỡ hệ thống thì BACK huỷ. `app:` = regex tên icon (lấy `aapt dump badging … application-label`).
- Hết lượt gen free trong ngày (`dung_neu`) → đoạn reward/loading/result dừng; **không mua sub** (app Pro = mất ads),
  chờ hôm sau hoặc máy khác.

## Ép fail (dòng "load fail thì …", `*_fail_time`)

- Private DNS `dns.adguard-dns.com` chặn domain quảng cáo, Firebase / API vẫn chạy (lỗi errorCode 0). Đổi wifi để bỏ
  cache DNS; xong **luôn** `settings delete global private_dns_mode` + `private_dns_specifier`, chờ ping thông.
  "Máy test luôn fill" không phải lý do BLOCKED.
- **`*_fail_time=N` đếm số lần load fail từ lần fail đầu tiên** (preload fail cũng tính); fail đủ N lần thì không reload
  nữa. `=3` → 3 lần fail rồi hết request của vị trí là PASS (QA chốt 13/11, `luat-qa-da-chot.md`). Đếm theo vòng: bấm vị
  trí (fail → đi tiếp) → về Home → load lại. Chấm: `iaa_cham_log.cham_fail_time(su_kien(log, units), i, n)`.
- "Chỉ show 1 ad/session": session mới = mở lại app qua splash (force-stop + mở icon).

## Bẫy đã gặp (đừng kẹt lại)

- **Máy đang bị lượt khác dùng**: trước khi lái, `ps -eo pid,etime,args | grep "rcr-check.*<serial>"` và hàng chờ bot
  (`out/bot-hang-doi.json`). Đừng `pgrep -f` trong vòng chờ — nó đếm cả chính lệnh chờ, không bao giờ thoát.
- **App thành Pro sau lượt check policy / mua sub test** (`PurchaseEG: verifyPurchased SUBS: true` trong log app): app
  không request ad nào. Chờ sub test hết hạn (~30 phút; kiểm `SUBS … size:0`) rồi mới lái.
- **Máy vivo chặn log riêng của app lúc có lúc không** — chấm bằng FA-SVC (process gms, luôn có), không bằng tag app.
- **Popup "AdMob native ad validator"** (ad test) che nút của app: bấm Dismiss / bấm phần nút lộ ra ngoài popup; bấm
  nhầm mở trang validator trong AdActivity → đóng bằng `custom-close` (góc trên trái).
- **App khác bật quảng cáo đè** (Zing MP3 WelcomeAdActivity…): force-stop app đó, mở lại app đang test; chỉ tap khi
  activity trên cùng đúng package đang test.
- **Đóng inter/reward thật**: chờ hết đếm ngược, tap `dismiss-button` / `close-button` (`clickable=false` vẫn tap được);
  không BACK khi AdActivity đang hiện ad thật.
- Banner không ghi `ad_load failed` cho tầng high — tool chấm thứ tự theo chu kỳ (request high gần nhất, high không fill
  rồi mới gọi thường), không đòi dòng fail.
