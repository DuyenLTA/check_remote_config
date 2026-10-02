"""Doc cac buoc Action dang CAU GHEP ma luat co ban cua `act_resolver` nuot mat.

Moi luat o day sinh ra tu mot cau that trong bo TC 3.5.0 da lam tool hoac dung
sai ly do, hoac te hon: KHONG dung ma lam sai im lang:
    "Vuot trai nhanh lien tuc 3-4 lan"       -> truoc: vuot 1 lan
    "Vuot phai ve OB2, roi vuot trai lai OB3" -> truoc: vuot 1 lan, sang TRAI
    "Vao OB3, cho qua 10s khong thao tac"     -> truoc: cho 3s (chua het timer)
    "Bam gio tu t0"                           -> truoc: di tim nut ten "gio"

`resolve(text, nodes, base)`: khop luat nao thi tra thao tac, khong thi None
de `act_resolver` xet tiep bang luat co ban. `base` la chinh `act_resolver.
resolve`, truyen vao de doc ve con lai ma khong import vong.
"""

from __future__ import annotations

import re

from .act_types import Background, NeedsHuman, NoOp, Rotate, Seq, Swipe, Tap, Wait

# "Tai t0+2s: vuot trai" - moc tinh tu luc vua toi man. `case_drive` cho toi
# moc roi moi lam ve sau dau hai cham.
MOC_T0_RE = re.compile(r"^\s*t[ạa]i\s+t0\s*\+\s*(\d+(?:[.,]\d+)?)\s*(?:s|giây|giay)\b\s*[:,]?\s*",
                       re.I)
# So giay o bat ky dau trong cau: "cho 5s", "cho them 10s", "(5s)", "3 giay".
SO_GIAY_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:s|giây|giay|sec)\b", re.I)
QUA_RE = re.compile(r"\bqu[áa]\s+\d", re.I)
# "Cho qua 10s" phai cho QUA moc, khong phai dung moc: cong them cho chac.
VUOT_MOC = 2.0
BAM_GIO_RE = re.compile(r"\bb[ấa]m\s*gi[ờo]\b", re.I)
KHONG_THAO_TAC_RE = re.compile(r"^\s*kh[ôo]ng\s+thao\s+t[áa]c\b", re.I)
NOI_TIEP_RE = re.compile(r"^\s*(?:sau\s+[đd][óo]|r[ồo]i|ti[ếe]p\s+(?:theo|[đd][óo]))\s*,?\s+", re.I)
# "O OB3, cho 3s", "O man ke cho them 5s" - ve dau chi noi dang o dau.
O_MAN_CHO_RE = re.compile(r"^\s*[ởo]\s+[^,]{1,30}?,?\s*(?=(?:chờ|cho|đợi|doi)\b)", re.I)
HOME_RE = re.compile(r"\bnh[ấa]n\s+home\b|\bb[ấa]m\s+home\b|\bbackground\b", re.I)
XOAY_RE = re.compile(r"^\s*xoay\b", re.I)
HUONG_XOAY_RE = re.compile(r"\b(ngang|d[ọo]c)\b", re.I)
NHANH_RE = re.compile(
    r"\s*nhanh\s+li[êe]n\s+t[ụu]c\s+(\d+)(?:\s*[-–]\s*(\d+))?\s*l[ầa]n(?:\s+trong\s*<?\s*\d+\s*s)?",
    re.I)
CHUOI_RE = re.compile(r"\s*,?\s*\br[ồo]i\b\s*|\s*→\s*", re.I)
SPLASH_XONG_RE = re.compile(r"^\s*ho[àa]n\s*th[àa]nh\s+splash\b", re.I)
X_HIEN_RE = re.compile(r"^\s*(?:n[úu]t\s+|button\s+)?X\s+(?:xu[ấa]t\s+)?hi[ệe]n\b", re.I)
# Cho het splash: phu het timeout load inter (~10s) - giong `CHO_TIMEOUT_ADS`.
CHO_SPLASH = 12.0
CHO_NEN_MAC_DINH = 10.0
TEN_HUONG = {"left": "trái", "right": "phải", "up": "lên", "down": "xuống"}


