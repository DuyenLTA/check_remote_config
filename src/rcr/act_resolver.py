"""Dich mot buoc Action trong file TC thanh thao tac tren may.

NGUYEN TAC: tha NEEDS_HUMAN con hon doan. Mot cu tap sai cho tren may that la
bam vao quang cao hoac mua hang that - hong ca luot test va ton tien that.
Vi vay: khong tim thay node, hoac tim ra NHIEU HON MOT node khop, deu tra
NeedsHuman. Khong bao gio lay node dau tien cho xong.

Cac dang cau nhan duoc (do tren 1272 buoc that cua bo TC chung):
    "Quan sat man hinh"          -> NoOp   (chuyen sang buoc cham)
    "Mo app" / "Cold start app"  -> NoOp   (tool da mo app o buoc patch roi)
    "Config RC"                  -> NoOp   (config da dat xong truoc do)
    'Nhan nut "See All"'         -> Tap    (chuoi trong ngoac kep)
    "Bam Submit"                 -> Tap    (chu sau dong tu, van phai khop DUY NHAT)
    "Mo tab Moment"              -> Tap    (ten tab)
    "Cho 3 giay"                 -> Wait
    "Vuot sang trai"             -> Swipe
Con lai -> NeedsHuman kem nguyen van cau, de nguoi doc biet phai lam gi.

"Hoan thanh luong FO den Home" / "Vao man Onboarding 2" -> GoTo: day la CA MOT
CHUOI man hinh, khong phai mot thao tac, nhung `fo_flow` biet duong di (luat o
`data/fo_flow.yaml`) nen giao cho no lai thay vi bo cho nguoi.

Ve sau dau phay chi duoc phep la ve QUAN SAT ("Chay luong FO den OB3, quan sat
banner"): quan sat la viec cua buoc cham, khong phai thao tac. Ve sau la viec
khac ("Vao OB3, ghi nhan thoi diem ad show") van la NeedsHuman - lai toi noi roi
coi nhu xong buoc la bo im cai ve sau, case do co the ra PASS gia. Cau khong mo
dau bang tu di chuyen cung khong nhan ("Vuot phai tai Onboarding 2" la VUOT,
khong phai di toi OB2).
"""

from __future__ import annotations

import re

from .act_types import (Action, Background, GoTo, Net, NeedsHuman, NoOp, Rotate, Seq,
                        Swipe, Tap, TapId, Wait, Watch)
from . import act_compound, net_ctl
from .act_nodes import find, tap_by_text
from .ui_dump import DeviceNode

__all__ = ["Action", "Background", "GoTo", "Net", "NeedsHuman", "NoOp", "Rotate", "Seq",
           "Swipe", "Tap", "TapId", "Wait", "Watch", "resolve", "find"]

