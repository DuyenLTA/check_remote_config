"""Jira REST (Server/DC) cho bot verify: tim issue dang Reviewing, comment, chuyen trang thai.

Goi thang REST bang PAT thay vi qua Claude headless: thao tac doi trang thai phai tat dinh,
khong ton tien + thoi gian khoi dong mcp-atlassian. Module khong tu doc env - bot truyen
`url, token` vao (de test). PAT chi nam trong header, khong bao gio vao chuoi loi.

Do tren jira.apero.vn (28/10/2026): cac transition (To Do / Done / ...) khong co field bat
buoc; JQL co key khong ton tai -> 400 ca lenh, them `validateQuery=warn` thi bo qua key do.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}-\d+$")
TIMEOUT = 30
USER_AGENT = "qa-workflow-bot/1.0"


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
    except (urllib.error.URLError, TimeoutError) as e:
        raise JiraLoi(f"{dich} khong ket noi duoc: {getattr(e, 'reason', e)}") from None
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


def comment(url: str, token: str, key: str, text: str) -> None:
    if not KEY_RE.fullmatch(key):
        raise JiraLoi(f"key Jira sai mau: {key!r}")
    _goi(url, token, "POST", f"/rest/api/2/issue/{key}/comment", {"body": text})


def chuyen(url: str, token: str, key: str, ten: str) -> None:
    """Chuyen issue sang transition co ten `ten` (khong phan biet hoa thuong). Tra theo ten
    vi id transition khac nhau giua cac workflow; khong co ten do -> loi, khong doan."""
    if not KEY_RE.fullmatch(key):
        raise JiraLoi(f"key Jira sai mau: {key!r}")
    d = _goi(url, token, "GET", f"/rest/api/2/issue/{key}/transitions")
    ts = (d or {}).get("transitions", [])
    tid = next((t["id"] for t in ts if t.get("name", "").casefold() == ten.casefold()), None)
    if tid is None:
        co = ", ".join(t.get("name", "") for t in ts)
        raise JiraLoi(f"{key} khong co transition '{ten}' (co: {co})")
    _goi(url, token, "POST", f"/rest/api/2/issue/{key}/transitions", {"transition": {"id": str(tid)}})
