# Nhánh `/rc-check` cho app SDK FO 3.7.0 / 3.7.1: chấm checklist SDK Next-Gen

Vào đây từ `.claude/commands/rc-check.md` mục 0b — `--preflight` đọc được app dùng **SDK FO 3.7.0 / 3.7.1** (bộ TC không có
bản này). Tham số: package, mục cần chấm (`1|2|3|4|all`, mặc định `all`), có thể kèm checklist dán vào. Bản SDK ghi
lên header report lấy từ dòng `Bản SDK FO` của preflight.

`$SK` = `<repo>/sdk-check` (repo tìm như `rc-check.md` mục 0). Trong đó:
- `references/checklist-muc1-sdk-build.txt`, `checklist-muc2-hien-thi-HT.txt`, `checklist-muc3-event-EV.txt`,
  `checklist-muc4-nextgen-KT-MED-CMP-EV3x-HV-RG.txt` — checklist gốc. User dán checklist mới thì **dùng bản user dán**.
- `references/how-to-measure-each-case.md` — đo bằng gì, chấm thế nào, bẫy đã gặp. **Đọc trước khi chạy.**
- `scripts/` — lái app, proxy mạng chậm, parse log. `assets/` — khung + mẫu report.

Python: `python3` trên Linux/macOS, **`python` trên Windows** (`python3` ở Windows là lối tắt Microsoft Store,
không chạy). Script `.sh` tự chọn đúng và tắt đổi đường dẫn của Git Bash (`MSYS_NO_PATHCONV=1`).

## Luật chấm (user chốt — không ngoại lệ)

1. Chỉ **Khớp** hoặc **Sai**. Không "Chưa test", "Không xác định", "Blocked". Lái hụt thì tự lái lại tới khi ra kết quả.
2. **Chỉ chấm Sai bug dev sửa được bằng code** (app, lib ads, SDK). Cấu hình tài khoản AdMob (form UMP…), quyết định PO
   (minSdk app, có nhắm EEA…), giới hạn SDK Google/server → mục "Ngoài phạm vi / không áp dụng", không viết "PO xác nhận".
3. minSdk: chấm theo **lib ads + SDK tutorial**, minSdk app kệ.
4. Phạm vi mặc định: **luồng tutorial** (splash, Language, onboarding, Question, paywall, app open khi quay lại). Case chỉ có
   in-app (rewarded chat, native danh sách, banner Home…) → mục ngoài phạm vi, trừ khi user bảo check in-app.
5. Case cần đổi Remote Config: app **debuggable** (`aapt2 dump badging <apk> | grep application-debuggable`) → đổi bằng
   `rcr-check --set key=value --keep` rồi `--restore` (xem `rc-check.md`), **không** đưa vào mục "Cần bản debuggable".
   Bản release mới tìm đường khác (đọc manifest, đọc RC qua `fetch_remote_config.py`, bản cũ để so); hết cách thật thì
   đưa vào mục riêng không tính và nói rõ cần gì.
6. Sai chỉ cần **một lượt** có bằng chứng chắc (đúng điều kiện, log cùng lượt) — không lặp lượt để "xác nhận Sai"
   (user chốt 24/10/2026: lặp chỉ tốn thời gian). Case "so bản cũ" vẫn phải đo bản cũ cùng điều kiện.
7. **Không git add / commit / push** trong lúc chấm (user bảo thì push cả hai tài khoản).
   Script lái sai / parse log hụt trên app mới → tự sửa script trong `$SK/scripts/` rồi chạy lại case đó
   (như `rc-check.md` mục 5e), không giao lại user; ghi phần đã sửa trong câu báo.
8. Hộp xin quyền: tự Allow; sau `pm clear` chạy `pm grant <pkg> android.permission.POST_NOTIFICATIONS`.
9. Không chạm/bấm quảng cáo ngoài thao tác case đòi (để log sạch); bấm CTA chỉ làm ở case cần (HT-03, HV-01, EV-07…)
   và ghi rõ trong report.
10. **Mọi máy QA đều là máy test AdMob** (user chốt 29/10/2026, xem `rc-check.md` mục 0c): được bấm quảng cáo để đo —
   kể cả bản release dùng ID thật (EV-07, EV-26, EV-27, HT-03, HV-01), mở Ad Inspector (MED-02); `ad_click` trong lượt
   **không** dừng lượt: ghi vào report rồi chạy tiếp.
