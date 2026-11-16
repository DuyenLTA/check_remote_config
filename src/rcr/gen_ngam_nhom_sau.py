"""Kich ban `rcr-gen-ngam` nhom R06 (het luot khi con luot dang tao), R07 (image_generation_success_time=2, mua sub),
S01 (user tu choi quyen thong bao luc dau -> popup xin quyen trong app).
"""

from __future__ import annotations

import re

from . import gen_ngam_may as may
from . import gen_ngam_tao as tao
from .gen_ngam_nhom_chung_2 import _nhin_toi_xong, _o_home_toi_xong, tao_anh, thoi_gian_toast
from .gen_ngam_nhom_dau import Ctx, LaiHut, _can, _cho_xong, _popup_home, _s, bam_dong_het_luot, \
    vao_nhom


async def nhom_r06(c: Ctx) -> None:
    so, ct = c.so, c.ct
    await vao_nhom(c)
    hai = [await tao_anh(c, "doi", ok_luc=12.6, hop_ok=c.so.nho.get("hop_ok") or c.ct.get("popup_hop_ok")) for _ in range(2)]
    con = [x for x in may.worker(await may.log(c.client, c.serial, hai[0]["t_confirm"])) if x[1] != "bat_dau"]
    ba = await tao.tao(c.client, c.serial, c.package, ct, "anh", "doi")
    _can(ba, "R06-01 lần tạo thứ 3")
    m = await c.nhin()
    # TC sua 16/11: "toast 'Daily limit reached' (2 luot dang tao da tinh)" - bo "do", bo "Try again tomorrow".
    # Cham: bi chan NGAY (khong vao man cho) khi con luot dang tao + co chu "Daily limit reached"; ghi dang hien thi.
    chu = [x for x in m.chu() if re.search(r"daily limit reached", x, re.I)] or \
        ([ba["het_luot"]] if re.search(r"daily limit reached", ba["het_luot"] or "", re.I) else [])
    dang = 2 - len(con)
    dang_popup = bool(m.tim(ct.get("het_luot_dong") or "$^"))
    so.ghi("GEN-R06-01", "Ảnh thứ 3 bị chặn", bool(ba["het_luot"]) and not ba["t_cho"] and bool(chu) and dang >= 1,
           f"2 ảnh vừa tạo ({dang} còn đang tạo lúc bấm lần 3): lần 3 "
           + (f"bị chặn ngay, hiện '{chu[0] if chu else ba['het_luot']}'" if ba["het_luot"] else "KHÔNG bị chặn")
           + (" (dạng popup có nút Back to Home, TC ghi toast)" if dang_popup else ""))
    so.ghi("GEN-R06-02", "0/2", bool(ba["het_luot"]) and c.nho["anh_bat_dau"] == 2,
           f"limit_gen_image_sub_per_day=2: tạo được {c.nho['anh_bat_dau']} ảnh, lần 3 bị chặn → còn 0/2")
    await bam_dong_het_luot(c)
    xong, to = await _o_home_toi_xong(c, hai[0]["t_confirm"], 2)
    cum = to["hien"]
    so.ghi("GEN-R06-02", "2 toast", len(cum) >= 2 and len(xong) >= 2,
           f"2 ảnh xong lúc {[f'{t - hai[0]['t_confirm']:.1f}s' for t, _s2 in xong]} (tính từ ảnh 1): toast hiện "
           f"{len(cum)} lần riêng, từ {[f'{x[1] - hai[0]['t_confirm']:.1f}s' for x in cum]}")
    if len(cum) >= 2:
        an = [thoi_gian_toast(x) for x in cum[:2]]
        so.ghi("GEN-R06-02", "tự ẩn sau 8s", all(dai and ngan <= 9.0 and dai >= 7.0 for ngan, dai in an),
               f"mỗi toast đứng trên màn trong khoảng {[f'{ngan:.1f}–{dai:.1f}s' for ngan, dai in an]} (nhìn UI "
               "~2,1s/lần, lúc đang ở màn khác thì khoảng rộng hơn) rồi tự mất")
    v = _can(await tao.tao(c.client, c.serial, c.package, ct, "video", "doi"), "R06-03 video")
    so.ghi("GEN-R06-03", "Tạo video bình thường", bool(v["t_cho"]) and not v["ad"] and not v["het_luot"],
           f"hết lượt ảnh rồi tạo video: vào màn chờ {'có' if v['t_cho'] else 'không'}, AdActivity "
           f"{'có' if v['ad'] else 'không'}, chặn: {v['het_luot'] or 'không'}")
    if c.nho.get("giu_video") and c.so.nho.get("video_dem"):
        c.log(f"  giữ số video/ngày đã đếm ở lượt trước: {c.so.nho['video_dem']}")
        return
    n = await dem_het_luot_video(c, 1)
    c.so.nho["video_dem"] = n
    so.ghi("GEN-R06-03", "còn 4/5", n == 5, f"tạo tiếp tới khi bị chặn: tổng {n} video trong ngày "
           f"(limit_gen_video_sub_per_day=5) → sau video đầu còn {5 - 1 if n == 5 else '?'}/5")


