"""ID ads tung vi tri lay tu checklist cua team, cho vi tri RC khong khai ID.

Tool quy mot request trong log ve vi tri bang cach so 3 so cuoi cua ID. Nguon
duy nhat truoc day la cac key `id_* = ca-app-pub-...` doc tu remote config cua
may - nhung app chi khai `id_*` cho tier goc va `_high`, trong khi bo TC test
chu yeu vao `high1`/`high2`. Thieu ID thi moi dong ve vi tri do deu ra
NOT_VERIFIABLE du log co du so lieu.

Nguon chinh: sheet "Check thong so KT" tai moi luot (`ad_units_sheet`), chon tab
theo package. `data/ad_units.yaml` la ban chep tay du phong. RC VAN THANG: ID doc
tu may la cai app THAT SU dung, con checklist chi la so team khai.
"""

from __future__ import annotations

from pathlib import Path

DATA = Path(__file__).parent / "data" / "ad_units.yaml"
# Ten vi tri noi loai ad -> loc bot khi hai vi tri trung 3 so cuoi (Piclux:
# `528` la ca 102-spl-n-inter-high1 lan 202-lfo2-n-native-high2, khac loai).
LOAI = (
    ("_inter", "interstitial"),
    ("_native", "native"),
    ("_banner", "banner"),
    ("_aoa", "app_open"),
    ("_reward", "rewarded"),
)


def bang(path: Path | None = None) -> dict[str, dict[str, str]]:
    """{package: {ten key: ID ads}}. Khong co file -> rong, khong phai loi."""
    import yaml

    try:
        data = yaml.safe_load((path or DATA).read_text(encoding="utf-8")) or {}
    except OSError:
        return {}
    return {pkg: dict(ids) for pkg, ids in data.items() if isinstance(ids, dict)}


# Bang doc tu sheet "Check thong so KT" o dau luot (`nap_sheet`). Rong khi chua
# nap - test khong goi nap nen khong bao gio cham mang.
_SHEET: dict[str, dict[str, str]] = {}


def nap_sheet(package: str, out_dir, log_fn=lambda _m: None) -> int:
    """Tai sheet, giu bang ID cua `package` cho ca luot. Tra so vi tri doc duoc."""
    from . import ad_units_sheet

    ids, ghi_chu = ad_units_sheet.tai(package, out_dir)
    log_fn(f"ID ads tung vi tri: {ghi_chu}")
    if ids:
        _SHEET[package] = ids
    return len(ids)


def cho_package(package: str, path: Path | None = None) -> dict[str, str]:
    """Sheet (ban moi nhat) de len file yaml chep tay; RC cua may de len ca hai (o noi goi)."""
    return bang(path).get(package, {}) | _SHEET.get(package, {})


def loai_cua(key: str) -> str:
    """Loai ad ma ten key noi toi, "" neu ten khong noi gi."""
    low = key.lower()
    for manh, loai in LOAI:
        if manh in low:
            return loai
    return ""
