"""Cham mau chu tren anh goc. Anh dung bang Pillow theo ca do that Piclux 2.4.0 (24/10/2026):
subtitle #E0E0E0 tren nen sang chuyen mau - nen gan mau chu nhung hiem khi trung tuyet doi."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw

from rcr import assert_check as a
from rcr import mau_chu, ui_dump

PKG = "com.ai.app"
CFG = {"splash_ui_config": '{"type":"image","title":"Piclux","title_color":"#4957FF",'
                           '"sub_title":"Saving","sub_title_color":"#E0E0E0"}'}
XML = (f'<hierarchy rotation="0"><node index="0" text="" resource-id="{PKG}:id/root" class="x" '
       f'package="{PKG}" content-desc="" clickable="false" enabled="true" bounds="[0,0][400,600]">'
       f'<node index="0" text="Piclux" resource-id="{PKG}:id/splTextTitleIds" class="t" package="{PKG}" '
       'content-desc="" clickable="false" enabled="true" bounds="[0,200][400,260]" />'
       f'<node index="1" text="Saving" resource-id="{PKG}:id/splTextSubTitleIds" class="t" package="{PKG}" '
       'content-desc="" clickable="false" enabled="true" bounds="[0,260][400,320]" />'
       '</node></hierarchy>')


def _png(title=(0x49, 0x57, 0xFF), sub=(0xE0, 0xE0, 0xE0)) -> bytes:
    img = Image.new("RGB", (400, 600))
    for y in range(600):                      # nen sang chuyen mau, sat #E0E0E0 nhung khong trung
        ImageDraw.Draw(img).line([(0, y), (399, y)], fill=(214 + y % 6, 212 + y % 5, 211))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 215, 360, 245], fill=title)
    d.rectangle([40, 275, 360, 305], fill=sub)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _drive(png):
    nodes = ui_dump.app_nodes(ui_dump.parse_dump(XML), PKG)
    return {"steps": [{"n": 1, "dump": XML, "action": {"kind": "noop"}, "activity": "SplashActivity",
                       "mau": mau_chu.do(nodes, png, ["#4957FF", "#E0E0E0"])}]}


LINE = "1. Title đúng màu #4957FF; Subtitle đúng màu #E0E0E0."


def test_mau_dung_ca_khi_nen_sat_mau_chu_thi_pass():
    out = a.check(LINE, {}, _drive(_png()), {"crashed": False}, cfg=CFG)
    assert out["verdict"] == a.PASS and "'Saving'" in out["reason"]


def test_mau_sai_thi_fail():
    out = a.check(LINE, {}, _drive(_png(sub=(0x9E, 0x9E, 0x9E))), {"crashed": False}, cfg=CFG)
    assert out["verdict"] == a.FAIL and "Subtitle" in out["reason"]


def test_nen_trung_han_mau_chu_thi_khong_ket_luan():
    nen_trung = Image.new("RGB", (400, 600), (0xE0, 0xE0, 0xE0))
    buf = io.BytesIO()
    nen_trung.save(buf, format="PNG")
    out = a.check("Subtitle đúng màu #E0E0E0", {}, _drive(buf.getvalue()), {"crashed": False}, cfg=CFG)
    assert out["verdict"] == a.NEEDS_HUMAN and "không tách được" in out["reason"]


def test_chua_co_anh_goc_thi_can_nguoi():
    drive = {"steps": [{"n": 1, "dump": XML, "action": {"kind": "noop"}, "activity": "SplashActivity"}]}
    out = a.check(LINE, {}, drive, {"crashed": False}, cfg=CFG)
    assert out["verdict"] == a.NEEDS_HUMAN and "ảnh gốc" in out["reason"]
