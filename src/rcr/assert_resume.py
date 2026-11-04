"""Cham dong Expected ve QUANG CAO RESUME (mo lai app tu nen): 501 AOA, 502 native full, 503 inter.

Truoc day tool khong nhan ra cac dong nay (AD_TYPES khong co AOA, khong co khai niem resume) nen moi dong
"ad resume AOA 501_aoa_high hien thi" roi xuong "phai nhin mat" - lot AIP936 03/11/2026 phai do tren may ~12 dong.
Cham theo dung luat QA da chot 03/11/2026:
- resume co the hien o man tutorial; "khong show ad resume" o Splash / inter / notification la dung khi khong
  co show nao cua 50x;
- kho test khong fill -> request dung unit resume la dat (khong co ad de hien);
- "dong ad resume -> ve dung man X, reload native Y": man sau buoc cuoi phai la X; native Y khong fill thi app
  thoi request sau 3 lan fail (dung thiet ke) -> chi can vi tri Y co request trong luot.
"""

from __future__ import annotations

import re

from . import assert_ui
from .verdict_levels import CONFIG_BLOCKED, FAIL, NEEDS_HUMAN, PASS, out

RESUME_RE = re.compile(r"(?:ad|aoa|inter|native\s+full)\s+resume|resume\s+(?:ad|aoa|inter|50[123])", re.I)
MA_RESUME_RE = re.compile(r"(?<!\d)(50[123])(?!\d)")
MA_VI_TRI_RE = re.compile(r"(?<!\d)([1-4]\d\d)(?!\d)")
KHONG_RE = re.compile(r"kh[oô]ng\s+(?:show|hi[eệ]n|hi[eể]n\s+th[iị])", re.I)
DONG_VE_RE = re.compile(r"(?:đóng|dong|close|bấm close).{0,40}?(?:về|ve|quay lại)", re.I)
# Buoc dua app ra nen / mo lai: khong co buoc nay thi "khong request resume" chua noi len gi.
RA_NEN_RE = re.compile(r"home|recent|mở lại|mo lai|kill|launcher|notification|thông báo", re.I)


def _ma_cua(text: str) -> list[str]:
    ma = MA_RESUME_RE.findall(text)
    if ma:
        return sorted(set(ma))
    low = text.lower()
    if "aoa" in low or "app open" in low:
        return ["501"]
    if "native full" in low:
        return ["502"]
    if "inter" in low:
        return ["503"]
    return ["501", "502", "503"]


def _cua_vi_tri(units: list[dict], ma: str) -> list[dict]:
    return [u for u in units if any(f"_{ma}_" in k or k.startswith(f"id_{ma}_") for k in u.get("rc_keys") or [])]


def _da_ra_nen(drive: dict) -> bool:
    buoc = [str(st.get("step") or st.get("s") or "") for st in (drive or {}).get("steps") or []]
    return any(RA_NEN_RE.search(b) for b in buoc)


def _ten(units: list[dict]) -> str:
    return ", ".join(f"…{str(u.get('unit', ''))[-3:]}" for u in units) or "—"


def cham(text: str, ads: dict, drive: dict) -> dict | None:
    """Dong noi ve ad resume -> ket qua; dong khac -> None."""
    if not RESUME_RE.search(text or ""):
        return None
    units = list((ads.get("units") or {}).values())
    ma = _ma_cua(text)
    cua = [u for m in ma for u in _cua_vi_tri(units, m)]
    shown = [u for u in cua if u.get("shown")]
    req = [u for u in cua if u.get("requested")]
    vi_tri = "/".join(ma)

    if DONG_VE_RE.search(text):
        # Tra ten man CHI o ve truoc "reload": "ve dung Question, reload 305-onb5-..." co chu "onb" -> nham Onboarding.
        d = dict(drive or {})
        if d.get("final_sau_dong"):
            d["final"] = d["final_sau_dong"]       # man sau khi tool dong ad resume
        man = assert_ui._man_da_toi(re.split(r"reload", text, flags=re.I)[0], d)
        if man is None:
            return None
        native = [m for m in MA_VI_TRI_RE.findall(text.split("reload", 1)[-1]) if not m.startswith("50")]
        if not native:
            return man
        nv = [u for m in native for u in units if u.get("requested") and
              any(f"_{m}_" in k or k.startswith(f"id_{m}_") for k in u.get("rc_keys") or [])]
        if not nv:
            # Chay chuoi: log rieng case khong thay request vi native da fail >= 3 lan o case truoc -> app thoi
            # reload (dung thiet ke QA chot 03/11/2026). Chi tinh khi lich su ca chuoi KHONG co lan load duoc nao.
            truoc = [u for m in native for u in (ads.get("units_don") or {}).values()
                     if any(f"_{m}_" in k or k.startswith(f"id_{m}_") for k in u.get("rc_keys") or [])]
            hong = sum(u.get("load_failed", 0) for u in truoc)
            if hong >= 3 and not any(u.get("loaded") for u in truoc):
                return out(man["verdict"], f"{man['reason']}; native {'/'.join(native)} đã load hỏng {hong} lần ở "
                           "các bước trước trong chuỗi, chưa load được lần nào — app thôi reload (đúng thiết kế)", text)
            return out(FAIL if man["verdict"] == PASS else man["verdict"],
                       f"{man['reason']}; native {'/'.join(native)} không có request nào trong lượt", text)
        tom = ", ".join(f"…{str(u['unit'])[-3:]} request {u['requested']} lần" for u in nv)
        return out(man["verdict"], f"{man['reason']}; native {'/'.join(native)}: {tom} — không fill thì app "
                   "giữ vùng ad, request hỏng 3 lần thì thôi reload (đúng thiết kế)", text)

    if KHONG_RE.search(text):
        if shown:
            return out(FAIL, f"ad resume {vi_tri} vẫn show ({_ten(shown)})", text)
        them = f" (có request {_ten(req)}, không show)" if req else ""
        return out(PASS, f"không có show nào của ad resume {vi_tri}{them}", text)

    if shown:
        return out(PASS, f"ad resume {vi_tri} show ({_ten(shown)}, {sum(u['shown'] for u in shown)} lần)", text)
    if req:
        return out(PASS, f"ad resume {vi_tri} được request ({_ten(req)}) nhưng kho không fill — request đúng là đạt",
                   text)
    if not _da_ra_nen(drive):
        return out(NEEDS_HUMAN, "lượt chưa có bước đưa app ra nền rồi mở lại nên chưa có resume để chấm", text)
    san_sang = [st["aoa_san_sang"] for st in (drive or {}).get("steps") or [] if "aoa_san_sang" in st]
    if "501" in ma and san_sang:
        if not any(san_sang):
            # AOA chi show khi da load xong luc mo lai; chua load xong la do kho / mang, khong phai loi app.
            return out(CONFIG_BLOCKED, "AOA chưa load xong lúc mở lại app (đã chờ ở nền tới 20s) — kho/mạng chậm, "
                       "chưa tạo được điều kiện để resume hiện", text)
        loaded = [u for u in cua if u.get("loaded")]
        return out(FAIL, f"AOA đã load sẵn trước khi mở lại ({_ten(loaded)}) nhưng không show ad resume {vi_tri}",
                   text)
    co_load = [u for u in cua if u.get("loaded")]
    if co_load:
        return out(NEEDS_HUMAN, f"ad resume {vi_tri} có load ({_ten(co_load)}) nhưng không show, không rõ load xong "
                   "trước hay sau lúc mở lại", text)
    return out(FAIL, f"đã đưa app ra nền và mở lại nhưng không có request nào của ad resume {vi_tri}", text)
