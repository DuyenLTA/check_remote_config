"""Tra link trang Rollout + link Checklist cua mot app tren Confluence (lenh /rollout cua bot).

- Rollout: trang con cua trang app, ten kieu `AIP924 - Rollout`, `AIP893 Rollout History`, `[AAP871] Rollout - ...`.
  Tim bang CQL theo ma app + "rollout", chi nhan trang co dung ma app trong ten; nhieu trang -> trang sua gan nhat.
- Checklist: file Google Sheet rieng cua app (vd "AIP893 - Glovy - ... - Checklist"), khong nam o trang Rollout ma
  duoc dan o cac trang version cua app dang `Checklist: <link sheet>`. Lay link sheet dau tien co chu "checklist"
  dung ngay truoc, tren trang sua gan nhat duoi trang app. Bo "Checklist test" (sheet test chung, khong cua app).

Can CONFLUENCE_BASE_URL + CONFLUENCE_TOKEN (PAT) - doc qua `cau_hinh_bot.env` (env -> bien User Windows -> bot.env),
khong co thi dung lai dong `export CONFLUENCE_...` trong ~/.bashrc (cung cap ma `spec_sync` dang dung).
Nginx cua confluence.apero.vn chan User-Agent mac dinh cua urllib -> gui UA trinh duyet.
"""

from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from pathlib import Path

from .cau_hinh_bot import _doc_file_env, env

UA = "Mozilla/5.0"
SO_TRANG_DO = 25                      # so trang con (sua gan nhat) doc body de tim link checklist
LINK_SHEET = re.compile(r'href="(https://docs\.google\.com/spreadsheets/d/[^"]+)"')
TRUOC_LINK = 80                       # so ky tu chu (da bo the) truoc link de tim nhan "checklist"


class ConfluenceLoi(Exception):
    """Thieu cau hinh hoac goi Confluence loi - tra nguyen van cho nguoi go lenh."""


def _cau_hinh() -> tuple[str, str]:
    """Dung lai URL + PAT Confluence dang dung cho `spec_sync` (dong `export CONFLUENCE_...` trong ~/.bashrc):
    bot chay bang systemd / Task Scheduler khong nap .bashrc -> doc thang file khi env + bot.env khong co."""
    bashrc = _doc_file_env(Path.home() / ".bashrc")
    base = (env("CONFLUENCE_BASE_URL") or bashrc.get("CONFLUENCE_BASE_URL", "")).strip().rstrip("/")
    token = (env("CONFLUENCE_TOKEN") or bashrc.get("CONFLUENCE_TOKEN", "")).strip()
    if not base or not token:
        raise ConfluenceLoi("bot chưa có CONFLUENCE_BASE_URL / CONFLUENCE_TOKEN")
    return base, token


def _get(base: str, token: str, path: str, **params) -> dict:
    url = f"{base}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise ConfluenceLoi(f"gọi Confluence lỗi: {exc}") from None


def _co_ma(title: str, ma: str) -> bool:
    """Ma app dung nguyen cum trong ten trang (AIP93 khong khop AIP931)."""
    return re.search(rf"(?<![A-Z0-9]){re.escape(ma)}(?![0-9])", title.upper()) is not None


def chon_trang_rollout(ket_qua: list[dict], ma: str) -> dict | None:
    """Trang co ma app + chu rollout trong ten; ket_qua da xep sua gan nhat truoc -> lay trang dau."""
    return next((p for p in ket_qua if "rollout" in p["title"].lower() and _co_ma(p["title"], ma)), None)


def link_checklist(body: str) -> list[str]:
    """Moi link Google Sheet co nhan "checklist" ngay truoc (khong tinh "checklist test"), theo thu tu trong trang."""
    ra = []
    for m in LINK_SHEET.finditer(body):
        dau_the = body.rfind("<", 0, m.start())          # bo the <a ...> dang mo cua chinh link nay
        truoc = html.unescape(re.sub(r"<[^>]+>", " ", body[max(0, dau_the - 600):dau_the]))
        truoc = re.sub(r"\s+", " ", truoc).lower()[-TRUOC_LINK:]
        # Nhan co the bi tach the giua chu ("Ch ecklist") -> so khi bo khoang trang.
        gon = truoc.replace(" ", "")
        if "checklist" in gon and not gon.endswith(("checklisttest", "checklisttest:")):
            ra.append(html.unescape(m.group(1)))
    return ra


