"""Boc cap `key = value` remote config ra khoi cot Test Data cua 1 case.

LOC BANG WHITELIST KEY DOC THAT TU MAY (rc_baseline). Cot Test Data KHONG chi
chua RC key - file that con co param analytics (`source = navigation`,
`click_area = cta_button`, `category = "Anime"`, `feature_name`, `template_id`).
Khong loc thi tool se day rac vao remote config. Nho whitelist, khong can tester
khai bao gi: key nao khong co trong config cua app thi tu roi ra.

BA DANG PHAI DANH `NEEDS_HUMAN`, KHONG DUOC DOAN:
  1. Runtime toggle: `key: true -> false -> true (doi khi app dang chay)`.
     Patch file + restart KHONG lam duoc - app phai tu fetch lai luc dang chay.
  2. Sua field trong JSON: `restore.enable = false`. Cau do khong neu key goc;
     `restore` la `id` cua mot phan tu trong mang `moment_spotlight_banners`,
     suy ra la doan.
  3. Test Data rong ma Precondition co ve co key: chi doc Test Data, khong tu
     boc tu Precondition (van xuoi, de boc sai).
"""

from __future__ import annotations

import re

from .models import Case, RcCaseData

# Mui tien cac kieu tester hay dung cho runtime toggle.
ARROWS = ("→", "->", "=>", "⇒")

# Tim UNG VIEN key (identifier bat ky), roi `=`/`:`, roi gia tri.
# KHONG doi key phai co dau '_': config that co key khong underscore (vd
# `AppSettings`) -> doi underscore la bo sot key hop le. WHITELIST moi la bo
# loc; regex chi co viec tim ung vien.
_KEY = r"[A-Za-z][A-Za-z0-9_]*"
PAIR_RE = re.compile(
    rf"(?P<key>{_KEY})\s*[:=]\s*(?P<val>.*?)(?=(?:,\s*{_KEY}\s*[:=])|$)",
    re.DOTALL,
)
# Gia tri la cho trong chua dien: `<id template dang test>`, `<gia tri tuong ung>`
PLACEHOLDER_RE = re.compile(r"<[^<>]*>")
# Key co dau '.' -> sua field trong JSON (vd restore.enable)
DOTTED_RE = re.compile(r"\b[A-Za-z][\w]*\.[A-Za-z][\w]*\s*[:=]")


def extract(case: Case, whitelist: set[str] | frozenset[str]) -> RcCaseData:
    """Tra ve cap key/value da loc, hoac ly do can nguoi lam tay."""
    raw = case.test_data.strip()
    if not raw or raw.upper() in ("N/A", "NA", "-"):
        return RcCaseData(overrides={}, needs_human="Test Data trong - khong co key nao de dat")

    if any(a in raw for a in ARROWS):
        return RcCaseData(
            overrides={},
            needs_human=(
                "runtime toggle (doi gia tri khi app dang chay) - ngoai pham vi tool: "
                "patch file + mo lai app khong tai hien duoc, app phai tu fetch luc dang chay"
            ),
        )

    if DOTTED_RE.search(raw):
        return RcCaseData(
            overrides={},
            needs_human=(
                "sua field ben trong JSON - cau khong neu key goc, suy ra la doan. "
                "Tester tu dat gia tri cho key chua JSON do"
            ),
        )

    found = {m.group("key"): _clean(m.group("val")) for m in PAIR_RE.finditer(raw)}
    if not found:
        return RcCaseData(
            overrides={},
            needs_human=f"khong boc duoc cap key=value nao tu Test Data: {raw[:80]!r}",
        )

    overrides = {k: v for k, v in found.items() if k in whitelist}
    ignored = tuple(sorted(k for k in found if k not in whitelist))

    # Gia tri con la cho trong -> patch vao la ghi nguyen chuoi mo ta vao config.
    holes = sorted(k for k, v in overrides.items() if PLACEHOLDER_RE.search(v))
    if holes:
        return RcCaseData(
            overrides={},
            ignored=ignored,
            needs_human=(
                f"gia tri chua dien, con la cho trong: {', '.join(f'{k}={overrides[k]!r}' for k in holes)}. "
                "Tester dien gia tri that vao file testcase roi chay lai"
            ),
        )
    if not overrides:
        return RcCaseData(
            overrides={},
            ignored=ignored,
            needs_human=(
                "khong co key nao thuoc remote config cua app - "
                f"bo qua: {', '.join(ignored)}. Co the la param analytics, khong phai RC key"
            ),
        )
    return RcCaseData(overrides=overrides, ignored=ignored)


def _clean(val: str) -> str:
    """Chuan hoa gia tri thanh dang RC luu (LUON la string).

    Giu nguyen van JSON va chuoi rong: `[]` phai ra `"[]"`, `""` phai ra `""`
    (khong duoc coi la 'khong co gia tri' roi bo qua).
    """
    v = val.strip()
    # Bo phan chu thich trong ngoac don o cuoi: `false (mac dinh)` -> `false`
    v = re.sub(r"\s*\((?:[^()]*)\)\s*$", "", v).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'“”":
        return v[1:-1]
    if v.startswith("“") and v.endswith("”"):
        return v[1:-1]
    low = v.lower()
    if low in ("true", "false"):
        return low
    return v


def whitelist_of(baseline) -> frozenset[str]:
    """Whitelist = dung tap key app that su co. Khong hardcode."""
    return frozenset(baseline.configs)
