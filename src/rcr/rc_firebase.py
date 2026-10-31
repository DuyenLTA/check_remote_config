"""Doi Remote Config TREN SERVER Firebase cho ban release (khong run-as duoc), chi qua dieu kien cua QA.

User chot 30/10/2026: bat dev build them ban debug de nghiem thu SDK bat tien. QA tu tao dieu kien `testvsl`
(app.id + app.version cua ban dang test, keo len THU 1) -> tool chi gan / go gia tri cua dieu kien do, khong dung
default hay dieu kien khac nen user tren store khong bi anh huong. QA xoa dieu kien khi test xong.

Goi Remote Config REST v1 bang tai khoan QA da `firebase login` (refresh token trong configstore cua
firebase-tools). Moi lan PUT kem `If-Match: <etag>`: co nguoi vua publish -> 412, doc lai roi gan lai - khong de
thay doi cua nguoi khac (tuong duong bam Cancel popup "co nguoi sua" roi set lai tren Console). PUT la publish luon.
"""

from __future__ import annotations

import gzip
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .models import RcError
from .rc_variants import ABSENT

DIEU_KIEN = "testvsl"
API = "https://firebaseremoteconfig.googleapis.com/v1/projects/{project}/remoteConfig"
# OAuth client cong khai cua firebase-tools (lib/api.js) - refresh token do `firebase login` cap gan voi client nay.
CLIENT_ID = "563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com"
CLIENT_SECRET = "j9iVZfS8kkCEFUPaAeJV0sAi"
SO_LAN_THU = 3
THU_MANG = 4          # loi mang (VPN / handshake timeout, do 31/10/2026) -> thu lai
CHO_MANG = 5.0
TIMEOUT = 30
# Danh dau tham so do tool tao (key app doc ma server chua khai): chi tham so mang dau nay moi duoc xoa khi go.
# Tham so cua nguoi khac du co mac dinh "dung gia tri trong app" van giu nguyen (user chot 31/10/2026: khong
# dong vao bat cu thu gi ngoai gia tri cua dieu kien testvsl).
TOOL_TAO = "rc-check tạm (chỉ có giá trị ở điều kiện testvsl) - tool tự xoá"


def _tool_tao(p: dict) -> bool:
    return p.get("description") == TOOL_TAO and p.get("defaultValue") == {"useInAppDefault": True}


def _configstore() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "configstore" / "firebase-tools.json"


def da_dang_nhap() -> bool:
    """Co refresh token cua `firebase login` tren may (chua kiem con han)."""
    try:
        return bool(json.loads(_configstore().read_text(encoding="utf-8"))["tokens"]["refresh_token"])
    except (OSError, KeyError, ValueError, TypeError):
        return False


def _mang(goi):
    """Goi `goi()`; loi ket noi / timeout -> thu lai THU_MANG lan roi RcError (run_batch bat RcError tung case,
    URLError tran ra la chet ca luot - AIP886 31/10/2026). HTTPError (server tra loi) khong thu lai o day."""
    for lan in range(THU_MANG):
        try:
            return goi()
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if lan == THU_MANG - 1:
                raise RcError(f"không kết nối được Firebase sau {THU_MANG} lần: {exc}") from None
            time.sleep(CHO_MANG)


def token() -> str:
    try:
        rt = json.loads(_configstore().read_text(encoding="utf-8"))["tokens"]["refresh_token"]
    except (OSError, KeyError, ValueError):
        raise RcError("chưa đăng nhập Firebase CLI: chạy `firebase login` bằng tài khoản có quyền sửa RC") from None
    body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": rt, "client_id": CLIENT_ID,
                                   "client_secret": CLIENT_SECRET}).encode()
    try:
        def goi():
            with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=body, timeout=TIMEOUT) as r:
                return json.load(r)["access_token"]
        return _mang(goi)
    except urllib.error.HTTPError as e:
        raise RcError(f"đăng nhập Firebase hết hạn (HTTP {e.code}): chạy lại `firebase login --reauth`") from None


def _goi(project: str, tok: str, method: str = "GET", template: dict | None = None, etag: str = ""):
    h = {"Authorization": f"Bearer {tok}", "Accept-Encoding": "gzip"}
    data = None
    if template is not None:
        h.update({"Content-Type": "application/json; UTF-8", "If-Match": etag})
        data = json.dumps(template).encode("utf-8")
    req = urllib.request.Request(API.format(project=urllib.parse.quote(project)), data=data, method=method, headers=h)

    def goi():
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return json.loads(raw), r.headers.get("ETag", "")
    # PUT timeout sau khi da toi server: gui lai cung etag -> 412 -> _sua doc lai va gan lai (gan lap lai vo hai).
    return _mang(goi)


def doc(project: str, tok: str) -> tuple[dict, str]:
    try:
        return _goi(project, tok)
    except urllib.error.HTTPError as e:
        raise RcError(f"không đọc được Remote Config {project} (HTTP {e.code}): "
                      f"{e.read()[:200].decode('utf-8', 'replace')}") from None


def kiem_dieu_kien(t: dict, dk: str = DIEU_KIEN) -> str:
    """Bieu thuc cua `dk`; thieu hoac khong dung THU 1 -> RcError (dieu kien tren no khop truoc thi gia tri
    test bi bo qua ma khong ai biet)."""
    ds = t.get("conditions") or []
    i = next((n for n, c in enumerate(ds) if c.get("name") == dk), None)
    if i is None:
        raise RcError(f"Remote Config chưa có điều kiện `{dk}` (QA tạo theo app + version đang test)")
    if i != 0:
        raise RcError(f"điều kiện `{dk}` đang đứng thứ {i + 1}, phải kéo lên thứ 1")
    return ds[0].get("expression", "")


