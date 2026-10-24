"""Ket qua mot dong checklist SDK Next-Gen.

Report cuoi chi co Khop / Sai (luat skill nextgen-sdk-check). Code tra them hai
trang thai trung gian de khoanh vung phan khong tu dong duoc:
  - DO_TAY: luat code khong cham chac duoc (can bam quang cao, lac may, nhin mat...)
    -> Claude do tren may roi ghi bang `rcr-sdk-check --cham-tay`.
  - KHONG_AP_DUNG: app khong co thu checklist hoi (vd khong co banner trong luong
    tutorial) -> muc "Ngoai pham vi / khong ap dung", khong tinh.
"""

from __future__ import annotations

KHOP, SAI, DO_TAY, KHONG_AP_DUNG = "KHOP", "SAI", "DO_TAY", "KHONG_AP_DUNG"
HOP_LE = (KHOP, SAI, DO_TAY, KHONG_AP_DUNG)
# Bang chung toi da moi dong - report doc duoc, khong dump ca log.
TOI_DA_BANG_CHUNG = 12


def kq(ma: str, ten: str, ket: str, ly_do: str, bang_chung=(), ghi_chu: str = "") -> dict:
    if ket not in HOP_LE:
        raise ValueError(f"ket {ket!r} khong hop le")
    return {"ma": ma, "ten": ten, "ket": ket, "ly_do": ly_do,
            "bang_chung": list(bang_chung)[:TOI_DA_BANG_CHUNG], "ghi_chu": ghi_chu, "cham_boi": "code"}
