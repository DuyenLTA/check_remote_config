"""Tien trinh con cua mot luot bot (cai build, Claude headless) - chay va DUNG duoc giua chung.

`subprocess.run(timeout=)` chi giet tien trinh truc tiep: tren Windows `claude` la claude.CMD -> giet cmd.exe,
con claude / python rcr-check / adb song mo coi va giu khoa may. Module nay giu Popen theo `khoa` (serial may
test) va giet CA CAY: Windows `taskkill /T /F`, noi khac process group (`start_new_session`).

QA bam Dung (bot_dung_luot) -> `dung(serial, ly_do)`: danh dau + giet tien trinh dang chay; lenh sau cung luot
gap dau thi khong chay. Luong goi nhan `BiDung` thay cho ket qua.
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time

NHIP = 5.0
_lock = threading.Lock()
_dang: dict[str, subprocess.Popen] = {}
_dung: dict[str, str] = {}          # khoa -> ly do (ai bam Dung)
_chu: dict[str, object] = {}        # khoa -> job dang giu may (msg_id): bam Dung muon khong giet nham job sau
CHO_CHAU = 30.0     # tien trinh chinh da chet ma ong ra con bi chau giu -> doi them chung nay roi thoi


class BiDung(Exception):
    """Luot bi QA dung giua chung."""


def bat_dau(khoa: str, chu: object = None) -> None:
    """Dau moi luot tren may `khoa` cua job `chu`: bo dau Dung cu (luot truoc da xong)."""
    with _lock:
        _dung.pop(khoa, None)
        _chu[khoa] = chu


def bi_dung(khoa: str) -> str | None:
    with _lock:
        return _dung.get(khoa)


def _giet_cay(p: subprocess.Popen, khoa: str = "") -> None:
    try:
        if os.name == "nt":
            if p.poll() is None:     # taskkill /T di theo cha-con, cha chet roi thi khong lan duoc cay
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True, timeout=30)
        else:
            # Ca khi truong nhom da chet: thanh vien con lai cua nhom van giet duoc.
            os.killpg(p.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass
    if os.name != "nt" and khoa:
        # Tien trinh tu tach nhom (setsid) thoat killpg -> giet theo dong lenh mang dung serial may cua luot.
        subprocess.run(["pkill", "-KILL", "-f", "--", f"--serial {khoa}"], capture_output=True)
    try:
        p.kill()
    except OSError:
        pass


def dung(khoa: str, ly_do: str = "", chu: object = None) -> bool:
    """Dung luot cua job `chu` tren may `khoa`: danh dau + giet cay tien trinh dang chay. False khi may dang
    chay job khac (bam Dung muon, luot cu da xong) - khong lam gi."""
    with _lock:
        if chu is not None and _chu.get(khoa) != chu:
            return False
        _dung[khoa] = ly_do or "QA bấm Dừng"
        p = _dang.get(khoa)
    if p is not None:
        _giet_cay(p, khoa)
    return True


def chay(cmd: list[str], khoa: str, timeout: float, input: str | None = None,
         **kw) -> subprocess.CompletedProcess:
    """Nhu `subprocess.run(capture_output=True, text=True, timeout=...)` nhung het gio / bi dung thi giet ca
    cay. Het gio -> `TimeoutExpired` (kem stdout/stderr); bi dung -> `BiDung`."""
    with _lock:
        if khoa in _dung:
            raise BiDung(_dung[khoa])
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             start_new_session=os.name != "nt", **kw)
        _dang[khoa] = p
    han, chet_luc = time.monotonic() + timeout, None
    gui = input              # Popen.communicate chi nhan input o LAN DAU (goi lai kem input -> ValueError)
    try:
        while True:
            con = han - time.monotonic()
            try:
                # Nhip ngan de thay Dung / tien trinh chau giu ong ra (vd adb server) ma communicate khong tra.
                out, err = p.communicate(gui, timeout=max(0.1, min(NHIP, con)))
                break
            except subprocess.TimeoutExpired:
                gui = None
                if p.poll() is not None:
                    chet_luc = chet_luc or time.monotonic()
                    if bi_dung(khoa) is not None or time.monotonic() - chet_luc > CHO_CHAU:
                        _giet_cay(p, khoa)
                        out = err = ""
                        break
                if con <= 0:
                    _giet_cay(p, khoa)
                    try:
                        out, err = p.communicate(timeout=30)
                    except subprocess.TimeoutExpired:
                        out = err = ""
                    raise subprocess.TimeoutExpired(cmd, timeout, out, err) from None
    finally:
        with _lock:
            if _dang.get(khoa) is p:
                _dang.pop(khoa)
    ly_do = bi_dung(khoa)
    if ly_do is not None:
        raise BiDung(ly_do)
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)
