"""Tao / xoa dieu kien `testvsl` tren Firebase Remote Config (lenh /testvsl, nut tren tin nhac cua bot).

User chot 20/11/2026: QA hay quen xoa condition khi test xong -> bot tu tao condition theo dung version dang
test, va nhac xoa (kem nut) khi QA bao test pass. CHI xoa / sua condition do chinh tai khoan `firebase login`
tren may bot tao (tai khoan cua QA chu bot): nguoi tao doc tu lich su version Remote Config - `updateUser` cua
version dau tien co condition, tinh tu version moi nhat lui ve. Condition cua nguoi khac thi khong dung.

Moi lan publish deu chot chan: ngoai condition `testvsl` (va gia tri gan theo no), template phai y het ban vua doc.
"""

from __future__ import annotations

import copy
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import rc_firebase as rc
from .models import RcError

DIEU_KIEN = rc.DIEU_KIEN
RC_API = "https://firebaseremoteconfig.googleapis.com/v1/projects/{project}/remoteConfig"
QL_API = "https://firebase.googleapis.com/v1beta1"
# Firebase giu toi da 300 version; condition co tu truoc do thi khong biet ai tao -> khong xoa.
SO_VERSION_TOI_DA = 300
LUONG = 8                     # doc song song template cac version cu khi lui tim nguoi tao
VERSION_TRONG_DK = re.compile(r"app\.version\.contains\(\[([^\]]*)\]\)")


def email_dang_nhap() -> str:
    """Email tai khoan `firebase login` tren may bot (configstore cua firebase-tools)."""
    try:
        return json.loads(rc._configstore().read_text(encoding="utf-8"))["user"]["email"]
    except (OSError, KeyError, ValueError, TypeError):
        raise RcError(rc.CHUA_DANG_NHAP) from None


def ten_version(version: str) -> str:
    """"1.1.0 (3)" -> "1.1.0": condition so voi versionName, khong kem version code."""
    return re.sub(r"\s*[(\[].*$", "", (version or "").strip()).lstrip("vV").strip()


def bieu_thuc(app_id: str, version: str | list[str]) -> str:
    """Mot hoac nhieu version (tin build lech plan tuan -> chua ca hai, dev build lai dung khoi tao lai)."""
    cac = []
    for v in [version] if isinstance(version, str) else version:
        if ten_version(v) and ten_version(v) not in cac:
            cac.append(ten_version(v))
    return f"app.id == '{app_id}' && app.version.contains([{', '.join(repr(v) for v in cac)}])"


def versions_trong(expr: str) -> list[str]:
    m = VERSION_TRONG_DK.search(expr or "")
    return [v.strip().strip("'\"") for v in m.group(1).split(",") if v.strip()] if m else []


def _get(url: str, tok: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})

    def goi():
        with urllib.request.urlopen(req, timeout=rc.TIMEOUT) as r:
            return json.load(r)
    return rc._mang(goi)


def _dk(t: dict, dk: str = DIEU_KIEN) -> dict | None:
    return next((c for c in t.get("conditions") or [] if c.get("name") == dk), None)


# --- tim Firebase project + app id theo package (khong can may) ---------------------------------------------

def tim_app(package: str) -> dict:
    """{project, app_id} cua package: cache APK da keo (rc_firebase_app) truoc, khong co thi quet cac project
    tai khoan thay duoc (Firebase Management API) roi nho vao cache."""
    from . import rc_firebase_app as fa

    cache = fa._doc_cache()
    for v in cache.values():
        if isinstance(v, dict) and v.get("package") == package and v.get("project") and v.get("app_id"):
            return {"project": v["project"], "app_id": v["app_id"]}
    tok = rc.token()
    trang = ""
    while True:
        kq = _get(f"{QL_API}/projects?pageSize=100" + (f"&pageToken={trang}" if trang else ""), tok)
        for p in kq.get("results") or []:
            try:
                apps = _get(f"{QL_API}/projects/{p['projectId']}/androidApps", tok).get("apps") or []
            except urllib.error.HTTPError:
                continue                   # project khong co quyen doc app: bo qua
            for a in apps:
                if a.get("packageName") == package:
                    info = {"project": p["projectId"], "app_id": a["appId"], "package": package}
                    cache[f"pkg:{package}"] = info
                    fa._ghi_cache(cache)
                    return {"project": info["project"], "app_id": info["app_id"]}
        trang = kq.get("nextPageToken") or ""
        if not trang:
            raise RcError(f"không thấy Firebase app nào có package `{package}` trong các project tài khoản bot xem được")


