"""Chay lenh trong danh tinh cua app de doc/ghi /data/data/<pkg>/.

Hai duong vao, cung mot interface - phan con lai cua tool khong biet dang di
duong nao:

    run-as : app phai la ban debuggable
    su     : may phai root; nho duong nay ban RELEASE cung patch duoc

`adb push` KHONG ghi truc tiep vao /data/data - chi app do (hoac root) vao duoc
sandbox cua chinh no. Nen phase 2 phai di 2 chang: push vao /data/local/tmp roi
copy vao trong.

MOI DUONG DAN di qua `sh` tren device deu phai boc nhay: ten file frc_* chua
dau ':' (vd frc_1:310944273102:android:abc_firebase_activate.json).
"""

from __future__ import annotations

from .adb_parsers import PACKAGE_RE, SERIAL_RE, AdbError, output_error, parse_ls

RUN_AS = "run-as"
SU = "su"


def quote(s: str) -> str:
    """Boc nhay don cho 1 doi so di qua `sh` tren device."""
    return "'" + s.replace("'", "'\\''") + "'"


def guard(serial: str, package: str | None = None) -> None:
    if not SERIAL_RE.fullmatch(serial):
        raise AdbError(f"Serial khong hop le: {serial!r}")
    if package is not None and not PACKAGE_RE.fullmatch(package):
        raise AdbError(f"Package khong hop le: {package!r}")


async def run(
    client, serial: str, package: str, mode: str, *cmd: str, timeout: float | None = None
) -> tuple[str, str, int]:
    """Chay `cmd` trong danh tinh app. Tra (stdout, stderr, code) - khong raise."""
    guard(serial, package)
    if mode == SU:
        # `su -c` nhan MOT chuoi -> phai boc nhay 2 lop.
        inner = " ".join(quote(c) for c in cmd)
        return await client.shell_line(serial, f"su -c {quote(inner)}", timeout=timeout)
    return await client.shell(serial, RUN_AS, package, *cmd, timeout=timeout)


async def ls(
    client, serial: str, package: str, sub: str, *, mode: str = RUN_AS
) -> tuple[list[str], str | None]:
    """Liet ke file trong <data>/<sub>. Tra (ten_file, loi_neu_co)."""
    out, err, _ = await run(client, serial, package, mode, "ls", sub)
    problem = output_error(out, err)
    return (([] if problem else parse_ls(out)), problem)


async def cat(
    client, serial: str, package: str, path: str, *, mode: str = RUN_AS
) -> tuple[str, str | None]:
    """Doc 1 file trong sandbox app. Tra (noi_dung, loi_neu_co).

    `path` da boc nhay o tang goi (xem rc_baseline._q).
    """
    out, err, _ = await run(client, serial, package, mode, "cat", path)
    # File rong that va file loi deu cho out='' -> chi tin stderr, tru khi
    # stdout co dau vet loi ro rang.
    problem = output_error(err) or (output_error(out) if not out.strip() else None)
    return (("" if problem else out), problem)


async def detect_mode(client, serial: str, package: str) -> str:
    """Dò duong vao sandbox: RUN_AS | SU. Raise AdbError neu ca hai deu khong duoc.

    Goi 1 lan luc doc baseline; phase 2 dung lai ket qua thay vi do lai.
    """
    guard(serial, package)
    out, err, _ = await client.shell(serial, RUN_AS, package, "id")
    if "uid=" in out:
        return RUN_AS
    run_as_err = (err or out).strip() or "that bai"
    out2, _, _ = await client.shell_line(serial, "su -c id")
    if "uid=0" in out2:
        return SU
    raise AdbError(
        f"Khong vao duoc du lieu cua {package}.\n"
        f"  run-as: {run_as_err}\n"
        "  su: may khong root\n"
        "Can ban APK bat `debuggable` (xin dev), hoac may da root.\n"
        "Kiem tra APK truoc khi cai:\n"
        "  aapt dump badging <file.apk> | grep application-debuggable\n"
        "  (in ra dong do = dung duoc; khong in gi = khong dung duoc)"
    )
