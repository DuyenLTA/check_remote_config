"""Jira REST (Server/DC) cho bot verify: tim issue dang Reviewing, comment, chuyen trang thai.

Goi thang REST bang PAT thay vi qua Claude headless: thao tac doi trang thai phai tat dinh,
khong ton tien + thoi gian khoi dong mcp-atlassian. Module khong tu doc env - bot truyen
`url, token` vao (de test). PAT chi nam trong header, khong bao gio vao chuoi loi.

Do tren jira.apero.vn (28/10/2026): cac transition khong co field bat buoc; JQL co key khong
ton tai -> 400 ca lenh, them `validateQuery=warn` thi bo qua key do. Tu Reviewing workflow bug
KHONG co transition "To Do"/"Done" - chi co "Reject Issue" -> Reopened (cot To Do cua board) va
"Close Issue" -> Closed (cot Done) (do 29/10/2026 tren AIP922-106) -> chon transition theo ten
HOAC trang thai dich. Mang toi Jira chap chon (VPN) -> loi ket noi thi thu lai vai lan.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}-\d+$")
PROJECT_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")
MAX_AUTO_QA = 50
TIMEOUT = 30
USER_AGENT = "qa-workflow-bot/1.0"
SO_LAN_THU = 4
CHO_THU_LAI = 5.0
# Dich khi verify xong, theo thu tu uu tien (ten transition hoac trang thai dich).
DICH_PASS = ("Done", "Closed")
DICH_FAIL = ("To Do", "Reopened")


class JiraLoi(RuntimeError):
    pass


def bat(url: str, token: str) -> bool:
    """Tinh nang verify chi bat khi co token va URL https."""
    return bool(token) and url.startswith("https://")


class _KhongRedirect(urllib.request.HTTPRedirectHandler):
    """urllib mac dinh chep header Authorization sang host redirect toi (SSO, http) -> lo PAT. Chan han."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_MO = urllib.request.build_opener(_KhongRedirect)


def _goi(url: str, token: str, method: str, path: str, body: dict | None = None):
    """Loi ket noi (URLError: request chua toi server) thi thu lai - an toan ca voi POST. Timeout
    khi doc phan hoi thi KHONG thu lai: request co the da ghi roi, gui lai la comment trung."""
    for lan in range(SO_LAN_THU):
        try:
            return _goi_mot_lan(url, token, method, path, body)
        except _MatKetNoi as e:
            if lan == SO_LAN_THU - 1:
                raise JiraLoi(str(e)) from None
            time.sleep(CHO_THU_LAI)


class _MatKetNoi(Exception):
    pass


def _goi_mot_lan(url: str, token: str, method: str, path: str, body: dict | None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url.rstrip("/") + path, data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/json",
        "Content-Type": "application/json", "User-Agent": USER_AGENT})
    dich = f"Jira {method} {path.split('?')[0]}"
    try:
        with _MO.open(req, timeout=TIMEOUT) as r:
            raw = r.read()
        return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        chu = e.read()[:200].decode("utf-8", "replace")
        raise JiraLoi(f"{dich} -> HTTP {e.code}: {chu}") from None
    except urllib.error.URLError as e:
        raise _MatKetNoi(f"{dich} khong ket noi duoc: {e.reason}") from None
    except TimeoutError as e:
        raise JiraLoi(f"{dich} khong ket noi duoc: {e}") from None
    except Exception as e:  # noqa: BLE001 - mat ket noi giua chung, trang HTML 200 (proxy)...: khong in chi tiet
        raise JiraLoi(f"{dich} loi {type(e).__name__}") from None