# --- ai tao condition ----------------------------------------------------------------------------------------

def _cac_version(project: str, tok: str) -> list[dict]:
    """Cac version Remote Config, moi nhat truoc (toi da SO_VERSION_TOI_DA)."""
    ra, trang = [], ""
    while len(ra) < SO_VERSION_TOI_DA:
        kq = _get(RC_API.format(project=project) + ":listVersions?pageSize=100"
                  + (f"&pageToken={urllib.parse.quote(trang)}" if trang else ""), tok)
        ra += kq.get("versions") or []
        trang = kq.get("nextPageToken") or ""
        if not trang:
            break
    return sorted(ra, key=lambda v: -int(v.get("versionNumber") or 0))


def nguoi_tao(project: str, dk: str = DIEU_KIEN) -> str:
    """Email nguoi tao condition `dk` dang co (lan them gan nhat). Condition co tu truoc moc lich su Firebase con
    giu (300 version) -> nguoi dat bieu thuc hien tai trong lich su do. "" khi van khong xac dinh duoc (bieu thuc
    khong doi trong ca lich su con giu, hoac hien khong co condition)."""
    tok = rc.token()
    vs = _cac_version(project, tok)

    def bieu_thuc_luc(v: dict) -> str | None:
        t = _get(RC_API.format(project=project) + f"?versionNumber={v['versionNumber']}", tok)
        c = _dk(t, dk)
        return None if c is None else c.get("expression", "")

    def email(n: int) -> str:
        return (vs[n].get("updateUser") or {}).get("email") or ""

    hien, dat_bt = None, None          # bieu thuc hien tai / vi tri version DAT bieu thuc do (lui toi khi doi)
    with ThreadPoolExecutor(LUONG) as ex:
        for dau in range(0, len(vs), LUONG):
            for i, bt in enumerate(ex.map(bieu_thuc_luc, vs[dau:dau + LUONG])):
                n = dau + i
                if bt is None:
                    return email(n - 1) if n else ""
                if hien is None:
                    hien = bt
                elif dat_bt is None and bt != hien:
                    dat_bt = n - 1
    # Firebase chi giu 300 version gan nhat; rc-check publish 2 version moi case nen lich su chi con vai ngay
    # (AIP944 20/11/2026: 300 version tu 17/11, testvsl tao truoc do -> "khong xac dinh duoc nguoi tao").
    # Khong thay luc tao thi lay nguoi DAT bieu thuc hien tai (doi version gan nhat) trong lich su con giu.
    return email(dat_bt) if dat_bt is not None else ""


def trang_thai(project: str, dk: str = DIEU_KIEN) -> dict:
    """{co, bieu_thuc, versions, thu_tu, so_key, nguoi_tao, cua_toi} cua condition `dk` hien tai."""
    t, _ = rc.doc(project, rc.token())
    c = _dk(t, dk)
    if c is None:
        return {"co": False}
    tao = nguoi_tao(project, dk)
    return {"co": True, "bieu_thuc": c.get("expression", ""), "versions": versions_trong(c.get("expression", "")),
            "thu_tu": [x.get("name") for x in t.get("conditions") or []].index(dk) + 1,
            "so_key": len(rc.keys_dang_gan(t, dk)), "nguoi_tao": tao,
            "cua_toi": bool(tao) and tao.lower() == email_dang_nhap().lower()}


# --- sua template --------------------------------------------------------------------------------------------

