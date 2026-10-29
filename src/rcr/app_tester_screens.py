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
# Nut cua mot release da mo rong: tai moi / mo ban dang cai / ha cap.
NUT_BAN = {"download_button": "tai", "open_button": "dang_cai", "downgrade_release": "ha_cap"}
# `open_button` ghi "Install" khi APK da tai ma chua cai (bam Cancel o hop cai, do
# 27/10/2026) - cung id voi nut "Open" cua ban dang cai.
DA_TAI = "Install"
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


def _co(nodes, rid: str = "", text: str = "", package: str = ""):
    return next((n for n in nodes if (not rid or n.resource_id == rid)
                 and (not text or n.text == text) and (not package or n.package == package)), None)


def man(nodes) -> str:
    """Ten man dang hien: danh_sach, chi_tiet, consent, hop_cai, pp_quet, pp_dang_quet, pp_an_toan, khac."""
    if _co(nodes, "consentPage"):
        return "consent"
    if _co(nodes, "appListRecyclerView"):
        return "danh_sach"
    if _co(nodes, "appDetailRecyclerView"):
        return "chi_tiet"
    if _co(nodes, "button1", package=INSTALLER):
        return "hop_cai"
    if _co(nodes, package=PLAY_STORE):
        if _co(nodes, text="Scan app", package=PLAY_STORE):
            return "pp_quet"
        if _co(nodes, text="Scanning…", package=PLAY_STORE):
            return "pp_dang_quet"
        if _co(nodes, text="Install", package=PLAY_STORE):
            return "pp_an_toan"
    return "khac"


def nut_chu(nodes, text: str, package: str):
    """Node co chu dung `text` cua `package` (nut Play Protect khong co id)."""
    return _co(nodes, text=text, package=package)


def dong_app(nodes, bundle: str):
    """Node `bundle_id` khop CHINH XAC package, du cao de bam (khong bi cat o mep). None neu chua thay."""
    n = _co(nodes, "bundle_id", text=bundle)
    if n is None or n.bounds.bottom - n.bounds.top < 40:
        return None
    return n


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
        if loai_nut == "dang_cai" and nut.text == DA_TAI:
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


def _luc_day(b: dict) -> datetime:
    """Ngay App Tester ghi (`Oct 15, 2026 at 3:10 PM`); doc khong duoc -> coi la cu nhat."""
    try:
        return datetime.strptime(b["ngay"], "%b %d, %Y at %I:%M %p")
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
