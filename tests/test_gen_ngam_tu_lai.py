"""rcr-gen-ngam: doc may (thong bao, log worker, History, badge), phan tich video popup dem nguoc, cham vao file luot."""

from __future__ import annotations

import json

from PIL import Image, ImageDraw

from rcr import gen_ngam_cham, gen_ngam_may as may, gen_ngam_quay as quay
from rcr.ui_dump import Bounds, DeviceNode

P = "com.aimakeup.aifaceeditor.facemakeup.faceswap"
CT = may.cong_thuc(P)


def _n(text="", desc="", b=(0, 0, 10, 10), i=0):
    return DeviceNode(str(i), "", "android.view.View", text, desc, Bounds(*b), False, True, True, P, None, 0)


def test_push_doc_title_text_cua_app():
    out = """  NotificationRecord(0x05093081: pkg=com.khac user=UserHandle{0} id=7 tag=null importance=2 key=x
                android.title=String (Khac)
  NotificationRecord(0x05093082: pkg=%s user=UserHandle{0} id=100001 tag=null importance=2 key=0|x: Notification(channel=generation_channel flags=ONGOING_EVENT|NO_CLEAR|FOREGROUND_SERVICE))
                android.title=String (BeautyGenie)
                android.text=String (Creating your content…)
""" % P

    class C:
        async def shell(self, *a, **k):
            return out, "", 0
    import asyncio
    ra = asyncio.run(may.push(C(), "s", P))
    assert ra == [{"id": "100001", "title": "BeautyGenie", "text": "Creating your content…", "ongoing": True}]


def test_worker_va_mo_man_tu_logcat_epoch():
    dong = [
        "         1794589829.419  1794  3306 I ActivityTaskManager: START u0 {xflg=0x4 cmp=%s/com.vls.beautygenie.ui"
        ".processing.ProcessingActivity (has extras)} with" % P,
        "         1794589829.448  3792  3792 D WM-WorkerWrapper: Starting work for com.vls.beautygenie.worker.GenerationWorker",
        "         1794589860.270  3792  3941 I WM-WorkerWrapper: Worker result SUCCESS for Work [ id=dbf, tags={ com.vls"
        ".beautygenie.worker.GenerationWorker,generation_worker }",
        "         1794589677.535  3827  4279 I WM-WorkerWrapper: Worker result SUCCESS for Work [ id=34d, class=com.android"
        ".providers.media.photopicker.sync.ProactiveSyncWorker",
    ]
    assert may.worker(dong) == [(1794589829.448, "bat_dau"), (1794589860.27, "SUCCESS")]
    assert may.mo_man(dong, P) == [(1794589829.419, "ProcessingActivity")]


def test_badge_va_o_lich_su():
    m = may.Man(0, P, "HistoryActivity", [
        _n(desc="History", b=(852, 212, 912, 284), i=1), _n(text="2", b=(902, 202, 912, 254), i=2),
        _n(desc="Neon Graphic Liner", b=(48, 368, 528, 1008), i=3), _n(text="Generating", b=(187, 703, 390, 775), i=4),
        _n(desc="Bronze Cat-Eye", b=(552, 368, 1032, 1008), i=5), _n(text="New", b=(594, 398, 660, 470), i=6),
    ])
    assert may.badge(m, CT) == 2
    o = may.o_lich_su(m, CT)
    assert [(x["ten"], x["dang_tao"], x["moi"]) for x in o] == [("Neon Graphic Liner", True, False),
                                                                ("Bronze Cat-Eye", False, True)]


def _khung(so: str | None, nen: int = 40):
    """Khung 540x1200: nen toi; popup (tieu de + dong dem) khi so khong None."""
    im = Image.new("L", (540, 1200), nen)
    if so is not None:
        d = ImageDraw.Draw(im)
        d.rectangle((60, 480, 480, 760), fill=250)
        d.text((160, 525), "Still generating", fill=0)
        d.text((80, 580), f"Taking you to Home in {so}s", fill=0)
    return im


