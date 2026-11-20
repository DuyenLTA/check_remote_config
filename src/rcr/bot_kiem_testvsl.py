"""Kiem dieu kien `testvsl` tren Firebase TRUOC khi chay Claude cho ban release - thieu / sai thi nhac QA tao.

Luat (user chot 30-31/10/2026, nhac lai 02/11/2026): tool chi gan / go GIA TRI cua dieu kien `testvsl`, khong dung
default, tham so, condition cua nguoi khac. Tu 20/11/2026 (user chot): QA bam Check / go /check -> luot Check tu tao
condition theo version tin build, lech plan tuan thi them version plan (`tu_tao`, chi khi chua co hoac condition do tai khoan bot tao). Sau do
`loi_testvsl` chi DOC lai: van thieu / sai (condition nguoi khac) thi tag nguoi bam Check nho tao roi bam Chay lai.
"""

from __future__ import annotations

import asyncio

import logging

from . import rc_firebase, rc_firebase_app, rc_firebase_testvsl
from .adb_client import AdbClient
from .adb_parsers import AdbError
from .models import RcError


def doi_rc_firebase(job: dict, checklist: bool) -> bool:
    """Luot nay doi RC tren Firebase qua `testvsl`: ban release cai tu App Tester, nhanh bo TC (khong phai checklist
    Next-Gen)."""
    return job.get("loai_ban") == "release" and not checklist


log = logging.getLogger("rcr-bot")


async def tu_tao(serial: str, package: str, version: str, ma: str = "") -> str:
    """Luot Check (QA bam Check / /check): tao condition `testvsl` theo version tin build tren Firebase project cua
    APK vua cai. Tra dong ghi len tin goc ("" khi condition da dung, khong lam gi). Loi -> chi ghi canh bao,
    `loi_testvsl` ngay sau se nhac QA nhu cu."""
    if not rc_firebase.da_dang_nhap():
        return ""
    try:
        info = await rc_firebase_app.thong_tin_tren_may(AdbClient(), serial, package)
        from .bot_testvsl import versions_can_tao   # tin build lech plan tuan -> chua ca version plan
        cac = await asyncio.to_thread(versions_can_tao, ma, version) if ma else [version]
        kq = await asyncio.to_thread(rc_firebase_testvsl.tao, info["project"], info["app_id"], cac)
    except (RcError, AdbError, OSError) as exc:
        log.warning("tu tao testvsl %s %s: %s", package, version, exc)
        return f"⚠️ Không tự tạo được `{rc_firebase.DIEU_KIEN}`: {exc}"
    return "" if "không cần sửa" in kq else f"🧪 {kq}"


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
            f"Bấm **Tạo testvsl** để bot tạo điều kiện `{rc_firebase.DIEU_KIEN}` theo đúng app.id + version này "
            f"(đứng thứ 1; condition người khác tạo thì bot không sửa), hoặc tự tạo trên Firebase rồi kéo lên **thứ 1**. Xong thì bấm "
            f"**Chạy lại** (lượt verify: **Verify lại**) ở tin của lượt.")


def thieu_condition(loi: str) -> bool:
    """Loi do thieu / sai condition (khong phai may bot, khong phai dang nhap) -> co nut Tao testvsl."""
    return not loi.startswith(rc_firebase_app.MAY_BOT) and not any(x in loi for x in rc_firebase.LOI_DANG_NHAP)


THAT = loi_testvsl     # ban goc (test thay `loi_testvsl` bang ban gia mac dinh)
THAT_TAO = tu_tao     # ban goc cua `tu_tao` (conftest thay bang ban khong publish)
