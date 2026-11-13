"""Doc popup Rating (SDK com.apero.rating) tren may: sao, nut Rate, nut X, shortcut, event; do luc nut X hien.

Cay node cua popup (Compose, do AIP892 12/11/2026): sao la node content-desc "Star 1".."Star 5", nut X la
content-desc "Close" (chi co trong cay khi da hien), nhan nut la TextView "RATE" / "Rate on Google Play".
Man Rating full screen mo tu App Shortcut dung cung bo node.

Do nut X: dump uiautomator mat ~2,3s nen khong dung de bam giay. Thay vao do chup lien tuc khung raw tren may
(`screencap` ~4 khung/s, moc `$EPOCHREALTIME` cung dong ho voi `logcat -v epoch`), luc X da hien thi lay vi tri nut X,
so vung do tren tung khung voi khung cuoi (co X) va khung dau (chua co): giong khung cuoi hon -> X da hien.
Moc popup hien = event rating_placement_viewed.
"""

from __future__ import annotations

import asyncio
import re
import struct

from . import ui_dump

SAO_RE = re.compile(r"^Star ([1-5])$")
NUT_RATE_RE = re.compile(r"^rate\b", re.I)
THU_MUC = "/data/local/tmp/rcr-rating"
DAU_RAW = 16                     # header screencap raw Android 12+: w, h, format, colorspace (uint32)
VIEWED_RE = re.compile(r"^\s*(\d{9,}\.\d+).*name=rating_placement_viewed.*?placement_name=([a-z_]+)", re.M)
GOOGLE_PLAY = "com.android.vending"
GIONG = 6.0              # lech trung binh / kenh mau duoi muc nay = hai vung anh nhu nhau


def doc_popup(nodes) -> dict:
    """{"hien", "sao": {n: center}, "nut": nhan nut Rate|"", "x": center|None} tu cay node app."""
    sao = {int(m.group(1)): n.bounds.center for n in nodes
           if (m := SAO_RE.match(n.content_desc or "")) and not n.bounds.empty}
    nut = next((n.text for n in nodes if NUT_RATE_RE.match(n.text or "")), "")
    x = next((n for n in nodes if (n.content_desc or "") == "Close" and not n.bounds.empty), None)
    return {"hien": len(sao) == 5, "sao": sao, "nut": nut, "x": x.bounds.center if x else None,
            "x_khung": [x.bounds.left, x.bounds.top, x.bounds.right, x.bounds.bottom] if x else None}


async def nhin(client, serial: str, package: str) -> dict:
    return doc_popup(ui_dump.app_nodes(ui_dump.parse_dump(await ui_dump.dump(client, serial)), package))


def nut_rate(nodes):
    return next((n for n in nodes if NUT_RATE_RE.match(n.text or "")), None)


def parse_viewed(log: str) -> list[tuple[float, str]]:
    return [(float(t), p) for t, p in VIEWED_RE.findall(log or "")]


SU_KIEN_RE = re.compile(r"^\s*(\d{9,}\.\d+).*Logging event: origin=\w+,name=(rating_\w+),params=Bundle\[\{(.*?)\}\]",
                        re.M)


def parse_su_kien(log: str) -> list[dict]:
    """Event rating_* trong log FA-SVC: [{"t", "ten", "params"}] (bo param he thong ga_*)."""
    ra = []
    for t, ten, raw in SU_KIEN_RE.findall(log or ""):
        params = dict(kv.split("=", 1) for kv in (p.strip() for p in raw.split(",")) if "=" in kv)
        ra.append({"t": float(t), "ten": ten, "params": {k: v for k, v in params.items() if not k.startswith("ga_")}})
    return ra


async def su_kien(client, serial: str, moc: str = "") -> list[dict]:
    tu = ["-T", moc] if moc else []
    out, _, _ = await client.shell(serial, "logcat", "-d", "-v", "epoch", *tu, "-s", "FA-SVC:V")
    return parse_su_kien(out)


async def viewed(client, serial: str, moc: str = "") -> list[tuple[float, str]]:
    tu = ["-T", moc] if moc else []
    out, _, _ = await client.shell(serial, "logcat", "-d", "-v", "epoch", *tu, "-s", "FA-SVC:V")
    return parse_viewed(out)


def parse_shortcut(text: str, package: str) -> list[dict]:
    """Shortcut dong cua app trong `dumpsys shortcut`: [{"id", "nhan", "intent"}]."""
    khoi = text.split(f"Package: {package}", 1)
    if len(khoi) < 2:
        return []
    phan = re.split(r"\n\s*Package: ", khoi[1], maxsplit=1)[0]
    ra = []
    for m in re.finditer(r"ShortcutInfo \{id=([^,]+),.*?shortLabel=([^,\n]*).*?intents=\[([^\n]*)", phan, re.S):
        ra.append({"id": m.group(1), "nhan": m.group(2).strip(), "intent": m.group(3).strip()})
    return ra


