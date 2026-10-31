"""Tung thao tac tren man First Open: tim node, chon ngon ngu, bam nut chinh.

Port tu tool `ad-checklist-diff` (da chay hang tram luot tren may that). Giu
nguyen ba bai hoc dat gia nhat cua no:

1. **Tru vung quang cao theo HINH HOC, truoc khi xep hang bat cu thu gi.**
   Man Language cua Piclux chi co DUNG MOT node clickable: `ad_call_to_action`
   cua native ad. "Lay node bam duoc" la bam thang vao quang cao, roi bay sang
   Play Store va tinh mot cu click that vao chinh unit dang do.

2. **Nut chinh tim theo VI TRI, khong theo chu.** Nhan nut do remote config
   dat: "Go to Home", "Next", "Get Started" deu da tung ship cho cung mot nut.

3. **Hang English la hang BUNG RA, khong phai hang chon duoc.** Bam vao no chi
   mo ra cac bien the vung; phai lay bien the dau tien ben trong. Hang dau tien
   co checkbox lai la ngon ngu nao remote config xep dau - da tung chay ca luot
   bang tieng Hindi vi luat "lay checkbox dau tien".
"""

from __future__ import annotations

import re

from .ui_dump import DeviceNode

# Manh id noi "view nay thuoc ve quang cao". So theo doan cua id nen `btnAdd`
# khong bi doc nham thanh ad.
AD_MARKERS = ("ad_", "_ad", "nativead", "admob", "adview", "adcontainer", "banner", "shimmer")
# `exo_ad_overlay` la lop phu cua ExoPlayer (trinh phat video cua man onboarding),
# khong phai quang cao. Ten co "_ad" nen tung bi tru nham ca man.
NOT_AD_PREFIXES = ("exo_",)
# Vung quang cao that la mot O tren man, khong phai ca man. Hop lon hon muc
# nay gan nhu chac chan la container cua chinh man hinh -> tru no di la
# khong con gi bam duoc.
MAX_AD_BOX_SHARE = 0.5
# Id cua nut tiep tuc, theo do uu tien. Id la layout TU KHAI ten nut nen thang
# moi suy luan theo hinh dang.
CONTINUE_IDS = (
    "btnNextQuestion", "btnNextOnboardingImage", "btnNextOnboarding",
    "btnContinue", "btnGetStarted", "btnStart", "btnNext",
)
CLOSE_IDS = ("btnClose", "ivClose", "imgClose", "closeButton", "btnSkip", "ivCancel")
CLOSE_DESCS = ("close", "dismiss", "đóng")
# Nut dong CUA QUANG CAO toan man (AdActivity): ca man la mot WebView cua ad, bam
# trat nut dong la click vao ad. `dismiss-button` la id cua creative web GMA (nhan
# "Đóng"/"Close"); chu dong phai KHOP TRON (khong lay "Close your eyes..." cua creative).
AD_CLOSE_IDS = ("dismiss-button",)
AD_CLOSE_WORDS = re.compile(r"^(close|close ad|đóng|skip|skip ad|bỏ qua|continue to app|tiếp tục.*ứng dụng|"
                            r"interstitial close button|×)$", re.I)
# Nhan GMA in tren creative khi may la test device ("Test Ad" / "Quảng cáo thử nghiệm"). Mot so creative
# (video WebView, Photogen 1.0.0 30/10/2026) ve nut X ma KHONG co node nao trong cay UI -> find_close_ad
# khong bao gio thay. Ad test thi BACK dong an toan (khong tinh traffic that), ad that thi van khong BACK.
AD_TEST_LABEL = re.compile(r"^(test ad|quảng cáo thử nghiệm)$", re.I)


def la_ad_test(nodes: list[DeviceNode]) -> bool:
    """Man AdActivity dang hien quang cao TEST cua GMA (co nhan test ad)."""
    return any(AD_TEST_LABEL.match(n.text.strip()) for n in nodes if n.visible)


# Dem nguoc cua quang cao toan man. Cau "... sau/in N s", "N giây" -> dem nguoc o dau tren man cung tinh. So tron
# 1-2 chu so chi tinh khi nam DE / SAT nut dong (dong ho dem hien tai cho nut dong): Sorapix 24/10/2026 co so "1"
# o thanh "More" canh nut Dong (so trang carousel) trong khi nut Dong da bam duoc.
DEM_NGUOC_CAU = re.compile(r"^\d{1,2}\s*(s|sec|giây)$|(sau|in|trong)\s+\d{1,2}\s*(s|sec|giây)?\b", re.I)
SO_TRON = re.compile(r"^\d{1,2}$")
SAT_NUT_DONG = 30                     # px quanh nut dong van coi la "cho cua nut dong"
# Phan man hinh (theo ti le) de tim nut chinh: duoi bang cau hoi, khong phai ca man.
BOTTOM_BAND = 0.45
MIN_WIDTH = 0.20
MAX_AREA = 0.25

