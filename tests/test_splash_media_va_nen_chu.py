"""Nen splash theo media_url (anh phu kin / GIF lap / GIF mot lan), mau nen khung chu, anh content OB."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw

from rcr import assert_mau, assert_splash_media, splash_media
from rcr.verdict_levels import FAIL, NEEDS_HUMAN, PASS


def _gif_frames(n=8):
    ra = []
    for i in range(n):
        img = Image.new("RGB", (90, 160), (20, 40, 60))
        ImageDraw.Draw(img).rectangle((5 + i * 9, 20, 25 + i * 9, 140), fill=(250, 200, 30))
        ra.append(img)
    return ra


def _gif_bytes(frames):
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    return buf.getvalue()


def _man(src, w=540, h=1200):
    """Khung man: media scale center_crop, nua duoi la chu + vung ad (bi che khi so)."""
    img = splash_media._dat_len_man(src, w, h, "center_crop").resize((w, h))
    ImageDraw.Draw(img).rectangle((0, int(h * 0.6), w, h), fill=(255, 255, 255))
    return img.resize(splash_media.KICH)


def _phan_tich(tmp_path, chuoi, loop):
    frames = _gif_frames()
    url = "https://example.com/robot.gif"
    import hashlib

    (tmp_path / hashlib.sha1(url.encode()).hexdigest()).write_bytes(_gif_bytes(frames))
    # khung man da nen o GIF (palette) -> doc lai tu file nhu app ve
    goc = splash_media._khung_media(_gif_bytes(frames))[0]
    khung = [(t, _man(goc[i])) for t, i in chuoi]
    cfg = {"type": "gif", "media_url": url, "video_loop": loop}
    return splash_media.phan_tich(cfg, {"khung": khung, "size": (540, 1200), "xml": ""}, "p", tmp_path)


def test_gif_lap_van_doi_sau_het_thoi_luong(tmp_path):
    chuoi = [(0.5 + k * 0.4, (k * 4) % 8) for k in range(8)]          # 3,3s > 0,8s GIF, quay vong
    sm = _phan_tich(tmp_path, chuoi, True)
    assert sm["che_do"] == "center_crop" and len(sm["splash"]) == 8
    ket = assert_splash_media.cham_nen("Nền GIF chạy lặp liên tục (video_loop=true).", {"splash_media": sm})
    assert ket["verdict"] == PASS, ket


def test_gif_mot_lan_dung_o_khung_cuoi(tmp_path):
    chuoi = [(0.4, 2), (0.8, 5), (1.2, 7), (1.6, 7), (2.0, 7), (2.4, 7)]
    sm = _phan_tich(tmp_path, chuoi, False)
    dong = "Nền GIF chạy 1 lần rồi dừng ở frame cuối (video_loop=false), sub_title 'Gif once'."
    assert assert_splash_media.cham_nen(dong, {"splash_media": sm})["verdict"] == PASS
    # cung chuoi do nhung TC doi lap -> FAIL (GIF dung)
    lap = assert_splash_media.cham_nen("Nền GIF chạy lặp liên tục (video_loop=true).", {"splash_media": sm})
    assert lap["verdict"] == FAIL


def test_gif_mot_lan_ma_van_doi_la_fail(tmp_path):
    chuoi = [(0.5 + k * 0.4, (k * 3) % 8) for k in range(7)]
    sm = _phan_tich(tmp_path, chuoi, False)
    ket = assert_splash_media.cham_nen("Nền GIF chạy 1 lần rồi dừng ở frame cuối (video_loop=false).",
                                       {"splash_media": sm})
    assert ket["verdict"] == FAIL


def test_khung_inter_khong_tinh_la_splash(tmp_path):
    chuoi = [(0.4, 1), (0.8, 2)]
    sm = _phan_tich(tmp_path, chuoi, True)
    assert all(d["tq"] >= splash_media.NGUONG_TQ for d in sm["splash"])
    den = {"khung": [(0.1, Image.new("RGB", splash_media.KICH, (0, 0, 0)))], "size": (540, 1200), "xml": ""}
    import hashlib

    url = "https://example.com/robot.gif"
    (tmp_path / hashlib.sha1(url.encode()).hexdigest()).write_bytes(_gif_bytes(_gif_frames()))
    sm2 = splash_media.phan_tich({"type": "gif", "media_url": url}, den, "p", tmp_path)
    assert "loi" in sm2
    assert assert_splash_media.cham_nen("Nền GIF chạy lặp", {"splash_media": sm2})["verdict"] == NEEDS_HUMAN


def test_progress_va_inter_splash():
    dump = ('<hierarchy><node index="0" text="" resource-id="p:id/splProcessId" class="android.widget.ImageView" '
            'package="p" bounds="[0,2039][1080,2303]" /></hierarchy>')
    drive = {"steps": [{"activity": "x.SplashActivity", "dump": dump}]}
    units = [{"unit": "*708", "rc_keys": ["id_102_spl_n_inter_high"], "requested": 1, "shown": 1}]
    ket = assert_splash_media.cham_progress("Progress và inter splash chạy như 3.6.0.", units, drive)
    assert ket["verdict"] == PASS and "splProcessId" in ket["reason"]
    assert assert_splash_media.cham_progress("Progress và inter splash chạy như 3.6.0.", [], drive)["verdict"] == FAIL


def test_mau_nen_khung_chu():
    drive = {"steps": [{"n": 4, "mau": [{"id": "nen_chu", "khung_id": "ctlContent", "pho_bien": "#F5F5F5",
                                          "nen": {"#F5F5F5": [9000, 10000]}, "dem": {}}]}]}
    assert assert_mau._cham_nen(drive, "#F5F5F5", "Nền text #F5F5F5")["verdict"] == PASS
    drive["steps"][0]["mau"][0]["nen"]["#F5F5F5"] = [100, 10000]
    assert assert_mau._cham_nen(drive, "#F5F5F5", "Nền text #F5F5F5")["verdict"] == FAIL
    assert assert_mau._cham_nen({"steps": []}, "#F5F5F5", "x")["verdict"] == NEEDS_HUMAN


def test_suy_mau_lop_phu_ban_trong_suot():
    from rcr import assert_nen_ban_trong as nbt

    nen = [(i * 7) % 256 for i in range(500)]
    a, c = 0.5, 245
    man = [a * c + (1 - a) * x for x in nen]
    doc, chan = nbt._hoi_quy(nen, man)
    assert abs((1 - doc) - a) < 1e-6 and abs(chan / (1 - doc) - c) < 1e-6
    assert nbt.khop("#F9FAF9", "#F5F5F5") and not nbt.khop("#C0C0C0", "#F5F5F5")



def test_id_inter_splash_doi_sang_slot_trong():
    cfg = {"splash_inter_high_n_id": "ca-app-pub-1/222", "id_102_spl_n_inter": "ca-app-pub-1/9",
           "show_102_spl_n_inter": "true", "native_lfo1_id": "ca-app-pub-1/333"}
    assert splash_media.id_inter_splash_trong(cfg) == {"splash_inter_high_n_id": "ca-app-pub-1/0000000001",
                                                       "id_102_spl_n_inter": "ca-app-pub-1/0000000001"}


def test_chu_gif_trong_ngoac_khong_phai_cau_hoi_gif():
    from rcr import assert_chu

    dump = '<hierarchy><node text="Gif loop" resource-id="p:id/t" class="x" package="p" bounds="[0,0][9,9]" /></hierarchy>'
    ket = assert_chu.cham("Title màu #FFD54F, sub_title 'Gif loop'.", {"steps": [{"dump": dump}], "walked": True})
    assert ket["verdict"] == PASS