def _ngoai_dk(t: dict, dk: str) -> str:
    """Template bo het dau vet cua `dk` (condition + gia tri gan theo no) - phan nay khong duoc doi."""
    t = rc._bo_dieu_kien(t, dk)
    t["conditions"] = [c for c in t.get("conditions") or [] if c.get("name") != dk]
    if not t["conditions"]:
        t.pop("conditions")
    return json.dumps(t, sort_keys=True)


def _publish(project: str, sua, dk: str) -> int:
    """Doc -> `sua(template)` -> chot chan ngoai `dk` -> PUT If-Match. 412 (nguoi khac vua publish) -> doc lai."""
    tok = rc.token()
    rc.quen(project)
    for _ in range(rc.SO_LAN_THU):
        t, etag = rc.doc(project, tok)
        t.pop("version", None)
        cu = copy.deepcopy(t)
        moi = sua(t)
        if _ngoai_dk(cu, dk) != _ngoai_dk(moi, dk):
            raise RcError(f"bot định sửa Remote Config ngoài điều kiện `{dk}` - đã chặn, không publish")
        try:
            kq, _ = rc._goi(project, tok, "PUT", moi, etag)
        except urllib.error.HTTPError as e:
            if e.code == 412:
                continue
            raise RcError(f"publish Remote Config {project} lỗi (HTTP {e.code}): {rc._than_loi(e)}") from None
        finally:
            rc.quen(project)
        return int((kq.get("version") or {}).get("versionNumber") or 0)
    raise RcError(f"Remote Config {project} bị người khác publish liên tục, thử lại sau")


def tao(project: str, app_id: str, version: str | list[str], dk: str = DIEU_KIEN) -> str:
    """Tao condition `dk` = app.id + dung version (dung THU 1). Da co: dung roi thi thoi; condition cua minh
    (va khong con key nao dang gan) thi doi sang version nay; cua nguoi khac thi khong dung. Tra cau tom tat."""
    expr = bieu_thuc(app_id, version)
    t, _ = rc.doc(project, rc.token())
    c = _dk(t, dk)
    if c is not None:
        dung_thu_1 = (t.get("conditions") or [{}])[0].get("name") == dk
        if c.get("expression") == expr and dung_thu_1:
            return f"`{dk}` đã đúng version ({', '.join(versions_trong(expr))}) và đang đứng thứ 1 — không cần sửa."
        if not trang_thai(project, dk)["cua_toi"]:
            raise RcError(f"`{dk}` của project {project} do người khác tạo — bot không sửa")
        if rc.keys_dang_gan(t, dk):
            raise RcError(f"`{dk}` đang gán {len(rc.keys_dang_gan(t, dk))} key (có lượt đang chạy?) — chưa đổi version")

    def sua(t: dict) -> dict:
        ds = [x for x in t.get("conditions") or [] if x.get("name") != dk]
        cu = _dk(t, dk) or {"name": dk, "tagColor": "TEAL"}
        t["conditions"] = [{**cu, "expression": expr}] + ds
        return t

    so = _publish(project, sua, dk)
    return f"Đã {'sửa' if c is not None else 'tạo'} `{dk}` = `{expr}` (thứ 1) — Remote Config version {so}."


def xoa(project: str, dk: str = DIEU_KIEN) -> str:
    """Xoa condition `dk` + moi gia tri gan theo no, CHI khi tai khoan bot tao. Tra cau tom tat."""
    tt = trang_thai(project, dk)
    if not tt["co"]:
        return f"Project {project} không còn condition `{dk}`."
    if not tt["cua_toi"]:
        raise RcError(f"`{dk}` của project {project} do người khác tạo"
                      f"{'' if tt['nguoi_tao'] else ' (hoặc không xác định được người tạo)'} — bot không xoá")

    def sua(t: dict) -> dict:
        t = rc._bo_dieu_kien(t, dk)
        t["conditions"] = [x for x in t.get("conditions") or [] if x.get("name") != dk]
        return t

    so = _publish(project, sua, dk)
    return f"Đã xoá `{dk}` (`{tt['bieu_thuc']}`) của project {project} — Remote Config version {so}."
