"""Doc man App Tester (Firebase App Distribution) + hop cai cua Android tu dump UI.

Ham thuan tren list DeviceNode -> test bang dump that da luu (fixtures/uidump_apptester_*,
uidump_installer_*, uidump_playprotect_*; do Pixel 6, App Tester v0.133, 27/10/2026).

Lai theo resource-id cua App Tester, khong theo toa do. Hop cua Play Protect
khong co id -> nhan theo chu, va chi chap nhan khi package la com.android.vending.

Cung mot version co the co NHIEU release (1.3.0 (13) hai ban: "fix bug r1" va
"apply next-gen") -> phan biet bang release note, khong chon theo version.
"""

from __future__ import annotations

import re
from datetime import datetime

APP_TESTER = "dev.firebase.appdistribution"
INSTALLER = "com.google.android.packageinstaller"
PLAY_STORE = "com.android.vending"
# OPPO/ColorOS chen man quet cai dat rieng ("No risks found" + nut "Install anyway") truoc hop cai
# (AIP882 29/10/2026, CPH2375) -> bam "Install anyway" (user chot).
OPPO_MARKET = "com.heytap.market"
OPPO_CAI = "Install anyway"
# Nut cua mot release da mo rong: tai moi / mo ban dang cai / ha cap.
NUT_BAN = {"download_button": "tai", "open_button": "dang_cai", "downgrade_release": "ha_cap"}
# `open_button` ghi "Install" khi APK da tai ma chua cai (bam Cancel o hop cai, do
# 27/10/2026) - cung id voi nut "Open" cua ban dang cai.
# Chu tren nut theo ngon ngu may: Pixel 7 de vi-VN (30/10/2026) -> "Cai dat", "Quet ung dung"...
# khong khop chu tieng Anh -> bot bao "khong co nut Download/Install" / "man la khi dang cai".
DA_TAI = ("Install", "Cài đặt")
PP_QUET = ("Scan app", "Quét ứng dụng")
PP_CAI = ("Install", "Cài đặt")
THU_LAI = ("Retry", "Thử lại")
# Moi may quet cai dat mot kieu (Play Protect, OPPO, Xiaomi, Samsung...; tieng Anh/Viet) -> gap hop nao
# cung chap nhan quet + cai (user chot 30/10/2026). So khop khong phan biet hoa thuong, bo khoang trang.
CHAP_NHAN = frozenset(c.casefold() for c in (
    *PP_QUET, *PP_CAI, OPPO_CAI, "Install anyway", "Vẫn cài đặt", "Cài đặt bất kể", "Cài đặt dù sao",
    "Continue installation", "Tiếp tục cài đặt", "Continue", "Tiếp tục", "Update", "Cập nhật",
    "Allow", "Cho phép", "OK", "Đồng ý", "Got it", "Đã hiểu", "Install without scanning",
    "Cài đặt mà không quét", "Scan", "Quét"))
# Ten build variant dinh lien ("1.4.0 (14) - prodDebug", AIP805 29/10/2026) -> `\bdebug\b` khong khop,
# ban debug bi coi la release. Cho phep tien to chu cai: debug, prodDebug, devDebug.
DEBUG_RE = re.compile(r"\b[a-z]*debug\b", re.I)
# Note ghi ro ban release ("prodRelease", "release build", "rls"); "No release notes" KHONG tinh.
RELEASE_RE = re.compile(r"\b(?:[a-z]*release|rls)\b(?!\s*notes?\b)", re.I)
# Note khong ghi loai -> "?": chi biet sau khi cai, doc co debuggable bang adb (user chot 29/10/2026).
CHUA_RO = "?"


def loai_theo_note(note: str) -> str:
    if DEBUG_RE.search(note):
        return "debug"
    return "release" if RELEASE_RE.search(note) else CHUA_RO


def _co(nodes, rid: str = "", text: str | tuple[str, ...] = "", package: str = ""):
    """`text` la tuple -> khop mot trong cac chu (cung nut o cac ngon ngu may)."""
    chu = (text,) if isinstance(text, str) else text
    return next((n for n in nodes if (not rid or n.resource_id == rid)
                 and (not text or n.text in chu) and (not package or n.package == package)), None)


def man(nodes) -> str:
    """Ten man dang hien: danh_sach, chi_tiet, consent, hop_cai, pp_quet, pp_dang_quet, pp_an_toan, oppo_cai,
    khac."""
    if _co(nodes, "consentPage"):
        return "consent"
    if _co(nodes, "appListRecyclerView"):
        return "danh_sach"
    if _co(nodes, "appDetailRecyclerView"):
        return "chi_tiet"
    if _co(nodes, "button1", package=INSTALLER):
        return "hop_cai"
    if _co(nodes, "install_status_primary_btn", package=OPPO_MARKET):
        return "oppo_cai"
    if _co(nodes, package=PLAY_STORE):
        if _co(nodes, text=PP_QUET, package=PLAY_STORE):
            return "pp_quet"
        if _co(nodes, text=PP_CAI, package=PLAY_STORE):
            return "pp_an_toan"
        # Dang quet (chu tuy ngon ngu) -> cho tiep, khong tinh la man la.
        return "pp_dang_quet"
    return "khac"