def la_shortcut_rating(s: dict) -> bool:
    return "rating" in s["id"].lower() or "RATING" in s["intent"] or s["nhan"].lower() in ("rate", "rating")


async def shortcuts(client, serial: str, package: str) -> list[dict]:
    out, _, _ = await client.shell(serial, "dumpsys", "shortcut")
    return parse_shortcut(out, package)


# ---- do nut X bang khung chup lien tuc ----

async def bat_dau_chup(client, serial: str, giay: float) -> None:
    # Script ghi ra file roi chay nen: `$` trong vong lap phai duoc may tinh moi vong, khong bi shell ngoai thay truoc.
    lenh = (f"rm -rf {THU_MUC}; mkdir -p {THU_MUC}; end=$(( $(date +%s) + {int(giay) + 1} )); "
            f"while [ $(date +%s) -lt $end ]; do screencap {THU_MUC}/$EPOCHREALTIME.raw; done")
    await client.shell_line(serial, f"echo '{lenh}' > {THU_MUC}.sh; nohup sh {THU_MUC}.sh >/dev/null 2>&1 &")


async def _vung(client, serial: str, tep: str, khung: list[int]) -> bytes:
    """Vung nut X (hang tron chieu ngang) cua mot khung raw - chi keo ve vai tram KB thay vi 10MB."""
    dau, _, _ = await client.run_binary("-s", serial, "exec-out", f"head -c {DAU_RAW} {tep}")
    if len(dau) < 8:
        return b""
    w = struct.unpack("<I", dau[:4])[0]
    hang = w * 4
    l, t, r, b = khung
    raw, _, _ = await client.run_binary(
        "-s", serial, "exec-out", f"tail -c +{DAU_RAW + t * hang + 1} {tep} | head -c {(b - t) * hang}")
    return b"".join(raw[y * hang + l * 4: y * hang + r * 4] for y in range(len(raw) // hang))


def _lech(a: bytes, b: bytes) -> float:
    if not a or len(a) != len(b):
        return 1e9
    buoc = max(1, len(a) // 4000)
    return sum(abs(a[i] - b[i]) for i in range(0, len(a), buoc)) / len(range(0, len(a), buoc))


def phan_tich(khung_x: list[tuple[float, bytes]], t0: float | None) -> dict:
    """Moc nut X hien tu chuoi (gio may, vung X) - khung cuoi coi la da co X, khung dau la chua."""
    if len(khung_x) < 2:
        return {"loi": "không đủ khung chụp"}
    dau, cuoi = khung_x[0][1], khung_x[-1][1]
    if _lech(dau, cuoi) < GIONG:
        # Khung dau da giong khung cuoi (co X): X hien tu truoc khung dau -> moc X <= khung dau.
        goc = t0 if t0 is not None else khung_x[0][0]
        return {"t0": t0, "khung": len(khung_x), "x_hien_s": round(khung_x[0][0] - goc, 2),
                "x_chua_hien_luc_s": None, "khung_dau_s": round(khung_x[0][0] - goc, 2), "co_tu_khung_dau": True}
    co = [(t, _lech(v, cuoi) < _lech(v, dau)) for t, v in khung_x]
    hien = next((t for t, c in co if c), None)
    truoc = [t for t, c in co if not c and (hien is None or t < hien)]
    goc = t0 if t0 is not None else co[0][0]
    return {"t0": t0, "khung": len(co), "x_hien_s": round(hien - goc, 2) if hien is not None else None,
            "x_chua_hien_luc_s": round(truoc[-1] - goc, 2) if truoc else None,
            "khung_dau_s": round(co[0][0] - goc, 2)}


async def ket_thuc_chup(client, serial: str, x_khung: list[int] | None, t0: float | None) -> dict:
    """Doc cac khung da chup, tra ket qua do nut X roi xoa khung tren may."""
    try:
        if not x_khung:
            return {"loi": "không thấy nút X trên popup để đo"}
        out, _, _ = await client.shell(serial, "ls", THU_MUC)
        tep = sorted((float(f[:-4]), f) for f in out.split() if f.endswith(".raw") and _so(f[:-4]))
        khung = [(t, await _vung(client, serial, f"{THU_MUC}/{f}", x_khung)) for t, f in tep]
        return phan_tich([(t, v) for t, v in khung if v], t0)
    finally:
        await client.shell(serial, "rm", "-rf", THU_MUC)


def _so(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


async def cho_het_chup(giay: float) -> None:
    await asyncio.sleep(giay + 1.5)