async def dem_het_luot_video(c: Ctx, da: int) -> int:
    """Tao video lien tiep (doi popup ve Home giay 8) toi khi bi chan. Bi chan vi qua max_concurrent (chua phai het
    luot) thi doi mot luot xong roi thu lai."""
    ct = c.ct
    tu = await may.gio(c.client, c.serial)
    for _ in range(12):
        kq = await tao.tao(c.client, c.serial, c.package, ct, "video", "doi")
        _can(kq, "đếm lượt video")
        if kq["t_cho"]:
            da += 1
            continue
        if kq["het_luot"]:
            await bam_dong_het_luot(c)
            return da
        m = await c.nhin()
        c.log(f"  video không vào màn chờ ({[s for s in m.chu()][:6]}) → chờ một lượt xong")
        await tao.ve_main(c.client, c.serial, c.package, ct)
        await _cho_xong(c, tu, 1, 300)
        tu = await may.gio(c.client, c.serial)
    return da


async def nhom_r07(c: Ctx) -> None:
    so, ct = c.so, c.ct
    v = await vao_nhom(c)
    so.ghi("GEN-R07-01", "Mua thành công", v["sub"]["premium"],
           ("mua gói test weekly (thẻ test), " if v["sub"]["mua"] else "gói test còn hạn, ")
           + f"log billing sau mở lại: premium={v['sub']['premium']}")
    kq = await tao_anh(c, "doi", "r07")
    vao = kq["log_vao"] - kq["t_confirm"] if kq.get("log_vao") else -1
    so.ghi("GEN-R07-02", "Không có ads", not kq["ad"] and 0 <= vao < 2.5,
           f"Confirm → ProcessingActivity sau {_s(vao)}, AdActivity: {'có' if kq['ad'] else 'không'}")
    # Ve Home cho anh xong, bam View tren toast; tach khung video (popup giay 12) SAU buoc nay - lam truoc thi toast da
    # an khi toi luc nhin (luot 16/11: tach khung 10-20s).
    await tao.vao_tab(c.client, c.serial, c.package, ct, "tab_home")
    c.nho.pop("man_view", None)
    c.nho["chup_toast"] = True
    await _nhin_toi_xong(c, kq["t_confirm"], 1, cho_view=True)
    m = c.nho.get("man_view") or await c.nhin()
    mau = c.nho.pop("mau_toast", "")
    kqm = await may.cho(c.client, c.serial, c.package, lambda x: x.o(ct["man_ket_qua"]), 8.0)
    xong = await _cho_xong(c, kq["t_confirm"], 1, 30)
    loi = [s2 for _t, s2 in xong if s2 != "SUCCESS"]
    so.ghi("GEN-R07-03", "thành công ngay lần đầu", len(xong) == 1 and not loi,
           f"image_generation_success_time=2, Premium: GenerationWorker {[s2 for _t, s2 in xong]}")
    xanh = bool(re.search(r"\((\d+), (\d+), (\d+)\)", mau)) and _la_xanh(mau)
    chu_toast = [x for x in m.chu() if re.search(ct["toast_xong"], x)]
    so.ghi("GEN-R07-03", "Toast xanh", bool(chu_toast) and bool(kqm) and xanh and
           any(re.search("creation is ready", x) for x in chu_toast),
           f"toast {chu_toast or 'không thấy'} (màu nền {mau or '?'}) → bấm View: "
           f"{kqm.act if kqm else 'không tới Kết quả'}")
    d = tao.phan_tich_video(kq)
    hien = d["t_hien"] - kq["log_vao"] if d.get("t_hien") else -1
    ve = kq["log_ra"] - kq["log_vao"] if kq.get("log_ra") else -1
    so.ghi("GEN-R07-02", "Giây 12", 11.5 <= hien <= 12.8 and 14.5 <= ve <= 15.6,
           f"popup hiện {_s(hien)} (khung video{', ' + d['loi'] if d.get('loi') else ''}), START {kq.get('ra_man')} "
           f"{_s(ve)} sau vào màn chờ")
    await tao.dong_rate(c.client, c.serial, c.package, ct)
    hai = []
    for _ in range(2):
        k = await tao_anh(c, "doi", ok_luc=12.6, hop_ok=c.so.nho.get("hop_ok") or c.ct.get("popup_hop_ok"))
        x = await _cho_xong(c, k["t_confirm"], 1, 90)
        hai.append([s2 for _t, s2 in x])
    so.ghi("GEN-R07-04", "Cả 2 lần", all(h == ["SUCCESS"] for h in hai),
           f"tạo thêm 2 ảnh, ảnh trước xong mới tạo ảnh sau: GenerationWorker {hai}")
    # TC sua 16/11: limit_gen_image_sub_per_day=3, video=2; lan 4 phai bi chan bang toast do co chu cua TC.
    lim_anh = int((c.nho.get("config") or {}).get("limit_gen_image_sub_per_day") or 3)
    lim_vid = int((c.nho.get("config") or {}).get("limit_gen_video_sub_per_day") or 2)
    da = c.nho.get("anh_bat_dau", 0)
    bon = await tao.tao(c.client, c.serial, c.package, ct, "anh", "doi")
    _can(bon, "R07-04 lần tạo thứ 4")
    m = await c.nhin()
    toast_ht = await may.toast_he_thong(c.client, c.serial, c.package)
    chu = [x for x in m.chu() if re.search(r"daily limit|tomorrow|limit reached", x, re.I)]
    dung_chu = any(re.search(r"Daily limit reached\. Try again tomorrow", x) for x in chu)
    so.ghi("GEN-R07-04", "trừ đúng 3", da == lim_anh and not bon["t_cho"],
           f"tạo được {da} ảnh trong nhóm (limit_gen_image_sub_per_day={lim_anh}), lần {da + 1} bị chặn → còn 0/{lim_anh}"
           if not bon["t_cho"] else f"lần {da + 1} vẫn tạo được ảnh (limit {lim_anh})")
    so.ghi("GEN-R07-04", "lần 4", not bon["t_cho"] and dung_chu and (toast_ht or not bon["het_luot"]),
           f"lần 4: {'không tạo ảnh' if not bon['t_cho'] else 'VẪN tạo ảnh'}, app hiện "
           + (f"popup '{bon['het_luot']}' (chữ trên màn {chu})" if bon["het_luot"] else f"chữ {chu}")
           + (", có toast hệ thống" if toast_ht else ", không có toast")
           + ("" if dung_chu else " — không có chữ 'Daily limit reached. Try again tomorrow.' như TC"))
    await bam_dong_het_luot(c)
    vid = await dem_het_luot_video(c, 0)
    so.ghi("GEN-R07-01", "Lượt ảnh còn", da == lim_anh and vid == lim_vid,
           f"app không hiện số lượt → đếm tới khi bị chặn ngay sau mua gói: ảnh {da}/{lim_anh}, video {vid}/{lim_vid}")


