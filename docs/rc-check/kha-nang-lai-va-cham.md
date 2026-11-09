# rc-check — tool lái được gì, chấm được gì (chi tiết mục 1)

Đọc khi: case có câu Action lạ, tool dừng `NEEDS_HUMAN` ở bước lái, hoặc cần biết một dòng Expected được chấm bằng gì.

## Bước Action lái được

- `Quan sát…` (không thao tác), `Nhấn nút "X"` / `Mở tab X` (tap), `Chờ N giây`, `Vuốt sang trái/phải/lên/xuống`,
  `Tắt mạng` / `Bật lại mạng`.
- **Bước đi tới cả một màn** (`Hoàn thành luồng FO đến Home`, `Vào màn Onboarding 2`) — `fo_flow` lo. OB1/2/3 sang
  màn bằng **vuốt**, không bấm Next, vì chính nút Next là thứ đang được test.
- Câu ghép (bộ TC 3.5.0) — trước đây bị làm **sai im lặng**:
  - `Vuốt trái nhanh liên tục 3-4 lần` → vuốt đủ 4 lần, không suy trang theo số lần vuốt
  - `Vuốt phải về OB2, rồi vuốt trái…` → đúng thứ tự
  - `Chờ quá 10s` → chờ quá mốc, không phải 3s mặc định; `Ở OB3, chờ thêm 5s`, `Sau đó vuốt…`
  - `Nhấn Home (background 10s)` rồi `Mở lại app` → đưa app lên thật
  - `Xoay ngang rồi xoay dọc` → xong luôn trả chế độ xoay của máy về như cũ
  - `Tại t0+2s: <thao tác>` — **t0 = lúc vừa tới màn của case, CHƯA phải lúc ad show**; report ghi thao tác làm lúc t0+bao nhiêu
- `Bấm giờ` / `ghi nhận thời điểm ad show` = tool **đứng yên quan sát**: đo mốc vào/rời trang OB3 + ad show/fail bằng
  `logcat -v epoch` (tới ms), nhìn liên tục để thấy nút X / số đếm. Vào tới OB3 là **nhìn ngay**, không dump + chụp trước
  bước (mất 3–5s, timer 3s là trang đã đi mất). Nhìn bằng `dumpsys activity top` (~0,15s/khung) xen `uiautomator`
  (~2,5s, đọc được chữ): chỉ dùng uiautomator thì khung đầu trễ ~7s, cả cụm OB3X ra FAIL oan.
- `Mở app không mạng` ≠ `Mở app`: tool ngắt wifi + data **trước** `am start`, rồi bật lại và **chờ ping thông** (`svc`
  trả về ngay lúc mạng chưa lên). Cuối case luôn trả mạng về, kể cả khi case hỏng giữa chừng.

## Không gắn cứng theo một app

Tool dùng cho nhiều app (user chốt 07/10/2026). Nút X / số đếm nhận theo **vai trò**: gợi ý id trong
`src/rcr/data/ui_names.yaml` + nghĩa tên id (skip/close/dismiss… — timeout/countdown/timer) + content-desc + chữ chỉ là số
ở vùng trên màn. App mới đặt tên id lạ thì **thêm vào yaml**, không sửa code, không viết id của một app vào code hay workflow.

Câu khác — hoặc **nhiều node cùng khớp** — thì dừng kèm lý do, **không tap bừa**.

Hai chỗ nới lỏng có chủ ý:
- **Câu vuốt không nêu hướng** (`Vuốt theo đúng hướng icon gợi ý`) → lấy hướng sang trang kế (trái). Vuốt không bấm trúng
  gì nên đoán sai chỉ làm màn không đổi.
- **Vế sau dấu phẩy chỉ là quan sát / đối soát console / một cú chờ thì không chặn bước đi tới màn**: `Chạy luồng FO đến
  OB3, quan sát banner` lái được; `Vào màn OB2, chờ hết timeout load ad` lái tới rồi **đứng yên 12s**. Vế sau là việc khác
  mà tool không làm được thì vẫn dừng — bỏ im vế sau là PASS giả.

## Dòng Expected chấm bằng gì

| Loại dòng | Chấm bằng |
|---|---|
| quảng cáo | log request/load/show |
| chữ, node | cây UI |
| "icon là animation lặp" | chụp nhiều khung, so vùng node |
| "user vuốt sang màn kế" | một cú vuốt thật |
| "app bắn event X" | log `FA-SVC` |
| "luồng FO thông suốt" | nhật ký lái |
| bố cục splash ("neo ngay trên mép native", "không đè banner", "cách mép 12–16dp", "giữa màn", "không dịch chuyển khi native show") | bounds trong dump, đổi dp theo `wm density` (id ở mục `bo_cuc` của `src/rcr/data/ui_names.yaml`) |
| màu chữ ("Title đúng màu #4957FF") | PNG gốc: đếm pixel trùng màu (lệch ≤4/kênh) trong khung chữ so dải đối chứng sát bên, bounds đọc lại từng khung. Nền trùng màu chữ → NEEDS_HUMAN, không FAIL |
| phải nhìn mắt (đúng design, ảnh full-screen) | `NOT_VERIFIABLE` — không đoán thành PASS; Claude tự đo theo mục 5b |
