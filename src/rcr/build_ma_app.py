"""Tach tin build cua dev tren Discord -> ma app, version, loai ban can cai, package.

KHONG bam theo mau cau: dev doi mau tin la bot mat tin (28/10/2026 doi tu "Ban build
AIP882---AI-Video v4.3.0 (40) da duoc hoan thien" sang "AIP922 v3.7.0 (30) da len QA",
bot im lang bo qua). Chi tim hai thu o BAT KY DAU trong tin:
  - ma app: 3 chu + 3 so (AIP922)
  - version kem code: 4.3.0 (40), v3.7.0(30)
Thieu mot trong hai -> None; discord_bot hoi o kenh QA chu khong im lang.
Link (Drive, Firebase) bo truoc khi tim: trong link co so giong version.

Luat chon nhanh (user chot 28/10/2026):
  - tin co so SDK tutorial 3.7.0 / 3.7.1 (KHONG phai versionName) hoac chu next-gen -> checklist Next-Gen,
    cai ban release (release khong debuggable, chi cham duoc Next-Gen)
  - so SDK khac (3.5.4, 3.6.1, 3.6.2, 3.7.2...) hoac "revert next-gen" -> bo TC theo tab, ban debug
  - build KHONG apply SDK (build chuc nang, fix bug) -> bo qua: chua co workflow cho loai nay
So SDK chi lay khi dung sau chu tutorial / sdk / apply - "ads-core 2.0.0", "bump 4.3.0" khong tinh.

Package tra tu sheet "Check thong so KT": tab trung ma app, dong "Package name".
Khong doan theo ten app trong tin.
"""

from __future__ import annotations

import re

MA_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{3}\d{3})(?!\d)")
VERSION_RE = re.compile(r"v?\s?(\d+(?:\.\d+)+)\s*[(\[]\s*(\d+)\s*[)\]]", re.I)
# Ten app ngay sau ma, noi bang gach ("AIP882---AI-Video v4.3.0"); khong co gach thi khong co ten.
TEN_RE = re.compile(r"\s*-+\s*(\S[^\n]*?)\s+v?\s?\d+(?:\.\d+)+\s*[(\[]", re.I)
# "Tutorial SDK 3.7.0", "tutorial-sdk/3.7.0@abc", "apply tutorial 3.6.1", "apply 3.7.0", "SDK 3.6.2".
SDK_RE = re.compile(r"(?:tutorial|sdk|apply)(?:[\s/_-]*(?:tutorial|sdk))*[\s/_:-]*v?(\d+\.\d+\.\d+)", re.I)
REVERT_RE = re.compile(r"revert\s+next[\s-]?gen", re.I)
NEXT_GEN_RE = re.compile(r"next[\s-]?gen", re.I)
DAU_HIEU_BUILD_RE = re.compile(r"build|bản|\bqa\b|apk|release|debug|\d+\.\d+", re.I)
LINK_RE = re.compile(r"https?://\S+")
MENTION_RE = re.compile(r"<[@#][!&]?\d+>")
# Dau dinh dang markdown Discord: dev go "Ban build **AIP920** v1.6.0 (7)" (do 2026-10-27).
MARKDOWN_RE = re.compile(r"\*\*|__|~~|\|\||`|\*")
# Tutorial 3.7.0 = Next-Gen (user chot 2026-10-27), them 3.7.1 (2026-10-29) - cham duoc tren ban release.
NEXT_GEN_TUTORIAL = ("3.7.0", "3.7.1")


def _sach(text: str) -> str:
    return MENTION_RE.sub(" ", LINK_RE.sub(" ", MARKDOWN_RE.sub("", text or "")))


KENH_PROJECT_RE = re.compile(r"^([a-z]{3}\d{3})-")


def ma_cua_kenh(ten: str) -> str:
    """Kenh rieng cua project `aip920-ai-english-official-group` -> "AIP920"; kenh khac -> ""."""
    m = KENH_PROJECT_RE.match((ten or "").lower())
    return m.group(1).upper() if m else ""


def co_ma_app(text: str) -> bool:
    """Tin co ma app VA co dau hieu bao build (chu build/ban/QA/apk/release/debug hoac so version) -> la tin
    bao build, doc khong ra version thi phai hoi chu khong bo qua. Chi go ma app ('AIP918') la noi chuyen
    trong kenh, khong hoi (user phan nan 30/10/2026)."""
    t = _sach(text)
    return bool(MA_RE.search(t)) and bool(DAU_HIEU_BUILD_RE.search(t))


def tach(text: str, ma_kenh: str = "") -> dict | None:
    """{ma, ten, version, next_gen, tutorial, sdk} hoac None khi thieu ma app hoac version (code).

    `next_gen`: False khi "revert next-gen", True khi nhac next-gen, None khi khong nhac.
    `tutorial`: so SDK dung sau chu tutorial / sdk / apply, "" khi tin khong nhac.
    `sdk`: build co apply SDK khong (co so SDK hoac nhac next-gen) - False thi bot bo qua.
    `ma_kenh`: ma app suy tu ten kenh project (`aip922-...`) - dung khi tin trong kenh do khong ghi ma.
    """
    text = _sach(text)
    ma, ver = MA_RE.search(text), VERSION_RE.search(text)
    if not (ma or ma_kenh) or not ver:
        return None
    ten = TEN_RE.match(text, ma.end()) if ma else None
    # Version build hay duoc nhac lai trong ghi chu ("v3.7.0 (30) - tutorial-sdk/3.7.0"): bo het truoc
    # khi tim tutorial, khong thi version app bi doc thanh ban tutorial.
    ghi_chu = re.sub(rf"v?\s?{re.escape(ver.group(1))}\s*[(\[]\s*{ver.group(2)}\s*[)\]]", " ", text, flags=re.I)
    if REVERT_RE.search(ghi_chu):
        next_gen = False
    elif NEXT_GEN_RE.search(ghi_chu):
        next_gen = True
    else:
        next_gen = None
    tut = SDK_RE.search(ghi_chu)
    return {
        "ma": (ma.group(1) if ma else ma_kenh).upper(),
        "ten": ten.group(1).strip(" -") if ten else "",
        "version": f"{ver.group(1)} ({ver.group(2)})",
        "next_gen": next_gen,
        "tutorial": tut.group(1) if tut else "",
        "sdk": bool(tut) or next_gen is not None,
    }


def la_next_gen(tin: dict) -> bool:
    """Tin ghi next-gen hoac SDK 3.7.0 / 3.7.1 ma khong revert -> checklist Next-Gen, con lai bo TC theo tab."""
    if tin.get("next_gen") is False:
        return False
    return bool(tin.get("next_gen") or tin.get("tutorial") in NEXT_GEN_TUTORIAL)


def loai_ban(tin: dict) -> str:
    """Ban cai tu App Tester: luon "release" (user chot 31/10/2026: khong bat dev build them ban debug - bo TC doi
    Remote Config tren Firebase qua dieu kien `testvsl`, xem rc_firebase). Truoc do ban khong next-gen la "debug"."""
    return "release"


def package_cua(path, ma: str) -> str:
    """Package o dong "Package name" cua tab ten `ma` trong sheet KT, "" neu khong co."""
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = next((w for w in wb.worksheets if w.title.strip().upper() == ma.upper()), None)
        if ws is None:
            return ""
        for r in ws.iter_rows(values_only=True):
            o = [str(v).strip() for v in r if v not in (None, "")]
            if len(o) >= 2 and o[0].lower() == "package name":
                return o[1]
        return ""
    finally:
        wb.close()