def test_phan_tich_popup_dem_3_2_1_moi_so_1s():
    ds, t = [], 0.0
    for so, n in ((None, 120), ("3", 10), ("2", 10), ("1", 10)):
        for _ in range(n):
            ds.append((round(t, 1), _khung(so)))
            t += 0.1
    for _ in range(20):                                    # ve Home: man khac han
        ds.append((round(t, 1), Image.new("L", (540, 1200), 200)))
        t += 0.1
    r = quay.phan_tich(ds, [312, 1040, 769, 1116], [132, 1140, 948, 1284], 1000.0)
    assert r["so_trang_thai"] == 3
    moc = [r["t_hien"], *r["t_doi"], r["t_ve_home"]]
    assert all(0.8 <= b - a <= 1.2 for a, b in zip(moc, moc[1:]))
    assert abs((r["t_ve_home"] - r["t_hien"]) - 3.0) < 0.25


def test_cham_khop_theo_chu_dong_va_bo_dong_t2i(tmp_path):
    luot = tmp_path / "x.luot.json"
    rec = {"key": "GEN-R02-04", "verdict": "NEEDS_HUMAN", "lines": [
        {"v": "NEEDS_HUMAN", "e": "Có hiện toast + nút View hiện trên màn chọn style; không có push."},
        {"v": "NEEDS_HUMAN", "e": "View → màn Kết quả có popup rate app (nếu điều kiện thỏa)."},
        {"v": "NOT_VERIFIABLE", "e": "Vùng mô tả hiện đúng 3 dòng (phần dư bị cắt) + nút copy."}]}
    luot.write_text(json.dumps({"package": P, "records": [rec], "xong": True}), encoding="utf-8")
    so = gen_ngam_cham.So()
    so.ghi("GEN-R02-04", "hiện toast", True, "toast hiện 1 lần")
    so.ghi("GEN-R02-04", "View", False, "không tới Kết quả")
    kq = gen_ngam_cham.ghi_luot(str(luot), P, so, CT["bo_dong"], lambda m: None)
    r = json.loads(luot.read_text(encoding="utf-8"))["records"][0]
    assert [l["v"] for l in r["lines"]] == ["PASS", "FAIL"]
    assert r["verdict"] == "FAIL" and r["dong_bo"][0]["e"].startswith("Vùng mô tả")
    assert kq["con_cham_tay"] == []


def test_cum_toast_do_tu_luc_hien_khong_tu_luc_worker():
    may.NHAT_KY_TOAST[:] = [(10.0, False), (12.0, True), (14.1, True), (16.2, True), (18.3, True), (20.4, False),
                            (30.0, False), (32.0, True), (34.0, False)]
    from rcr.gen_ngam_nhom_chung_2 import thoi_gian_toast
    cum = may.cum_toast(0)
    assert cum == [(10.0, 12.0, 18.3, 20.4), (30.0, 32.0, 32.0, 34.0)]
    assert [round(x, 1) for x in thoi_gian_toast(cum[0])] == [6.3, 10.4]      # dung 6,3-10,4s: cham 8s PASS
    may.NHAT_KY_TOAST.clear()


def test_record_khung_moi_dong_cho_tool_lai_theo_nhom():
    from rcr import precond_android
    rec = precond_android.record_khung("IAA-01", {"label": "#IAA-01 Home", "feature": "IAA"},
                                       {"expects": ("Load native khi vào Home.", "Show đúng ID.")})
    assert rec["key"] == "IAA-01" and rec["verdict"] == "NEEDS_HUMAN"
    assert [l["v"] for l in rec["lines"]] == ["NEEDS_HUMAN", "NEEDS_HUMAN"]
    assert [l["e"] for l in rec["lines"]] == ["Load native khi vào Home.", "Show đúng ID."]