11. **Chạy hết, đo tay hết**: báo xong khi report không còn `Đo tay` — mọi dòng `DO_TAY` đo rồi ghi `--cham-tay` ra
   Khớp/Sai. Lượt AIP918 2.4.0 (29/10/2026) dừng ở "còn 20 dòng đo tay" là sai quy trình. Dòng thật sự không đo được
   (cần dev chỉ màn / nút, cần mua sub mà máy không có tài khoản test) thì vẫn thử hết cách, rồi ghi rõ đã thử gì và
   cần đúng thứ gì — không để trống.

## Chạy bằng script, KHÔNG tự chấm

User chốt 24/10/2026: kết quả phải giống nhau mỗi lần chạy. Cả 4 mục chấm bằng code:

```
<bin>/rcr-sdk-check --package <pkg> --serial <serial> --muc 1,2,3,4 --sdk <bản từ preflight> --app-label "<tên> <version>"
```

Luôn truyền `--serial` (cùng serial với preflight): cắm từ 2 máy trở lên thì thiếu nó là dừng ngay, và 2 lượt
song song trên 2 máy không được đụng máy của nhau.

~12 phút, `run_in_background`. Thu log vào `out/sdk-<pkg>-<giờ>/`: 10 lần mở lạnh, 10 lần mở lại, FO user mới +
Home → mở lại ×2, lượt mất mạng (30s rồi bật mạng đi tiếp), lượt mạng chậm qua proxy (luôn gỡ proxy khi xong). Chấm bằng
luật cố định, ra `ket-qua.json` + `report.html`. stdout: `{thu_muc, report, dem}`.

10 lần mở lạnh **không có event quảng cáo nào** (Remote Config đang tắt ads) → tool tự **bỏ lượt FO** (đỡ ~1,7 phút),
`bang-chung.json` có `fo_bo_qua`; các dòng dựa vào FO ra `DO_TAY` kèm lý do đó. Báo user: cần PO bật ads trên RC hoặc
bản debug (để tool bật ads) rồi chạy lại — không phải bug dev.

- Dòng `KHOP` / `SAI` / `KHONG_AP_DUNG` do code chấm: **không sửa tay, không chấm lại theo cảm nhận**. Nghi luật sai →
  sửa luật trong `src/rcr/sdk_nextgen_cham_*.py` + thêm test bằng chính log đó (mục 5e của `rc-check.md`), rồi
  `rcr-sdk-check --cham-lai <thu_muc>` — cùng log thì cùng kết quả; dòng đã đo tay được giữ nguyên.
- Chỉ dòng `DO_TAY` mới đo tay (bấm quảng cáo test, nhìn native/banner, Ad Inspector, mua sub, bản release…), đo xong ghi:
  `rcr-sdk-check --cham-tay <thu_muc> --ma EV-07 --ket KHOP|SAI --ly-do "<số đo / cách đo>"`. Report còn `Đo tay` = chưa xong.
- Code không chắc thì ra `DO_TAY`, không đoán: lượt lái FO lỗi → mọi `SAI` dựa trên log đó thành `DO_TAY`; tắt mạng mà
  máy vẫn ra internet → dòng mất mạng thành `DO_TAY`.
- Footer report có `ad_click` từng lượt: ghi vào report, chạy tiếp và đo tay hết (mọi máy là máy test — luật 10).

Đo tay theo cách đo + bẫy ở `references/how-to-measure-each-case.md` và quy trình dưới.

## Quy trình đo tay

1. **Máy + bản**: `adb devices -l`. Cắm nhiều máy thì `export ANDROID_SERIAL=<serial>` trước mọi lệnh `adb` /
   script dưới đây (script gọi `adb` trơn) — không đặt là `adb` báo "more than one device" hoặc đụng máy của lượt khác. `dumpsys package <pkg> | grep -E "versionName|versionCode|lastUpdateTime"`,
   `sha256sum` APK (`adb pull $(pm path)` vào scratchpad, dùng lại cho cài đè). Máy khoá thì mở khoá trước. Kiểm sub
   test còn hạn (xem bẫy). Kiểm cờ debuggable (luật 5).
2. **Bản cũ để so** — mặc định BỎ (user chốt 15/10): CMP-01/02/03, KT-07, HV-06, EV-27 ghi "bỏ theo yêu cầu"; KT-02 chấm
   theo timeout RC, MED-01 theo adapter bản mới. Chỉ dùng bản cũ khi user đưa APK cùng key:
   `~/.cache/ad-checklist-diff/<pkg>-<versionCode>.apk`; kiểm `unzip -l | grep play-services-ads.properties` (= SDK cũ).
