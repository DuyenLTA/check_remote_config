# Remote Config Case Runner

Đổi giá trị **Firebase Remote Config** của app Android **từ file testcase** — không cần
quyền admin Firebase, không đụng server thật, chỉ ảnh hưởng đúng một máy đang cắm.

> **Trạng thái: phase 3/6.** Hiện **nạp được file testcase, bóc ra key/value cần đặt, đặt
> giá trị và xác nhận nó sống qua lần mở app**. Phần tự thao tác trên app và chấm PASS/FAIL
> ở các phase sau.

## Cần gì trước khi chạy

1. **Python 3.12+** (`python3 --version`)
2. **adb** — cài Android platform-tools. Không nằm trong PATH thì:
   ```bash
   export ADB_PATH=$HOME/Android/Sdk/platform-tools/adb
   ```
3. **Điện thoại Android** bật *USB debugging*, cắm cáp, bấm **Allow** trên máy.
   Kiểm tra: `adb devices` phải hiện `device` (không phải `unauthorized`).
4. **App phải vào được vùng dữ liệu riêng của nó** — một trong hai:
   - app là **bản build bật `debuggable`** (dùng `run-as`), hoặc
   - **máy đã root** (dùng `su`) — đường này bản **release** cũng patch được.

### Kiểm APK trước khi cài — khỏi gỡ app xong mới biết sai bản

```bash
$HOME/Android/Sdk/build-tools/37.0.0/aapt dump badging <file.apk> | grep application-debuggable
```

| Kết quả | Nghĩa |
|---|---|
| in ra `application-debuggable` | ✅ dùng được |
| không in gì | ❌ không dùng được, **dù tải ở đâu** |

`debuggable` là cờ **nung sẵn trong APK lúc build** — tải lại bản khác ở nguồn khác không
giải quyết được. Cần xin dev bản bật cờ đó (trong `build.gradle`: `buildTypes { ... debuggable true }`).

Hỏi dev thêm: bản đó dùng **chung Firebase project với production hay project riêng**?
Nếu riêng thì danh sách key remote config sẽ khác.

**Cài bản debuggable dễ vấp 3 chỗ:** khác chữ ký ký APK → phải gỡ bản cũ, **mất sạch data app**;
có thể trỏ Firebase project khác → key khác; package có thể có hậu tố (`...aiart.debug`) →
thành app riêng, cài song song được.

## Chạy

```bash
./start.sh                    # http://127.0.0.1:8000
PORT=9000 ./start.sh          # đổi cổng
RCR_NO_BROWSER=1 ./start.sh   # không tự mở browser
```

Lần đầu ~30 giây (tự tạo venv + cài thư viện). Các lần sau ~1 giây. Cổng bận thì tự nhảy
cổng trống kế tiếp.

Chỉ bind `127.0.0.1`. Tool **không có auth** mà điều khiển được adb → không được expose ra
LAN. Có middleware chặn thêm trong code, không phụ thuộc cách khởi động.

## Dùng

1. Chọn **Device** → **App** → bấm **Đọc baseline**.
2. Đọc bảng baseline:

| Dòng | Nghĩa |
|---|---|
| **Số key remote config** | tổng key app đang có trong cache Firebase RC |
| **Key bị mirror** | key mà SDK Apero còn giữ **bản sao** ở prefs riêng — patch phải ghi cả 2 chỗ |
| **File mirror (sẽ patch)** | file prefs có key trùng tên với remote config |
| **File `vsl_*` bỏ qua** | file `vsl_*` **không** phải mirror — là **state nội bộ app**, tuyệt đối không ghi vào |
| **Đường ghi** | `run-as` (app debuggable) hoặc `su` (máy root) |

3. Ô **Tìm key** để đối chiếu tên key trong file testcase với key thật trên máy.
4. Chọn **file testcase** (`.xlsx`) → **Nạp file testcase**. Bảng hiện từng case kèm key/value
   tool sẽ đặt, và case nào cần làm tay **kèm lý do**.

### Bảng case đọc thế nào

| Cột | Nghĩa |
|---|---|
| **Key sẽ đặt** | cặp key/value bóc từ cột `Test Data`, đã lọc bằng key thật của app |
| **bỏ qua: ...** | key có trong `Test Data` nhưng **không** thuộc remote config — thường là param analytics (`click_area`, `source`, `category`) |
| **cần người** | tool không tự chạy case này, kèm lý do cụ thể |

Bốn lý do `cần người`, đều là **cố tình không đoán**:

| Lý do | Ví dụ trong file thật |
|---|---|
| runtime toggle | `enable_feature_aialbum: true → false → true` — app phải tự fetch lúc đang chạy, patch file + mở lại không tái hiện được |
| sửa field trong JSON | `restore.enable = false` — câu không nêu key gốc, suy ra là đoán |
| giá trị còn là chỗ trống | `template_id = <id template đang test>` — patch vào là ghi nguyên chuỗi mô tả vào config |
| không key nào thuộc RC | `source = navigation` — param analytics, không phải remote config |

