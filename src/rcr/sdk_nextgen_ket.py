"""Ket qua mot dong checklist SDK Next-Gen.

Report cuoi chi co Khop / Sai (luat skill nextgen-sdk-check). Code tra them hai
trang thai trung gian de khoanh vung phan khong tu dong duoc:
  - DO_TAY: luat code khong cham chac duoc (can bam quang cao, lac may, nhin mat...)
    -> Claude do tren may roi ghi bang `rcr-sdk-check --cham-tay`.
  - KHONG_AP_DUNG: app khong co thu checklist hoi (vd khong co banner trong luong
    tutorial) -> muc "Ngoai pham vi / khong ap dung", khong tinh.
    Cung trang thai nay con dung cho dong tool KHONG LAM DUOC (kho khong fill, can may EEA, can APK ban cu...):
    `khong_lam_duoc` tach rieng nhom do de report noi ro phan viec QA con phai tu lam.
"""

from __future__ import annotations

import re

KHOP, SAI, DO_TAY, KHONG_AP_DUNG = "KHOP", "SAI", "DO_TAY", "KHONG_AP_DUNG"
HOP_LE = (KHOP, SAI, DO_TAY, KHONG_AP_DUNG)
# Bang chung toi da moi dong - report doc duoc, khong dump ca log.
TOI_DA_BANG_CHUNG = 12
# Ly do cua dong KHONG_AP_DUNG ma app CO thu do, chi la tool/may khong tao duoc dieu kien (doc tu ket-qua.json that
# 11-19/11/2026). Con lai (chi co trong app, luong khong co banner, tai khoan AdMob chua cau hinh UMP) la khong ap dung.
_KHONG_LAM_DUOC = re.compile(r"chưa đo được|không đo được|không tạo được|không mua được|cần apk bản cũ|"
                             r"bỏ theo yêu cầu|không giả lập được|không có (native video )?fill|đã thử \d+ lượt|cần dev chỉ", re.IGNORECASE)


def khong_lam_duoc(r: dict) -> bool:
    """Dong KHONG_AP_DUNG nay la 'tool khong lam duoc' (QA con phai tu lam), khong phai app khong co."""
    return r.get("ket") == KHONG_AP_DUNG and bool(_KHONG_LAM_DUOC.search(r.get("ly_do") or ""))


def kq(ma: str, ten: str, ket: str, ly_do: str, bang_chung=(), ghi_chu: str = "") -> dict:
    if ket not in HOP_LE:
        raise ValueError(f"ket {ket!r} khong hop le")
    return {"ma": ma, "ten": ten, "ket": ket, "ly_do": ly_do,
            "bang_chung": list(bang_chung)[:TOI_DA_BANG_CHUNG], "ghi_chu": ghi_chu, "cham_boi": "code"}
