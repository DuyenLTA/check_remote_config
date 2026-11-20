"""Bo IAA chay theo NHOM bien the: dat config mot bien the cho MOI vi tri cung luc.

Luot AIP893 2.6.0 (12-13/11/2026): 9 vi tri x 4 bien the = 36 case, tool khong lai duoc cau
"Di toi vi tri X dung nhu mo ta" nen Claude lai app 36 lan. Bien the cua cac vi tri doc lap nhau
(moi vi tri mot cap key show_<ten>_high / show_<ten>), nen dat cung luc bien the "bat" cho ca 9 vi tri
roi lai app MOT lan la du log cho ca 9 case `-01`; tuong tu `-02` (chi thuong), `-03` (chi high),
`-04` (tat). 4 lan lai app thay vi 36.
"""

from __future__ import annotations

from .models import RcError
from .tc_iaa_tu_sheet_kt import ViTri

# Bien the -> (so case, bat tang high?, bat tang thuong?). Khop thu tu `tao_case`: -01 bat ca hai,
# -02 chi thuong, -03 chi high, -04 tat.
BIEN_THE = {
    "bat": (1, True, True),
    "thuong": (2, False, True),
    "high": (3, True, False),
    "tat": (4, False, False),
}


def so_case(bien_the: str) -> int:
    if bien_the not in BIEN_THE:
        raise RcError(f"Biến thể phải là một trong: {', '.join(BIEN_THE)} (nhận được {bien_the!r})")
    return BIEN_THE[bien_the][0]


def gia_tri(ds: list[ViTri], bien_the: str) -> dict[str, str]:
    """{key RC: 'true'/'false'} cua bien the cho moi vi tri.

    Vi tri chi co mot tang khong co case `-02`/`-03`: o hai bien the do giu tang duy nhat BAT de lai app
    van thay vi tri (khong anh huong vi tri khac, khong co case nao cham no o luot nay)."""
    so_case(bien_the)
    _, high, thuong = BIEN_THE[bien_the]
    ra: dict[str, str] = {}
    for v in ds:
        hai_tang = v.high is not None and v.thuong is not None
        for tang, bat in ((v.high, high), (v.thuong, thuong)):
            if tang is None:
                continue
            if not hai_tang and bien_the in ("thuong", "high"):
                bat = True
            ra[tang.key] = "true" if bat else "false"
    return ra


def config_cua_case(ds: list[ViTri], ma: str) -> dict[str, str]:
    """Key RC `rcr-iaa` da dat cho vi tri cua case `IAA-ii-nn` o bien the nn (de report hien o "Config da dat";
    khung `--khung` khong dat config theo case nen record de trong -> report tung ghi "khong dat key nao")."""
    try:
        _, i, n = ma.split("-")
        bien_the = next(b for b, (so, *_) in BIEN_THE.items() if so == int(n))
        v = ds[int(i) - 1]
    except (ValueError, StopIteration, IndexError):
        return {}
    return gia_tri([v], bien_the)


def ma_case(i: int, bien_the: str) -> str:
    """Vi tri thu i (dem tu 1, thu tu sheet) -> ma case cua bien the, vd IAA-03-02."""
    return f"IAA-{i:02d}-{so_case(bien_the):02d}"


def ap_unit_that(ds: list[ViTri], unit_that: dict[str, str]) -> tuple[list[ViTri], list[str]]:
    """Thay ID sheet bang unit THAT cua build (`{ten ad tren sheet: ID}`, vd `inter_feature_high`).

    Sheet "Check thong so KT" ghi ID khong co trong build (audit 3c bao lech): cham theo ID sheet thi moi vi tri ra
    "0 request" -> FAIL gia (AIP933 Hypix 20/11/2026: 16/16 ID muc 3 vang trong APK). Luat rc-check 3c: dong ads cua
    vi tri lech cham theo unit that trong log. Tra (ds moi, ["ten: ID sheet -> ID that"]); ten khong co tren sheet
    -> RcError (go sai ten la cham nham vi tri)."""
    from dataclasses import replace
    con = dict(unit_that)
    ra, doi = [], []
    for v in ds:
        moi = {}
        for tang_ten in ("high", "thuong"):
            t = getattr(v, tang_ten)
            if t is not None and t.ten in con:
                id_moi = con.pop(t.ten)
                doi.append(f"{t.ten}: {t.id} -> {id_moi}")
                moi[tang_ten] = replace(t, id=id_moi)
        ra.append(replace(v, **moi) if moi else v)
    if con:
        co = sorted(t.ten for v in ds for t in (v.high, v.thuong) if t)
        raise RcError(f"--unit-that: không có ad {', '.join(sorted(con))} trên sheet (có: {', '.join(co)})")
    return ra, doi


def ban_do_unit(ds: list[ViTri]) -> dict[str, tuple[int, str]]:
    """ID day du `ca-app-pub-.../...` -> (so vi tri, 'high'|'thuong')."""
    ra = {}
    for i, v in enumerate(ds, 1):
        if v.high:
            ra[v.high.id] = (i, "high")
        if v.thuong:
            ra[v.thuong.id] = (i, "thuong")
    return ra
