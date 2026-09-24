"""Boc cap `key = value` remote config ra khoi cot Precondition + Test Data cua 1 case.

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
  3. Ep trang thai load ad (`105-spl-n-native-high: fail`) ma vi tri CHUA co key
     ID da do trong `data/ad_id_keys.yaml`. Co thi ad_state doi ID ad trong RC
     (ID sai = fail, ID test = fill) va case chay binh thuong.

GOP PRECONDITION + TEST DATA (chot 2026-09-23): bo TC dung chung ghi key bat buoc
o Precondition, Test Data chi ghi key dang doi. Trung key -> Test Data thang.
Precondition la van xuoi nen chi boc cap `key=value`, WHITELIST loc phan con lai;
dong Precondition co mui ten (`high=true -> load fail`) la mo ta trang thai,
khong phai gia tri -> bo ca dong.
"""

from __future__ import annotations

import re

from . import ad_state, rc_pairs, rc_variants
from .models import Case, RcCaseData

ARROWS = rc_pairs.ARROWS

# Gia tri la cho trong chua dien: `<id template dang test>`, `<gia tri tuong ung>`
PLACEHOLDER_RE = re.compile(r"<[^<>]*>")
# Key co dau '.' -> sua field trong JSON (vd restore.enable)
DOTTED_RE = re.compile(r"\b[A-Za-z][\w]*\.[A-Za-z][\w]*\s*[:=]")
EMPTY = ("", "N/A", "NA", "-")



def extract(case: Case, whitelist: set[str] | frozenset[str]) -> RcCaseData:
    """Tra ve cap key/value da loc, hoac ly do can nguoi lam tay."""
    raw = case.test_data.strip()
    has_td = raw.upper() not in EMPTY

    if has_td and any(a in raw for a in ARROWS):
        return RcCaseData(
            overrides={},
            needs_human=(
                "runtime toggle (doi gia tri khi app dang chay) - ngoai pham vi tool: "
                "patch file + mo lai app khong tai hien duoc, app phai tu fetch luc dang chay"
            ),
        )

    if has_td and DOTTED_RE.search(raw):
        return RcCaseData(
            overrides={},
            needs_human=(
                "sua field ben trong JSON - cau khong neu key goc, suy ra la doan. "
                "Tester tu dat gia tri cho key chua JSON do"
            ),
        )

    bad = ad_state.unreadable(raw) if has_td else []
    if bad:
        return RcCaseData(
            overrides={},
            needs_human=f"ky hieu trang thai ad khong doc duoc: {'; '.join(bad)} - viet day du vd `102-spl-n-inter-high: fail`",
        )
    # Trung vi tri -> Test Data thang, nhu cap key=value
    markers = ad_state.find(case.precondition) | (ad_state.find(raw) if has_td else {})
    forced, unresolved = ad_state.resolve(markers, whitelist)
    if unresolved:
        return RcCaseData(
            overrides={},
            needs_human=(
                f"can ep trang thai load ad ({', '.join(f'{m}: {markers[m]}' for m in unresolved)}) - "
                "vi tri nay chua co key ID ad da do la SDK doc (data/ad_id_keys.yaml), phai lam tay"
            ),
        )

    pre = rc_pairs.pairs(rc_pairs.precondition_lines(case.precondition))
    # Ky hieu `102-...: fail` khop PAIR_RE thanh cap rac (`high: fail`) -> bo truoc khi boc
    td = rc_pairs.pairs(ad_state.MARKER_RE.sub("", raw)) if has_td else {}
    td |= forced
    if not pre and not td:
        why = (f"khong boc duoc cap key=value nao tu Test Data: {raw[:80]!r}" if has_td
               else "Test Data trong va Precondition khong co key nao de dat")
        return RcCaseData(overrides={}, needs_human=why)

    found = pre | td  # trung key -> Test Data thang
    # Key cua app duoc NHAC ma khong co gia tri (`splash_ui_config hop le nhung
    # image_url rong`) -> chay voi config mac dinh la sai ma khong ai biet.
    mentioned = _mentioned(rc_pairs.precondition_lines(case.precondition) + "\n" + raw, whitelist)
    vague = sorted(mentioned - set(found) - set(forced))
    if vague:
        return RcCaseData(
            overrides={},
            needs_human=(
                f"key duoc nhac nhung khong co gia tri cu the: {', '.join(vague)} - "
                "ghi ro `key = gia tri` trong Precondition"
            ),
        )
    overrides = {k: v for k, v in found.items() if k in whitelist}
    ignored = tuple(sorted(k for k in found if k not in whitelist))
    from_pre = tuple(sorted(k for k in overrides if k not in td))

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
    overrides, variants, too_many = rc_variants.split(overrides)
    if too_many:
        return RcCaseData(overrides={}, ignored=ignored, needs_human=too_many)
    if variants and not overrides:
        return RcCaseData(overrides={}, ignored=ignored, variants=variants,
                          from_precondition=from_pre)
    if not overrides:
        return RcCaseData(
            overrides={},
            ignored=ignored,
            needs_human=(
                "khong co key nao thuoc remote config cua app - "
                f"bo qua: {', '.join(ignored)}. Co the la param analytics, khong phai RC key"
            ),
        )
    return RcCaseData(overrides=overrides, ignored=ignored, variants=variants,
                      from_precondition=from_pre)


def _mentioned(text: str, whitelist) -> set[str]:
    """Key cua app xuat hien nhu mot tu rieng trong van ban."""
    words = set(re.findall(r"[A-Za-z][A-Za-z0-9_]*", text))
    return words & set(whitelist)


def whitelist_of(baseline) -> frozenset[str]:
    """Whitelist = dung tap key app that su co. Khong hardcode."""
    return frozenset(baseline.configs)
