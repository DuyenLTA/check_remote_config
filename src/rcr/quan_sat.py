"""Theo doi man lien tuc: dump cay UI lien tiep, ghi moc gio cua MAY moi khung.

Dung cho cac dong Expected phai NHIN THEO THOI GIAN ma truoc day day het cho
nguoi ("X hien tai ~t0+5s", "co so dem nguoc", "KHONG hien X"). Nguoi test
khong biet tool dang chay toi case nao de ma nhin kip - tool tu nhin.

Moc gio lay bang `date` tren MAY, cung dong ho voi `logcat -v epoch`: doi chieu
truc tiep voi luc ad show / luc roi trang trong log (ob3_log), khong lech gio
giua may tinh va dien thoai.

Ten node doc tu layout `fragment_onboarding_3` trong APK Piclux 2.8.0:
    btnSkip         ImageView nut X - mac dinh GONE
    btnTimeoutSkip  TextView so dem nguoc (chu "5") - mac dinh GONE
GONE thi khong co trong dump -> co node = dang hien.
"""

from __future__ import annotations

import time

from . import fo_steps, ui_dump

X_IDS = ("btnSkip",)
DEM_IDS = ("btnTimeoutSkip",)


def _id(node) -> str:
    return node.resource_id.rsplit("/", 1)[-1]


def tim(nodes, ids) -> list:
    return [n for n in nodes if n.visible and not n.bounds.empty and _id(n) in ids]


async def gio_may(client, serial: str) -> float:
    out, _, _ = await client.shell(serial, "date", "+%s.%N")
    try:
        return float(out.strip())
    except ValueError:
        return time.time()          # may khong in %N -> dong ho may tinh, lech it


async def mot_khung(client, serial: str, package: str) -> tuple[dict, list]:
    """Mot lan nhin: (khung, nodes). Moc gio lay TRUOC dump - dump mat ~1-2s."""
    t = await gio_may(client, serial)
    nodes = ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package)
    dem = tim(nodes, DEM_IDS)
    khung = {"t": t, "x": bool(tim(nodes, X_IDS)),
             "dem": (dem[0].text or "").strip() if dem else "",
             "trang": fo_steps.onboarding_page(nodes)}
    return khung, nodes


async def theo_doi(client, serial: str, package: str, giay: float, khung: list,
                   dung_khi=None) -> list | None:
    """Nhin lien tuc trong `giay` giay, them khung vao `khung`.

    `dung_khi(nodes)` tra True thi dung som va tra `nodes` cua lan nhin do.
    """
    het = time.monotonic() + giay
    while time.monotonic() < het:
        k, nodes = await mot_khung(client, serial, package)
        khung.append(k)
        if dung_khi and dung_khi(nodes):
            return nodes
    return None
