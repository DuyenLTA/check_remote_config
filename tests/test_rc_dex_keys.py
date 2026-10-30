"""Key server chua khai nhung app co doc (DEX) van dat duoc.

Tai hien AI Home Design 1.8.0 (30/10/2026): bo TC 3.6.1 dat
`onboard_config_content_new`, server chua khai key nay nhung app co chuoi trong
DEX. Truoc day tool coi la param analytics, bo di -> ca bo R01..O02 chay tren
noi dung mac dinh cua app.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest
from conftest import PKG, SERIAL
from test_dex_check import FakeApkAdb, make_apk

from rcr import rc_baseline, rc_dex_keys, rc_extract, rc_patch
from rcr.models import RcError

NOW = 1788519653885


@pytest.fixture
def bl(adb):
    return asyncio.run(rc_baseline.read(adb, SERIAL, PKG))


@pytest.fixture
def apk_adb(tmp_path):
    apk = make_apk(tmp_path / "base.apk", {"classes38.dex": b"\x00onboard_config_content_new\x00source\x00"})
    return FakeApkAdb({"/data/app/~~x/base.apk": str(apk)})


def test_chi_nhan_key_co_trong_dex(bl, apk_adb, tmp_path):
    keys = {"onboard_config_content_new", "question_screen_config", "source", "n"}
    moi = asyncio.run(rc_dex_keys.bo_sung(apk_adb, bl, keys, tmp_path, lambda _m: None))
    # `source` co trong DEX nhung khong giong ten key RC -> van loai, nhu param analytics
    assert moi.dex_keys == {"onboard_config_content_new"}


def test_key_server_da_khai_khong_soi_lai(bl, apk_adb, tmp_path):
    co_san = next(iter(bl.configs))
    moi = asyncio.run(rc_dex_keys.bo_sung(apk_adb, bl, {co_san}, tmp_path, lambda _m: None))
    assert moi is bl
    assert apk_adb.pulls == []


def test_whitelist_gom_key_dex(bl):
    moi = replace(bl, dex_keys=frozenset({"onboard_config_content_new"}))
    assert "onboard_config_content_new" in rc_extract.whitelist_of(moi)
    assert "onboard_config_content_new" not in rc_extract.whitelist_of(bl)


def test_patch_ghi_key_dex_vao_activate(bl):
    gia_tri = '[{"language_code":"fr","onb1":{"title":"FR - OB1 title"}}]'
    with pytest.raises(RcError, match="khong co trong remote config"):
        rc_patch.build_writes(bl, {"onboard_config_content_new": gia_tri}, NOW)

    moi = replace(bl, dex_keys=frozenset({"onboard_config_content_new"}))
    writes = dict(rc_patch.build_writes(moi, {"onboard_config_content_new": gia_tri}, NOW))
    activate = next(v for k, v in writes.items() if k.startswith("files/"))
    assert json.loads(activate)["configs_key"]["onboard_config_content_new"] == gia_tri
    # key moi khong co node mirror nao -> khong ghi mirror
    assert all(not k.startswith("shared_prefs/vsl_") for k in writes)
