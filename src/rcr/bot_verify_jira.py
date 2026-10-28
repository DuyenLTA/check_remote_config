"""Logic thuan (khong mang, khong Discord) cua luot bot tu verify bug dev da keo sang Reviewing.

Chi bug bot tu tao tren Jira (ghi chu "tao moi") moi duoc verify: issue bot chi cap nhat vao
ban co san co the do nguoi log, noi dung khac case cua bot -> tu keo Done de sai.
Ket luan chi PASS/FAIL khi luot chay XONG va verdict dung chuoi do; moi thu khac giu nguyen
Reviewing. Chu trong comment Jira / tin Discord do code soan tu state, cat ngan tung truong.
"""

from __future__ import annotations

import re
import unicodedata

# `<tab>#<so|TC ID>` (tab co the co dau cach: `daily checkin#4`) hoac TC ID tran (`SDK350-OB3X-013`).
# Ma checklist Next-Gen (`HT-03`) khong khop -> khong chay lai duoc bang --case.
CASE_TC_RE = re.compile(r"^[\w.]+(?: [\w.]+)*#[\w.-]+$|^SDK\d{3}-[\w-]+$")
MAX_TRUONG = 300
MAX_TIN = 1900


def _khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def _cat(s, n: int = MAX_TRUONG) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def ung_vien(tin: dict, ma: str) -> list[dict]:
    """Moi issue bot da tao cho app `ma` (qua cac tin build cu) -> [{key, link, case, bug, loai_ban_goc}].
    Mot key chi lay mot lan (tin moi hon de len)."""
    ra: dict[str, dict] = {}
    for c in tin.values():
        if c.get("ma") != ma or not isinstance(c.get("jira"), dict):
            continue
        bug_theo_case = {b.get("case"): b for b in c.get("bugs") or [] if isinstance(b, dict)}
        for i in c["jira"].get("issues") or []:
            key = str(i.get("key") or "")
            if not key or not _khong_dau(str(i.get("ghi_chu") or "")).startswith("tao moi"):
                continue
            case = str(i.get("case") or "")
            ra[key] = {"key": key, "link": str(i.get("link") or ""), "case": case,
                       "bug": bug_theo_case.get(case) or {}, "loai_ban_goc": c.get("loai_ban", "")}
    return list(ra.values())


def phan_loai(uv: list[dict], loai_ban_moi: str) -> tuple[list[dict], list[tuple[dict, str]]]:
    """(chay duoc, [(bo qua, ly do)])."""
    chay, bo = [], []
    for u in uv:
        if not CASE_TC_RE.fullmatch(u["case"]):
            bo.append((u, "case checklist Next-Gen — cần verify tay"))
        elif u["loai_ban_goc"] and u["loai_ban_goc"] != loai_ban_moi:
            bo.append((u, f"bug từ bản {u['loai_ban_goc']}, build mới là bản {loai_ban_moi} — cần verify tay"))
        else:
            chay.append(u)
    return chay, bo


def ket_luan(kq: dict, u: dict) -> str | None:
    """"PASS" / "FAIL" hoac None (giu Reviewing)."""
    if kq.get("trang_thai") != "XONG":
        return None
    for c in kq.get("cases") or []:
        if c.get("case") == u["case"] and c.get("verdict") in ("PASS", "FAIL"):
            return c["verdict"]
    return None


def _thuc_te(kq: dict, u: dict) -> str:
    return next((c.get("thuc_te", "") for c in kq.get("cases") or [] if c.get("case") == u["case"]), "")


def noi_dung_comment(u: dict, kl: str, job: dict, kq: dict, may: str) -> str:
    dong = [f"[Bot auto verify] {kl} trên build {_cat(job.get('version'), 40)} ({job.get('loai_ban', '')}), "
            f"máy {_cat(may, 60)}, case {u['case']}.",
            f"Expected: {_cat(u['bug'].get('expected'))}",
            f"Thực tế: {_cat(_thuc_te(kq, u))}"]
    if str(kq.get("link") or "").startswith("https://"):   # duong dan file tren may dev khong mo duoc
        dong.append(f"Report: {_cat(kq['link'], 500)}")
    dong.append("→ Done" if kl == "PASS" else "→ Bug reopen (To Do)")
    return "\n".join(dong)


def tin_ket_qua(job: dict, dong: list[tuple[str, dict, str]]) -> str:
    """dong: [(loai, uv, ghi chu)] voi loai in done|todo|giu|bo -> tin qa-auto <= MAX_TIN ky tu."""
    icon = {"done": "✅ Done", "todo": "🔁 To Do", "giu": "⚠️ Giữ Reviewing", "bo": "⏭ Bỏ qua", "cho": "⏳ Chờ chạy"}
    ra = [f"🔁 **Verify bug Reviewing** — **{job.get('ma', '')}** `{_cat(job.get('version'), 40)}`"]
    for loai, u, ghi_chu in dong:
        them = f" — {_cat(ghi_chu, 160)}" if ghi_chu else ""
        ra.append(f"{icon[loai]} [{u['key']}]({u['link']}) `{u['case']}`{them}" if u["link"]
                  else f"{icon[loai]} {u['key']} `{u['case']}`{them}")
    chu = "\n".join(ra)
    return chu if len(chu) <= MAX_TIN else chu[: MAX_TIN - 1] + "…"


def tin_bao_dev_fail(job: dict, dong: list[tuple[str, dict, str]]) -> str | None:
    """Tin bao dev o kenh project: bug verify lai van FAIL, da keo ve To Do. None khi khong co."""
    fail = [u for loai, u, _ in dong if loai == "todo"]
    if not fail:
        return None
    ban = f"{job.get('ma', '')}---{job['ten']}" if job.get("ten") else job.get("ma", "")
    ra = [f"🔁 **Bug reopen** — bản build **{ban} v{_cat(job.get('version'), 40)}**",
          f"Verify lại vẫn FAIL, đã kéo {len(fail)} bug về To Do:"]
    for u in fail:
        tieu_de = f" — {_cat(u['bug'].get('tieu_de'), 120)}" if u["bug"].get("tieu_de") else ""
        link = f"\n  <{u['link']}>" if u["link"] else ""
        ra.append(f"• **{u['key']}**{tieu_de}{link}")
    chu = "\n".join(ra)
    return chu if len(chu) <= MAX_TIN else chu[: MAX_TIN - 1] + "…"
