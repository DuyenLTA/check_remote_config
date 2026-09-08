"""Test doc lai config sau khi mo app.

Diem phai gac:
  - verify sau patch -> ok (khong lech)
  - app fetch de mat patch -> phat hien duoc, verdict_hint = BLOCKED (khong FAIL)
  - key dung o activate ma SAI o mirror -> van phai bao lech (app doc mirror)
  - so sanh mirror theo KIEU (int '7' vs '7', boolean 'TRUE' vs 'true')
  - doc lai file loi -> bao lech kem ly do, khong crash
"""

from __future__ import annotations

import asyncio
import json

import pytest
from conftest import ACTIVATE, APP_ID, PKG, SERIAL

from rcr import rc_baseline, rc_patch, rc_verify
from rcr.models import RcError

ACT = f"files/{ACTIVATE}"
MIR = "shared_prefs/vsl_template4_remote_first_open.xml"
NOW = 1788519653885


def base(adb):
    return asyncio.run(rc_baseline.read(adb, SERIAL, PKG))


def verify(adb, bl, expected):
    return asyncio.run(rc_verify.verify(adb, bl, expected))


def test_sau_patch_thi_verify_ok(adb):
    bl = base(adb)
    ov = {"enable_onb3_screen": "false", "ad_load_timeout": "99"}
    asyncio.run(rc_patch.patch(adb, bl, ov, now_ms=NOW))
    res = verify(adb, bl, ov)
    assert res.ok
    assert res.mismatches == ()
    assert res.fetch_time_ms == NOW
    assert res.summary["verdict_hint"] == "ok"


def test_app_fetch_de_mat_patch_thi_ra_BLOCKED(adb):
    """Build dev dat minimumFetchInterval=0 -> throttle vo hieu. Day la ca thuc te."""
    bl = base(adb)
    ov = {"ad_load_timeout": "99"}
    asyncio.run(rc_patch.patch(adb, bl, ov, now_ms=NOW))
    # app fetch that: config bi ghi de bang gia tri tu Firebase
    live = json.loads(adb.files[ACT])
    live["configs_key"]["ad_load_timeout"] = "20"
    live["fetch_time_key"] = NOW + 60_000
    adb.files[ACT] = json.dumps(live, separators=(",", ":"))

    res = verify(adb, bl, ov)
    assert not res.ok
    m = res.mismatches[0]
    assert (m.key, m.want, m.got, m.where) == ("ad_load_timeout", "99", "20", "activate")
    # BLOCKED = chua test duoc; KHONG phai FAIL = app sai
    assert res.summary["verdict_hint"] == "BLOCKED"


def test_key_dung_o_activate_ma_sai_o_mirror_van_bao_lech(adb):
    """App doc mirror -> lech o mirror la app hanh xu theo gia tri cu."""
    bl = base(adb)
    ov = {"enable_onb3_screen": "false"}
    asyncio.run(rc_patch.patch(adb, bl, ov, now_ms=NOW))
    # mirror bi tra ve gia tri cu (vd SDK tu sync lai)
    adb.files[MIR] = adb.files[MIR].replace(
        '<boolean name="enable_onb3_screen" value="false" />',
        '<boolean name="enable_onb3_screen" value="true" />',
    )
    res = verify(adb, bl, ov)
    assert not res.ok
    m = res.mismatches[0]
    assert m.key == "enable_onb3_screen"
    assert m.where == "vsl_template4_remote_first_open.xml"
    assert (m.want, m.got) == ("false", "true")


def test_so_sanh_mirror_dich_dinh_dang_khong_phai_noi_long(adb):
    """Mirror luu CO KIEU (<int value="7">), RC luu STRING ("7").

    So mirror phai dich dinh dang truoc khi so - day la DICH, khong phai noi
    long. Con activate thi khong can dich nen so thang tung ky tu.
    """
    bl = base(adb)
    asyncio.run(rc_patch.patch(adb, bl, {"banner_fail_time": "7"}, now_ms=NOW))
    res = verify(adb, bl, {"banner_fail_time": "7"})
    assert res.ok
    # bang chung la 2 dinh dang that su khac nhau tren may:
    assert json.loads(adb.files[ACT])["configs_key"]["banner_fail_time"] == "7"
    assert '<int name="banner_fail_time" value="7" />' in adb.files[MIR]