Tool **đọc duy nhất cột `Test Data`**, không tự bóc key từ `Precondition`: cột đó là văn xuôi,
bóc ra dễ sai.

## Chạy một lượt không cần web UI (`rcr-check`)

Dùng cho slash command `/rc-check`, hoặc gõ tay. stdout là **đúng một dòng JSON**,
tiến độ ra stderr.

```bash
.venv/bin/rcr-check --package <pkg>                          # doc baseline
.venv/bin/rcr-check --package <pkg> --tc BO_TC.xlsx          # bang case + so luot
.venv/bin/rcr-check --package <pkg> --tc BO_TC.xlsx --tab 3.4.0 \
     --case 3.4.0#1,3.4.0#3 --report out/run.html
.venv/bin/rcr-check --package <pkg> --set splash_banner_change=false
.venv/bin/rcr-check --package <pkg> --keep      # giu patch de tu mo app xem
.venv/bin/rcr-check --package <pkg> --restore   # tra ve ban da luu o luot --keep
```

**`--tab 3.4.0` chỉ chạy đúng tab đó**, không kéo theo base và các delta khác — nêu
đích danh một bản SDK thì chỉ phần đó là cần, chạy thừa là ngồi chờ máy thật cho không.

`--case` nhận nhiều case ngăn bằng dấu phẩy, và `--report out/run.html` xuất trang HTML
tự chứa: **ảnh chụp từng bước**, từng dòng Expected kèm tool đo được gì, log quảng cáo,
nút lọc theo verdict và mục lục nhảy tới từng case.

Case trong workbook bộ chung định danh bằng **`<bản SDK>#<số>`** (`--case 6.4.0#1`):
số case trùng nhau giữa các tab — số `1` có ở 5 tab. Gõ mỗi con số vẫn được nếu nó chỉ
có ở một tab; mơ hồ thì tool dừng và liệt kê.

Workbook **bộ chung nhiều tab** `TC SDK <version>` thì tool lấy base + mọi delta ≤
bản SDK của app. Bản SDK **tự đo từ logcat** (`VslTemplate4FirstOpenSDK: Using
version X`) — đọc buffer sẵn có trước, không có thì mở lại app rồi đọc. Biết sẵn
thì truyền `--sdk 3.2.0` để khỏi đo. Đo được rồi thì không đoán: lấy nhầm tab là
chấm bằng TC của bản khác mà không ai biết. File một sheet thì đọc thẳng.

Bản SDK **không suy ra được từ versionName của app**: Piclux 2.8.0 đang nhúng FO
SDK 3.5.4-alpha02 — hai con số không liên quan. Tool đọc log của **đúng PID app đích**:
tag `VslTemplate4FirstOpenSDK` mọi app nhúng SDK đều in, mà logcat thì chung cả máy —
đọc cả buffer là nhặt bản SDK của app khác (đã vấp).

Case có giá trị lựa chọn (`layout1/2/3`) chạy **nhiều lượt** — mỗi giá trị một
lượt mở app. Verdict của case = lượt xấu nhất.

Case có Precondition kiểu "chưa từng mở app / fresh install" thì tool **đặt lại
trạng thái trước khi patch** (`pm clear` xoá luôn file vừa ghi, nên reset phải đi
trước). Ba mức: mặc định chỉ `force-stop`; cần state sạch thì **lật cờ
`ARG_KEY_SHOW_ONBOARDING`** — app vào lại luồng first-open mà giữ nguyên
login/ngôn ngữ/data; app không có cờ đó mới dùng `pm clear`, và sau đó chờ app tự
sinh lại `frc_*.json` rồi mới patch. Luật nhận Precondition để ở
`src/rcr/data/reset_rules.yaml`. Đường `--set` không có Precondition để đọc, muốn
ép state sạch thì thêm `--fresh`.

Trước khi patch, tool **soi chuỗi key trong `classes*.dex`** của mọi APK (base +
split). Key không có trong DEX → app không đọc key đó → `KEY_NOT_USED`, không tốn
một lượt mở app. Đo thật trên Piclux: `enable_101_spl_a_banner` có trong remote
config mà **code không tham chiếu** — chấm tiếp là ra PASS giả. Kết quả cache theo
`(package, versionCode)`; `--no-dex-check` để bỏ bước này.

Config đặt xong và verify xong thì tool **lái app qua các bước Action của case**:
`Quan sát…` → không thao tác, `Nhấn nút "X"` / `Mở tab X` → tap, `Chờ N giây` → chờ.
Câu khác, hoặc **nhiều hơn một node cùng khớp**, hoặc không node nào khớp → dừng kèm lý
do, **không tap bừa**: một cú tap sai chỗ trên máy thật là bấm vào quảng cáo hoặc mua
hàng thật. Quảng cáo đang che màn hình cũng dừng — tool không tự tìm nút đóng. `--no-actions`
để chỉ đặt config, không lái.

