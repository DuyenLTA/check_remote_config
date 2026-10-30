"""Keo bug bot da log (label `auto-qa`) dang nam backlog vao sprint active cua project.

User chot 30/10/2026: dev hay tao sprint muon -> luc log Jira board chua co sprint active, bug roi xuong
backlog. Bot dinh ky tim bug `auto-qa` chua thuoc sprint nao, chua xong; project nao da co sprint active
thi them bug vao sprint do (trang thai giu nguyen - bug moi o cot To Do). Chi dung bug cua bot (label),
khong cham issue nguoi khac tao.

Do tren jira.apero.vn 30/10/2026: JQL `sprint is EMPTY` chay duoc; bug moi log trang thai "Request"
(statusCategory new); board lay qua `/rest/agile/1.0/board?projectKeyOrId=`.
"""

from __future__ import annotations

import asyncio
import logging
import urllib.parse

from . import bot_jira_rest as jira
from .bot_jira_marker import LABEL

log = logging.getLogger("rcr-bot")
CHU_KY = 10 * 60          # giay giua 2 lan quet; dev tao sprint xong toi da ~10 phut bug len sprint
MAX_BUG = 200


def bug_ngoai_sprint(url: str, token: str) -> dict[str, list[str]]:
    """{project: [key]} cua bug `auto-qa` chua thuoc sprint nao va chua xong."""
    jql = f'labels = "{LABEL}" AND sprint is EMPTY AND statusCategory != Done ORDER BY key'
    q = urllib.parse.urlencode({"jql": jql, "fields": "status", "maxResults": MAX_BUG})
    d = jira._goi(url, token, "GET", f"/rest/api/2/search?{q}")
    ra: dict[str, list[str]] = {}
    for i in (d or {}).get("issues", []):
        key = str(i.get("key") or "")
        if jira.KEY_RE.fullmatch(key):
            ra.setdefault(key.rsplit("-", 1)[0], []).append(key)
    return ra


def sprint_active(url: str, token: str, project: str) -> dict | None:
    """Sprint active dau tien tren cac board cua project ({id, name}); chua co -> None."""
    if not jira.PROJECT_RE.fullmatch(project or ""):
        raise jira.JiraLoi(f"project key Jira sai mau: {project!r}")
    q = urllib.parse.urlencode({"projectKeyOrId": project})
    for b in (jira._goi(url, token, "GET", f"/rest/agile/1.0/board?{q}") or {}).get("values", []):
        if b.get("type") != "scrum":          # board kanban khong co sprint -> API tra 400
            continue
        s = jira._goi(url, token, "GET", f"/rest/agile/1.0/board/{int(b['id'])}/sprint?state=active") or {}
        for sp in s.get("values", []):
            return {"id": int(sp["id"]), "name": str(sp.get("name") or "")}
    return None


def them_vao_sprint(url: str, token: str, sprint_id: int, keys: list[str]) -> None:
    sach = [k for k in keys if jira.KEY_RE.fullmatch(k)]
    if sach:
        jira._goi(url, token, "POST", f"/rest/agile/1.0/sprint/{int(sprint_id)}/issue", {"issues": sach})


def keo(url: str, token: str) -> list[str]:
    """Mot lan quet; tra dong bao cho QA, moi project da keo mot dong. Loi mot project khong chan project khac."""
    dong = []
    for project, keys in bug_ngoai_sprint(url, token).items():
        try:
            sp = sprint_active(url, token, project)
            if sp is None:
                continue
            them_vao_sprint(url, token, sp["id"], keys)
        except jira.JiraLoi as exc:
            log.warning("khong keo duoc bug %s vao sprint: %s", project, exc)
            continue
        dong.append(f"📌 **{project}**: đã kéo {len(keys)} bug từ backlog vào sprint **{sp['name']}** "
                    f"({', '.join(keys)})")
    return dong


async def vong_lap(bot) -> None:
    """Chay nen trong bot: moi CHU_KY quet mot lan, co bug duoc keo thi bao kenh QA."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        if jira.bat(bot.jira_url, bot.jira_token):
            try:
                dong = await asyncio.to_thread(keo, bot.jira_url, bot.jira_token)
                if dong:
                    await bot.get_channel(bot.kenh_qa).send("\n".join(dong)[:2000])
            except Exception as exc:          # noqa: BLE001 - loi Jira / Discord khong duoc giet vong lap
                log.warning("quet bug backlog loi: %s", exc)
        await asyncio.sleep(CHU_KY)
