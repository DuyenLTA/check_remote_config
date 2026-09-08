# Remote Config Case Runner

Đổi giá trị **Firebase Remote Config** của app Android **từ file testcase** — không cần
quyền admin Firebase, không đụng server thật, chỉ ảnh hưởng đúng một máy đang cắm.

> **Trạng thái: phase 1/6.** Hiện đọc được baseline remote config của app.
> Phần patch / chạy case / chấm PASS-FAIL ở các phase sau.

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

## Test

```bash
.venv/bin/python -m pytest          # khong can cam may
.venv/bin/python -m pytest -m device  # test can device that
```

Suite dùng `FakeAdb` với nội dung file **thật** đọc từ máy, nên gác đúng schema thật.
