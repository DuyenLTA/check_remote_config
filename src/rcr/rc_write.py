"""Ghi file vao sandbox cua app. Hai chang, vi `adb push` khong vao /data/data.

    chang 1: adb push <local> /data/local/tmp/rcr_<n>   (shell ghi duoc)
    chang 2: copy tu tmp vao trong bang danh tinh app

XOA FILE TAM NGAY SAU DO, ke ca khi chang 2 that bai: /data/local/tmp ai doc
cung duoc: de lai la phoi remote config cua app nay ra cho moi app khac tren may.

GHI BANG REDIRECT (`cat tmp > dest`), KHONG dung `cp`:
redirect mo file dich san co voi O_TRUNC nen GIU NGUYEN chu so huu va nhan
SELinux cua file do. `cp` tao file moi thi file se thuoc root (duong `su`) ->
app khong doc duoc. Doi lai: file dich PHAI ton tai san. Dung voi luong cua
tool - baseline da doc chinh may file do; sau `pm clear` thi phase 4 cho app
tu sinh lai file truoc khi patch.

Duong `run-as` con them mot buoc du phong: nhieu may (Android moi, SELinux
chat) khong cho tien trinh app doc file cua shell, luc do `run-as ... cat tmp`
tra "Permission denied"; van ghi duoc bang cach cho SHELL doc file roi day qua
stdin cua tien trinh app.
"""

from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path

from . import app_sandbox
from .adb_client import PUSH_TIMEOUT
from .models import RcError

log = logging.getLogger(__name__)

TMP_DIR = "/data/local/tmp"


def _tmp_path() -> str:
    """Ten file tam do MINH dat - ten file/key cua tester khong di vao duong dan."""
    return f"{TMP_DIR}/rcr_{uuid.uuid4().hex[:12]}"


async def write_file(
    client, serial: str, package: str, mode: str, dest_rel: str, content: str
) -> None:
    """Ghi `content` thanh <data>/<dest_rel> cua app. Raise RcError kem loi that.

    `dest_rel` la duong dan tuong doi trong sandbox, vd
    "files/frc_<id>_firebase_activate.json".
    """
    app_sandbox.guard(serial, package)
    remote_tmp = _tmp_path()
    local = Path(tempfile.mkstemp(prefix="rcr_", suffix=".tmp")[1])
    try:
        local.write_text(content, encoding="utf-8")
        out, err, code = await client._run(
            "-s", serial, "push", str(local), remote_tmp, timeout=PUSH_TIMEOUT
        )
        if code != 0:
            raise RcError(f"push that bai: {(err or out).strip()}")
        await _copy_in(client, serial, package, mode, remote_tmp, dest_rel)
    finally:
        local.unlink(missing_ok=True)
        # Xoa ca khi that bai: file con lai la config cua app nay nam o cho moi
        # app khac doc duoc. Loi xoa khong duoc de che loi that o tren.
        try:
            await client.shell(serial, "rm", "-f", remote_tmp)
        except Exception:  # noqa: BLE001
            log.warning("khong xoa duoc file tam %s tren may", remote_tmp)


async def _copy_in(
    client, serial: str, package: str, mode: str, remote_tmp: str, dest_rel: str
) -> None:
    dest = app_sandbox.quote(dest_rel)
    if mode == app_sandbox.SU:
        # root: redirect giu nguyen owner + nhan SELinux cua file dich san co.
        inner = f"cat {remote_tmp} > {dest}"
        out, err, _ = await client.shell_line(
            serial, f"su -c {app_sandbox.quote(inner)}", timeout=PUSH_TIMEOUT
        )
        problem = _problem(out, err)
        if problem:
            raise RcError(f"su ghi {dest_rel} that bai: {problem}")
        return

    # run-as: app tu doc file cua shell (nhanh), that bai thi day qua stdin.
    #
    # PHAI dung shell_line + boc nhay ca cau lenh trong. `adb shell run-as pkg
    # sh -c "cat tmp > dest"` KHONG chay dung: adb noi argv thanh MOT dong roi
    # cho `sh` NGOAI tren device chay, nen dau `>` bi shell ngoai an mat, no tao
    # file theo cwd cua chinh no (`/`) va bao "No such file or directory".
    inner = f"cat {remote_tmp} > {dest}"
    out, err, _ = await client.shell_line(
        serial, f"run-as {package} sh -c {app_sandbox.quote(inner)}", timeout=PUSH_TIMEOUT
    )
    problem = _problem(out, err)
    if not problem:
        return
    log.warning("run-as doc file cua shell that bai (%s) - thu duong stdin", problem)
    line = f"cat {remote_tmp} | run-as {package} sh -c {app_sandbox.quote(f'cat > {dest_rel}')}"
    out, err, _ = await client.shell_line(serial, line, timeout=PUSH_TIMEOUT)
    problem2 = _problem(out, err)
    if problem2:
        raise RcError(
            f"khong ghi duoc {dest_rel}.\n  duong 1 (app doc file shell): {problem}\n"
            f"  duong 2 (stdin): {problem2}"
        )


def _problem(out: str, err: str) -> str | None:
    """`run-as`/`su` bao loi ma van exit 0 -> phai doc ca stdout."""
    from .adb_parsers import output_error

    extra = ("su: not found", "inaccessible", "cannot create", "read-only")
    joined = f"{out} {err}"
    low = joined.lower()
    for hint in extra:
        if hint in low:
            return joined.strip()
    return output_error(out, err)
