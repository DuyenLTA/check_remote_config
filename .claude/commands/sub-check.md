---
description: Chạy bộ TC sub chung (IAP & Subscription Android) trên máy thật cho một app — mua gói test, gia hạn, cancel, ads × Premium — rồi xuất report
argument-hint: "<package> [--serial <serial>] [--case <số TC,số TC>] [--version '<x.y.z (n)>']"
---

Chạy bộ TC sub Android (sheet `SUB_Android`, tab `TC Sub Android`, chung mọi app) cho một app trên máy thật. Tham số: $ARGUMENTS

## 0. Repo + lệnh

Tìm `<repo>` như mục 0 của `rc-check.md` (file có `src/rcr/cli_sub.py`). `<bin>` = `<repo>/.venv/Scripts` (Windows)
hoặc `<repo>/.venv/bin`. Mọi bước máy đi qua **`<bin>/rcr-sub`** (đường dẫn tuyệt đối), mỗi lệnh in một dòng JSON;
lỗi in `LOI: …` ra stderr. Lệnh có máy tự giữ khoá `out/.may-<serial>.lock`. Giữa hai lệnh `rcr-sub` dùng `adb -s <serial>`
thường (chụp màn, dump UI, logcat, bấm) — Git Bash: `export MSYS_NO_PATHCONV=1` trước khi gọi adb.

```
<bin>/rcr-sub tc [--chon 1,63]                         # bộ TC theo lịch: so, nhom, kich_ban, precondition, action, expected, can, bat_dau
<bin>/rcr-sub profile --package P [--ghi '<json>']     # profile app
<bin>/rcr-sub paywall|mua|play|cancel|resubscribe|doi-the|cho-het-ky|mo-lanh|may-bay ...   # xem docstring cli_sub.py
<bin>/rcr-sub report --luot <luot.json> --out <file.html>
```

## 1. Luật cứng

- **Mọi máy QA đăng nhập tài khoản License Tester** — mua là giao dịch test, không hỏi user. `rcr-sub mua` tự từ chối
  bấm Subscribe khi popup không có thẻ test; gặp lỗi đó thì **dừng cả lượt** (tài khoản lạ), không tìm cách lách.
- **Chu kỳ gia hạn test đọc từ popup** (`popup.chu_ky_phut`): tài khoản test hiện tại Weekly / Monthly **5 phút**,
  Yearly **30 phút** (user chốt 04/11/2026). Sheet ghi lệch thì theo popup, nêu ở ghi chú, không tính là bug app.
- **Trạng thái billing chỉ cập nhật khi kill app rồi mở lại** (user chốt 04/11/2026): gói hết hạn / bị revoke lúc app ở
  nền, mở lại bằng icon mà app vẫn Premium là **đúng thiết kế, không phải bug**. Case cần thấy trạng thái mới (hết hạn,
  revoke, mua ở máy khác, đổi tài khoản…) thì kill app rồi mở lại (`rcr-sub mo-lanh`) rồi mới chấm. Expected nào đòi
  "cập nhật khi resume, không cần kill" (TC63) → chấm theo luật này, ghi rõ trong `thuc_te`.
- Ẩn app bằng **Home**, mở lại bằng **icon** (`monkey -p <pkg> -c android.intent.category.LAUNCHER 1`), không dùng Recent.
- Quảng cáo: chờ hết đếm ngược rồi mới đóng (nút X của ad), không bấm sớm.
- Không `pm clear` giữa lượt trừ khi case đòi (mất profile trạng thái app). Cài lại app (TC67) thì gỡ rồi cài bản đang test
  bằng `rcr-cai-build --package P --version "<ver>" --loai release --serial S`.
- Hết lượt **phải trả tài khoản về sạch**: gói nào còn Active thì `rcr-sub cancel` (để lượt sau bắt đầu "chưa mua").

## 2. Chuẩn bị

1. `adb devices -l`: máy `<serial>` ở `device`; app đã cài (`pm list packages | grep <pkg>`); versionName/versionCode từ
   `dumpsys package <pkg>`.
