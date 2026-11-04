"""Doc ba man cua luong mua sub tu dump UI (ham thuan, khong adb): Paywall, popup Google Play, trang
Manage subscription cua Play Store.

Do tren may that 04/11/2026 (plans/261104-1140-sub-check-android/phase-01-spike-ket-qua.md):
- Paywall SDK VisionLab (`VslBillingActivity`): goi la text Weekly/Monthly/Yearly, dau chon la content-desc
  Selected/Unselected, gia nam cung hang. Nut `Continue`, `Continue with ads`, dong = `Close Billing Screen`.
- Popup Google Play: resource-id bi lam roi -> chon theo chu. Gia dang `₫182,000/5 min` - chu ky gia han TEST
  doc tu day (Weekly = 5 phut), khong tin so phut ghi trong sheet.
- Play Store: `Next payment: ₫… on Nov 4, 2026, 2:02 PM`, `Canceled`, `Your subscription will end on …`,
  `Expired on …`; nut `Cancel subscription`, `Resubscribe`, `Update`, `Pause payments`.
Chu Play Store theo ngon ngu may (may test de tieng Anh) - doc them vai tu tieng Viet thuong gap.
"""

from __future__ import annotations

import re
from datetime import datetime

from .ui_dump import DeviceNode

GOI = ("weekly", "monthly", "yearly")
GIA_RE = re.compile(r"[₫$€£¥]\s?[\d.,]+|[\d.,]+\s?(?:₫|đ|VND|USD)", re.I)
CHU_KY_TEST_RE = re.compile(r"/\s*(\d+)\s*(min|minute|minutes|phút)\b", re.I)
NGAY_RE = re.compile(r"([A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2}\s?[AP]M)")
POPUP_ACT = "com.android.vending"
PAYWALL_ACT = "VslBillingActivity"


def _chu(n: DeviceNode) -> str:
    return (n.text or n.content_desc or "").replace(" ", " ").replace("&#10;", "\n").strip()


def _tim(nodes: list[DeviceNode], *mau: str, desc: bool = True) -> DeviceNode | None:
    """Node dau tien co text (hoac content-desc) bang mot trong `mau` (khong phan biet hoa thuong)."""
    muon = {m.lower() for m in mau}
    for n in nodes:
        if (n.text or "").strip().lower() in muon or (desc and (n.content_desc or "").strip().lower() in muon):
            return n
    return None


def _cha_bam_duoc(nodes: list[DeviceNode], n: DeviceNode) -> DeviceNode:
    """Node bam duoc chua `n` (chu thuong nam trong vung clickable cha)."""
    theo_id = {x.node_id: x for x in nodes}
    cur = n
    while cur is not None and not cur.clickable:
        cur = theo_id.get(cur.parent_id or "")
    if cur is not None:
        return cur
    # Compose: vung clickable khong phai cha trong cay ma la node anh em bao trum -> lay node clickable nho nhat bao n
    bao = [x for x in nodes if x.clickable and x.bounds.left <= n.bounds.left and x.bounds.right >= n.bounds.right
           and x.bounds.top <= n.bounds.top and x.bounds.bottom >= n.bounds.bottom]
    return min(bao, key=lambda x: (x.bounds.right - x.bounds.left) * (x.bounds.bottom - x.bounds.top), default=n)


def toa_do(nodes: list[DeviceNode], n: DeviceNode) -> tuple[int, int]:
    return _cha_bam_duoc(nodes, n).bounds.center


# --- Paywall --------------------------------------------------------------------------------
def doc_paywall(nodes: list[DeviceNode]) -> dict | None:
    """{goi: [{ten, gia, chon, xy}], continue, ads, dong} hoac None khi man khong co du 3 thu: ten goi, nut tiep tuc."""
    goi = []
    for n in nodes:
        ten = (n.text or "").strip().lower()
        if ten not in GOI:
            continue
        hang = [x for x in nodes if abs(x.bounds.center[1] - n.bounds.center[1]) < 80 and x is not n]
        gia = next((x.text.strip() for x in hang if x.text and GIA_RE.search(x.text)), "")
        dau = next((x.content_desc for x in hang if (x.content_desc or "").lower() in ("selected", "unselected")), "")
        goi.append({"ten": ten, "gia": gia, "chon": dau.lower() == "selected", "xy": toa_do(nodes, n)})
    nut = _tim(nodes, "Continue", "Subscribe", "Tiếp tục", "Start", "Try for free")
    if not goi or nut is None:
        return None
    ads = _tim(nodes, "Continue with ads", "Tiếp tục với quảng cáo")
    dong = _tim(nodes, "Close Billing Screen", "Close", "Đóng")
    return {"goi": goi, "continue": toa_do(nodes, nut), "ads": toa_do(nodes, ads) if ads else None,
            "dong": toa_do(nodes, dong) if dong else None}


