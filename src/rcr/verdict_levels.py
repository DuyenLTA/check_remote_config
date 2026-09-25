"""Cac trang thai cham va thang bac giua chung. Khong logic, khong I/O.

KHONG co trang thai rieng cho "ad khong fill": user chot 2026-09-25 rang request
dung ma khong fill thi van tinh PASS - khong fill la chuyen cua kho quang cao.

De rieng vi ca `assert_check` lan `assert_ads` deu can, ma hai module do thi
goi lan nhau khong duoc (vong import).
"""

from __future__ import annotations

PASS = "PASS"
FAIL = "FAIL"
NOT_VERIFIABLE = "NOT_VERIFIABLE"  # tool khong do duoc bang dump/log - nguoi nhin
NEEDS_HUMAN = "NEEDS_HUMAN"        # can thao tac tay moi den duoc trang thai do
CONFIG_OK = "CONFIG_OK"            # dat duoc config, case khong co dong Expected nao
CONFIG_BLOCKED = "BLOCKED"         # config khong song qua lan mo app -> chua test duoc

# Xau nhat dung dau - verdict cua case lay phan tu dau tien gap duoc.
# CONFIG_OK dung TRUOC PASS: "dat duoc config" ken hon "da cham va dung".
SEVERITY = (FAIL, CONFIG_BLOCKED, NEEDS_HUMAN, NOT_VERIFIABLE, CONFIG_OK, PASS)


def worst(verdicts) -> str:
    """Verdict cua case = dong xau nhat."""
    seen = set(verdicts)
    for level in SEVERITY:
        if level in seen:
            return level
    return NOT_VERIFIABLE


def out(verdict: str, reason: str, actual) -> dict:
    return {"verdict": verdict, "reason": reason, "actual": actual}
