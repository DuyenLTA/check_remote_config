# Remote Config Case Runner

Đổi giá trị **Firebase Remote Config** của app Android **từ file testcase** — không cần
quyền admin Firebase, không đụng server thật, chỉ ảnh hưởng đúng một máy đang cắm.

> **Trạng thái: phase 6/6, chạy được đầu-cuối bằng dòng lệnh.** Nạp file testcase → bóc
> key/value → đặt giá trị → xác nhận nó sống qua lần mở app → lái app tới màn cần chấm →
> chấm từng dòng Expected → xuất report HTML tự chứa (`rcr-check --report`).
> **Còn thiếu:** nút chạy case trên web UI — hiện phải gõ `rcr-check` hoặc dùng slash
> command `/rc-check`.

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

**Windows:** chạy `./start.sh` trong Git Bash, script tự nhận ra Windows. Venv nằm ở
`.venv/Scripts` thay vì `.venv/bin`. Muốn cài tay, không qua `start.sh`:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e .
.venv/Scripts/rcr-check --help
```

Sheet ID ads từng vị trí ("Check thông số KT") mặc định là sheet của team QA. Team khác
dùng sheet cùng khuôn thì đặt `RC_AD_UNITS_SHEET=<link sheet>`, không cần sửa code. Bộ TC
thì truyền bằng `--tc <link sheet>` như thường.

### Cài lệnh `/rc-check` cho Claude Code (mỗi máy một lần)

Claude Code chỉ đọc lệnh trong `~/.claude/commands/`. Tạo file
`~/.claude/commands/rc-check.md` là một file trỏ về repo: nội dung chỉ bảo Claude tìm repo
theo thứ tự `git rev-parse --show-toplevel` → `$RC_RUNNER_REPO` →
`~/projects/check_remote_config` → `~/Desktop/check_remote_config` → `~/check_remote_config`, rồi đọc
`<repo>/.claude/commands/rc-check.md`. Clone repo về chỗ khác thì đặt biến
`RC_RUNNER_REPO=<đường dẫn repo>`. Không chép nguyên file lệnh sang: hai bản sẽ lệch nhau sau
mỗi lần `git pull`. Lệnh mới chỉ hiện ở phiên Claude Code mở sau đó.

Cùng lệnh `/rc-check` còn **tự chấm checklist nâng cấp SDK quảng cáo Next-Gen** khi app dùng SDK FO
**đúng 3.7.0** (bản này không có bộ TC; 3.6.1 đã revert next-gen nên chạy bộ TC): `--preflight` đọc bản SDK từ log lúc mở app rồi chọn nhánh, không cần
gõ gì thêm. Quy trình ở `sdk-check/WORKFLOW.md`; script, checklist gốc và cách đo nằm trong `sdk-check/`.
Cả 4 mục chấm bằng code: `rcr-sdk-check --package <pkg> --muc 1,2,3,4` — cùng bộ log thì cùng kết quả
(`--cham-lai <thư mục>`); dòng code không chấm chắc được ra `DO_TAY`, đo tay rồi ghi bằng `--cham-tay`.

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
tự chứa, bày đúng khuôn **bảng test case** của tester:

| Case | Description case | Preconditions | Step | Expected Result | Actual Result | Status Test |
|---|---|---|---|---|---|---|

Cột **Step** ghi từng bước Action kèm nhãn tool làm được gì (`tap` / `wait` / `goto` /
`needs_human`) — nhìn là biết case chết ở bước nào. Cột **Expected** và cột **Actual**
đánh số **song song**: dòng thứ i của Actual là kết quả của dòng thứ i của Expected, nên
so sánh bằng mắt chứ không phải tự ghép. Case sai còn có hộp **Lý do fail** gom lý do các
dòng trượt. **Ảnh chụp từng bước** và bảng log quảng cáo nằm trong ô Actual; bấm ảnh là
phóng to tại chỗ (ảnh chỉ nhúng một lần — nhúng hai lần là nhân đôi dung lượng trang).

Trang gom nhóm theo **tính năng** (cột Feature của file TC), có ô đếm bấm được để lọc,
dropdown trạng thái và ô tìm. Mỗi hàng mang `id="c-<mã case>"` để dán link nhảy thẳng tới
một case khi log bug.

### Kiểm trước khi chạy — `--preflight`

```bash
.venv/bin/rcr-check --package com.example.app --preflight
```

Vài giây, in bảng `OK` / `LOI` / `CHU Y`: máy, màn hình không khoá, app đã cài, vào được dữ
liệu app (bản debuggable hoặc root), tải được sheet TC, sheet ID ads có tab của app, RAM
trống của máy tính (< 4 GB thì cảnh báo). Có dòng `LOI` thì exit 1 kèm việc cần làm.
`chay-khong-claude.bat` tự chạy bước này trước.

### Lượt bị tắt giữa chừng, gộp lượt — `--tiep`, `--gop`

Chạy `--case` thì kết quả ghi xuống **file lượt** sau mỗi case (cạnh report:
`out/run.html` → `out/run.luot.json`; trường `luot` trong JSON). Lượt chết giữa chừng vẫn còn
các case đã xong.

```bash
# chay not case chua co ket qua (lay lai TC, tab, danh sach case, report tu file)
.venv/bin/rcr-check --package <pkg> --tiep out/run.luot.json
# chay lai vai case, gop vao luot cu (case chay lai de len theo key)
.venv/bin/rcr-check --package <pkg> --tc "<link>" --case <key,key> --gop out/run.luot.json --report out/run-gop.html
# chi gop cac file luot co san thanh mot report - khong can may
.venv/bin/rcr-check --package <pkg> --gop out/a.luot.json --gop out/b.luot.json --report out/gop.html
```

### Ghi kết quả chấm tay — `--cham-tay`

Dòng tool chưa chấm được, đo tay trên máy xong thì ghi vào file lượt (không cần máy):

```bash
.venv/bin/rcr-check --package <pkg> --cham-tay out/run.luot.json   --case 3.4.0#SDK340-UI-001 --dong 1,4 --ket PASS --ly-do "screencap: ảnh phủ kín 1080x2400"
```

Tool tính lại verdict của case, giữ dấu vết `cham_tay` và dựng lại report của file lượt.

### Chạy không cần Claude — `--khong-claude`

Trên Windows, chạy đúng một lệnh trên máy đang cắm điện thoại:

```bat
rem tool tự đo bản SDK FO rồi chọn tab
chay-khong-claude.bat com.example.app
rem chỉ tab 3.4.0 (tab có dấu cách thì để trong ngoặc kép: "daily checkin")
chay-khong-claude.bat com.example.app 3.4.0
```

Lệnh này tương đương `rcr-check --khong-claude --package … --case all [--tab …]`. Cờ này điền sẵn những gì agent vẫn tự lấy:

| | Có Claude (`/rc-check`) | `--khong-claude` |
|---|---|---|
| Chọn case | agent chọn danh sách `--case` | `--case all` = mọi case tool chạy được trong tab |
| Bộ TC, report | agent truyền | `--tc` mặc định sheet TC chung, `--report out/rc-<pkg>-<giờ>.html` |
| Case chưa ra PASS/FAIL | agent tự đo trên máy (§5b) | tool vẫn tự chạy lại tối đa 3 lần như cũ; còn lại ghi **"Cần người xem"** trong tin Discord |
| FAIL | agent rà FAIL giả (§5d) | tool vẫn bắt FAIL phải lặp lại, lệch nhau thì ghi "không ổn định" |
| Gửi report | Claude publish artifact | tin Discord **đính kèm file HTML** (file > 9 MB thì chỉ ghi đường dẫn local) |

Không cờ thì hành vi y như cũ. Những việc vẫn cần người (hoặc Claude) làm: các dòng phải nhìn
bằng mắt (đúng design, đúng màu), rà PASS giả bằng ảnh chụp, case có thao tác tool chưa hiểu.

### Publish report thành artifact

Kết quả check ID ads (`/rc-check` bước audit, trang `<AD_AUDIT_REPO>/tools/ad-checklist-diff/out/<package>-artifact.html`) được đọc bằng code (`audit_tom_tat.py`): bot Discord thêm dòng "🔎 ID ads" vào tin và chỉ đính kèm MỘT file report. Report Next-Gen và nhánh TC có 2 tab ("Checklist"/"Bộ TC" và "Check ID ads"): tab 2 nhúng nguyên trang audit bằng `<iframe srcdoc>` (`report_tab_audit.py`, tự chứa, chạy offline), khối tóm tắt vẫn ở đầu tab 1; không có audit thì tab 2 báo "Chưa check ID ads cho build này"; report + audit quá ~9 MiB thì chỉ giữ khối tóm tắt. Audit cùng ngày với lượt chạy; Next-Gen copy trang audit vào `out/sdk-<pkg>-<giờ>/audit.html` + lưu tóm tắt trong `ket-qua.json` nên `--cham-tay`/`--cham-lai` dựng lại đúng nội dung đã lưu (không bị audit build khác ghi đè).

Report HTML đã sẵn khuôn artifact (mở đầu bằng `<title>`, không bọc `html/head/body`) nên
publish thẳng file được. Tool **không tự publish**: nó chạy ở `127.0.0.1`, không có đường tới
claude.ai — Claude publish rồi ghi link lại:

```bash
.venv/bin/rcr-artifact --url "https://claude.ai/..." --generated-at "<generated_at trong JSON>"
.venv/bin/rcr-artifact            # in link da luu cua luot truoc
```

URL artifact **cố định**: republish cùng file giữ nguyên link, nên lượt sau đừng rải link mới.
`generated_at` lưu kèm là bắt buộc — thiếu nó thì không phân biệt được link đang trỏ tới lượt
vừa chạy hay một lượt cũ, và gửi nhầm báo cáo cũ cho team là sai một cách im lặng.

Cả quy trình (chọn máy → chạy → đọc verdict → publish → ghi link) nằm ở slash command
`/rc-check`, và file lệnh **nằm trong repo** ở `.claude/commands/rc-check.md` — clone về là
có, không phải chép tay. Claude Code chỉ đọc `~/.claude/commands/`, nên trỏ nó sang repo:

```bash
ln -s "$PWD/.claude/commands/rc-check.md" ~/.claude/commands/rc-check.md
```

Sửa cách chạy thì sửa file trong repo, đừng sửa bản ở `~/.claude/` — hai bản là chắc chắn
lệch, và bản người khác clone về là bản lạc hậu.

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
`FAIL` (kèm actual) / `NOT_VERIFIABLE` (dòng tool không đo được, người nhìn) / `NEEDS_HUMAN`.
Verdict case = dòng xấu nhất (thang bậc ở `src/rcr/verdict_levels.py`).
Case ads chấm ở **tầng request/load**, không đòi nhìn thấy ad: inter load nhanh hơn banner
nên nó đè lên trước khi kịp nhìn. **Ad không fill vẫn tính `PASS`** — unit được request đúng
là logic app đúng, kho quảng cáo không trả ad là chuyện của kho; chỉ FAIL khi **không có
request nào**.

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

## Thông báo Discord

Tool gửi tin vào Discord khi một lượt chạy xong (có FAIL → ⛔, không FAIL → ✅), khi app thiếu
trong sheet thông số KT, và khi report được publish. Gửi hỏng chỉ in một dòng cảnh báo ra
stderr, không đổi kết quả hay exit code của lượt chạy.

Máy đã cấu hình bot (`DISCORD_BOT_TOKEN` + `DISCORD_QA_CHANNEL_ID`, xem mục bot bên dưới) thì tin đi
**bằng bot vào kênh QA** (`qa-auto`), cùng chỗ với tin của bot. Máy không có bot thì dùng webhook:

1. Discord → *Server Settings* → *Integrations* → *Webhooks* → *New Webhook* (chọn channel) → *Copy Webhook URL*.
2. Đặt biến môi trường (đừng ghi URL vào file nào trong repo — repo này public):
   ```bash
   export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/<id>/<token>"
   ```
3. Tắt hẳn việc gửi: `DISCORD_NOTIFY=0`.

Gửi tay một tin (slash command dùng cho các điểm dừng agent tự xử lý):
`rcr-notify --kind stop --title "..." --line "..." [--action "..."] [--link URL]`.

## Bot build-watch (`rcr-bot`) — Windows và Ubuntu

Dev đăng tin `Bản build <MÃ> v<x.y.z> (<code>) …` (hoặc QA chuyển tiếp tin đó) → bot hỏi ở kênh QA kèm
nút **Check** → người được duyệt bấm → bot tải đúng bản từ App Tester (tin ghi next-gen: bản release, còn
lại: release có note `debug`) → chạy `/rc-check` bằng Claude headless → trả kết quả + link report vào tin.
Cắm nhiều máy thì mỗi máy chạy một build, song song.

1. Cài thêm: `<bin>/python -m pip install -e ".[dev,bot]"`.
2. Tạo bot ở Discord Developer Portal, bật **Message Content Intent**, mời vào server có kênh build + kênh QA.
3. Cấu hình — **không ghi vào repo (repo public)**. Một trong hai:
   - file `~/.config/rcr/bot.env` (dùng được cả hai hệ điều hành; Ubuntu bắt buộc dùng file này):
     ```
     DISCORD_BOT_TOKEN=...
     DISCORD_BUILD_CHANNEL_ID=<id kênh dev>[,<id kênh QA chuyển tiếp tin>]
     DISCORD_QA_CHANNEL_ID=...
     DISCORD_DUYET_USER_IDS=<id người được bấm, phẩy ngăn cách>
     DISCORD_QA_ROLE_ID=<tuỳ chọn>
     DISCORD_DEV_IDS=<id dev được tag khi báo bug, phẩy ngăn cách>
     JIRA_URL=https://jira.apero.vn           # tuỳ chọn: bật tự verify bug Reviewing
     JIRA_PERSONAL_TOKEN=<PAT Jira>           # cùng token với mcp-atlassian
     ```
   - Windows: biến User (`[Environment]::SetEnvironmentVariable('DISCORD_BOT_TOKEN','...','User')`).
4. Mỗi máy điện thoại: App Tester đã đăng nhập tài khoản tester, USB debugging, màn hình không khoá.
5. Chạy thử: `<bin>/rcr-bot`. Tự bật khi đăng nhập:
   - Ubuntu: `bash deploy/cai-bot-linux.sh` (systemd user service, log `journalctl --user -u rcr-bot -f`)
   - Windows: `powershell -ExecutionPolicy Bypass -File deploy\cai-bot-windows.ps1` (Task Scheduler, log `out/bot-run.log`)

**Tự verify bug Reviewing** (có `JIRA_PERSONAL_TOKEN`): bug do tool log (từ bot Discord, `rc-check` trong terminal
hay checklist Next-Gen) mang **label `auto-qa`** + một dòng marker cuối description
`AUTOQA case=<mã case> ban=<debug|release> pkg=<package>`. Dev kéo bug sang **Reviewing** → khi dev báo build mới
của app đó (kể cả build không ghi SDK, như build fix bug: build đó không có tin hỏi Check, chỉ có lượt verify), bot tìm bug Reviewing theo label (JQL `project = <MÃ> AND labels = "auto-qa" AND status = Reviewing`,
tối đa 50) + bug bot log cũ chưa có label (theo state), gộp theo key, rồi xếp lượt verify (tin 🔁 riêng ở kênh QA,
không cần bấm Check): cài build, chạy lại đúng các case trong marker, **PASS → comment + Done**,
**FAIL → comment + To Do** rồi tag dev ở kênh project; lượt dừng / không ổn định / Claude không kết luận → giữ Reviewing.
Từ Reviewing, workflow bug không có transition tên "To Do"/"Done": bot chọn theo tên **hoặc** trạng thái đích —
FAIL → `Reject Issue` (Reopened, nằm ở cột To Do), PASS → `Close Issue` (Closed, cột Done). Mất kết nối Jira
(VPN rớt) → tự thử lại 4 lần; vẫn lỗi thì giữ Reviewing, bấm **Verify lại** — đã có comment của bot thì không comment trùng.
Mỗi lượt chạy **một nhóm case**: mã bộ TC (`<tab>#<số>`) chạy bằng `--case`; mã dòng checklist Next-Gen
(`EV-07`, `HT-03`, `KT-02`, `MED-02`, `1.7`…) chạy checklist `rcr-sdk-check` rồi đo tay riêng các mã đó nếu `DO_TAY`
(timeout 70 phút), `KHOP → PASS`, `SAI → FAIL`, còn lại giữ Reviewing. Lẫn hai nhóm → chạy nhóm đông hơn, nhóm kia
bấm **Verify lại** sau. Thiếu marker, khác loại bản (debug/release) hoặc khác package → bỏ qua, báo "cần verify tay".
Dev kéo Reviewing sau khi báo build → QA bấm **Verify lại** ở tin build / tin kết quả. Thiếu token → tính năng
tắt, luồng Check giữ nguyên.

**Báo dev**: bug vừa log Jira và bug verify vẫn FAIL được báo ở **kênh riêng của project** (cùng server với kênh
build, tên bắt đầu bằng mã app: `aip920-…`), tag các dev trong `DISCORD_DEV_IDS`. Kênh project được tìm ở server của tin build trước, không có thì ở các
server khác bot đang ở (QA gửi lại tin build ở kênh QA). Log đủ bug và báo được dev → kênh QA không có tin mới, chỉ
tin menu bug đổi dòng trạng thái. Không có kênh / bot không có quyền gửi (kênh Publishing `apb…`), log thiếu bug hay
Jira báo lỗi → bot báo ở kênh QA (kèm nội dung để QA chuyển tay khi không báo được dev).

Lệnh tay: `rcr-cai-build --package <pkg> --version "4.3.0 (40)" --loai debug|release [--serial S]` (cài đúng
bản từ App Tester), thêm `--chi-kiem` để chỉ xem App Tester đang có những bản nào.

## Test

```bash
.venv/bin/python -m pytest          # khong can cam may
.venv/bin/python -m pytest -m device  # test can device that
```

Suite dùng `FakeAdb` với nội dung file **thật** đọc từ máy, nên gác đúng schema thật.