def _tham_so(t: dict, key: str) -> dict | None:
    if key in (t.get("parameters") or {}):
        return t["parameters"][key]
    return next((g["parameters"][key] for g in (t.get("parameterGroups") or {}).values()
                 if key in (g.get("parameters") or {})), None)


def gan(t: dict, gia_tri: dict[str, str], dk: str = DIEU_KIEN) -> dict:
    """Gan `gia_tri` vao dieu kien `dk` (sua `t` tai cho). Key chua co tren RC -> tham so moi, mac dinh dung gia
    tri trong app (user khac van nhu cu)."""
    for key, v in gia_tri.items():
        p = _tham_so(t, key)
        if p is None:
            p = t.setdefault("parameters", {})[key] = {"defaultValue": {"useInAppDefault": True},
                                                       "description": TOOL_TAO}
        # `<absent>` cua bo TC = app khong nhan key -> dung gia tri mac dinh trong app.
        p.setdefault("conditionalValues", {})[dk] = {"useInAppDefault": True} if v == ABSENT else {"value": str(v)}
    return t


def go(t: dict, keys, dk: str = DIEU_KIEN) -> dict:
    """Bo gia tri cua `dk` khoi `keys`; tham so chi con lai mac-dinh-trong-app (tool tu tao) thi xoa han."""
    for key in keys:
        p = _tham_so(t, key)
        if p is None:
            continue
        (p.get("conditionalValues") or {}).pop(dk, None)
        if "conditionalValues" in p and not p["conditionalValues"]:
            del p["conditionalValues"]       # tra tham so ve y nhu luc chua gan
        if "conditionalValues" not in p and _tool_tao(p) and key in (t.get("parameters") or {}):
            del t["parameters"][key]
    return t


def _bo_dieu_kien(t: dict, dk: str) -> dict:
    """Template bo het gia tri cua `dk` va tham so chi do tool tao (mac dinh trong app, khong con gia tri nao)."""
    import copy

    t = copy.deepcopy(t)
    t.pop("version", None)
    nhom = [t.get("parameters") or {}] + [g.get("parameters") or {} for g in (t.get("parameterGroups") or {}).values()]
    for ps in nhom:
        for k in list(ps):
            (ps[k].get("conditionalValues") or {}).pop(dk, None)
            if not ps[k].get("conditionalValues"):
                ps[k].pop("conditionalValues", None)
                if _tool_tao(ps[k]) and ps is t.get("parameters"):
                    del ps[k]
    return t


def chi_doi_dieu_kien(cu: dict, moi: dict, dk: str = DIEU_KIEN) -> None:
    """Chot chan (user chot 30/10/2026: "bat buoc chi duoc sua vao condition testvsl"): ngoai gia tri cua `dk`,
    template moi phai y het ban vua doc - default, dieu kien khac, thu tu dieu kien. Khac -> RcError, khong publish."""
    if json.dumps(_bo_dieu_kien(cu, dk), sort_keys=True) != json.dumps(_bo_dieu_kien(moi, dk), sort_keys=True):
        raise RcError(f"tool định sửa Remote Config ngoài điều kiện `{dk}` (default / điều kiện khác) - đã chặn, "
                      "không publish")


def _sua(project: str, sua, dk: str) -> int:
    """Doc -> kiem dieu kien -> `sua(template)` -> publish voi If-Match; 412 (nguoi khac vua publish) -> lam lai."""
    tok = token()
    for _ in range(SO_LAN_THU):
        t, etag = doc(project, tok)
        kiem_dieu_kien(t, dk)
        t.pop("version", None)
        import copy

        cu = copy.deepcopy(t)
        gui = sua(t)
        chi_doi_dieu_kien(cu, gui, dk)
        try:
            moi, _ = _goi(project, tok, "PUT", gui, etag)
            return int((moi.get("version") or {}).get("versionNumber") or 0)
        except urllib.error.HTTPError as e:
            if e.code != 412:
                raise RcError(f"publish Remote Config {project} lỗi (HTTP {e.code}): "
                              f"{e.read()[:300].decode('utf-8', 'replace')}") from None
    raise RcError(f"Remote Config {project} bị người khác publish liên tục, thử lại sau")


def dat(project: str, gia_tri: dict[str, str], dk: str = DIEU_KIEN) -> int:
    """Publish `gia_tri` theo dieu kien `dk`; tra version RC moi."""
    return _sua(project, lambda t: gan(t, gia_tri, dk), dk)


def tra(project: str, keys, dk: str = DIEU_KIEN) -> int:
    return _sua(project, lambda t: go(t, keys, dk), dk)


def keys_dang_gan(t: dict, dk: str = DIEU_KIEN) -> list[str]:
    ps = dict(t.get("parameters") or {})
    for g in (t.get("parameterGroups") or {}).values():
        ps.update(g.get("parameters") or {})
    return [k for k, p in ps.items() if dk in (p.get("conditionalValues") or {})]


def tra_het(project: str, dk: str = DIEU_KIEN) -> int:
    """Go MOI gia tri cua `dk` (sau case / cuoi luot / don luot chet giua chung). Khong co gi -> khong publish."""
    t, _ = doc(project, token())
    if not keys_dang_gan(t, dk):
        return 0
    return _sua(project, lambda t: go(t, keys_dang_gan(t, dk), dk), dk)
