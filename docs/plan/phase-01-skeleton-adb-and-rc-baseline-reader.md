---
phase: 1
title: "Skeleton + adb + RC baseline reader"
status: completed
priority: P1
effort: "1d"
dependencies: []
---

# Phase 1: Skeleton + adb + RC baseline reader

## Overview
Dựng repo `~/projects/rc-case-runner` theo khuôn `tsa`/`usv`, và đọc được **baseline remote
config thật** của 1 app: appId, toàn bộ key, kiểu từng key, danh sách file mirror.

Baseline là nền của mọi thứ sau: whitelist key lấy từ đây, kiểu XML mirror lấy từ đây,
giá trị gốc để restore lấy từ đây.

## Requirements
- Functional: chọn device → chọn app (chỉ app debuggable) → trả về `RcBaseline`.
- Functional: phát hiện app **không debuggable** và báo rõ ngay, không để lỗi mơ hồ về sau.
- Non-functional: chỉ bind `127.0.0.1`; module <200 LOC; suite pytest chạy được khi không cắm máy.

## Architecture

```
rc_baseline.read(client, serial, package) -> RcBaseline
  1. run-as pkg ls files/            -> tim frc_<appId>_firebase_activate.json
                                        (regex: ^frc_(.+)_firebase_activate\.json$)
  2. run-as pkg cat files/<ten>      -> configs_key, fetch_time_key, template_version
  3. run-as pkg ls shared_prefs/     -> frc_<appId>_firebase_settings.xml + vsl_*.xml
  4. run-as pkg cat shared_prefs/... -> parse XML: {key: (kieu, gia_tri)}
```

`RcBaseline` (frozen dataclass):
- `app_id: str` — bóc từ tên file, cần cho mọi đường dẫn sau
- `configs: dict[str, str]` — key → value (RC luôn lưu string)
- `fetch_time_ms: int`, `template_version: int | None`
- `settings_xml: str` — nguyên văn, để phase 2 sửa tại chỗ bằng regex
- `mirrors: dict[str, dict[str, tuple[str, str]]]` — tên file → {key: (kieu_xml, value)}.
  Chỉ giữ node có tên key **giao với `configs`**; node còn lại bỏ ngay khi đọc.
- `mirrored_keys: frozenset[str]` — key có mặt ở ≥1 mirror (giao với `configs`)
- `non_mirror_files: tuple[str, ...]` — file `vsl_*` có 0 key giao → **không bao giờ ghi vào**,
  giữ tên lại chỉ để hiện lên UI cho tester biết đã bỏ qua file nào
- `write_mode: str` — `run-as` | `su`. Dò 1 lần ở đây, phase 2 dùng lại (xem phase 2). Thử
  `run-as pkg id` → không được thì `su -c id` → cả hai không được thì `RcError` kèm hướng dẫn.

**Vì sao giữ `settings_xml` nguyên văn:** file do Android ghi, có thứ tự và format riêng.
Parse rồi render lại là rủi ro làm app không đọc được. Phase 2 chỉ thay đúng 1 số bằng regex.

## Related Code Files
- Create: `pyproject.toml`, `start.sh`, `src/rcr/__init__.py`, `src/rcr/main.py`
- Create: `src/rcr/adb_client.py` — port từ `usv/adb_client.py` (đã có `dump_ui`, `screencap`,
  `launch`, `screen_metrics`, `current_focus`); thêm `_run` trả nguyên `(out, err, code)`
- Create: `src/rcr/adb_parsers.py` — `PACKAGE_RE`, `SERIAL_RE`, `find_adb`, `parse_devices`,
  `parse_packages`, `AdbError` (port từ `tsa/adb_parsers.py`)
- Create: `src/rcr/rc_baseline.py`, `src/rcr/models.py`
- Create: `src/rcr/web/index.html`, `web/app.js`, `web/style.css` (tối giản: chọn device + app)
- Create: `tests/test_rc_baseline.py`, `tests/conftest.py`
- Read để tham chiếu: `~/projects/ui-spec-verifier/src/usv/adb_client.py`,
  `~/Downloads/Tool_test_data_app-main/src/tsa/adb_parsers.py`, `.../pyproject.toml`, `.../start.sh`

## Implementation Steps
1. Scaffold repo: `pyproject.toml` — deps `fastapi`, `uvicorn[standard]`, `openpyxl`,
   `python-multipart`, `pyyaml` (phase 4 dùng cho `reset_rules.yaml`); dev `pytest`, `httpx`.
   `package-data`: `rcr = ["data/*.yaml", "web/*"]` để `pip install .` không -e vẫn chạy.
   `pytest.ini_options`: `pythonpath=["src"]`, `addopts = "-m 'not device'"`, marker `device`.
   `start.sh` mirror `tsa` (tự tạo venv, đổi port khi bận, `RCR_NO_BROWSER=1`).
2. `adb_parsers.py`: port `PACKAGE_RE`/`SERIAL_RE`/`find_adb`/`parse_devices`/`parse_packages`.
   **Không** port phần logcat/uid — round 2 mới cần.