INDICATOR_ID = "indicatorPageOnboarding"
DOT_ID = "dot"

TITLE_ID = "titleLanguageItem"
CHECKBOX_ID = "checkboxLanguageItem"
EXPAND_ID = "iconExpandLanguageItem"


def is_ad_node(node: DeviceNode) -> bool:
    low = node.resource_id.lower()
    if low.startswith(NOT_AD_PREFIXES):
        return False
    return any(mark in low for mark in AD_MARKERS)


def _area(b) -> int:
    return max(0, b.right - b.left) * max(0, b.bottom - b.top)


def ad_boxes(nodes: list[DeviceNode]) -> list:
    """Cac o quang cao tren man. Bo hop qua lon - do la container cua man."""
    if not nodes:
        return []
    screen = max(_area(n.bounds) for n in nodes) or 1
    return [
        n.bounds for n in nodes
        if is_ad_node(n) and _area(n.bounds) < screen * MAX_AD_BOX_SHARE
    ]


def outside_ads(nodes: list[DeviceNode]) -> list[DeviceNode]:
    """Bo moi node NAM TRONG vung cua mot view quang cao.

    Tru theo hinh hoc chu khong theo id cua chinh node: nut CTA cua native ad
    thuong khong mang chu 'ad' nao trong id cua no.
    """
    boxes = ad_boxes(nodes)
    out = []
    for n in nodes:
        x, y = n.bounds.center
        if any(b.left <= x <= b.right and b.top <= y <= b.bottom for b in boxes):
            continue
        out.append(n)
    return out


def find_node(nodes: list[DeviceNode], resource_id: str = "", text: str = "") -> DeviceNode | None:
    """Node khop id (theo duoi) hoac text. Khong tinh node trong vung quang cao."""
    pool = [n for n in outside_ads(nodes) if n.visible]
    if resource_id:
        hit = [n for n in pool if n.resource_id == resource_id]
        return hit[0] if hit else None
    if text:
        low = text.casefold()
        hit = [n for n in pool if n.text.casefold() == low] or \
              [n for n in pool if low in n.text.casefold()]
        return hit[0] if hit else None
    return None


def find_continue(nodes: list[DeviceNode], screen: tuple[int, int]) -> DeviceNode | None:
    """Nut chinh cua man. Id truoc, khong co thi lay nut o dai duoi man hinh."""
    pool = outside_ads([n for n in nodes if n.visible and not n.bounds.empty])
    for wanted in CONTINUE_IDS:
        hit = [n for n in pool if n.resource_id == wanted]
        if hit:
            return hit[0]
    width, height = screen
    band = height * BOTTOM_BAND
    cands = [
        n for n in pool
        if n.bounds.top > band
        and (n.bounds.right - n.bounds.left) > width * MIN_WIDTH
        and (n.bounds.right - n.bounds.left) * (n.bounds.bottom - n.bounds.top)
        < width * height * MAX_AREA
        and (n.text or n.content_desc or n.clickable)
    ]
    return max(cands, key=lambda n: n.bounds.top) if cands else None


def find_close(nodes: list[DeviceNode]) -> DeviceNode | None:
    pool = outside_ads([n for n in nodes if n.visible and not n.bounds.empty])
    for wanted in CLOSE_IDS:
        hit = [n for n in pool if n.resource_id == wanted]
        if hit:
            return hit[0]
    for n in pool:
        if any(d in n.content_desc.casefold() for d in CLOSE_DESCS):
            return n
    return None


def _trong(a, b) -> bool:
    return (a.bounds.left >= b.bounds.left and a.bounds.top >= b.bounds.top
            and a.bounds.right <= b.bounds.right and a.bounds.bottom <= b.bounds.bottom)


def _sat(a, b, le: int = SAT_NUT_DONG) -> bool:
    return not (a.bounds.right < b.bounds.left - le or a.bounds.left > b.bounds.right + le
                or a.bounds.bottom < b.bounds.top - le or a.bounds.top > b.bounds.bottom + le)


def dang_dem_nguoc(nodes: list[DeviceNode], nut: DeviceNode | None = None) -> bool:
    """Quang cao con dang dem nguoc ("Đóng sau 3s", "Skip in 4", so "5" ngay cho nut dong): CHUA duoc bam dong.
    Bam trong luc dem nguoc la cham vao quang cao -> GMA ghi ad_click (user 29/10/2026: "phai doi no chay het
    thoi gian roi hang bam")."""
    for n in nodes:
        if not n.visible:
            continue
        for t in (n.text.strip(), n.content_desc.strip()):
            if t and (DEM_NGUOC_CAU.search(t) or (SO_TRON.match(t) and nut is not None and _sat(n, nut))):
                return True
    return False


