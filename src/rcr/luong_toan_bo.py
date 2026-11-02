"""Case doi di HET luong FO toi Home: khong duoc dung som o man cua key ads.

`run_batch` dung o man cuoi cung ma key / ma vi tri cua case nhac toi (doc log o do la du,
tiet kiem ~90s). Nhung case "Luong: LFO1 → LFO2 → OB2 → OB4 → Home" hay "Toan luong" cham
CHINH duong di toi Home: dung o OB5 thi dong luong khong ai cham va man Question / Home
khong bao gio toi (AIP936 1.9.0 02/11/2026: RG04-01 / RG05-01 / RG06-01 / RG07-01 dung o
OnboardingActivity#5, dong "Luong ... → Home" ra NOT_VERIFIABLE, "khong hien thi OB1" FAIL oan).
"""

from __future__ import annotations

import re

TOAN_LUONG_RE = re.compile(r"(?:→|->)\s*home\b|to[àa]n\s+lu[ồo]ng|h[ếe]t\s+lu[ồo]ng\b.{0,30}\bhome\b", re.I)


def can_di_het(expects=(), label: str = "") -> bool:
    """Dong Expected / ten case noi ve ca duong di toi Home."""
    return any(TOAN_LUONG_RE.search(t or "") for t in [*expects, label])
