"""Phan viec cua bot build-watch khong dinh toi Discord: tra package, goi rcr-cai-build, soan tin.

Tach khoi `discord_bot` de test khong can Discord / may.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from . import ad_units_sheet, build_ma_app, tc_source
from . import bot_jira_rest as jira_rest
from .models import RcError

log = logging.getLogger("rcr-bot")

TIMEOUT_CAI = 1500   # > app_tester_ui.TIMEOUT_CAI + mo App Tester
# Gioi han file dinh kem cua bot o server khong boost.
MAX_DINH_KEM = 10 * 1024 * 1024
TRANG_THAI = {"XONG": ("✅", "Xong"), "DUNG": ("⚠️", "Dừng — cần người xem"),
              "LOI": ("⛔", "Lỗi"), "HET_GIO": ("⏱️", "Hết giờ")}


def package_cua(ma: str, out_dir: Path) -> str:
    """Ma app -> package qua sheet "Check thong so KT" (tai ban moi, hong thi dung ban cu)."""
    link = os.environ.get("RC_AD_UNITS_SHEET") or ad_units_sheet.LINK
    try:
        path = tc_source.tai_ve(link, out_dir)
    except RcError:
        path = Path(out_dir) / f"tc-{tc_source.SHEET_RE.search(link).group(1)}.xlsx"
        if not path.exists():
            return ""
    return build_ma_app.package_cua(path, ma)


def _cli(args: list[str], timeout: int) -> dict:
    """Chay `rcr-cai-build` -> JSON, hoac {"loi": "..."} (dong LOI cua stderr)."""
    cmd = [sys.executable, "-m", "rcr.cli_cai_build", *args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"loi": f"rcr-cai-build quá {timeout // 60} phút"}
    if p.returncode == 0:
        return json.loads(p.stdout.strip().splitlines()[-1])
    dong = [d for d in p.stderr.splitlines() if d.startswith("LOI:")]
    loi = dong[-1][4:].strip() if dong else (p.stderr or p.stdout)[-300:]
    # Tin Discord bi ghi de khi QA bam Thu lai -> ghi lai o log bot de con tra duoc nguyen nhan.
    log.warning("rcr-cai-build %s loi: %s", " ".join(args), loi)
    return {"loi": loi}


def cai(package: str, version: str, loai: str, serial: str, drive: str = "") -> dict:
    """Co `drive` (link Drive QA tra loi vao tin hoi) -> tai APK tu link, khong qua App Tester."""
    them = ["--apk-url", drive] if drive else []
    return _cli(["--package", package, "--version", version, "--loai", loai, "--serial", serial, *them],
                TIMEOUT_CAI)


def hoi_link_drive(c: dict) -> str | None:
    """Cai tu App Tester hong (thuong la chua co ban debug tren App Tester) -> hoi QA gui link Drive cua APK
    (user chot 29/10/2026). Da cai tu link Drive ma van hong -> None (hoi lai cung vo ich)."""
    if c.get("drive"):
        return None
    return (f"📦 **{c['ma']}** `{c['version']}`: App Tester chưa có bản {c.get('loai_ban') or 'debug'}? "
            "Trả lời tin này kèm **link Google Drive của APK** (chia sẻ \"Ai có link đều xem được\") "
            "— bot nhận link xong thì bấm chạy lại, bot sẽ tải APK từ link đó thay cho App Tester.")


def tin_da_cai(c: dict, ten: str, viec: str) -> str:
    """Tin MOI (tra loi duoi tin hoi) khi tai + cai duoc build: chi sua tin cu thi kenh khong bao, QA khong
    biet bot da tim duoc build (user chot 30/10/2026)."""
    nguon = "link Drive" if c.get("drive") else "App Tester"
    return (f"📲 {dau_tin(c)}\nĐã tải được bản {c.get('loai_ban') or ''} từ {nguon} và cài lên máy **{ten}** "
            f"— đang chạy {viec}.")


def ten_may(serial: str, model: str) -> str:
    return f"{model} ({serial[-4:]})" if model else serial


def dau_tin(c: dict) -> str:
    return f"**{c['ma']}** {c['ten']} `{c['version']}` — `{c['package']}`"


def tin_hoi(c: dict) -> str:
    """Tin o kenh QA khi thay build moi: hoi co chay khong."""
    goc = f"\n[Tin build]({c['link_tin']})" if c.get("link_tin") else ""
    if c.get("drive"):                    # QA tra loi kem link Drive (ban debug) -> khong qua App Tester
        return f"{dau_tin(c)}\n📦 tải APK từ link Drive QA gửi rồi chạy /rc-check. Chạy không?{goc}"
    if build_ma_app.la_next_gen(c):
        ghi = "next-gen → tải bản release, chấm checklist Next-Gen"
    else:
        ghi = "tải bản release, đổi RC qua điều kiện `testvsl` trên Firebase"
    return f"{dau_tin(c)}\n{ghi} từ App Tester rồi chạy /rc-check. Chạy không?{goc}"


def file_report(kq: dict, out_dir: Path) -> Path | None:
    """File HTML de dinh kem khi KHONG co link artifact (user chot 27/10/2026: co link thi chi gan link).

    `link` do Claude ghi -> chi nhan file .html nam trong `out_dir`, khong dinh kem file bat ky.
    """
    link = kq.get("link") or ""
    if not link or link.startswith("https://"):
        return None
    # Claude hay ghi duong dan TUONG DOI tinh tu repo ("out/sdk-.../report.html", luot AIP920
    # 28/10/2026) du prompt doi tuyet doi -> noi vao thu muc repo (cha cua out_dir), khong vao CWD.
    f = Path(link)
    if not f.is_absolute():
        f = Path(out_dir).parent / f
    try:
        f = f.resolve()
        f.relative_to(Path(out_dir).resolve())
    except (OSError, ValueError):
        return None
    if f.suffix.lower() != ".html" or not f.is_file() or f.stat().st_size > MAX_DINH_KEM:
        return None
    return f


def tin_ket_qua(c: dict, kq: dict, dinh_kem: Path | None = None) -> str:
    dau, chu = TRANG_THAI.get(kq["trang_thai"], ("•", kq["trang_thai"]))
    dong = [f"{dau} {dau_tin(c)} — {chu}", kq.get("tom_tat", "")[:300]]
    if kq.get("link", "").startswith("https://"):
        dong.append(f"Report: {kq['link']}")
    elif dinh_kem:
        dong.append(f"Report: file `{dinh_kem.name}` đính kèm (chưa publish được artifact)")
    elif kq.get("link"):
        dong.append(f"Report trên máy chạy bot: `{kq['link']}`")
    if kq.get("phut") is not None:
        dong.append(f"{kq['phut']} phút · ${kq.get('chi_phi') or 0:.2f}")
    return "\n".join(d for d in dong if d)


def lua_chon_bug(bugs: list[dict]) -> list[tuple[str, str, str]]:
    """(value, label, description) cho menu chon cua Discord - label/description toi da 100 ky tu."""
    return [(str(i), f"{b['case']} · {b['tieu_de']}"[:100], f"{b['muc_do']} · {b['thuc_te']}"[:100])
            for i, b in enumerate(bugs)]


def tin_bug(bugs: list[dict], chon: list[int] | None = None, c: dict | None = None) -> str:
    """Tin hoi QA review: dau tin co app + link report (user chot 28/10/2026: phai mo duoc report de
    xem), moi bug mot khoi tach dong trong de doc nhanh roi tick ngay tren Discord."""
    c = c or {}
    dong = [f"🐞 **{len(bugs)} bug cần review**" + (f" — {dau_tin(c)}" if c.get("ma") else ""),
            "Tick bug thật trong menu rồi bấm **Log Jira**."]
    link = str(c.get("link_report") or "")
    if link.startswith("https://"):              # duong dan file tren may thi QA khong mo duoc
        dong.append(f"📄 [Mở report]({link})")
    elif link.lower().endswith(".html"):         # publish hong -> bot dinh kem file report vao tin nay
        dong.append(f"📄 Report: file `{link.replace(chr(92), '/').rsplit('/', 1)[-1]}` đính kèm (chưa publish được artifact)")
    for i, b in enumerate(bugs):
        dau = "☑" if chon and i in chon else "☐"
        muc = f" · {b['muc_do']}" if b.get("muc_do") else ""
        dong += ["", f"{dau} **{i + 1}. {b['tieu_de'][:150]}**{muc}", f"> Case: `{b['case']}`",
                 f"> Expected: {b['expected'][:150]}", f"> Thực tế: {b['thuc_te'][:200]}"]
    # Tin Discord toi da 2000 ky tu; danh sach dai thi cat (link report o dau tin van con).
    t = "\n".join(dong)
    return t if len(t) <= 1900 else t[:1880] + "\n… (xem report)"


def tin_jira(kq: dict, so_bug: int) -> str:
    so = len([i for i in kq.get("issues") or [] if i.get("key")])
    dau = "✅" if so == so_bug and not kq.get("loi") else "⚠️"
    dong = [f"{dau} Đã log {so}/{so_bug} bug lên Jira"]
    for i in kq.get("issues") or []:
        ghi = f" ({i['ghi_chu']})" if i.get("ghi_chu") else ""
        dong.append(f"• {i['case']} → {i['key'] or 'không tạo'} {i['link']}{ghi}".rstrip())
    if kq.get("luu_y"):
        dong.append(f"Lưu ý: {kq['luu_y'][:300]}")
    if kq.get("loi"):
        dong.append(f"⛔ Lỗi: {kq['loi'][:300]}")
    if kq.get("chi_phi") is not None:
        dong.append(f"Chi phí: ${kq['chi_phi'] or 0:.2f}")
    return "\n".join(dong)


def tin_bao_dev(c: dict, kq: dict, bugs: list[dict]) -> str | None:
    """Tin bao dev cuoi luot log Jira: so bug + link Jira cua project, khong liet ke
    tung bug (dai). None khi khong co issue nao tao duoc -> khong lam phien dev bang tin rong.
    """
    issues = [i for i in kq.get("issues") or []
              if i.get("key") and not i.get("ghi_chu", "").startswith("bỏ qua")]
    if not issues:
        return None
    # Ghi dung nhu dong dau tin build cua dev ("AIP882---AI-Video v4.3.0 (40)") cho dev khoi nham ban.
    ban = f"{c['ma']}---{c['ten']}" if c.get("ten") else c["ma"]
    link = jira_rest.link_project([i.get("link", "") for i in issues])
    return "\n".join([f"🐞 **Nhờ dev check bug** — bản build **{ban} v{c['version']}**",
                      f"Đã log {len(issues)} bug lên Jira: "
                      + (f"<{link}>" if link else ", ".join(i["key"] for i in issues))])