def find_close_ad(nodes: list[DeviceNode], cho_dem_nguoc: bool = True) -> DeviceNode | None:
    """Node can bam de dong quang cao toan man, hoac None (KHONG bam gi thay vi bam mu).

    Bam vao CHU dong ben trong nut, khong vao tam nut: Sorapix 24/10/2026 co node
    "More" de len nua phai `dismiss-button`. Khong tru vung quang cao nhu `find_close`:
    o AdActivity ca man la quang cao nen tru di thi khong con gi.
    Con dem nguoc hoac nut dong chua bat (enabled=false) -> None: doi quang cao chay het thoi gian.
    `cho_dem_nguoc=False`: da cho qua tran (so trong creative bi doc nham la dem nguoc) -> bo qua dem nguoc.
    """
    pool = [n for n in nodes if n.visible and n.enabled and not n.bounds.empty]
    nut = next((n for n in pool if n.resource_id in AD_CLOSE_IDS), None)
    if nut is None:
        nut = next((n for n in pool if AD_CLOSE_WORDS.match(n.text.strip()) or AD_CLOSE_WORDS.match(n.content_desc.strip())), None)
    if nut is None or (cho_dem_nguoc and dang_dem_nguoc(nodes, nut)):
        return None
    chu = [n for n in pool if n is not nut and AD_CLOSE_WORDS.match(n.text.strip()) and _trong(n, nut)]
    return chu[0] if chu else nut


def language_targets(nodes: list[DeviceNode], language: str, bien_the: str = "") -> list[DeviceNode]:
    """Cac node can bam de chon `language`, theo dung thu tu.

    Hang co checkbox -> chon thang. Hang co icon bung -> bam bung roi lay bien the:
    `bien_the` (case doi, vd "English (United States)") khop theo `fo_ngon_ngu.khop_bien_the`,
    khong co bien the nao khop -> [] (khong bam bua bien the khac roi cham noi dung sai ngon ngu);
    khong doi bien the -> BIEN THE DAU TIEN.
    """
    rows = [n for n in nodes if n.resource_id == TITLE_ID and n.visible]
    row = next((n for n in rows if n.text.casefold().startswith(language.casefold())), None)
    if row is None:
        return []
    controls = [n for n in nodes if n.resource_id in (CHECKBOX_ID, EXPAND_ID) and n.visible]
    same_row = [c for c in controls if abs(c.bounds.center[1] - row.bounds.center[1]) < 40]
    if same_row and same_row[0].resource_id == CHECKBOX_ID:
        return [row]
    # Hang bung: bien the la cac hang THUT VAO nam ngay duoi hang cha.
    variants = []
    for n in sorted((n for n in rows if n.bounds.top > row.bounds.bottom), key=lambda n: n.bounds.top):
        if n.bounds.left <= row.bounds.left:
            break                     # het nhom bien the cua hang nay
        variants.append(n)
    if variants:
        if not bien_the:
            return [variants[0]]      # da bung san - bam lai icon la GAP LAI
        from .fo_ngon_ngu import khop_bien_the
        i = khop_bien_the(bien_the, [v.text for v in variants])
        return [] if i is None else [variants[i]]
    return [row, "expanded"]          # can bung roi doc lai o vong sau


def onboarding_page(nodes: list[DeviceNode]) -> int:
    """Dang o trang onboarding thu may (1-based). 0 neu khong doc duoc.

    Cac trang OB dung CHUNG mot activity, nen ten man khong phan biet duoc
    OB1/OB2/OB3. Doc theo cham chi trang: cham cua trang hien tai duoc keo DAI
    ra (do that: 53px so voi 21px cua cham thuong).
    """
    dots = [n for n in nodes if n.resource_id == DOT_ID and n.visible] or _cham_khong_id(nodes)
    if not dots:
        return 0
    dots.sort(key=lambda n: n.bounds.left)
    widest = max(dots, key=lambda n: n.bounds.right - n.bounds.left)
    return dots.index(widest) + 1


def _cham_khong_id(nodes: list[DeviceNode]) -> list[DeviceNode]:
    """Cham chi trang KHONG co resource-id (AIP886 2.7.0: 4 view 41px, cham active 73px, cung hang y=1297-1318):
    mot hang 3-6 node nho khong chu, khong id, cung top, dung mot cai rong han ro (>= 1,4 lan cai hep nhat)."""
    nho = [n for n in nodes if n.visible and not n.resource_id and not (n.text or "").strip()
           and 0 < n.bounds.bottom - n.bounds.top <= 40 and 0 < n.bounds.right - n.bounds.left <= 120]
    hang: dict[int, list[DeviceNode]] = {}
    for n in nho:
        hang.setdefault(n.bounds.top // 4, []).append(n)
    for nhom in hang.values():
        if not 3 <= len(nhom) <= 6:
            continue
        rong = sorted(n.bounds.right - n.bounds.left for n in nhom)
        if rong[-1] >= 1.4 * rong[0] and rong[-2] < 1.4 * rong[0]:
            return nhom
    return []