3. `adb_client.py`: port từ `usv`. Bắt buộc có `_run` trả `(out, err, code)` **không raise** —
   thông báo của `run-as` là thứ duy nhất phân biệt "không debuggable" / "chưa cài" / "SELinux chặn".
4. `models.py`: `RcBaseline`, `RcError`.
5. `rc_baseline.py`: 4 bước như Architecture. Parse XML mirror bằng `re.findall` trên
   `<(boolean|string|long|int|float) name="..." (value="..."|>...)` — **không** dùng
   `xml.etree` để tránh mất format khi ghi lại ở phase 2.
6. **Phân loại mirror bằng giao tên key**, không theo tên file. File `vsl_*` có 0 key giao với
   `configs` là state nội bộ app (`vsl_template4_prefs.xml`, `vsl_widget_local_prefs.xml`) →
   xếp vào `non_mirror_files`, tuyệt đối không ghi. Tên file **không** phải căn cứ tin được:
   `vsl_rating_remote_prefs.xml` có chữ `remote` mà chỉ 3/5 key là RC.
7. `main.py`: FastAPI, middleware chặn host khác `127.0.0.1`, route
   `GET /api/devices`, `GET /api/packages?serial=`, `POST /api/baseline`.
8. Web UI tối giản: dropdown device + app, bấm "Đọc baseline" → hiện số key, danh sách mirror
   **và danh sách file `vsl_*` bị bỏ qua**, cảnh báo đỏ nếu app không debuggable.
9. Test bằng FakeAdb: fixture trả nội dung `ls`/`cat` giả lấy từ dữ liệu thật đã đo.

## Success Criteria
- [ ] `./start.sh` chạy, mở `127.0.0.1:8000`, bind LAN bị chặn
- [ ] Chọn `com.ai.videogenerator.photocreator.aiart` → `app_id` đúng, `len(configs)` = **200**,
      `mirrors` có **3** file, `mirrored_keys` = **91**, `non_mirror_files` = **2**
      (`vsl_template4_prefs.xml`, `vsl_widget_local_prefs.xml`)
- [ ] Chọn `aiphotogenerator.photoshoot.aiart.aiimagegenerator` → `len(configs)` = **206**,
      `mirrored_keys` = **98**, `mirrors` có **4** file (gồm `vsl_rating_remote_prefs.xml`
      chỉ 3/5 key là RC → chỉ 3 key đó được giữ)
- [ ] Chọn `com.aiartvideo.imageai.aigenerator` (Pixel 4) → `len(configs)` = **257**,
      `mirrors` **rỗng**, `mirrored_keys` **rỗng** — app không dùng SDK mirror, không được crash
- [ ] Chọn `ai.photogenerator.aivideo.aivideogenerator.aiart` → lỗi rõ ràng
      "app không debuggable", không phải traceback
- [ ] `pytest` xanh khi **không** cắm máy; test `device` bị skip
- [ ] Mọi module <200 LOC

## Risk Assessment
- **Tên file `frc_*` chứa dấu `:`** (vd `frc_1:310944273102:android:...`) → mọi đường dẫn phải
  bọc nháy khi qua `sh` trên device. Đã gặp thật khi đo.
- **`run-as` báo lỗi mà exit 0** trên một số ROM → phải quét stdout tìm
  `not debuggable` / `unknown package` / `permission denied`, không tin returncode.
- App có nhiều `frc_*_activate.json` (vd `_fireperf_activate.json`) → chỉ lấy đúng
  `_firebase_activate.json`, bỏ namespace khác.


## Ket qua thuc te (2026-09-07)

Repo: `~/projects/rc-case-runner`. 37 test xanh khi khong cam may. Moi module <200 LOC.

Do that tren Pixel 4 (`99261FFAZ0077C`, Android 12):

| App | Key | Mirror-key | File mirror | Bo qua (state noi bo) |
|---|---|---|---|---|
| `com.aiphotogenearator.aivideogenerator.photogallery` | 195 | 73 | 2 | `vsl_template4_prefs.xml` |
| `lingospeak.english.learnlanguage.speak` | 131 | 92 | 4 (co mirror mot phan) | `vsl_checkin_local_prefs.xml`, `vsl_template4_prefs.xml` |
| `com.aiartvideo.imageai.aigenerator` | 257 | **0** | **{}** khong crash | — |
| `ai.photogenerator.aivideo.aivideogenerator.aiart` (AIP922) | — | — | — | `RcError` kem huong dan, khong traceback |

Server: `GET /` 200, static 200, `/api/devices` OK, app khong debuggable → **400** (khong 500),
`Host: evil.local` → **403**, chua doc baseline → 400. Log server **0 traceback**.

Phat sinh ngoai plan: tach `app_sandbox.py` khoi `adb_client.py` (dung ranh gioi logic
"chay lenh trong danh tinh app" vs "goi adb", va la nen cho `rc_write` o phase 2).