def sheet_id(link: str) -> str:
    m = re.search(r"/spreadsheets/d/([\w-]+)", link)
    return m.group(1) if m else link


def ten_sheet(link: str) -> str | None:
    """Ten file sheet doc tu <title> trang edit; sheet khong mo "ai co link" -> None (khong biet ten)."""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id(link)}/edit"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=15) as r:
            m = re.search(r"<title>([^<]*)</title>", r.read(400_000).decode("utf-8", "replace"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None
    ten = html.unescape(m.group(1)).rsplit(" - Google", 1)[0].strip() if m else ""
    return ten if ten and "sign in" not in ten.lower() and "đăng nhập" not in ten.lower() else None


def chon_checklist(ung_vien: list[tuple[str, dict]], ma: str, doc_ten=ten_sheet) -> tuple[dict | None, list[str]]:
    """Chon link checklist cua dung app. `ung_vien`: (link, trang) theo trang sua gan nhat truoc.
    Uu tien file co ma app trong ten; file ten ghi ma app khac (copy tu template app khac) -> bo;
    khong doc duoc ten -> giu lam du phong. Tra (lua chon | None, ten cac file bi bo)."""
    du_phong, bo, da_xem = None, [], set()
    for link, trang in ung_vien:
        sid = sheet_id(link)
        if sid in da_xem:
            continue
        da_xem.add(sid)
        ten = doc_ten(link)
        if ten and _co_ma(ten, ma):
            return {"url": link, "ten": ten, **trang}, bo
        if ten is None:
            du_phong = du_phong or {"url": link, "ten": None, **trang}
        else:
            bo.append(ten)
    return du_phong, bo


def tim(ma_app: str) -> dict:
    """{"ma", "rollout": {title, url} | None, "checklist": {url, trang, trang_url} | None, "app": title | None}."""
    ma = ma_app.strip().upper()
    base, token = _cau_hinh()
    ra: dict = {"ma": ma, "rollout": None, "checklist": None, "app": None}
    d = _get(base, token, "/rest/api/content/search", limit=50, expand="ancestors",
             cql=f'type=page AND title ~ "{ma}" ORDER BY lastmodified DESC')
    trang = d.get("results", [])
    ro = chon_trang_rollout(trang, ma)
    if ro:
        ra["rollout"] = {"title": ro["title"], "url": base + ro["_links"]["webui"]}
        app = (ro.get("ancestors") or [None])[-1]
    else:                                 # khong co Rollout: trang app = trang co ma app nam cao nhat trong cay
        cac = [p for p in trang if _co_ma(p["title"], ma)]
        app = min(cac, key=lambda p: len(p.get("ancestors") or []), default=None)
    if not app:
        return ra
    ra["app"] = app["title"]
    con = _get(base, token, "/rest/api/content/search", limit=SO_TRANG_DO, expand="body.storage",
               cql=f'(ancestor={app["id"]} OR id={app["id"]}) AND type=page AND text ~ "checklist" '
                   "ORDER BY lastmodified DESC")
    ung_vien = [(link, {"trang": p["title"], "trang_url": base + p["_links"]["webui"]})
                for p in con.get("results", [])
                for link in link_checklist(p.get("body", {}).get("storage", {}).get("value", ""))]
    ra["checklist"], ra["bo"] = chon_checklist(ung_vien, ma)
    return ra


def tin_tra_loi(kq: dict) -> str:
    """Tin Discord cho /rollout."""
    dong = [f"🔗 **{kq['ma']}**" + (f" — {kq['app']}" if kq.get("app") else "")]
    ro, ck = kq.get("rollout"), kq.get("checklist")
    dong.append(f"• Rollout: [{ro['title']}]({ro['url']})" if ro else "• Rollout: không thấy trang Rollout trên Confluence")
    if ck:
        ten = f"**{ck['ten']}**" if ck.get("ten") else "chưa xác nhận tên file (sheet không mở cho người có link)"
        dong.append(f"• Checklist: {ck['url']}\n  {ten} — lấy từ trang [{ck['trang']}]({ck['trang_url']})")
    else:
        dong.append("• Checklist: không thấy link checklist trên các trang của app")
    if kq.get("bo"):
        dong.append(f"  Bỏ qua link checklist của app khác: {', '.join(kq['bo'][:3])}")
    return "\n".join(dong)