def dang_reviewing(url: str, token: str, keys: list[str]) -> list[str]:
    """Cac key dang o trang thai Reviewing. Key sai mau bi loai truoc khi ghep JQL;
    key da xoa / chuyen project khong tra ve -> coi nhu khong Reviewing."""
    sach = sorted({k for k in keys if KEY_RE.fullmatch(k)})
    if not sach:
        return []
    jql = f"key in ({', '.join(sach)}) AND status = Reviewing"
    q = urllib.parse.urlencode({"jql": jql, "fields": "status", "maxResults": len(sach), "validateQuery": "warn"})
    d = _goi(url, token, "GET", f"/rest/api/2/search?{q}")
    return [i["key"] for i in (d or {}).get("issues", [])]


def tim_auto_qa(url: str, token: str, project: str) -> list[dict]:
    """Bug dang Reviewing mang label `auto-qa` cua project: [{key, link, summary, marker}]; marker la
    {case, loai_ban, package} doc tu description, None khi thieu / sai mau. Toi da MAX_AUTO_QA issue."""
    from .bot_jira_marker import LABEL, doc_marker

    if not PROJECT_RE.fullmatch(project or ""):
        raise JiraLoi(f"project key Jira sai mau: {project!r}")
    jql = f'project = {project} AND labels = "{LABEL}" AND status = Reviewing ORDER BY key'
    q = urllib.parse.urlencode({"jql": jql, "fields": "summary,description", "maxResults": MAX_AUTO_QA,
                                "validateQuery": "warn"})
    d = _goi(url, token, "GET", f"/rest/api/2/search?{q}")
    ra = []
    for i in (d or {}).get("issues", []):
        key = str(i.get("key") or "")
        if not KEY_RE.fullmatch(key):
            continue
        f = i.get("fields") or {}
        ra.append({"key": key, "link": f"{url.rstrip('/')}/browse/{key}", "summary": str(f.get("summary") or ""),
                   "marker": doc_marker(f.get("description"))})
    return ra


def comment(url: str, token: str, key: str, text: str) -> None:
    if not KEY_RE.fullmatch(key):
        raise JiraLoi(f"key Jira sai mau: {key!r}")
    _goi(url, token, "POST", f"/rest/api/2/issue/{key}/comment", {"body": text})


def da_comment(url: str, token: str, key: str, dau: str) -> bool:
    """Issue da co comment bat dau bang `dau` chua - verify lai sau khi chuyen trang thai loi thi
    khong comment trung."""
    if not KEY_RE.fullmatch(key):
        raise JiraLoi(f"key Jira sai mau: {key!r}")
    d = _goi(url, token, "GET", f"/rest/api/2/issue/{key}/comment?maxResults=200")
    return any(str(c.get("body") or "").startswith(dau) for c in (d or {}).get("comments", []))


def chuyen(url: str, token: str, key: str, ten: str | tuple[str, ...]) -> None:
    """Chuyen issue qua transition khop `ten` theo ten transition HOAC trang thai dich (khong phan
    biet hoa thuong); nhieu ten thi ten dau khop truoc. Tra theo ten vi id transition khac nhau giua
    cac workflow; khong khop ten nao -> loi, khong doan."""
    if not KEY_RE.fullmatch(key):
        raise JiraLoi(f"key Jira sai mau: {key!r}")
    cac_ten = (ten,) if isinstance(ten, str) else tuple(ten)
    d = _goi(url, token, "GET", f"/rest/api/2/issue/{key}/transitions")
    ts = (d or {}).get("transitions", [])

    def khop(t: dict, x: str) -> bool:
        return x.casefold() in (str(t.get("name") or "").casefold(),
                                str((t.get("to") or {}).get("name") or "").casefold())

    tid = next((t["id"] for x in cac_ten for t in ts if khop(t, x)), None)
    if tid is None:
        co = ", ".join(f"{t.get('name', '')} -> {(t.get('to') or {}).get('name', '?')}" for t in ts)
        raise JiraLoi(f"{key} khong co transition '{' / '.join(cac_ten)}' (co: {co})")
    _goi(url, token, "POST", f"/rest/api/2/issue/{key}/transitions", {"transition": {"id": str(tid)}})
