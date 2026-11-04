"""Doc logcat cua thu vien billing dung chung (`PurchaseEG`, `VslBilling`) -> trang thai mua cua app.

Do tren may that 04/11/2026 (AIP936): app in log nay o moi lan khoi dong va moi lan mua, nen day la nguon chac
nhat de biet app dang Premium hay free ma khong can biet giao dien rieng cua tung app.
- `verifyPurchased SUBS  code:0 ===   size:N` -> N > 0: con goi; N = 0: free (doc luc khoi dong / query lai)
  code khac 0 (vd -1 SERVICE_DISCONNECTED, gap 04/11/2026 luc mo lanh) -> query hong, KHONG ket luan premium
- `onPurchasesUpdated code: C` -> ket qua mua: 0 OK, 1 USER_CANCELED, 7 ITEM_ALREADY_OWNED, khac = loi
- `idPurchase: <sku>` -> sku vua mua
- `onAcknowledgePurchaseResponse: <loi>` -> acknowledge; rong = OK
- `purchase detected, releasing every preloaded ...` -> app bo ads preload khi mua
"""

from __future__ import annotations

import re

VERIFY_RE = re.compile(r"verifyPurchased\s+(SUBS|INAPP)\s+code:\s*(-?\d+)\s*=+\s*size:\s*(\d+)")
UPDATED_RE = re.compile(r"onPurchasesUpdated code:\s*(-?\d+)")
SKU_RE = re.compile(r"idPurchase:\s*([\w.]+)")
ACK_RE = re.compile(r"onAcknowledgePurchaseResponse:\s*(.*)$")
NHA_ADS_RE = re.compile(r"purchase detected, releasing every preloaded (\w+)")
SKU_CAU_HINH_RE = re.compile(r"onBillingSetupFinished:\s*([a-z0-9_]+\.[\w.]+)")
MA_KQ = {-1: "SERVICE_DISCONNECTED", 0: "OK", 1: "USER_CANCELED", 2: "SERVICE_UNAVAILABLE", 3: "BILLING_UNAVAILABLE", 4: "ITEM_UNAVAILABLE",
         5: "DEVELOPER_ERROR", 6: "ERROR", 7: "ITEM_ALREADY_OWNED", 8: "ITEM_NOT_OWNED", 12: "NETWORK_ERROR"}
# Dong `idPurchase` mang tag AperoAppsflyer (khong phai PurchaseEG) -> loc theo ca tu khoa, khong chi tag.
TAG = ("PurchaseEG", "VslBilling", "AdPreload", "idPurchase")


def doc(dong: list[str]) -> dict:
    """Cac dong logcat -> {premium (True/False/None), mua: [ma ket qua], sku_mua, ack: [loi], nha_ads: [loai],
    sku_cau_hinh}. `premium` lay tu lan verify SUBS cuoi; khong co verify thi theo lan mua OK cuoi; khong co gi -> None."""
    premium, mua, sku, ack, nha, cau_hinh, verify_loi = None, [], [], [], [], [], []
    for d in dong:
        if m := VERIFY_RE.search(d):
            if m.group(1) == "SUBS" and m.group(2) == "0":
                premium = int(m.group(3)) > 0
            elif m.group(1) == "SUBS":
                ma = int(m.group(2))
                verify_loi.append(MA_KQ.get(ma, f"CODE_{ma}"))
        elif m := UPDATED_RE.search(d):
            ma = int(m.group(1))
            mua.append(MA_KQ.get(ma, f"CODE_{ma}"))
            if ma == 0:
                premium = True
        elif m := SKU_RE.search(d):
            sku.append(m.group(1))
        elif m := ACK_RE.search(d):
            ack.append(m.group(1).strip())
        elif m := NHA_ADS_RE.search(d):
            nha.append(m.group(1))
        elif m := SKU_CAU_HINH_RE.search(d):
            if m.group(1) not in cau_hinh:
                cau_hinh.append(m.group(1))
    return {"premium": premium, "mua": mua, "sku_mua": sku[-1] if sku else "", "ack": ack,
            "ack_loi": [a for a in ack if a], "nha_ads": sorted(set(nha)), "sku_cau_hinh": cau_hinh,
            "verify_loi": verify_loi}


def sku_theo_goi(cau_hinh: list[str], goi: str) -> str:
    """'weekly' + ['aip936.weekly.699', ...] -> 'aip936.weekly.699' ('' khi khong co)."""
    return next((s for s in cau_hinh if goi.lower() in s.lower()), "")