# Buoc doi soat tren console ngoai (AdMob, Firebase, dashboard). Tool cham ads
# bang log cua may, khong mo console - nhung day KHONG phai cho phai dung lai:
# dung thi moi buoc sau do khong chay, trong khi buoc nay chang dong gi den app.
# Dong Expected tuong ung da co luat rieng o `assert_ads.EXTERNAL_RE`.
CONSOLE_RE = re.compile(r"admob|firebase\s*console|ad\s*manager|dashboard", re.I)
# Cau chi quan sat, khong thao tac.
OBSERVE_RE = re.compile(r"^\s*(quan\s*sát|quan\s*sat|kiểm\s*tra|kiem\s*tra|xem|observe|verify|check)\b", re.I)
# Chuoi trong ngoac kep - ngoac thang, ngoac cong, ngoac don kieu Viet.
QUOTED_RE = re.compile(r"[\"“”'‘’]([^\"“”'‘’]{1,60})[\"“”'‘’]")
# Buoc mo app: tool da tu mo app sau khi patch -> khong lam gi them.
# "Mo app -> LFO1" thi ve phai mui ten la man hinh MONG DOI, khong phai thao tac.
LAUNCH_RE = re.compile(r"^\s*(?:mở|mo|open|cold\s*start|khởi\s*động|khoi\s*dong)\s*(?:lại|lai)?\s*app\b", re.I)
# Buoc dat config: chinh la viec tool vua lam xong truoc do.
CONFIG_RE = re.compile(r"^\s*(?:config|cấu\s*hình|cau\s*hinh|set|đặt|dat)\s+(?:rc|remote\s*config)\b", re.I)
# "Bam Submit." - dong tu + ten nut, khong co ngoac kep. Van phai khop DUY NHAT
# mot node moi tap, nen khong phai la doan bua.
TAP_WORD_RE = re.compile(r"^\s*(?:bấm|bam|nhấn|nhan|chọn|chon|tap|click|press)\s+(?:vào|vao|nút|nut|button)?\s*(.+?)\s*[.。]?$", re.I)
TAB_RE = re.compile(r"^\s*(?:mở|mo|open|chuyển\s*sang|chuyen\s*sang)\s+tab\s+(.+?)\s*\.?$", re.I)
WAIT_RE = re.compile(r"^\s*(?:chờ|cho|đợi|doi|wait)\s*(\d+)?", re.I)
# Buoc "di toi mot man hinh". Phai MO DAU bang tu di chuyen: cau chi nhac ten
# man o giua ("Vuot phai tai Onboarding 2") khong phai lenh di toi man do.
GOTO_RE = re.compile(
    r"^\s*(?:hoàn\s*thành|hoan\s*thanh|vào|vao|đi\s*(?:đến|den|tới|toi)|di\s*(?:den|toi)"
    r"|chạy|chay|quay\s*(?:lại|lai)|trở\s*(?:lại|lai)|tro\s*(?:lai))\b",
    re.I)
# Cau vuot. KHONG doi hoi phai neu huong: vuot khong bam trung thu gi, nen doan
# sai huong chi lam man khong doi - khac han mot cu tap sai (bam quang cao, mua
# hang that). Khong neu huong thi lay huong sang trang ke, dung huong ma
# `fo_flow` dung de di qua OB1/2/3.
SWIPE_RE = re.compile(r"^\s*(?:vuốt|vuot|swipe|lướt|luot|kéo|keo)\b", re.I)
DIRECTION_WORDS = (
    (re.compile(r"\b(?:trái|trai|left)\b", re.I), "left"),
    (re.compile(r"\b(?:phải|phai|right)\b", re.I), "right"),
    (re.compile(r"\b(?:lên|len|up)\b", re.I), "up"),
    (re.compile(r"\b(?:xuống|xuong|down)\b", re.I), "down"),
)
DEFAULT_SWIPE = "left"
# Ve dung sau dau phay/cham phay. Ve quan sat thi bo qua duoc, ve khac thi khong.
CLAUSE_RE = re.compile(r"[,;]")
DEFAULT_WAIT = 3.0
# "Cho het timeout load ad" - TC khong neu so giay. Dat cao hon timeout load ad
# thuong gap (~10s) de cu cho phu het ca lan thu cuoi cung.
CHO_TIMEOUT_ADS = 12.0
TIMEOUT_RE = re.compile(r"timeout|h[ếe]t\s*gi[ờo]", re.I)
MAX_WAIT = 60.0


