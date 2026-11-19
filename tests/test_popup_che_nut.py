"""Ne popup 'AdMob native ad validator' (cua so rieng, khong co trong dump) khi bam nut Next OB4."""

from __future__ import annotations

import asyncio
from pathlib import Path

from rcr import popup_che_nut as p
from rcr.ui_dump import Bounds

PKG = "com.nxl.app"


def _cua_so(so, ty, frame, hien=True):
    return (f"  Window #{so} Window{{a u0 {PKG}/{PKG}.OnboardingActivity}}:\n"
            f"    mAttrs={{(0,0)(1x1) ty={ty} fmt=TRANSPARENT\n"
            f"    Frames: parent=[0,0][1080,2408] frame={frame} last={frame}\n"
            f"    isVisible={'true' if hien else 'false'}\n")


# Do that vivo V2143 12/11/2026: hai popup validator chong nhau tren nut "FR - Get Started" [554,1260][951,1363].
DUMPSYS = ("WINDOW MANAGER WINDOWS\n" + _cua_so(13, "APPLICATION", "[201,900][1081,1327]")
           + _cua_so(14, "APPLICATION", "[0,1040][880,1467]")
           + _cua_so(15, "APPLICATION", "[0,0][1080,2408]", hien=False)
           + _cua_so(16, "BASE_APPLICATION", "[0,0][1080,2408]"))
NUT = Bounds(554, 1260, 951, 1363)


def test_doc_khung_popup_dang_hien_cua_app():
    assert p.khung_popup(DUMPSYS, PKG) == [(201, 900, 1081, 1327), (0, 1040, 880, 1467)]
    assert p.khung_popup(DUMPSYS, "com.khac") == []


def test_hai_popup_che_diem_cu_thi_chon_goc_con_trong():
    x, y = p.diem_trong(NUT, p.khung_popup(DUMPSYS, PKG))
    assert x >= 880 and y >= 1327 and 554 <= x < 951 and 1260 <= y < 1363
    cu = p.diem_trong(NUT, [])
    assert cu == (554 + (951 - 554) * 3 // 4, 1260 + (1363 - 1260) * 5 // 6)


def test_khong_doc_duoc_dumpsys_thi_bam_diem_cu():
    class Hong:
        async def shell(self, *a, **k):
            raise OSError("adb chet")
    assert asyncio.run(p.diem_bam(Hong(), "S", PKG, NUT)) == p.diem_trong(NUT, [])


def test_nut_thuong_khong_bi_che_thi_bam_giua_nhu_cu():
    assert p.diem_trong(NUT, [], p.DIEM_GIUA_TRUOC) == NUT.center
    x, y = p.diem_trong(NUT, [(0, 1040, 880, 1467)], p.DIEM_GIUA_TRUOC)
    assert x >= 880 and 554 <= x < 951


def test_diem_dismiss_popup_validator_che_tron_nut_generate():
    # Do that Pixel 7 (density 440) 17/11/2026, AIP944: popup [0,1114][880,1541], nut Dismiss tam ~(702,1439).
    x, y = p.diem_dismiss([(0, 1114, 880, 1541)], 440 / 160)[0]
    assert 600 <= x <= 806 and 1403 <= y <= 1477


def test_diem_dismiss_bo_qua_cua_so_khong_phai_validator():
    assert p.diem_dismiss([(0, 0, 1080, 2400), (100, 100, 300, 200)], 2.75) == []



def test_nut_dismiss_nhan_theo_mau_anh_that():
    # Cat tu anh chup Pixel 7 17/11/2026 (vung [560,1300]-[880,1480]): nut Dismiss tam ~(701,1385) man hinh.
    png = (Path(__file__).parent / "fixtures" / "validator_dismiss_crop.png").read_bytes()
    assert p.la_nut_dismiss(png, 701 - 560, 1385 - 1300)
    assert not p.la_nut_dismiss(png, 5, 5)                    # nen trang / den ngoai nut
    assert not p.la_nut_dismiss(b"khong phai png", 10, 10)
