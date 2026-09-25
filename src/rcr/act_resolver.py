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
Con lai -> NeedsHuman kem nguyen van cau, de nguoi doc biet phai lam gi.

"Hoan thanh luong FO den Home" / "Vao man Onboarding 2" van la NeedsHuman: do la
CA MOT CHUOI man hinh, khong phai mot thao tac - doan la lac ngay tu buoc dau.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .ui_dump import DeviceNode

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
DEFAULT_WAIT = 3.0
MAX_WAIT = 60.0


@dataclass(frozen=True, slots=True)
class Tap:
    node_label: str
    x: int
    y: int
    matched: str

    @property
    def summary(self) -> dict:
        return {"kind": "tap", "node": self.node_label, "x": self.x, "y": self.y,
                "matched": self.matched}


@dataclass(frozen=True, slots=True)
class Wait:
    seconds: float

    @property
    def summary(self) -> dict:
        return {"kind": "wait", "seconds": self.seconds}


@dataclass(frozen=True, slots=True)
class NoOp:
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "noop", "reason": self.reason}


@dataclass(frozen=True, slots=True)
class NeedsHuman:
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "needs_human", "reason": self.reason}


Action = Tap | Wait | NoOp | NeedsHuman


def resolve(step: str, nodes: list[DeviceNode]) -> Action:
    """Mot buoc Action -> thao tac. Khong dich duoc -> NeedsHuman."""
    text = (step or "").strip()
    if not text:
        return NoOp("buoc rong")
    if OBSERVE_RE.match(text):
        return NoOp("buoc quan sat - khong thao tac, chuyen sang cham")
    if LAUNCH_RE.match(text):
        return NoOp("tool da mo app sau khi patch - buoc nay da xong")
    if CONFIG_RE.match(text):
        return NoOp("config da duoc dat truoc do - buoc nay da xong")

    wait = WAIT_RE.match(text)
    if wait and not QUOTED_RE.search(text):
        seconds = float(wait.group(1)) if wait.group(1) else DEFAULT_WAIT
        if seconds > MAX_WAIT:
            return NeedsHuman(f"cho {seconds:g}s - qua {MAX_WAIT:g}s, TC co ve viet nham")
        return Wait(seconds)

    quoted = QUOTED_RE.search(text)
    if quoted:
        return _tap_by_text(quoted.group(1).strip(), nodes, f'chuoi trong ngoac: "{quoted.group(1)}"')

    tab = TAB_RE.match(text)
    if tab:
        return _tap_by_text(tab.group(1).strip(), nodes, f"ten tab: {tab.group(1)}")

    word = TAP_WORD_RE.match(text)
    if word and len(word.group(1)) <= 40:
        return _tap_by_text(word.group(1).strip(), nodes, f"chu sau dong tu: {word.group(1)}")

    return NeedsHuman(f"khong dich duoc buoc: {text!r}")


def _tap_by_text(wanted: str, nodes: list[DeviceNode], matched: str) -> Action:
    """Tim node theo text/content-desc. Phai DUY NHAT moi tap."""
    hits = find(wanted, nodes)
    if not hits:
        return NeedsHuman(f"khong thay node nao khop {wanted!r} tren man hinh")
    if len(hits) > 1:
        names = ", ".join(n.label for n in hits[:4])
        return NeedsHuman(
            f"{len(hits)} node cung khop {wanted!r} ({names}) - khong doan node nao la dung"
        )
    node = hits[0]
    x, y = node.bounds.center
    return Tap(node.label, x, y, matched)


def find(wanted: str, nodes: list[DeviceNode]) -> list[DeviceNode]:
    """Node khop text/content-desc. Uu tien khop DUNG HAN truoc khi khop mot phan.

    Chi xet node bam duoc: chu tren man hinh thuong nam o TextView khong
    clickable, con cai bam duoc la cha no - tap vao chu van trung vao cha.
    """
    want = wanted.casefold()
    pool = [n for n in nodes if n.visible and not n.bounds.empty]
    exact = [n for n in pool if want in (n.text.casefold(), n.content_desc.casefold())]
    if exact:
        return _outermost(exact)
    partial = [
        n for n in pool
        if want in n.text.casefold() or want in n.content_desc.casefold()
    ]
    return _outermost(partial)


def _outermost(hits: list[DeviceNode]) -> list[DeviceNode]:
    """Bo node nam TRONG node khac cung khop - cung mot chu, dung dem 2 lan."""
    ids = {n.node_id for n in hits}
    return [n for n in hits if not _has_ancestor(n, ids)]


def _has_ancestor(node: DeviceNode, ids: set[str]) -> bool:
    parent = node.parent_id
    while parent:
        if parent in ids:
            return True
        parent = parent.rsplit(".", 1)[0] if "." in parent else None
    return False
