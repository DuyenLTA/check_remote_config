"""Test soi key trong DEX. Khong can may that: dung APK gia dung dang zip.

Diem phai gac:
  - quet MOI apk (base + split), khong dung o base -> khong bao KEY_NOT_USED oan
  - cache theo (package, versionCode) -> khong keo lai APK vai chuc MB moi case
  - versionCode doi -> cache cu tu mat hieu luc
"""

from __future__ import annotations

import asyncio
import shutil
import zipfile

import pytest
from conftest import PKG, SERIAL

from rcr import dex_check
from rcr.adb_parsers import AdbError


def make_apk(path, dex_blobs: dict[str, bytes]):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("AndroidManifest.xml", b"binary-xml")
        for name, blob in dex_blobs.items():
            zf.writestr(name, blob)
    return path


class FakeApkAdb:
    """pm path tra danh sach apk; pull chep file da dung san ra dich."""

    def __init__(self, apks: dict[str, str], version_code="20"):
        self.apks = apks  # duong dan tren may -> file that tren dia
        self.version_code_value = version_code
        self.pulls: list[str] = []

    async def shell(self, serial, *args, timeout=None):
        if args[:2] == ("pm", "path"):
            return "".join(f"package:{p}\n" for p in self.apks), "", 0
        return "", "", 0

    async def version_code(self, serial, package):
        return self.version_code_value

    async def _run(self, *args, timeout=None):
        if "pull" in args:
            i = args.index("pull")
            remote, local = args[i + 1], args[i + 2]
            self.pulls.append(remote)
            shutil.copy(self.apks[remote], local)
            return f"pulled {remote}\n", "", 0
        return "", "", 0


@pytest.fixture
def apks(tmp_path):
    base = make_apk(tmp_path / "base.apk", {
        "classes.dex": b"\x00junk" + b"splash_banner_change" + b"junk",
        "classes2.dex": b"enable_onb3_screen",
    })
    split = make_apk(tmp_path / "split_feature.apk", {"classes.dex": b"widget_layout_id"})
    return {"/data/app/~~x/base.apk": str(base), "/data/app/~~x/split_feature.apk": str(split)}


def test_scan_apk_doc_moi_file_dex(apks):
    found = dex_check.scan_apk(
        __import__("pathlib").Path(apks["/data/app/~~x/base.apk"]),
        ["splash_banner_change", "enable_onb3_screen", "khong_co"],
    )
    assert found == {"splash_banner_change", "enable_onb3_screen"}


def test_key_nam_o_split_van_tim_ra(apks, tmp_path):
    """App cai qua Play bi chia base + split - grep moi base la bao oan."""
    adb = FakeApkAdb(apks)
    out = asyncio.run(dex_check.check(adb, SERIAL, PKG, ["widget_layout_id"], tmp_path))
    assert out == {"widget_layout_id": True}
    assert len(adb.pulls) == 2  # phai di tiep sang split moi thay


def test_key_app_khong_doc_thi_False(apks, tmp_path):
    adb = FakeApkAdb(apks)
    out = asyncio.run(dex_check.check(adb, SERIAL, PKG, ["khong_app_nao_doc"], tmp_path))
    assert out == {"khong_app_nao_doc": False}


def test_tim_thay_het_thi_khong_keo_them_apk(apks, tmp_path):
    adb = FakeApkAdb(apks)
    asyncio.run(dex_check.check(adb, SERIAL, PKG, ["splash_banner_change"], tmp_path))
    assert adb.pulls == ["/data/app/~~x/base.apk"]


def test_cache_theo_versionCode(apks, tmp_path):
    adb = FakeApkAdb(apks)
    keys = ["splash_banner_change"]
    asyncio.run(dex_check.check(adb, SERIAL, PKG, keys, tmp_path))
    asyncio.run(dex_check.check(adb, SERIAL, PKG, keys, tmp_path))
    assert len(adb.pulls) == 1  # luot 2 doc cache, khong keo lai

    adb.version_code_value = "21"  # app duoc nang cap -> cache cu het hieu luc
    asyncio.run(dex_check.check(adb, SERIAL, PKG, keys, tmp_path))
    assert len(adb.pulls) == 2


def test_khong_thay_apk_thi_bao_ro(tmp_path):
    adb = FakeApkAdb({})
    with pytest.raises(AdbError, match="Khong thay APK"):
        asyncio.run(dex_check.check(adb, SERIAL, PKG, ["k"], tmp_path))