def nut_chap_nhan(nodes):
    """Nut dong y cua hop quet / cai bat ky (khong phai cua App Tester): None neu man khong co."""
    return next((n for n in nodes if n.package != APP_TESTER and n.text
                 and n.text.strip().casefold() in CHAP_NHAN), None)


def nut_chu(nodes, text: str | tuple[str, ...], package: str):
    """Node co chu dung `text` cua `package` (nut Play Protect khong co id)."""
    return _co(nodes, text=text, package=package)


def dong_app(nodes, bundle: str):
    """Node de bam vao app co `bundle_id` khop CHINH XAC package, du cao (khong bi cat o mep). None neu chua thay.

    Dong package bi mep duoi cat con 32px ma ten app cung dong van hien du (AIP882 29/10/2026: trang nao
    cung roi dung mep -> vuot qua mai, bao "khong co app") -> bam vao ten app cung dong."""
    n = _co(nodes, "bundle_id", text=bundle)
    if n is None:
        return None
    dong = n.node_id.rsplit(".", 1)[0] + "."
    ten = next((x for x in nodes if x.resource_id == "app_name" and x.node_id.startswith(dong)), None)
    return next((x for x in (n, ten) if x is not None and x.bounds.bottom - x.bounds.top >= 40), None)


def _con(nodes, cha) -> list:
    tien_to = cha.node_id + "."
    return [n for n in nodes if n.node_id.startswith(tien_to)]


def cac_ban(nodes) -> list[dict]:
    """Moi release dang thay tren man chi tiet: version, ngay, note, loai, trang thai nut.

    `nut` chi co khi release dang mo rong ("tai" | "da_tai" | "dang_cai" | "ha_cap"), `node_nut` de bam,
    `node_mo` (version_info) de bam mo rong. Note: ban day du neu dang mo, khong thi ban rut gon.
    """
    ra = []
    for row in (n for n in nodes if n.resource_id == "release_row"):
        con = _con(nodes, row)
        ver = _co(con, "version_info")
        ngay = _co(con, "distributed_at")
        # Dong nao cung co note (it nhat "No release notes"): thieu mot trong ba la
        # dong bi cat o mep man -> doc o lan cuon sau, khong de thanh release gia.
        note = _co(con, "release_notes_full") or _co(con, "release_notes_short")
        if ver is None or ngay is None or note is None:
            continue
        nut = next((n for n in con if n.resource_id in NUT_BAN), None)
        loai_nut = NUT_BAN[nut.resource_id] if nut else ""
        if loai_nut == "dang_cai" and nut.text in DA_TAI:
            loai_nut = "da_tai"
        ra.append({
            "version": ver.text,
            "ngay": ngay.text.split("•")[0].strip(),
            "note": note.text,
            "loai": loai_theo_note(note.text),
            "mo_rong": _co(con, "caret_up") is not None,
            "nut": loai_nut,
            "node_nut": nut,
            "node_mo": ver,
        })
    return ra


NGAY_VI_RE = re.compile(r"thg (\d{1,2}) (\d{1,2}), (\d{4}) lúc (\d{1,2}):(\d{2}) (SA|CH)")


def _luc_day(b: dict) -> datetime:
    """Ngay App Tester ghi (`Oct 15, 2026 at 3:10 PM` / may vi-VN `thg 10 30, 2026 lúc 3:42 CH`);
    doc khong duoc -> coi la cu nhat."""
    try:
        return datetime.strptime(b["ngay"], "%b %d, %Y at %I:%M %p")
    except ValueError:
        pass
    m = NGAY_VI_RE.search(b["ngay"])
    if not m:
        return datetime.min
    thang, ngay, nam, gio, phut, buoi = m.groups()
    gio = int(gio) % 12 + (12 if buoi == "CH" else 0)
    try:
        return datetime(int(nam), int(thang), int(ngay), gio, int(phut))
    except ValueError:
        return datetime.min


def chon_ban(cac: list[dict], version: str, loai: str) -> tuple[dict | None, str]:
    """Release dung version + loai -> (release, ""); khong co thi (None, ly do).

    Dev day lai cung version + loai nhieu lan -> lay lan day moi nhat (user chot 28/10/2026).
    App Tester xep moi o tren: `max` giu ban dau tien khi ngay bang nhau / khong doc duoc ngay.
    Note khong ghi loai (CHUA_RO): release van tinh nhu truoc (dev hiem ghi "release"); debug chi
    lay khi khong co ban nao ghi ro debug - cai xong `cai` kiem co debuggable bang adb.
    """
    cung_ver = [b for b in cac if b["version"] == version]
    if not cung_ver:
        return None, f"App Tester chưa có {version}"
    dung = [b for b in cung_ver if b["loai"] == loai or (loai == "release" and b["loai"] == CHUA_RO)]
    if not dung:
        dung = [b for b in cung_ver if b["loai"] == CHUA_RO]
    if not dung:
        co = ", ".join(sorted({b["loai"] for b in cung_ver}))
        return None, f"{version} chưa có bản {loai} (mới có: {co})"
    return max(dung, key=_luc_day), ""


def khoa_ban(b: dict) -> tuple[str, str, str]:
    """Khoa de gop release qua nhieu lan cuon (cung release hien o 2 dump)."""
    return b["version"], b["ngay"], b["note"][:40]
