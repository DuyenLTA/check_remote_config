"""Hang doi job cua bot build-watch + khoa may.

Moi dien thoai mot luot tai mot thoi diem; nhieu may thi nhieu luot song song
(build khac nhau, user chot 27/10/2026). Job duyet xong vao hang FIFO, may nao
ranh lay job dau tien chua chay. Hang doi luu ra `out/bot-hang-doi.json` -> bot
khoi dong lai van chay tiep.

Khoa may la khoa cua HE DIEU HANH tren `out/.may-<serial>.lock` (msvcrt tren
Windows, fcntl noi khac): process chet la khoa tu nha, khong de lai khoa mo coi.
Khoa theo serial -> luot tren may A khong chan luot tren may B.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path

def khoa_may(out_dir: Path, serial: str) -> Path:
    return Path(out_dir) / f".may-{serial}.lock"


def _khoa_file(fd: int) -> bool:
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _mo_khoa_file(fd: int) -> None:
    if os.name == "nt":
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)


@contextmanager
def giu_may(path: Path):
    """Giu khoa may trong khoi `with`; may dang co luot khac -> BlockingIOError, khong cho."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT)
    try:
        if not _khoa_file(fd):
            raise BlockingIOError(f"máy đang có lượt khác giữ {path.name}")
        try:
            yield
        finally:
            _mo_khoa_file(fd)
    finally:
        os.close(fd)


def may_ban(path: Path) -> bool:
    """True neu process khac dang giu khoa may."""
    try:
        with giu_may(path):
            return False
    except BlockingIOError:
        return True


# Trang thai cua MOT luot chay (ket qua, buoc da gui, may phu dang giu). Job moi xep tu tin build cu
# (bam Check / Thu lai) khong duoc mang theo: mang `kq` thi bot chi gui lai ket qua cu ma khong chay.
TRUONG_LUOT = ("kq", "dong", "da_bao", "da_bao_bug", "da_bao_dev", "da_log", "da_ping", "ten_may", "bat_dau", "dang_o", "giao_luc", "pha")


def _khoa_job(job: dict) -> tuple[str, str, str, str]:
    # Luot verify bug va luot Check cung build la hai viec khac nhau -> khong chan nhau.
    # Luot tab tinh nang: rating va widget cung build cung la hai viec khac nhau.
    return job["package"], job["version"], job.get("loai_job", "check"), ",".join(job.get("tabs") or [])


class HangDoi:
    """`jobs`: FIFO gom ca job dang chay; `dang_chay`: msg_id cac job dang chay tren mot may nao do."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.jobs: list[dict] = []
        # msg_id (tin cua bot o kenh QA, dang chuoi vi JSON) -> build cua tin do, de bam nut con biet build nao.
        self.tin: dict[str, dict] = {}
        self.dang_chay: set[int] = set()
        # "MA|version" build khong ghi SDK da bao o qa-auto: bot khoi dong lai quet tin lo khong bao lai (10/11/2026
        # AIP893 bi bao 6 lan sau 6 lan restart). Giu 200 build gan nhat.
        self.da_bao: list[str] = []
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
            self.jobs = data.get("jobs", [])
            self.tin = data.get("tin", {})
            self.da_bao = data.get("da_bao", [])
        # Bot chet giua luot -> job do chua xong: chay lai tu dau, khong bo qua.

    def luu(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"jobs": self.jobs, "tin": self.tin, "da_bao": self.da_bao[-200:]},
                                  ensure_ascii=False, indent=1),
                       encoding="utf-8")
        tmp.replace(self.path)

    def bao_lan_dau(self, khoa: str) -> bool:
        """True (va ghi nho) neu chua bao `khoa` lan nao."""
        if khoa in self.da_bao:
            return False
        self.da_bao.append(khoa)
        self.luu()
        return True

    def trung(self, job: dict) -> bool:
        return any(_khoa_job(j) == _khoa_job(job) for j in self.jobs)

    def them(self, job: dict) -> int | None:
        """Vi tri (1 = chay tiep theo) hoac None neu cung package + version + loai job da trong hang."""
        if self.trung(job):
            return None
        for k in TRUONG_LUOT:
            job.pop(k, None)
        self.jobs.append(job)
        self.luu()
        return len(self.jobs)

    def vi_tri(self, msg_id: int) -> int | None:
        return next((i + 1 for i, j in enumerate(self.jobs) if j["msg_id"] == msg_id), None)

    def _ranh(self, j: dict) -> bool:
        return j["msg_id"] not in self.dang_chay and not j.get("dang_o")

    def dang_chay_tren_may(self, j: dict) -> bool:
        """Luot da duoc giao may (chinh hoac phu), ke ca dang gui ket qua - khong con nam cho trong hang."""
        return not self._ranh(j)

    def _dang_test(self, j: dict) -> bool:
        """Dang cai / chay test tren mot may (chinh hoac phu). Da co `kq` = chi con gui ket qua, khong dung RC."""
        return not self._ranh(j) and j.get("kq") is None

    def lay(self) -> dict | None:
        """Job dau tien chua chay (khong xoa khoi hang toi khi `xong`). Moi may ranh goi mot lan.
        `dang_o` (job da giao cho may tinh phu, luu ca qua lan khoi dong lai) cung la dang chay.
        Job da co `kq` (chay xong, chi con gui ket qua) khong can may -> `lay_cho_gui`."""
        # Cung package thi chay LAN LUOT: luot bo TC go het gia tri `testvsl` cua Firebase project luc doc baseline /
        # luc QA bam Dung -> hai luot cung app song song (Check + verify cung build, hai build) xoa RC cua nhau
        # giua case, ra PASS/FAIL sai. Job sau cho; job khac app van chay o may ranh.
        ban = {j.get("package") for j in self.jobs if self._dang_test(j)}
        job = next((j for j in self.jobs if self._ranh(j) and j.get("kq") is None and j.get("package") not in ban),
                   None)
        if job is not None:
            self.dang_chay.add(job["msg_id"])
        return job

    def lay_cho_gui(self) -> list[dict]:
        """Job da chay xong tren may nhung chua gui duoc ket qua (bot tat / mat mang giua luc gui):
        chi gui lai ket qua, khong chay lai lan nua."""
        cac = [j for j in self.jobs if self._ranh(j) and j.get("kq") is not None]
        self.dang_chay.update(j["msg_id"] for j in cac)
        return cac

    def huy(self, msg_id: int) -> str:
        """QA bam Huy: "da_huy" (bo khoi hang) | "dang_chay" (dang chay tren may - khong huy giua luot
        vi co the con RC testvsl dang gan tren Firebase) | "khong_co" (da xong / khong trong hang)."""
        job = next((j for j in self.jobs if j["msg_id"] == msg_id), None)
        if job is None:
            return "khong_co"
        if not self._ranh(job) or job.get("kq") is not None:
            return "dang_chay"
        self.xong(job)
        return "da_huy"

    def cap_nhat(self, job: dict, **truong) -> None:
        """Ghi ket qua / buoc da gui vao job roi luu file -> bot khoi dong lai biet lam tiep tu dau."""
        job.update(truong)
        self.luu()

    def xong(self, job: dict) -> None:
        self.jobs = [j for j in self.jobs if j["msg_id"] != job["msg_id"]]
        self.dang_chay.discard(job["msg_id"])
        self.luu()

    def nho_tin(self, c: dict) -> None:
        self.tin[str(c["msg_id"])] = c
        self.luu()

    def tin_cua(self, msg_id: int) -> dict | None:
        return self.tin.get(str(msg_id))
