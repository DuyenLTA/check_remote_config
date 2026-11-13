# rc-check — cách hiểu TC QA đã chốt (BẮT BUỘC đọc trước khi chấm / báo bug)

Chấm theo đây, không theo câu chữ TC cũ. TC của bản đang chấm ghi khác **kiến thức nền** thì TC thắng; nhưng các luật QA
chốt dưới đây thắng câu chữ TC.

## Kiến thức nền SDK (QA chốt 06/11/2026)

`sdk-check/references/logic-preload-load-ads-fo-co-ban.md`, gộp từ các tab **"Tổng hợp SDK x"** của sheet TC (6.4.0 nền →
3.2.0 → 3.3.0 → 3.4.0 → 3.5.0; app SDK X dùng mọi mục ≤ X). Gồm: ad load TẠI màn nào, **bảng ad resume theo màn** (Y ở
LFO1/LFO2/OB1/OB2/OB4/Question/OB old khi Home/Recent/khoá màn/notification; N ở Splash/inter/OB3/OB5/consent; kill app/kéo
thanh thông báo/mất mạng → N), OB5, tắt high1/high2 ⇒ 0 request, SWIPE OB2, OB3 auto swipe + nút X, progress splash,
list_language, reload 202 khi chọn ngôn ngữ. Dòng nào kiến thức nền nói là đúng thì KHÔNG đưa vào bug.

User thêm/sửa tab "Tổng hợp SDK x" bất cứ lúc nào: mỗi lượt tool so với bản thô `sdk-check/references/tong-hop-sdk/` và in
`CANH BAO: tab Tong hop SDK moi/doi` → đọc tab đó (`rcr-tong-hop --tc <link>`), cập nhật file kiến thức, rồi
`rcr-tong-hop --tc <link> --ghi` chốt bản thô, commit.

## TC SDK 3.6.1 (template 4)

- Ad resume ở màn tutorial (LFO1, OB1, Question…): AOA hiện khi mở lại là **đúng**, kể cả TC cũ ghi "không show ad resume".
- **Home không có resume.** Kỳ vọng resume ở Home mà không có thì không FAIL.
- Native request hỏng 3 lần (no fill) thì app **thôi request**, đúng thiết kế (log NativeAdHelper "Resume repeat 3 times").
  Dòng "đóng ad resume → reload native" mà không có request mới thì PASS.
- **Tên ad không chỉ ra màn:** `301_onb1_o_native` là ad của màn Question. Trước khi chấm FAIL "vẫn load X" phải biết màn
  nào dùng unit đó.
- Splash GIF `video_loop=false` mà vẫn lặp là đúng.
- Cursor hint LFO2 hiện sau `lfo2_cursor_delay` giây **tính từ lúc bấm chọn ở LFO1**; đổi ngôn ngữ ở LFO2 không đếm lại.

## TC SDK 3.5.4 (05/11/2026, AIP872) — áp cho cả các bản FO khác

- App SDK 3.5.4 chấm thẳng theo **tab gốc "TC SDK 3.5.4"**. KHÔNG dùng tab "Bản sao của TC SDK 3.5.4" (bản cũ, ngược luật).
- **Logic hứng ad:** 202 (LFO2) chưa show ở LFO2 thì OB1 hứng → OB1 hiện native 202 là **đúng**; OB sau hiện ad của màn
  trước (vd OB2 hiện …034 khi tắt OB1/OB3) cũng là hứng, không FAIL.
- **Ad resume** (AOA 501 / inter 503 / native full 502) hiện khi ẩn rồi mở lại là **đúng**, kể cả trong luồng tutorial.
- **Tắt một màn chỉ bỏ ad có logic preload/load TẠI màn đó.** Ad load ở Splash vẫn load là đúng (tắt OB3 mà 303 load ở
  Splash, tắt OB Old mà 301_o request ở Splash — đều PASS).
- **Bỏ hẳn dòng "focus ngôn ngữ đầu tiên"** (R02-02): không chấm, không đưa vào bug.

## TC SDK 3.5.4 (05/11/2026, AIP893) — tool: `assert_qa_man_tat_hung_202`

- **Hứng 202:** ad 202 đã load mà chưa show (vd request mới sau khi bấm đổi ngôn ngữ ở LFO2) thì màn OB **đầu tiên**
  show ad 202 đó thay ad của màn (OB1; tắt OB1 thì OB2). "Native 301 hiển thị, không show 202" mà OB1 show 202 → PASS.
- **Màn tắt giữ logic load:** tắt màn (enable_onbN_screen / enable_ob1_old_screen = false) thì ad của màn đó vẫn
  preload/load ở vị trí cũ như luồng đủ, chỉ không show. Câu TC "không có loadAd <ad màn tắt>" bỏ; có request là đúng,
  thiếu request ở điểm preload của luồng đủ là FAIL (so với lượt luồng đủ cùng máy). Màn khác giữ logic thường (305 vẫn
  preload như khi có OB4).

## IAA (13/11/2026, AIP893)

- **`*_fail_time=N` (vd `inter_style_fail_time`) đếm từ lần fail ĐẦU TIÊN** — lần preload fail cũng tính. N = tổng số lần
  load (preload + gọi lại), không phải N lần gọi lại sau preload. `=3` → 3 lần load rồi thôi là PASS.