3. **Log**: `setprop debug.firebase.analytics.app <pkg>`, `log.tag.FA`/`FA-SVC VERBOSE`; mỗi lượt một file
   `adb logcat -v threadtime > <scratchpad>/log-X.txt &` + file marks ghi mốc thao tác.
4. **Lái app** bằng `bash $SK/scripts/<tên>.sh` (đều nhận package làm tham số):
   - `ui-dump.sh` — liệt kê node + toạ độ; `tap-by-id.sh '<regex id/text>'`
   - `cold-start-new-user.sh <pkg> <marks>` — pm clear + mở + chờ qua splash
   - `drive-fo-to-home.sh <pkg> <marks> [noclear]` — đi hết FO tới Home, đóng ads (nút theo resource-id VslTemplate4)
   - `continue-fo-from-current-screen.sh <marks> [stop-regex]` — đi tiếp FO từ màn đang mở
   - `splash-inter-display-cases.sh <pkg> <out>` — HT-03/HV-01/HV-02/HT-05/HT-04 trên inter splash (user cũ)
   - `hunt-fullscreen-native-onboarding.sh <pkg> <out> [n]` — chạy user mới tới khi OB toàn màn có fill (HT-09)
   - `slow_ads_proxy.py PORT DELAY KBPS [HOST_REGEX]` — mạng chậm (docstring có lệnh nối/gỡ proxy)
5. **Phân tích**: `parse_fa_events.py` + `summarize_ad_events.py` (EV), `compare_ad_requests.py old new` (CMP-01/02),
   `launch_stage_timing.py logs…` (CMP-03, KT-02), `fetch_remote_config.py <apk> out.json` (RC thật của bản release).
6. **RG-01** (bộ TC SDK theo version): có bộ TC thì chạy nhánh testcase của `rc-check.md` (`--tc <bộ TC> --sdk <X.Y.Z>`), lấy
   PASS/FAIL của report đó làm Khớp/Sai cho RG-01 (link report rc-check ghi trong case); không có bộ TC thì RG-01 vào mục
   "Ngoài phạm vi / không áp dụng" kèm lý do "bản SDK này không có bộ TC".
7. Mỗi vòng nói 1 dòng đang ở case nào / màn nào.

## Report

- HTML artifact, một report mỗi lần user gửi một mục (hoặc gộp nếu user bảo). Khung:
  `$SK/assets/report-style-and-filter-script.html` (style + script lọc), mẫu đầy đủ: `$SK/assets/example-report-lingospeak.html`.
- Bố cục: header (package, bản + sha, bản SDK, máy, giờ chạy, phạm vi) → 4 thẻ lọc (Tất cả / Khớp / Sai / Sai mới — không phải lỗi
  có sẵn ở bản cũ) → khối **Cần báo dev** (chỉ bug dev) → danh sách `<details data-v="pass|fail" [data-new="1"]>` gập theo
  nhóm, mỗi case có dòng log bằng chứng **cùng lượt** với kết luận → mục "Ngoài phạm vi / không áp dụng" → mục "Cần bản
  debuggable" nếu có → footer liệt kê lượt chạy + trạng thái máy để lại.
- Viết tiếng Việt, ngắn, có số đo thật. Không có mục ảnh chụp.
- Publish bằng Artifact (icon `checklist`) rồi **chỉ đưa link, không tự mở trang**. Chạy lại case → cập nhật đúng file/URL
  cũ (thêm khối "Lượt n" trong case, sửa thẻ đếm).
- Trả lời user: link (riêng tư, bật Share nếu cần), số Khớp/Sai, từng Sai là gì, case không tính và vì sao, trạng thái máy
  (proxy đã gỡ, RC đã restore, sub test, bản đang cài).

## Log bug lên Jira (lượt có người trong terminal)

Dòng `SAI` đã rà xong, user chọn log → skill `anthropic-skills:jira-log-bug`, mỗi dòng một issue, kèm **label `auto-qa`** và
**một dòng marker riêng ở cuối description** (bot Discord dựa vào đó để tự verify lại khi dev chuyển Reviewing):
`AUTOQA case=<mã dòng, vd EV-07> ban=<debug|release> pkg=<package>`. Mã dòng đúng như cột mã trong checklist
(`EV-07`, `HT-03`, `KT-02`, `MED-02`, `HV-01`, `1.7`); `ban` = loại bản đang cài trên máy test. Không thêm ký tự định dạng
quanh dòng marker, không đổi chữ.
