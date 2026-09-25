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


def language_targets(nodes: list[DeviceNode], language: str) -> list[DeviceNode]:
    """Cac node can bam de chon `language`, theo dung thu tu.

    Hang co checkbox -> chon thang. Hang co icon bung -> bam bung roi lay BIEN
    THE DAU TIEN ben trong (khop theo ten bien the la them mot thu phai theo doi
    ban build: "English (US)" hay "English (United States)").
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
    below = [n for n in rows if n.bounds.top > row.bounds.bottom]
    variants = [n for n in below if n.bounds.left > row.bounds.left]
    if variants:
        return [variants[0]]          # da bung san - bam lai icon la GAP LAI
    return [row, "expanded"]          # can bung roi doc lai o vong sau


def onboarding_page(nodes: list[DeviceNode]) -> int:
    """Dang o trang onboarding thu may (1-based). 0 neu khong doc duoc.

    Cac trang OB dung CHUNG mot activity, nen ten man khong phan biet duoc
    OB1/OB2/OB3. Doc theo cham chi trang: cham cua trang hien tai duoc keo DAI
    ra (do that: 53px so voi 21px cua cham thuong).
    """
    dots = [n for n in nodes if n.resource_id == DOT_ID and n.visible]
    if not dots:
        return 0
    dots.sort(key=lambda n: n.bounds.left)
    widest = max(dots, key=lambda n: n.bounds.right - n.bounds.left)
    return dots.index(widest) + 1