2. Tài khoản Google trên máy: `adb -s S shell dumpsys account | grep -o "Account {name=[^,]*, type=com.google}"`.
   ≥ 2 tài khoản → TC đổi tài khoản (`can: tai_khoan_2`) chạy được. Máy khác đang `device`, cùng tài khoản, đã cài app,
   **không bị khoá** (`out/.may-<serial2>.lock`) → TC `can: may_2` chạy được. Thiếu → verdict `CAN_TEST_TAY` kèm lý do.
3. **Profile app** (`rcr-sub profile --package P`). Chưa có → dò một lần rồi ghi:
   - Mở app tới Home: `rcr-sub ve-home --serial S --package P` (lái qua FO, tự đóng popup Home).
   - Tìm đường vào Paywall: nút vương miện / `Premium` / `PRO` / banner "Go Premium"… — thử, dump UI, xác nhận bằng
     `rcr-sub paywall` (đọc ra 3 gói + Continue). Paywall SDK VisionLab là `VslBillingActivity`.
   - Quyền lợi Premium (các dòng tính năng trên Paywall — TC16); màn có ad, mỗi dòng
     `"<màn / activity>: <loại ad> (<đuôi adUnit>)"` lấy từ màn + logcat (TC74/75/76).
   - **Dấu hiệu Premium và đường quản lý sub chỉ thấy được sau khi mua** (vd AIP936: nút `Premium` biến mất, Settings
     mới hiện `Cancel Subscription`). Lúc dò ghi phỏng đoán và liệt kê khoá đó trong `chua_xac_nhan`; ngay sau lần mua
     đầu (TC1) xem lại màn rồi ghi đè + bỏ khoá khỏi `chua_xac_nhan`. App không có mục quản lý sub → `quan_ly_sub: []`,
     quản lý qua `rcr-sub play`.
   - Ghi (gộp vào profile đã có, chỉ thay khoá truyền vào): `rcr-sub profile --package P --ghi '{"duong_vao_paywall":[{"desc":"Premium"}],"dau_hieu_premium":{"an_desc":"Premium"},"quan_ly_sub":[{"desc":"Settings"},{"text":"Cancel Subscription"}],"quyen_loi":["..."],"man_co_ad":["Home: native (…987)"],"chua_xac_nhan":["dau_hieu_premium","quan_ly_sub"],"ghi_chu":"..."}'`
   - Kiểm lại từ trạng thái lạnh: `am force-stop P` rồi `rcr-sub paywall` phải tự tới Paywall.
4. Trạng thái đầu: `rcr-sub play --serial S --package P` (danh sách). Gói app đang Active → cancel + `cho-het-ky` trước
   (TC đầu lịch cần "chưa mua"). `rcr-sub mo-lanh` → `premium: false` mới bắt đầu.

## 3. Chạy theo lịch

`rcr-sub tc [--chon …]` trả case đã xếp theo `bat_dau` (chua_mua → active → da_cancel → het_han → grace → hold).
Ghi tiến độ sau **mỗi case** vào `<repo>/out/sub-<pkg>-<serial>.luot.json`
(`{package, app, version, may, bat_dau, cap_nhat, xong, cases:[{so, nhom, kich_ban, expected, verdict, thuc_te, anh:[...]}]}`).
File cùng package + serial, `xong: false`, `cap_nhat` trong 12 giờ → lượt trước bị ngắt: **chạy tiếp** các case chưa có verdict.

**Gộp quan sát để đỡ chờ** — một lần mua thật trả lời được nhiều TC, ghi verdict riêng cho từng TC:
- Mua Weekly (TC1) cùng lúc chấm TC36 (cấp ngay), TC77 (không App Open khi quay về), TC80 (banner/native ẩn ngay).
- Đang Active: chấm liền 16, 43, 44, 47, 67, 71, 74, 75, 76, 38/40/41 (nếu đủ máy/tài khoản), 61 (upgrade) rồi 62.
- Cancel (28/45) → còn Premium tới hết kỳ → `cho-het-ky` → kill + mở lại → về free: chấm 28, 45, 63 (hết hạn lúc app ở nền),
  82, 60.
