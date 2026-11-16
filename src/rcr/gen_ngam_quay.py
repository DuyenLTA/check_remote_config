"""Quay man hinh luc o man cho de do popup dem nguoc ("Taking you to Home in 3s") theo tung giay.

`uiautomator dump` mat ~2,1s / lan tren Pixel 6 (do 16/11/2026) -> nhin UI hut so "3s", khong do duoc "moi so ~1s";
`uiautomator events` cua app Compose khong mang chu. Nen: screenrecord 540x1200, tach khung 10 fps, roi so vung chu
popup (khung lay tu mot lan dump luc popup dang hien) giua cac khung:
  - popup hien: vung tieu de popup giong khung tham chieu;
  - so dem doi: vung dong dem nguoc doi han giua hai khung lien tiep khi popup dang hien.
Gio khung -> gio may: neo vao khung man hinh doi lon cuoi cung (ve Home) = moc START MainActivity trong logcat.
"""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

FPS = 10
TL = 0.5                # 1080x2400 -> 540x1200


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


async def bat(serial: str, ten: str, giay: int = 40) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        "adb", "-s", serial, "shell", "screenrecord", "--bit-rate", "3000000", "--size", "540x1200",
        "--time-limit", str(giay), f"/sdcard/rcr_gn_{ten}.mp4",
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)


async def dung(serial: str, ten: str, proc, thu_muc: Path) -> Path | None:
    subprocess.run(["adb", "-s", serial, "shell", "pkill", "-INT", "screenrecord"], check=False)
    try:
        await asyncio.wait_for(proc.wait(), 10)
    except asyncio.TimeoutError:
        proc.kill()
    await asyncio.sleep(1.0)
    thu_muc.mkdir(parents=True, exist_ok=True)
    dich = thu_muc / f"gn_{ten}.mp4"
    subprocess.run(["adb", "-s", serial, "pull", f"/sdcard/rcr_gn_{ten}.mp4", str(dich)], check=False,
                   capture_output=True)
    subprocess.run(["adb", "-s", serial, "shell", "rm", "-f", f"/sdcard/rcr_gn_{ten}.mp4"], check=False)
    return dich if dich.is_file() and dich.stat().st_size > 0 else None


def khung(mp4: Path) -> list:
    """[(giay tu dau video, anh xam PIL)] 10 fps."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([_ffmpeg(), "-loglevel", "error", "-i", str(mp4), "-vf", f"fps={FPS}", f"{d}/f_%04d.png"],
                       check=True)
        ra = []
        for f in sorted(Path(d).glob("f_*.png")):
            ra.append(((int(f.stem[2:]) - 1) / FPS, Image.open(f).convert("L").copy()))
    return ra


def _vung(hop, rong: int, cao: int):
    l, t, r, b = (int(v * TL) for v in hop)
    return max(0, l), max(0, t), min(rong, r), min(cao, b)


def _lech(a, b) -> float:
    from PIL import ImageChops, ImageStat
    return ImageStat.Stat(ImageChops.difference(a, b)).mean[0]


def _diem_doi(a, b) -> int:
    from PIL import ImageChops
    return sum(ImageChops.difference(a, b).point(lambda v: 255 if v > 50 else 0).histogram()[255:])


def phan_tich(ds: list, hop_tieu_de, hop_dem, t_ve_home: float) -> dict:
    """{t_hien, so_trang_thai, t_doi [...], neo} theo gio may. hop_*: [l, t, r, b] toa do man that (1080x2400)."""
    if len(ds) < 3:
        return {"loi": "video quá ngắn"}
    rong, cao = ds[0][1].size
    vt, vd = _vung(hop_tieu_de, rong, cao), _vung(hop_dem, rong, cao)
    # Neo: khung doi toan man lon nhat cuoi video (man cho -> Home) ~ START MainActivity.
    doi_lon = [(i, _lech(ds[i - 1][1], ds[i][1])) for i in range(1, len(ds))]
    i_ve = max(doi_lon[len(doi_lon) // 3:], key=lambda x: x[1])[0]
    lech_gio = t_ve_home - ds[i_ve][0]
    # Khung tham chieu tieu de popup: khung ngay truoc khi ve Home (popup dang hien chac chan).
    ref = ds[i_ve - 2][1].crop(vt)
    hien = [i for i in range(i_ve) if _lech(ds[i][1].crop(vt), ref) < 6]
    if not hien:
        return {"loi": "không thấy popup trong video", "neo": t_ve_home}
    dau = hien[0]
    # Doi mot chu so chi lam lech trung binh ~0,1 tren ca dong chu -> dem so diem anh doi han (>50 muc xam); bo
    # 0,5s dau (popup dang hien dan len - do 16/11/2026: hien dan 0,2-0,4s).
    doi = [ds[i][0] + lech_gio for i in range(dau + 1, i_ve)
           if ds[i][0] - ds[dau][0] > 0.5 and ds[i_ve][0] - ds[i][0] > 0.3 and _diem_doi(ds[i - 1][1].crop(vd), ds[i][1].crop(vd)) > 15]
    # Mot lan doi so co the keo dai 2 khung (fade) -> gop doi cach nhau < 0,35s.
    gop: list[float] = []
    for t in doi:
        if not gop or t - gop[-1] > 0.35:
            gop.append(t)
    return {"t_hien": round(ds[dau][0] + lech_gio, 2), "t_doi": [round(t, 2) for t in gop],
            "so_trang_thai": len(gop) + 1, "t_ve_home": t_ve_home}