def resolve(step: str, nodes: list[DeviceNode]) -> Action:
    """Mot buoc Action -> thao tac. Khong dich duoc -> NeedsHuman."""
    text = (step or "").strip()
    if not text:
        return NoOp("bước rỗng")
    ghep = act_compound.resolve(text, nodes, resolve)
    if ghep is not None:
        return ghep
    if OBSERVE_RE.match(text):
        return NoOp("bước quan sát — không thao tác, chuyển thẳng sang chấm")
    # Cau ve MANG phai xet truoc cau mo app: "Mo app khong mang" khop ca hai,
    # ma ve "khong mang" moi la thu case dang hoi. Bo im ve do = PASS gia.
    if net_ctl.BAT_RE.search(text):
        return Net(True, "bước bảo bật lại mạng")
    if LAUNCH_RE.match(text):
        if net_ctl.TAT_RE.search(text):
            return NoOp("app đã được mở sẵn trong lúc mạng đang tắt — bước này xong rồi")
        return NoOp("app đã được mở lại sau khi đặt config — bước này xong rồi")
    if net_ctl.TAT_RE.search(text):
        return Net(False, "bước bảo tắt mạng")
    if CONFIG_RE.match(text):
        return NoOp("config đã được đặt trước đó — bước này xong rồi")
    if CONSOLE_RE.search(text) and not QUOTED_RE.search(text):
        # "Hoan thanh luong FO, doi soat AdMob console": ve doi soat la viec cua
        # PO, nhung ve DAU van la mot chuyen di that. Bo ca cau la bo luon cu
        # lai, va moi dong cham ve man cuoi deu thanh "chua toi noi".
        di = _goto(text)
        if di:
            return di
        return NoOp("đối soát trên console ngoài — việc của PO; tool chấm ads bằng log "
                    "của máy. Bước này không động gì đến app nên đi tiếp")

    wait = WAIT_RE.match(text)
    if wait and not QUOTED_RE.search(text):
        seconds = act_compound.so_giay(text) or (
            float(wait.group(1)) if wait.group(1) else DEFAULT_WAIT)
        if seconds > MAX_WAIT:
            return NeedsHuman(f"chờ {seconds:g}s — quá {MAX_WAIT:g}s, TC có vẻ viết nhầm")
        return Wait(seconds)

    if SWIPE_RE.match(text):
        return _swipe(text)

    quoted = QUOTED_RE.search(text)
    if quoted:
        return tap_by_text(quoted.group(1).strip(), nodes, f'chuoi trong ngoac: "{quoted.group(1)}"')

    tab = TAB_RE.match(text)
    if tab:
        return tap_by_text(tab.group(1).strip(), nodes, f"ten tab: {tab.group(1)}")

    word = TAP_WORD_RE.match(text)
    if word and len(word.group(1)) <= 40:
        return tap_by_text(word.group(1).strip(), nodes, f"chu sau dong tu: {word.group(1)}")

    goto = _goto(text)
    if goto:
        return goto
    return NeedsHuman(f"không dịch được bước: {text!r}")


def _swipe(text: str) -> Action:
    """Cau vuot -> Swipe. Huong lay tu cau, khong neu thi lay huong sang trang ke."""
    for pattern, direction in DIRECTION_WORDS:
        if pattern.search(text):
            return Swipe(direction, f"hướng nêu trong câu: {direction}")
    return Swipe(DEFAULT_SWIPE, "TC không nêu hướng — lấy hướng sang trang kế")


def _goto(text: str) -> Action | None:
    """Buoc thuan di chuyen -> GoTo. Khong phai thi tra None."""
    from . import fo_flow  # noi day de tranh vong import khi fo_flow lon len

    head, *rest = CLAUSE_RE.split(text)
    if not GOTO_RE.match(head):
        return None
    # Ve sau duoc phep la: quan sat, doi soat console (viec cua PO), hoac mot
    # cu CHO - cho thi lam duoc that nen khong bo. Con lai la mot viec khac ma
    # buoc nay khong lam -> tra None, de cau roi ve NeedsHuman.
    cho = 0.0
    for ve in (v.strip() for v in rest):
        if not ve or OBSERVE_RE.match(ve) or CONSOLE_RE.search(ve):
            continue
        giay = _cho_bao_lau(ve)
        if giay is None:
            return None
        cho = max(cho, giay)
    target = fo_flow.target_for(head)
    if not target:
        return None
    ly_do = f"lái qua luồng FO tới {target}"
    return GoTo(target, ly_do + (f", chờ {cho:g}s tại đó" if cho else ""), cho)


def _cho_bao_lau(ve: str) -> float | None:
    """Ve nay la mot cu cho? -> so giay. Khong phai cho -> None.

    "cho het timeout load ad" khong neu so giay: lay CHO_TIMEOUT_ADS, dat cao
    hon timeout load ad thuong gap de chac chan cu cho phu het lan thu cuoi.
    """
    m = WAIT_RE.match(ve)
    if not m:
        return None
    giay = act_compound.so_giay(ve)
    if giay:
        return giay
    if m.group(1):
        return float(m.group(1))
    return CHO_TIMEOUT_ADS if TIMEOUT_RE.search(ve) else DEFAULT_WAIT