# --- Popup Google Play ----------------------------------------------------------------------
def doc_popup(nodes: list[DeviceNode]) -> dict | None:
    """Popup xac nhan mua cua Google Play: {ten_goi, gia, chu_ky_phut, the, la_test, subscribe, dong, doi_the}.
    None khi khong phai popup (khong co nut Subscribe / Buy)."""
    if not any(n.package == POPUP_ACT for n in nodes):
        return None
    nut = _tim(nodes, "Subscribe", "Buy", "Đăng ký", "Mua", desc=False)
    if nut is None:
        return None
    chu = [_chu(n) for n in nodes if n.package == POPUP_ACT and _chu(n)]
    gia_node = next((c for c in chu if GIA_RE.search(c) and "/" in c), "")
    ky = CHU_KY_TEST_RE.search(gia_node)
    the = next((n.text.strip() for n in nodes if (n.text or "").lower().startswith("test card")), "")
    ten_goi = next((c for c in chu if any(g in c.lower() for g in GOI) and not GIA_RE.search(c)), "")
    dong = _tim(nodes, "Close", "Đóng")
    doi_the = next((n for n in nodes if (n.content_desc or "").lower().startswith("test card") and n.clickable), None)
    return {
        "ten_goi": ten_goi, "gia": gia_node, "chu_ky_phut": int(ky.group(1)) if ky else None, "the": the,
        # Giao dich test: the test hoac dong "This is a test subscription". Khong co -> tai khoan la, KHONG mua.
        "la_test": bool(the) or any("test subscription" in c.lower() for c in chu),
        "subscribe": toa_do(nodes, nut), "dong": toa_do(nodes, dong) if dong else None,
        "doi_the": doi_the.bounds.center if doi_the else None,
    }


def the_test(nodes: list[DeviceNode], loai: str) -> tuple[int, int] | None:
    """Trong danh sach phuong thuc thanh toan: dong the test can chon. loai: approves | declines | slow."""
    mau = {"approves": "always approves", "declines": "always declines", "slow": "approves after a few minutes"}[loai]
    for n in nodes:
        if mau in _chu(n).lower() and (loai != "approves" or "after" not in _chu(n).lower()):
            return toa_do(nodes, n)
    return None


# --- Play Store: Manage subscription ----------------------------------------------------------
def _gio(s: str) -> str:
    """'Nov 4, 2026, 2:02 PM' -> '2026-11-04T14:02' ('' khi khong doc duoc)."""
    m = NGAY_RE.search(s or "")
    if not m:
        return ""
    try:
        return datetime.strptime(m.group(1).replace(" ", " "), "%b %d, %Y, %I:%M %p").strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        return ""


def doc_play(nodes: list[DeviceNode]) -> dict:
    """Trang Manage subscription (hoac danh sach Subscriptions): {trang_thai, ten_goi, gio_ke_tiep, het_luc, the,
    nut: {cancel, resubscribe, update, pause}}. trang_thai: active | canceled | expired | none | unknown."""
    chu = [_chu(n) for n in nodes if _chu(n)]
    gop = "\n".join(chu)
    thap = gop.lower()
    nut = {k: toa_do(nodes, n) for k, n in (
        ("cancel", _tim(nodes, "Cancel subscription", "Hủy gói thuê bao")),
        ("resubscribe", _tim(nodes, "Resubscribe", "Đăng ký lại")),
        ("update", _tim(nodes, "Update", "Cập nhật", desc=False)),
        ("pause", _tim(nodes, "Pause payments", "Tạm dừng thanh toán"))) if n is not None}
    ke_tiep = next((c for c in chu if c.lower().startswith("weekly") or "next payment" in c.lower()), "")
    if "next payment" in thap and "cancel" in nut:
        tt = "active"
    elif "canceled" in thap or "will end on" in thap:
        tt = "canceled"
    elif "expired on" in thap and "next payment" not in thap:
        tt = "expired"
    elif "couldn't find your subscription" in thap or "couldn’t find your subscription" in thap:
        tt = "none"                                   # deep link sku: goi da het han / chua tung mua
    elif "don't have any active subscriptions" in thap or "you don’t have any" in thap:
        tt = "none"
    else:
        tt = "unknown"
    het = next((c for c in chu if "will end on" in c.lower() or "expired on" in c.lower()), "")
    return {
        "trang_thai": tt,
        "ten_goi": next((c.split("\n")[0] for c in chu if any(c.lower().startswith(g) for g in GOI)), ""),
        "gio_ke_tiep": _gio(ke_tiep) if "next payment" in ke_tiep.lower() else "",
        "het_luc": _gio(het),
        "the": next((c for c in chu if c.lower().startswith("test card")), ""),
        "nut": nut,
    }


def nut_duoi(nodes: list[DeviceNode], *chu: str) -> tuple[int, int] | None:
    """Nut bam duoc THAP NHAT co chu `chu`. Man xac nhan cua Play Store lap lai chu cua nut o tieu de (tieu de khong
    bam duoc) - bam tieu de thi khong co gi xay ra (lan chay thu dau tien da dinh khi cancel)."""
    mau = {c.lower() for c in chu}
    hits = [n for n in nodes if (n.text or n.content_desc or "").strip().lower() in mau]
    nut = [_cha_bam_duoc(nodes, n) for n in hits]
    nut = [n for n in nut if n.clickable and n.bounds.bottom - n.bounds.top < 400]   # bo vung bam ca man
    return max(nut, key=lambda n: n.bounds.top).bounds.center if nut else None


def nut_xac_nhan_cancel(nodes: list[DeviceNode]) -> tuple[int, int] | None:
    """Man khao sat cancel: bam thang nut "Cancel subscription" o duoi, khong chon ly do (user chot 04/11/2026)."""
    return nut_duoi(nodes, "Cancel subscription", "Hủy gói thuê bao")


def nut_xac_nhan_resubscribe(nodes: list[DeviceNode]) -> tuple[int, int] | None:
    """Sheet "Resubscribe to <app>?" (goi cu duoc khoi phuc): nut "Resubscribe" o duoi, ben "No thanks"."""
    return nut_duoi(nodes, "Resubscribe", "Đăng ký lại")
