"""screen_size phai tra kich thuoc theo huong dang xoay: may xoay ngang ma dung kich thuoc doc thi vuot lech."""
import asyncio

from rcr import device_app


class _Client:
    def __init__(self, cur: str):
        self.cur = cur

    async def shell(self, serial, *a):
        if a[:2] == ("wm", "size"):
            return "Physical size: 1080x2280\n", "", 0
        if a[:3] == ("dumpsys", "window", "displays"):
            return f"  init=1080x2280 440dpi base=1080x2280 480dpi {self.cur} app=1080x2148\n", "", 0
        return "", "", 0


def test_may_doc_giu_nguyen():
    assert asyncio.run(device_app.screen_size(_Client("cur=1080x2280"), "S")) == (1080, 2280)


def test_may_xoay_ngang_thi_dao_kich_thuoc():
    assert asyncio.run(device_app.screen_size(_Client("cur=2280x1080"), "S")) == (2280, 1080)


def test_khong_doc_duoc_huong_xoay_thi_giu_kich_thuoc_doc():
    assert asyncio.run(device_app.screen_size(_Client(""), "S")) == (1080, 2280)