- Case "chưa mua" mà **không** hoàn tất mua (52, 90, 91, 8, 78, 6, 73) chạy **trước** lần mua đầu.
- Mỗi lần cần quay lại "chưa mua": cancel + `cho-het-ky` (~1 chu kỳ: 5 phút Weekly/Monthly, **30 phút Yearly**).
  Gói Yearly tốn chờ lâu nhất: gom các case cần Yearly (89, 61, 62) liền nhau và để cuối nhóm. Gia hạn nhiều kỳ (TC23): sub test tự hết sau ~6 lần.

Cách đo:
- **Mua / popup:** `rcr-sub mua --goi weekly|monthly|yearly [--the declines|slow] [--khong-xac-nhan] --anh-dir <repo>/out/sub-anh`
  → `popup` (giá, chu kỳ, thẻ), `log` (`mua` = mã kết quả, `sku_mua`, `ack_loi`, `nha_ads`), `ve_app`, ảnh. So giá popup với giá
  gói trên Paywall (`paywall.goi[].gia`).
- **Premium hay free:** `rcr-sub mo-lanh` (log `verifyPurchased SUBS … size:N`) **và** dấu hiệu UI trong profile **và**
  `rcr-sub play`. Lệch nhau giữa ba nguồn = phát hiện quan trọng, ghi rõ.
- **Đổi trạng thái gói** (hết hạn, revoke, Resubscribe ngoài app…): kill app rồi mở lại (`mo-lanh`) mới đọc được trạng thái
  mới — xem luật ở mục 1. Mở lại bằng icon mà chưa kill thì app giữ trạng thái cũ, không phải bug.
- **Ads:** logcat app (`adb logcat -d --pid=<pid>`): dòng load/show ad, `AdActivity` ở foreground, chữ `Test Ad`/`Ad` trên màn.
- **Không mạng:** `rcr-sub may-bay bat` … `tat` (luôn tắt lại kể cả khi case lỗi).
- Play Store: `play` / `cancel` / `resubscribe` / `doi-the --the declines` (Grace Period: đổi sang thẻ declines trước mốc gia hạn).

## 4. Verdict

`PASS` · `FAIL` · `BLOCKED` (tool/máy hỏng giữa chừng, chạy lại được) · `NEEDS_HUMAN` (không đo chắc được, ghi đã thử gì) ·
`CAN_TEST_TAY` (thiếu máy B / tài khoản 2 / cần người: refund ASO, Play Console chưa bật Grace Period).
- **FAIL chỉ khi đã chạy lại một lần cho ra cùng kết quả** với bằng chứng chắc (ảnh + log + trạng thái Play Store). Một lượt
  xác nhận là đủ, không lặp.
- Expected ghi message kèm mã fallback (`ERR_NET_001 – fallback, thay bằng message theo spec`): app hiện một thông báo
  rõ nghĩa tương đương là PASS; ghi nguyên văn chữ app hiện.
- Expected có `[Inferred — cần confirm với spec]`: chấm theo hành vi hợp lý, ghi rõ trong `thuc_te` là Expected suy đoán.
- Lỗi của tool (parser đọc sai màn, popup đổi giao diện) → tự sửa `src/rcr/sub_*.py` + chạy `pytest tests/test_sub_check.py`
  rồi chạy lại case, không giao user.

## 5. Report + báo lại

`rcr-sub report --luot <luot.json> --out <repo>/out/sub-<pkg>-<serial>-<hhmmss>.html`, publish thành artifact (Artifact tool,
cùng file thì republish đè giữ link), đưa link trong câu trả lời, không tự mở. Báo: app + version + máy, số case theo verdict,
từng FAIL (Expected → thực tế + bằng chứng), case `CAN_TEST_TAY` và thiếu gì, chu kỳ test thật, trạng thái tài khoản cuối.

Có FAIL thì làm như mục 7b của `rc-check.md` (terminal: hỏi user rồi mới log Jira; bot gọi: chỉ đưa vào `bugs`). Mã case trong
marker Jira: `sub#<số TC>`.

**Không `git add` / `commit` / `push`** khi user chưa bảo.
