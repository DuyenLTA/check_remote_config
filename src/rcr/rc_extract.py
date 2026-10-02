"""Boc cap `key = value` remote config ra khoi cot Precondition + Test Data cua 1 case.

LOC BANG WHITELIST KEY DOC THAT TU MAY (rc_baseline). Cot Test Data KHONG chi
chua RC key - file that con co param analytics (`source = navigation`,
`click_area = cta_button`, `category = "Anime"`, `feature_name`, `template_id`).
Khong loc thi tool se day rac vao remote config. Nho whitelist, khong can tester
khai bao gi: key nao khong co trong config cua app thi tu roi ra.

BA DANG PHAI DANH `NEEDS_HUMAN`, KHONG DUOC DOAN:
  1. Runtime toggle chi ghi o ten case / Precondition, Test Data khong co mui
     ten -> khong biet gia tri tung buoc. Co mui ten trong Test Data (quy uoc bo
     TC 3.5.0: moi mui ten = doi config, tat app, chay lai) thi CHAY duoc: moi
     buoc mot luot, `runtime=True`.
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

from . import ad_state, rc_guards, rc_pairs, rc_unit_codes, rc_variants
from .models import Case, RcCaseData

ARROWS = rc_pairs.ARROWS

EMPTY = ("", "N/A", "NA", "-")
# Tu chi quang cao trong van xuoi cua Precondition.
AD_WORDS_RE = re.compile(
    r"native|banner|inter|reward|app\s*open|\baoa\b|\bads?\b|quảng\s*cáo|quang\s*cao", re.I)
# Gia tri bat/tat. CHI cap dang nay moi la mot cong tac: `source = ads_screen` co
# chu "ads" nhung khong tat gi ca, con `OB2 = OFF` thi co.
ONOFF_RE = re.compile(r"^(?:on|off|true|false|bật|bat|tắt|tat|enable|disable)$", re.I)



def extract(case: Case, whitelist: set[str] | frozenset[str]) -> RcCaseData:
    """Tra ve cap key/value da loc, hoac ly do can nguoi lam tay."""
    raw = case.test_data.strip()
    has_td = raw.upper() not in EMPTY

    # Bo TC khong co cot Test Data thi runtime toggle nam o ten sub-scenario
    # ("Runtime: swipe_onb2 true -> false -> true") hoac o Precondition. Khong
    # doc hai cho do thi case chi chay duoc buoc dau ma van bi cham nhu da xong.
    td_runtime = has_td and any(a in raw for a in ARROWS)
    # "(doi khi app dang chay)": doi luc app CON CHAY - khac tat app roi mo lai.
    dang_chay = td_runtime and rc_variants.DANG_CHAY_RE.search(raw)
    if dang_chay or not td_runtime and (rc_guards.TOGGLE_RE.search(case.label)
                           or rc_guards.TOGGLE_RE.search(case.precondition)):
        return RcCaseData(
            overrides={},
            needs_human=(
                "runtime toggle (doi gia tri khi app dang chay) - ngoai pham vi tool: "
                "patch file + mo lai app khong tai hien duoc, app phai tu fetch luc dang chay"
            ),
        )

    if has_td and rc_guards.DOTTED_RE.search(raw):
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

    dong_pre = rc_pairs.precondition_lines(case.precondition)
    pre = rc_pairs.pairs(dong_pre)
    # Ky hieu `102-...: fail` khop PAIR_RE thanh cap rac (`high: fail`) -> bo truoc khi boc
    td = rc_pairs.pairs(ad_state.MARKER_RE.sub("", raw)) if has_td else {}
    td |= forced
    # Bo TC ghi key theo mau (`unit 102-spl-n-inter-high1 (key show_* tuong ung)
    # = false`) thay vi ten that. Suy ra `show_<ma>` va CHI nhan khi key do co
    # trong whitelist doc tu may. Uu tien thap nhat: ten viet ro thi thang.
    suy_ra = rc_unit_codes.pairs(
        dong_pre + ("\n" + raw if has_td else ""), whitelist)
    if not pre and not td and not suy_ra:
        why = (f"khong boc duoc cap key=value nao tu Test Data: {raw[:80]!r}" if has_td
               else "Test Data trong va Precondition khong co key nao de dat")
        return RcCaseData(overrides={}, needs_human=why)

    found = suy_ra | pre | td  # trung key -> Test Data thang, roi den ten viet ro
    # Key cua app duoc NHAC ma khong co gia tri (`splash_ui_config hop le nhung
    # image_url rong`) -> chay voi config mac dinh la sai ma khong ai biet.
    mentioned = rc_guards.mentioned(rc_pairs.precondition_lines(case.precondition) + "\n" + raw, whitelist)
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

    cong_tac = rc_guards.cong_tac_ads_chua_map(dong_pre + "\n" + raw, found, ignored, whitelist)
    if cong_tac:
        return RcCaseData(
            overrides={},
            ignored=ignored,
            needs_human=(
                f"cau bat/tat quang cao ma tool khong map duoc sang key RC: "
                f"{'; '.join(repr(v) for v in cong_tac)}. Chay tiep la cham tren may "
                "con dang bat quang cao - case se FAIL oan"
            ),
        )
    from_pre = tuple(sorted(k for k in overrides if k not in td))

    # Gia tri con la cho trong -> patch vao la ghi nguyen chuoi mo ta vao config.
    # `<absent>` la quy uoc "server khong tra key", khong phai cho trong.
    holes = sorted(k for k, v in overrides.items()
                   if rc_guards.PLACEHOLDER_RE.search(v.replace(rc_variants.ABSENT, "")))
    if holes:
        return RcCaseData(
            overrides={},
            ignored=ignored,
            needs_human=(
                f"gia tri chua dien, con la cho trong: {', '.join(f'{k}={overrides[k]!r}' for k in holes)}. "
                "Tester dien gia tri that vao file testcase roi chay lai"
            ),
        )
    # Runtime `a → b → c` (Test Data, quy uoc bo TC 3.5.0): mui ten = doi config,
    # tat app, chay lai luong. Lam duoc bang patch + mo lai, nhu moi luot khac.
    overrides, chuoi, loi = rc_variants.split_runtime(overrides)
    if loi:
        return RcCaseData(overrides={}, ignored=ignored, needs_human=loi)
    if chuoi:
        return RcCaseData(overrides=overrides, ignored=ignored, variants=chuoi,
                          runtime=True, from_precondition=from_pre)
    overrides, ong = rc_variants.split_pipe(overrides)
    if ong:
        return RcCaseData(overrides=overrides, ignored=ignored, variants=ong,
                          from_precondition=from_pre)
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


def whitelist_of(baseline) -> frozenset[str]:
    """Whitelist = dung tap key app that su co. Khong hardcode."""
    return frozenset(baseline.configs)