def test_patch_va_verify_dung_cung_mot_chuoi_thi_khop(adb):
    """Gia tri di tu file TC -> patch -> verify deu la MOT chuoi, nen khop.

    Ke ca chuoi hoa la 'TRUE': activate luu y nguyen 'TRUE', mirror luu 'true'
    (da dich sang kieu boolean) - ca hai deu duoc coi la khop.
    """
    bl = base(adb)
    asyncio.run(rc_patch.patch(adb, bl, {"enable_onb3_screen": "TRUE"}, now_ms=NOW))
    assert json.loads(adb.files[ACT])["configs_key"]["enable_onb3_screen"] == "TRUE"
    assert '<boolean name="enable_onb3_screen" value="true" />' in adb.files[MIR]
    assert verify(adb, bl, {"enable_onb3_screen": "TRUE"}).ok


def test_activate_so_thang_tung_ky_tu(adb):
    """Patch 'true' roi verify 'TRUE' -> LECH, va lech nay la dung.

    activate.json giu y nguyen chuoi da ghi; bao khop se che mat truong hop
    config that su khong phai cai minh dat.
    """
    bl = base(adb)
    asyncio.run(rc_patch.patch(adb, bl, {"enable_onb3_screen": "true"}, now_ms=NOW))
    res = verify(adb, bl, {"enable_onb3_screen": "TRUE"})
    assert not res.ok
    assert res.mismatches[0].where == "activate"


def test_key_bien_mat_khoi_config(adb):
    bl = base(adb)
    live = json.loads(adb.files[ACT])
    del live["configs_key"]["ad_load_timeout"]
    adb.files[ACT] = json.dumps(live, separators=(",", ":"))
    res = verify(adb, bl, {"ad_load_timeout": "99"})
    assert not res.ok
    assert res.mismatches[0].got is None


def test_khong_doc_lai_duoc_activate_thi_bao_loi_ro(adb):
    bl = base(adb)
    del adb.files[ACT]
    with pytest.raises(RcError, match="Khong doc lai duoc"):
        verify(adb, bl, {"ad_load_timeout": "99"})


def test_activate_khong_con_la_json(adb):
    bl = base(adb)
    adb.files[ACT] = "<<khong phai json>>"
    with pytest.raises(RcError, match="khong con la JSON"):
        verify(adb, bl, {"ad_load_timeout": "99"})


def test_khong_doc_lai_duoc_mirror_thi_bao_lech_chu_khong_crash(adb):
    bl = base(adb)
    ov = {"enable_onb3_screen": "false"}
    asyncio.run(rc_patch.patch(adb, bl, ov, now_ms=NOW))
    del adb.files[MIR]
    res = verify(adb, bl, ov)
    assert not res.ok
    assert res.mismatches[0].where == "vsl_template4_remote_first_open.xml"


def test_chi_doc_mirror_lien_quan(adb):
    """Key khong bi mirror -> khong can doc file mirror nao."""
    bl = base(adb)
    n_before = len(adb.calls)
    verify(adb, bl, {"ad_load_timeout": "99"})
    new_calls = adb.calls[n_before:]
    assert not any("vsl_" in c for c in new_calls), new_calls


def test_summary_liet_ke_du_lech(adb):
    bl = base(adb)
    live = json.loads(adb.files[ACT])
    live["configs_key"]["ad_load_timeout"] = "20"
    live["configs_key"]["splash_banner_change"] = "true"
    adb.files[ACT] = json.dumps(live, separators=(",", ":"))
    s = verify(adb, bl, {"ad_load_timeout": "99", "splash_banner_change": "false"}).summary
    assert s["ok"] is False
    assert len(s["mismatches"]) >= 2
    keys = {m["key"] for m in s["mismatches"]}
    assert {"ad_load_timeout", "splash_banner_change"} <= keys