def _la_xanh(mau: str) -> bool:
    r, g, b = (int(x) for x in re.findall(r"\d+", mau)[:3])
    return g > 120 and g > r + 30 and g >= b


async def nhom_s01(c: Ctx) -> None:
    v = await vao_nhom(c, cho_phep=False)
    await s01_trong_nhom(c, v)


async def s01_trong_nhom(c: Ctx, v: dict) -> None:
    """User tu choi quyen luc mo dau. Chay DAU nhom chung (cung config Test Data): bam Allow o S01-02 la cap quyen
    luon cho R02-R08 -> bot mot lan dat config + clear data + lai FO (~2 phut)."""
    so, ct = c.so, c.ct
    if not v["hoi_quyen"]:
        raise LaiHut("S01: mở lần đầu không thấy hộp thoại quyền để bấm Don't allow")
    await tao_anh(c, "doi")
    m = await may.cho(c.client, c.serial, c.package, lambda x: x.tim(ct["xin_quyen"]) is not None, 8.0)
    co = m is not None and m.tim(ct["xin_quyen_cho"]) is not None and m.tim(ct["xin_quyen_khong"]) is not None
    so.ghi("GEN-S01-01", "Get notified", co, "từ chối quyền lúc mở đầu, tạo ảnh để popup về Home: "
           + (f"hiện '{m.tim(ct['xin_quyen']).text}' + Allow / Not now" if co else "không hiện popup xin quyền"))
    if not co:
        return
    await tao.bam(c.client, c.serial, m.tim(ct["xin_quyen_cho"]), 1.0)
    hoi = await tao._tra_loi_quyen(c.client, c.serial, True, 8.0)
    out, _, _ = await c.client.shell(c.serial, "dumpsys", "package", c.package)
    cap = bool(re.search(r"POST_NOTIFICATIONS: granted=true", out or ""))
    so.ghi("GEN-S01-02", "hộp thoại xin quyền", hoi, "bấm Allow → " + ("hiện hộp thoại hệ thống, bấm Cho phép" if hoi
                                                                       else "không hiện hộp thoại hệ thống"))
    so.ghi("GEN-S01-02", "được bật", cap, f"dumpsys package: POST_NOTIFICATIONS granted={'true' if cap else 'false'}")
    await tao_anh(c, "doi")
    thay = await _popup_home(c, 6.0)
    so.ghi("GEN-S01-03", "Không hiện lại", not any(re.search(ct["xin_quyen"], s) for s in thay),
           f"tạo ảnh khác, popup về Home, nhìn 6s: {thay or 'không có popup'}")
