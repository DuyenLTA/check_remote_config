"""Dung bo case IAA (ads in-app) tu muc "3. ID ads inapp" cua tab app trong sheet "Check thong so KT".

QA dan thang bang vi tri ads in-app cua app vao muc 3 (user chot 12/11/2026): moi dong mot ad
(ten `native_loading_high` / `native_loading`, uu tien 1/2, mo ta logic preload / show / reload,
loai ad, ID `ca-app-pub-...`, key RC `show_<ten>`). Cot khong co dinh -> doc theo NOI DUNG o, khong
theo chi so cot (dong tiep theo cua cap high/thuong de trong o man hinh, o mo ta).

Moi vi tri (cap high + thuong) ra 4 case: bat ca hai, chi thuong, chi high, tat remote. Dong mo ta
cua sheet thanh dong Expected cua case "bat ca hai" - Claude doc va cham tay theo muc 5b.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Case, RcError

MUC_INAPP_RE = re.compile(r"^\s*3\s*\.\s*ID ads in\s*-?\s*app", re.I)
MUC_KHAC_RE = re.compile(r"^\s*\d+\s*\.\s+\S")
ID_RE = re.compile(r"^ca-app-pub-\d+/\d+$")
TEN_RE = re.compile(r"^[a-z0-9][a-z0-9_]*[a-z][a-z0-9_]*$")
# Cot loai ad: sheet co cho go sai ("Intersitial") -> so theo tien to.
LOAI = (("native", "Native"), ("banner", "Banner"), ("inter", "Interstitial"),
        ("reward", "Reward"), ("app open", "App Open"), ("appopen", "App Open"), ("open", "App Open"))


@dataclass(frozen=True)
class Tang:
    """Mot tang uu tien cua vi tri (high hoac thuong)."""
    ten: str
    id: str
    key: str


@dataclass
class ViTri:
    goc: str                       # ten bo `_high`: native_loading
    man: str = ""
    loai: str = ""
    mo_ta: str = ""
    high: Tang | None = None
    thuong: Tang | None = None


def _loai(o: str) -> str:
    low = o.strip().lower()
    if len(low) > 20:
        return ""
    return next((ten for tien_to, ten in LOAI if low.startswith(tien_to)), "")


def _doc_dong(o: list[str]) -> dict | None:
    """Mot dong cua muc 3 -> {ten, id, key, loai, mo_ta, man}; dong khong co ID ads -> None."""
    ma = next((c for c in o if ID_RE.match(c)), "")
    if not ma:
        return None
    key = next((c.lower() for c in o if re.fullmatch(r"show_[a-z0-9_]+", c, re.I)), "")
    ten_i = next((i for i, c in enumerate(o) if TEN_RE.match(c) and not c.startswith("show_")), -1)
    if ten_i < 0:
        return None
    ten = o[ten_i]
    loai = next((_loai(c) for c in o if _loai(c)), "")
    dai = [c for c in o if len(c) >= 30 and not ID_RE.match(c) and c != key]
    mo_ta = max(dai, key=len) if dai else ""
    # O man hinh: chu dung truoc o ten, khong phai so thu tu / uu tien.
    # openpyxl doc o STT thanh "1.0".
    man = next((c for c in o[:ten_i] if not re.fullmatch(r"\d+(?:\.0+)?", c) and c != mo_ta), "")
    return {"ten": ten, "id": ma, "key": key or f"show_{ten}", "loai": loai, "mo_ta": mo_ta, "man": man}


def doc_muc_inapp(rows: list[list[str]]) -> list[ViTri]:
    """Cac dong (o da strip, bo o trong) cua tab app -> vi tri in-app theo thu tu tren sheet."""
    trong_muc, man_truoc = False, ""
    vi_tri: dict[str, ViTri] = {}
    for o in rows:
        if not o:
            continue
        if MUC_INAPP_RE.match(o[0]):
            trong_muc = True
            continue
        if trong_muc and MUC_KHAC_RE.match(o[0]) and not ID_RE.match(o[0]) and len(o) == 1:
            break                                      # sang muc "4. ID ads resume"
        if not trong_muc:
            continue
        d = _doc_dong(o)
        if not d:
            continue
        man_truoc = d["man"] or man_truoc
        goc = re.sub(r"_high$", "", d["ten"])
        v = vi_tri.setdefault(goc, ViTri(goc=goc, man=man_truoc))
        v.loai = v.loai or d["loai"]
        v.mo_ta = v.mo_ta or d["mo_ta"]
        tang = Tang(d["ten"], d["id"], d["key"])
        if d["ten"].endswith("_high"):
            v.high = tang
        else:
            v.thuong = tang
    return list(vi_tri.values())


def _dong_mo_ta(mo_ta: str) -> list[str]:
    """Moi dong khong trong cua o mo ta -> mot dong Expected, giu nguyen chu (ke ca '*', '-', '=>')."""
    return [d.strip() for d in mo_ta.splitlines() if d.strip()]


def _case(n: str, v: ViTri, bien_the: str, bat: dict[Tang, bool], expects: list[str]) -> Case:
    noi = v.man or v.goc
    return Case(
        n=n, feature=f"IAA · {noi}", description=f"{v.goc} — {v.loai or 'ads'}", sub_scenario=bien_the,
        precondition="User free (chưa mua Premium). Mô tả vị trí lấy từ mục 3 ID ads inapp, sheet Check thông số KT.",
        test_data="\n".join(f"{t.key}={'true' if b else 'false'}" for t, b in bat.items()),
        actions=(f"Đi tới vị trí {noi} đúng như mô tả (màn preload, thao tác hiển thị, thao tác reload).",
                 "Quan sát hiển thị ads + log request / load / show của app."),
        expects=tuple(expects), user_state="old_user",
    )


def tao_case(ds: list[ViTri]) -> list[Case]:
    """Moi vi tri -> case bat ca hai / chi thuong / chi high / tat remote (tang nao thieu thi bo bien the do)."""
    out: list[Case] = []
    for i, v in enumerate(ds, 1):
        noi, loai = v.man or v.goc, v.loai or "ads"
        tang = [t for t in (v.high, v.thuong) if t]
        ma = lambda k: f"IAA-{i:02d}-{k:02d}"  # noqa: E731 - ma case on dinh theo thu tu vi tri tren sheet
        don = (f"Request ads đúng unit high {v.high.id} trước; high không fill thì gọi unit thường {v.thuong.id}."
               if v.high and v.thuong else f"Request ads đúng unit {tang[0].id}.")
        out.append(_case(ma(1), v, "Bật remote (high + thường)" if len(tang) == 2 else "Bật remote",
                         {t: True for t in tang},
                         # Expected = NGUYEN VAN tung dong cot Ad description (user chot 12/11/2026: check dung
                         # chinh xac cot nay, khong them cau tu viet) + dong ID lay tu cot ID cua sheet.
                         [*_dong_mo_ta(v.mo_ta), don]))
        if v.high and v.thuong:
            out.append(_case(ma(2), v, "Chỉ bật tầng thường", {v.high: False, v.thuong: True},
                             [f"Chỉ request unit thường {v.thuong.id}, không request unit high {v.high.id}.",
                              f"Có fill thì {loai} vẫn hiển thị tại {noi}."]))
            out.append(_case(ma(3), v, "Chỉ bật tầng high", {v.high: True, v.thuong: False},
                             [f"Chỉ request unit high {v.high.id}, không request unit thường {v.thuong.id}.",
                              f"Có fill thì {loai} vẫn hiển thị tại {noi}."]))
        out.append(_case(ma(4), v, "Tắt remote", {t: False for t in tang},
                         [f"Không request unit nào của vị trí ({', '.join(t.id for t in tang)}).",
                          f"Không preload, không hiển thị {loai} tại {noi}."]))
    return out


def tu_workbook(path, package: str) -> list[Case]:
    """File xlsx sheet KT -> case IAA cua tab co dong `Package name` = package."""
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            rows = [[str(v).strip() for v in r if v not in (None, "") and str(v).strip()]
                    for r in ws.iter_rows(values_only=True)]
            if not any(len(r) >= 2 and r[0].lower() == "package name" and r[1] == package for r in rows):
                continue
            ds = doc_muc_inapp(rows)
            if not ds:
                raise RcError(f"Tab {ws.title} (sheet Check thông số KT) chưa có vị trí nào ở mục "
                              "'3. ID ads inapp' - dán kịch bản IAA của app vào mục đó rồi chạy lại.")
            return tao_case(ds)
    finally:
        wb.close()
    raise RcError(f"Sheet Check thông số KT không có tab nào ghi Package name = {package}.")
