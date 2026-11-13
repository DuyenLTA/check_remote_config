"""Kiem dieu kien `testvsl` tren Firebase TRUOC khi chay Claude cho ban release - thieu / sai thi nhac QA tao.

Luat (user chot 30-31/10/2026, nhac lai 02/11/2026): tool chi gan / go GIA TRI cua dieu kien `testvsl`; dieu kien do
do QA tu tao (app.id + version dang test, keo len thu 1). Chua co / sai thi bot KHONG tu tao hay sua condition,
default, tham so cua nguoi khac - chi tag nguoi bam Check nho tao roi bam Chay lai. Kiem o day chi DOC (GET
template), khong publish; truoc day phai cho Claude chay toi preflight moi biet, va loi nhac lan trong tom tat.
"""

from __future__ import annotations

import asyncio

from . import rc_firebase, rc_firebase_app
from .adb_client import AdbClient
from .adb_parsers import AdbError
from .models import RcError


def doi_rc_firebase(job: dict, checklist: bool) -> bool:
    """Luot nay doi RC tren Firebase qua `testvsl`: ban release cai tu App Tester, nhanh bo TC (khong phai checklist
    Next-Gen)."""
    return job.get("loai_ban") == "release" and not checklist


async def loi_testvsl(serial: str, package: str) -> str | None:
    """Ly do chua chay duoc (thieu `testvsl`, khong dung thu 1, khong nhac version dang test...) hoac None khi on.
    May chua `firebase login` -> bao dang nhap ngay, khong de Claude chay roi dung o "xin ban debuggable"."""
    if not rc_firebase.da_dang_nhap():
        return rc_firebase.CHUA_DANG_NHAP
    try:
        info = await rc_firebase_app.thong_tin_tren_may(AdbClient(), serial, package)
    except AdbError as exc:
        # Keo APK hong (o dia may bot day, adb mat may): loi cua may bot, chua toi buoc doc condition.
        s = str(exc)
        return s if s.startswith(rc_firebase_app.MAY_BOT) else f"{rc_firebase_app.MAY_BOT} {s}"
    except RcError as exc:
        return str(exc)
    try:
        await asyncio.to_thread(rc_firebase_app.kiem_dieu_kien_test, info)
    except (RcError, AdbError) as exc:
        return str(exc)
    return None


def tin_nhac(job: dict, loi: str, duyet) -> str:
    """Tag nguoi bam Check (luot verify tu xep thi tag cac QA duoc duyet)."""
    ai = [job["nguoi_duyet"]] if job.get("nguoi_duyet") else sorted(duyet or [])
    tag = " ".join(f"<@{i}>" for i in ai)
    if loi.startswith(rc_firebase_app.MAY_BOT):               # o dia / adb may bot hong: condition khong lien quan
        return (f"⛔ {tag} **{job.get('ma', '')}** `{job.get('version', '')}` — chưa chạy được bản release: {loi}\n"
                f"Lỗi trên **máy bot** (chưa tới bước đọc điều kiện `{rc_firebase.DIEU_KIEN}`, condition không cần sửa). "
                f"Người quản máy bot dọn ổ / kiểm adb rồi bấm **Chạy lại** (lượt verify: **Verify lại**) ở tin của lượt.")
    if any(x in loi for x in rc_firebase.LOI_DANG_NHAP):       # loi dang nhap tren may bot, khong phai thieu testvsl -> khong nho tao condition
        return (f"⛔ {tag} **{job.get('ma', '')}** `{job.get('version', '')}` — chưa chạy được bản release: {loi}\n"
                f"Người quản máy bot chạy `firebase login` (hết hạn: `firebase login --reauth`) trên máy chạy lượt, xong bấm **Chạy lại** "
                f"(lượt verify: **Verify lại**) ở tin của lượt.")
    return (f"⛔ {tag} **{job.get('ma', '')}** `{job.get('version', '')}` — chưa chạy được bản release: {loi}\n"
            f"Nhờ tạo / sửa điều kiện `{rc_firebase.DIEU_KIEN}` trên Firebase (app.id + version đang test), kéo lên "
            f"**thứ 1**. Bot không tự tạo hay sửa condition, default hay tham số của người khác. Xong thì bấm "
            f"**Chạy lại** (lượt verify: **Verify lại**) ở tin của lượt.")


THAT = loi_testvsl     # ban goc (test thay `loi_testvsl` bang ban gia mac dinh)
