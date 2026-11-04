# Phase 1 — Spike trên máy thật (04/11/2026, Pixel 4 99261FFAZ0077C, AI Home Design / Homova 1.9.0, AIP936)

**Trạng thái:** xong

## Paywall — SDK billing dùng chung VisionLab
- Activity `com.visionlab.billing.ui.VslBillingActivity` → selector dùng chung các app cùng SDK.
- Đóng: content-desc `Close Billing Screen`. Gói: text `Weekly` / `Monthly` / `Yearly`, dòng giá kế bên (`₫182,000` + `/week`), chọn = content-desc `Selected` / `Unselected`.
- Nút: text `Continue` (vùng clickable cha), `Continue with ads`.
- Đường vào ở app này: nút content-desc `Premium` (vương miện) trên Home; FO cũng có màn Billing (walker đóng).

## Popup Google Play
- Activity `com.android.vending/...billing.acquire.LockToPortraitUiBuilderHostActivity`, resource-id bị làm rối → chọn theo chữ.
- Chữ: `Weekly 6.99` (tên gói), giá `₫182,000/5 min` → **chu kỳ test Weekly = 5 phút** (sheet ghi 3 phút — đọc từ popup, không tin sheet).
- Thẻ: dòng `Test card, always approves` (content-desc `Test card, always approves. Change paym…`, bấm để đổi thẻ).
- Dấu hiệu giao dịch test: `Test card…` + `This is a test subscription…`. Nút `Subscribe`. Đóng: content-desc `Close`.

## Logcat — thư viện billing dùng chung `PurchaseEG`
- Mua: `onPurchasesUpdated code: 0`, `idPurchase: aip936.weekly.699`, `VslBilling_Paying: Success`,
  `NativeAdPreload/BannerAdPreload: purchase detected, releasing…`.
- Acknowledge: `onAcknowledgePurchaseResponse: Server error, please try again.` rồi một dòng rỗng (cần theo dõi TC12).
- Khởi động: `verifyPurchased SUBS code:0 === size:N` → N>0 là còn gói, 0 là free.
- `onPurchasesUpdated` + `Success` log 2 lần cho 1 lần mua (2 listener) — ghi nhận, chưa phải bug.

## Play Store
- Deep link `https://play.google.com/store/account/subscriptions?sku=<sku>&package=<pkg>` → trang Manage subscription:
  `Next payment: … on <ngày>, <giờ>`, `₫…/5 minutes`, thẻ chính, nút `Update`, `Pause payments`, `Cancel subscription`.
- Cancel: `Cancel subscription` → màn khảo sát → bấm thẳng nút `Cancel subscription` ở dưới (không cần chọn lý do — user chốt; trên màn có thêm tiêu đề cùng chữ, đừng bấm nhầm)
  → trang ghi `Canceled`, `Your subscription will end on …`, nút `Resubscribe`.
- Không sku: danh sách `Active` / `Expired` (`Weekly 6.99 Expired on …`).

## Hành vi app quan sát được
- **TC63:** gói hết hạn lúc app ở nền → mở lại bằng icon (không kill): app vẫn Premium. Kill rồi mở lại:
  `verifyPurchased SUBS size:0` → về free. **User chốt: đúng thiết kế** — billing chỉ lấy trạng thái khi kill app mở lại.
- Mở lạnh đôi khi `verifyPurchased SUBS code:-1` (SERVICE_DISCONNECTED), app không thử lại (gặp 2 lần liền 14:38–14:40).
- Chu kỳ test (user chốt): Weekly / Monthly 5 phút, Yearly 30 phút.
- Settings > `Cancel Subscription` mở đúng danh sách Subscriptions của Play Store (TC43 đạt).

## Máy
- Pixel 4: 4 tài khoản Google (TC40 đổi tài khoản làm được). Pixel 6: 2 tài khoản.
- Driver phải giữ khoá máy `out/.may-<serial>.lock`; phiên Claude khác không giữ khoá vẫn có thể chen vào (gặp trên Pixel 6).
