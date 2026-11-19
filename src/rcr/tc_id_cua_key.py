"""Test Data ghi gia tri bang ten key khac: `question_inter_high_n_id=<ID splash_inter_high_n_id>` -> ID that cua key do.

Tab TC SDK 3.7.3 (18/11/2026) khong dan ID ma ghi "<ID splash_inter_high_n_id>" (= gia tri dang chay cua key
splash_inter_high_n_id) va "<ID inter test khac (khong preload)>" (= mot unit inter KHONG nam trong ad_preload). Truoc day
rc_extract coi ca hai la cho trong chua dien -> bo key do nhung van chay phan con lai: N01 / O01..O16 chay voi
question_inter_* / splash_inter_*_o_id = gia tri Firebase mac dinh, ket qua sai dieu kien ma khong ai biet.

- `<ID <key>>`: key co gia tri dang chay (baseline: template Firebase / file activate) -> thay bang gia tri do.
- `<ID inter test khac ...>`: unit interstitial test cong khai cua Google (luon tra ad test, khong nam trong ad_preload
  cua app nao) -> dung lam "ID khong preload".
Khong thay duoc (key khong co gia tri) -> giu nguyen, rc_extract van bao cho trong nhu cu (khong doan).
"""

from __future__ import annotations

import dataclasses
import re

# Unit interstitial mau cua Google Mobile Ads (developers.google.com/admob/android/test-ads).
INTER_TEST_GOOGLE = "ca-app-pub-3940256099942544/1033173712"

ID_KEY_RE = re.compile(r"<\s*ID\s+([A-Za-z][A-Za-z0-9_]*)\s*>")
ID_TEST_KHAC_RE = re.compile(r"<\s*ID\s+inter\s+test\s+kh[áa]c[^<>]*>", re.I)


def thay_chuoi(text: str, dang_chay: dict[str, str]) -> str:
    """Thay moi cho `<ID key>` / `<ID inter test khac ...>` trong mot o Test Data / Precondition."""
    if not text or "<" not in text:
        return text
    text = ID_TEST_KHAC_RE.sub(INTER_TEST_GOOGLE, text)

    def _id(m: re.Match) -> str:
        v = (dang_chay.get(m.group(1)) or "").strip()
        return v if v else m.group(0)

    return ID_KEY_RE.sub(_id, text)


def thay(pairs: list, dang_chay: dict[str, str]) -> list:
    """[(tab, Case)] -> cung danh sach, gia tri `<ID key>` da thay bang ID that."""
    ra = []
    for tab, c in pairs:
        td, pre = thay_chuoi(c.test_data or "", dang_chay), thay_chuoi(c.precondition or "", dang_chay)
        if td == (c.test_data or "") and pre == (c.precondition or ""):
            ra.append((tab, c))
        else:
            ra.append((tab, dataclasses.replace(c, test_data=td, precondition=pre)))
    return ra