Case có dòng Expected thì tool **chấm từng dòng** (`run.runs[i].assert`): `PASS` /
`FAIL` (kèm actual) / `BLOCKED_NO_FILL` (ad có request nhưng kho không trả ad — không phải
app sai) / `NOT_VERIFIABLE` (dòng tool không đo được, người nhìn) / `NEEDS_HUMAN`.
Verdict case = dòng xấu nhất. Case ads chấm ở **tầng request/load**, không đòi nhìn thấy ad:
inter load nhanh hơn banner nên nó đè lên trước khi kịp nhìn.

Case không có Expected thì verdict dừng ở `CONFIG_OK` / `BLOCKED` / `KEY_NOT_USED` —
tool đặt được config nhưng không tự kết luận gì về app.

Mặc định tool trả config về nguyên trạng ngay sau khi verify. `--keep` thì giữ
patch **và lưu snapshot config gốc** ra `out/` — đó là đường về duy nhất: lượt
sau đọc baseline sẽ ra bản đã patch, lúc đó không còn biết giá trị thật nữa.

### Đặt giá trị (API — nút trên UI làm ở phase 6)

```bash
S=<serial>; P=<package>
curl -s -X POST "http://127.0.0.1:8000/api/baseline?serial=$S&package=$P"
curl -s -X POST "http://127.0.0.1:8000/api/patch?serial=$S&package=$P" \
     -H 'content-type: application/json' \
     -d '{"splash_banner_change":"false","show_105_spl_n_native":"false"}'
# -> tat HAN app roi mo lai, sau do:
curl -s -X POST "http://127.0.0.1:8000/api/verify?serial=$S&package=$P" \
     -H 'content-type: application/json' \
     -d '{"splash_banner_change":"false","show_105_spl_n_native":"false"}'
curl -s -X POST "http://127.0.0.1:8000/api/restore?serial=$S&package=$P"
```

| Endpoint | Việc |
|---|---|
| `POST /api/patch` | ghi giá trị: mirror → settings → `activate.json` (**sau cùng**) |
| `POST /api/verify` | đọc lại sau khi mở app. Lệch → `verdict_hint: BLOCKED` |
| `POST /api/restore` | trả nguyên trạng + **mốc fetch cũ** → app tự lấy lại config thật |
| `POST /api/testcases` | upload `.xlsx` → bảng case + key/value đã bóc |

**`verify` lệch nghĩa là `BLOCKED`, không phải `FAIL`.** Hai kết luận khác hẳn nhau:
`FAIL` = app chạy sai so với expected; `BLOCKED` = chưa test được vì config không được giữ
(thường do build dev đặt `minimumFetchInterval = 0` nên throttle vô hiệu). Không phân biệt là
đẩy tester đi tìm bug không tồn tại.

## Cơ chế

Firebase RC SDK ghi cùng một chỗ, cùng một tên, ở **mọi app**:

```
files/frc_<appId>_firebase_activate.json        <- gia tri (moi value la string)
shared_prefs/frc_<appId>_firebase_settings.xml  <- moc throttle fetch
```

Đã kiểm chứng trên 2 máy / 2 bản Android / 5 app / 2 Firebase project.

**Hai chỗ phải hiểu, nếu không sẽ mất công tìm bug không tồn tại:**

1. **Patch mà không set `last_fetch_time_in_millis` = now thì app fetch đè mất patch.**
   Throttle 12h của SDK chính là đòn bẩy — đúng cái trước đây buộc tester phải clear cache.
   Không cắt mạng để chặn fetch: app under test cần mạng cho ads/API/analytics.

2. **Nhận mirror bằng giao tên key, không theo tên file.** Không phải file `vsl_*` nào cũng
   là mirror: `vsl_template4_prefs.xml` (chứa `ARG_KEY_SHOW_ONBOARDING`…) là state nội bộ app.
   Tên file không đáng tin — `vsl_rating_remote_prefs.xml` có chữ `remote` mà chỉ vài key là RC.

**Clear cache không còn cần** để lấy config mới (trước đây phải clear vì throttle giữ cache cũ).
Giờ chỉ clear khi test case đòi reset trạng thái app — và phải clear **trước** rồi mới patch,
vì `pm clear` xoá luôn file vừa ghi.

## Spec SDK (Confluence)

```bash
source <(grep '^export CONFLUENCE' ~/.bashrc)   # CONFLUENCE_BASE_URL + CONFLUENCE_TOKEN (PAT)
PYTHONPATH=src .venv/bin/python -m rcr.spec_sync          # tai trang moi / doi version
PYTHONPATH=src .venv/bin/python -m rcr.spec_sync --check  # chi xem, khong tai
```

Tải 6.4.0 + mọi `visionlab:tutorial` ≥ 3.0.1 về `src/rcr/data/specs/` (gitignore — tài liệu nội bộ).
Luật rút ra nằm ở `src/rcr/data/sdk_rules.yaml`, mỗi luật ghi `nguon` = pageId spec.

## Test

```bash
.venv/bin/python -m pytest          # khong can cam may
.venv/bin/python -m pytest -m device  # test can device that
```

Suite dùng `FakeAdb` với nội dung file **thật** đọc từ máy, nên gác đúng schema thật.