def so_giay(text: str) -> float | None:
    """So giay neu trong cau. "qua N" -> N + VUOT_MOC. Khong co so -> None."""
    m = SO_GIAY_RE.search(text or "")
    if not m:
        return None
    giay = float(m.group(1).replace(",", "."))
    return giay + VUOT_MOC if QUA_RE.search(text) else giay


def moc_t0(step: str) -> tuple[float, str] | None:
    """"Tai t0+2s: vuot trai" -> (2.0, "vuot trai"). Khong co moc -> None."""
    m = MOC_T0_RE.match(step or "")
    if not m:
        return None
    return float(m.group(1).replace(",", ".")), step[m.end():].strip()


def resolve(text: str, nodes, base):
    if BAM_GIO_RE.search(text):
        return NeedsHuman("bước bấm giờ: case cần đo khoảng thời gian từ lúc ad show — "
                          "tool chưa đo được thời gian (phần đo timer làm riêng)")
    if MOC_T0_RE.match(text):
        # `case_drive` da tach moc ra truoc; con toi day la cau goi thang.
        return base(moc_t0(text)[1], nodes)
    if X_HIEN_RE.match(text):
        return NoOp("mốc quan sát: nút X phải hiện — chấm ở dòng Expected")
    if KHONG_THAO_TAC_RE.match(text):
        return NoOp("bước bảo không thao tác — đứng yên, chuyển sang bước sau")
    if NOI_TIEP_RE.match(text):
        return base(NOI_TIEP_RE.sub("", text, count=1), nodes)
    if SPLASH_XONG_RE.match(text):
        return Wait(CHO_SPLASH)
    if O_MAN_CHO_RE.match(text):
        return base(O_MAN_CHO_RE.sub("", text, count=1), nodes)
    if HOME_RE.search(text):
        giay = so_giay(text) or CHO_NEN_MAC_DINH
        return Background(giay, f"nhấn Home, để app nằm nền {giay:g}s")
    if XOAY_RE.match(text):
        return _xoay(text)
    nhanh = NHANH_RE.search(text)
    if nhanh:
        return _lien_tuc(text, nhanh, nodes, base)
    return _chuoi(text, nodes, base)


def _xoay(text: str):
    huong = tuple("ngang" if h.lower() == "ngang" else "doc"
                  for h in HUONG_XOAY_RE.findall(text))
    if not huong:
        return NeedsHuman(f"câu xoay màn không nêu hướng: {text!r}")
    if huong[-1] != "doc":
        huong += ("doc",)        # luon tra man ve doc: cac buoc sau chup theo man doc
    return Rotate(huong, "xoay " + " → ".join("ngang" if h == "ngang" else "dọc" for h in huong))


def _lien_tuc(text: str, nhanh, nodes, base):
    """Bo ve "nhanh lien tuc N(-M) lan" ra, doc phan con lai, roi nhan so lan."""
    lan = int(nhanh.group(2) or nhanh.group(1))
    con = (text[:nhanh.start()] + text[nhanh.end():]).strip(" .")
    act = base(con, nodes)
    if isinstance(act, Swipe):
        return Swipe(act.direction, act.matched, lan)
    if isinstance(act, Tap):
        return Tap(act.node_label, act.x, act.y, act.matched, lan)
    return act


def _chuoi(text: str, nodes, base):
    """Cau vuot noi bang "roi"/"→" -> Seq. Chi nhan khi MOI ve deu la vuot.

    Ve nao khong phai vuot thi tra None: de nguyen cau cho luat co ban, roi
    no se ra NeedsHuman neu khong doc duoc - khong lam mot nua roi bo nua kia.
    """
    if not re.match(r"^\s*(?:vuốt|vuot|swipe)\b", text, re.I) or not CHUOI_RE.search(text):
        return None
    ve = [v.strip(" .") for v in CHUOI_RE.split(text) if v.strip(" .")]
    acts = tuple(base(v, nodes) for v in ve)
    if len(acts) < 2 or not all(isinstance(a, Swipe) for a in acts):
        return None
    return Seq(acts, "vuốt " + " rồi ".join(TEN_HUONG.get(a.direction, a.direction) for a in acts))
