"""Dong Expected co DIEU KIEN "Trong luc <vi tri X> dang hien thi: ..." - X phai show that moi cham ve sau.

AIP886 31/10/2026 (R03-02): "Trong luc inter resume 503_inter_high dang hien thi: logcat KHONG co log show 201"
ra PASS trong khi luot do KHONG co request 503 nao - ve phu dinh "khong co log 201" dung mot cach vo nghia
vi dieu kien chua bao gio xay ra. PASS gia.
"""

from __future__ import annotations

import re

from .ad_positions import _khop_vi_tri, _position_token
from .verdict_levels import NEEDS_HUMAN, NOT_VERIFIABLE, PASS, out

TRONG_LUC_RE = re.compile(
    r"trong\s+(?:l[úu]c|khi)\s+(?P<dk>.{3,80}?)\s+(?:[đd]ang\s+)?(?:hi[ểe]n\s*th[ịi]|show)", re.I)


# "Inter 102 hien thi full man, khong lo background device phia sau": hoi HINH ANH luc ad dang hien. Luat
# "request dung ma kho khong fill = PASS" khong ap duoc - chua co ad thi chua co gi de nhin (S03 AIP886).
# "khong lo" phai co dau (lộ): khong dau thi an nham "Khong load ..." (dong phu dinh ads thuong).
TRON_MAN_RE = re.compile(r"full\s*m[àa]n|to[àa]n\s*m[àa]n|ph[ủu]\s*k[íi]n|kh[ôo]ng\s+lộ\b|l[ộo]\s+(?:n[ềe]n|background)",
                         re.I)


def hien_thi_tron(text: str, units: list[dict], kind: str) -> dict | None:
    """Dong hoi ad hien thi kin man: chua show -> NEEDS_HUMAN; da show -> phai nhin anh (NOT_VERIFIABLE)."""
    if not kind or not TRON_MAN_RE.search(text):
        return None
    token = _position_token(text)
    thuoc = [u for u in units if token and _khop_vi_tri(u, token)]
    if any(u.get("shown") for u in thuoc):
        return out(NOT_VERIFIABLE, f"{token} đã show — dòng hỏi ad có kín màn không, phải xem khung hình lúc ad hiện",
                   token, tinh=True)
    yeu_cau = sum(int(u.get("requested") or 0) for u in thuoc)
    return out(NEEDS_HUMAN, f"{token or kind} chưa show ({yeu_cau} request, kho không fill) — chưa có ad để xem "
                            "hiển thị kín màn, chạy lại khi có fill", token)


KHONG_SHOW_RE = re.compile(r"kh[ôo]ng\s+(?:c[óo]\s+)?(?:log\s+)?(?:show|hi[ểe]n)", re.I)


def _ve_sau(sau: str, units: list[dict], token_dk: str) -> dict | None:
    """Dieu kien da xay ra: "... KHONG co log show 201-lfo1-n-native-high" -> vi tri o VE SAU khong duoc show.
    Truoc day luat ads lay ma dau tien trong cau (503) -> "khong request native nao cua 503" -> PASS sai ly do."""
    token = _position_token(sau)
    if not token or not KHONG_SHOW_RE.search(sau):
        return None
    thuoc = [u for u in units if _khop_vi_tri(u, token)]
    so_show = sum(int(u.get("shown") or 0) for u in thuoc)
    if not so_show:
        yeu_cau = sum(int(u.get("requested") or 0) for u in thuoc)
        return out(PASS, f"{token_dk} đã show; {token} không show lần nào trong lượt ({yeu_cau} request)", token)
    return out(NEEDS_HUMAN, f"{token_dk} đã show và {token} có {so_show} lần show — cần đối chiếu mốc giờ xem có "
                            f"trùng lúc {token_dk} đang hiển thị không", token)


def cham(text: str, units: list[dict]) -> dict | None:
    """Dieu kien khong xay ra -> NEEDS_HUMAN kem so do; xay ra / khong phai cau dieu kien -> None."""
    m = TRONG_LUC_RE.search(text)
    if not m:
        return None
    token = _position_token(m.group("dk"))
    if not token:
        return None
    thuoc = [u for u in units if _khop_vi_tri(u, token)]
    if any(u.get("shown") for u in thuoc):
        return _ve_sau(text[m.end():], units, token)
    yeu_cau = sum(int(u.get("requested") or 0) for u in thuoc)
    return out(NEEDS_HUMAN, f"điều kiện '{m.group('dk').strip()} đang hiển thị' không xảy ra trong lượt "
                            f"({token}: {yeu_cau} request, không show) — vế sau chưa kết luận được, chạy lại "
                            "khi kho có fill", token)
