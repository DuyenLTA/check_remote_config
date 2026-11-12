"""Tab TC "widget": buoc launcher (xac nhan dialog ghim, ra home screen, tap widget), cham widget tren launcher /
toast / popup dong / mo tu Splash, va precondition Android < 8.0 -> BLOCKED ngay.

Mau du lieu theo luot AIP893 widget 12/11/2026 (Pixel 4, Android 12) user da duyet lam chuan.
"""

from __future__ import annotations

import asyncio
import types

from rcr import act_exec, act_resolver, act_widget, assert_check, case_run, precond_android, rc_patch, run_batch
from rcr import ui_dump, widget_may
from conftest import SERIAL, FakeAdb

PKG = "com.aiphotogenerator.aivideomaker.photoslideshow"
LAUNCHER = "com.google.android.apps.nexuslauncher"
CFG = {"widget_screen_placement": "true",
       "vsl_widget_config": '{"addWidgetDialog":{"title":"Custom Title","subtitle":"Custom Sub","cta":"Custom CTA"},'
                            '"toast":{"success":"Widget added!"}}'}

APPWIDGET = f"""Providers:
  [0] provider ProviderId{{user:0, app:10321, cmp:ComponentInfo{{{PKG}/{PKG}.widget.VslWidgetReceiver}}}}
    min=(0x0)   updatePeriodMillis=0
Widgets:
  [0] id=3
    host=HostId{{user:0, app:10154, hostId:1024, pkg:{LAUNCHER}}}
    provider=ProviderId{{user:0, app:10321, cmp:ComponentInfo{{{PKG}/{PKG}.widget.VslWidgetReceiver}}}}
    host.callbacks=android.os.BinderProxy@1
  [1] id=1
    host=HostId{{user:0, app:10154, hostId:1024, pkg:{LAUNCHER}}}
    provider=ProviderId{{user:0, app:10111, cmp:ComponentInfo{{com.google.android.apps.weather/.Widget}}}}
Hosts:
  [0] hostId=HostId{{user:0, app:10154, hostId:1024, pkg:{LAUNCHER}}}
"""
APPWIDGET_CHUA_ADD = APPWIDGET.split("Widgets:")[0] + "Widgets:\nHosts:\n"

EVENTS = """EventType: TYPE_WINDOW_STATE_CHANGED; EventTime: 1; PackageName: com.google.android.apps.nexuslauncher
EventType: TYPE_NOTIFICATION_STATE_CHANGED; EventTime: 2; PackageName: %s; MovementGranularity: 0; Action: 0; ContentChangeTypes: []; WindowChangeTypes: [] [ ClassName: android.widget.Toast$TN; Text: [Widget added!]; ContentDescription: null ]
""" % PKG


def _node(text="", pkg=LAUNCHER, rid="", bounds="[0,0][100,100]"):
    return (f'<node index="0" text="{text}" resource-id="{rid}" class="android.widget.TextView" package="{pkg}" '
            f'content-desc="" clickable="true" enabled="true" visible-to-user="true" bounds="{bounds}" />')


def _dump(*nodes):
    return '<?xml version="1.0"?><hierarchy rotation="0">' + "".join(nodes) + "</hierarchy>"


DIALOG = _dump(_node("Add to Home screen", bounds="[600,1500][1000,1600]"), _node("Cancel", bounds="[100,1500][400,1600]"))
POPUP = _dump(_node("Custom Title", pkg=PKG), _node("Custom CTA", pkg=PKG))
HOME_APP = _dump(_node("Home", pkg=PKG))
LAUNCHER_CO_WIDGET = _dump(_node("Ready to get started?", rid=f"{PKG}:id/rootView", bounds="[67,131][1013,800]"),
                           _node("", rid=f"{PKG}:id/title", bounds="[100,200][500,260]"))


# --- dich cau ----------------------------------------------------------------

def test_ba_buoc_widget_dich_ra_thao_tac_launcher():
    assert isinstance(act_resolver.resolve("Xác nhận thêm widget trên dialog của launcher (nếu có).", []),
                      act_widget.XacNhanWidget)
    assert isinstance(act_resolver.resolve("Ra home screen điện thoại, quan sát widget.", []), act_widget.RaLauncher)
    assert isinstance(act_resolver.resolve("Tap vào widget.", []), act_widget.TapWidget)


def test_bam_cta_add_widget_now_van_la_tap_theo_chu_khong_phai_buoc_launcher():
    act = act_resolver.resolve('Bấm button "Custom CTA" (Add Widget Now).', [])
    assert not isinstance(act, act_widget.LOAI)
    # "Mo app vao Home" (sua cua phien khac) van lai FO toi Home.
    assert isinstance(act_resolver.resolve("Mở app vào Home, chờ popup Add Widget.", []), act_resolver.GoTo)


# --- doc may -----------------------------------------------------------------

def test_dumpsys_appwidget_chi_dem_widget_dang_gan_cua_app():
    ds = widget_may.parse_appwidget(APPWIDGET, PKG)
    assert ds == [{"id": "3", "provider": f"{PKG}/{PKG}.widget.VslWidgetReceiver", "host": LAUNCHER}]
    # Provider khai bao nhung chua gan vao host -> chua co widget.
    assert widget_may.parse_appwidget(APPWIDGET_CHUA_ADD, PKG) == []


def test_toast_doc_tu_accessibility_event():
    assert widget_may.parse_toast(EVENTS) == ["Widget added!"]
    assert widget_may.parse_toast("EventType: TYPE_NOTIFICATION_STATE_CHANGED; ClassName: android.app.Notification; "
                                  "Text: [Tin moi]") == []


def test_nut_xac_nhan_va_khung_widget_tren_launcher():
    chu, nut = widget_may.nut_xac_nhan(DIALOG, PKG)
    assert chu == "add to home screen" and nut.bounds.center == (800, 1550)
    assert widget_may.nut_xac_nhan(HOME_APP, PKG) == (None, None)
    hai = _dump(_node("Add", bounds="[0,0][10,10]"), _node("Add", bounds="[20,20][30,30]"))
    assert widget_may.nut_xac_nhan(hai, PKG) == ("", None)          # hai nut cung chu -> khong doan
    assert widget_may.vung_widget(LAUNCHER_CO_WIDGET, PKG) == (67, 131, 1013, 800)
    assert widget_may.vung_widget(DIALOG, PKG) is None


def test_displayed_lay_dung_man_cua_app_theo_thu_tu():
    log = (f"I ActivityTaskManager: Displayed {PKG}/.AIPhotoVideoMakerSplashActivity for user 0: +369ms\n"
           f"I ActivityTaskManager: Displayed {LAUNCHER}/.NexusLauncherActivity: +100ms\n"
           f"I ActivityTaskManager: Displayed {PKG}/.ui.MainActivity: +1s20ms\n")
    ds = widget_may.parse_displayed(log, PKG)
    assert [d["activity"] for d in ds] == [".AIPhotoVideoMakerSplashActivity", ".ui.MainActivity"]
    assert ds[0]["ms"] == "369ms"


# --- thao tac ----------------------------------------------------------------

def _chay_lam(monkeypatch, action, dumps, adb):
    it = iter(dumps)
    monkeypatch.setattr(ui_dump, "dump", lambda client, serial: _async(next(it)))
    monkeypatch.setattr(act_widget, "CHO_SAU_THAO_TAC", 0)
    monkeypatch.setattr(act_widget, "CHO_APPWIDGET", 0)
    monkeypatch.setattr(act_widget, "CHO_DIALOG", 0)
    monkeypatch.setattr(act_widget.asyncio, "sleep", lambda *_: _async(None))
    record, ctx = {}, act_exec.ctx_moi(PKG)
    asyncio.run(act_exec.lam(adb, SERIAL, action, record, ctx))
    return record


async def _async(v):
    return v


def test_xac_nhan_bam_nut_launcher_nghe_toast_doc_appwidget(monkeypatch):
    adb = FakeAdb(fails={"dumpsys appwidget": (APPWIDGET, "", 0), "uiautomator events": (EVENTS, "", 0)})
    rec = _chay_lam(monkeypatch, act_widget.XacNhanWidget("x"), [DIALOG], adb)
    assert adb.cmds_with("input tap 800 1550")
    ket = rec["widget_xac_nhan"]
    assert ket["dialog"] == "Add to Home screen" and ket["toast"] == ["Widget added!"]
    assert ket["appwidget"][0]["id"] == "3"


def test_khong_co_dialog_thi_khong_bam_gi(monkeypatch):
    adb = FakeAdb(fails={"dumpsys appwidget": (APPWIDGET, "", 0)})
    rec = _chay_lam(monkeypatch, act_widget.XacNhanWidget("x"), [HOME_APP], adb)
    assert not adb.cmds_with("input tap")
    assert rec["widget_xac_nhan"]["dialog"] == "" and rec["widget_xac_nhan"]["toast"] is None


def test_ra_launcher_nhan_home_va_thay_widget(monkeypatch):
    adb = FakeAdb(fails={"dumpsys appwidget": (APPWIDGET, "", 0)})
    rec = _chay_lam(monkeypatch, act_widget.RaLauncher("x"), [LAUNCHER_CO_WIDGET], adb)
    assert adb.cmds_with("KEYCODE_HOME")
    assert rec["widget_launcher"]["thay"] and rec["widget_launcher"]["appwidget"]


# --- cham ---------------------------------------------------------------------

def _drive(*buoc, final_dump=HOME_APP, final_act=f"{PKG}.MainActivity"):
    cuoi = {"n": 9, "step": "(sau bước cuối)", "activity": final_act, "dump": final_dump}
    return {"steps": [*buoc, cuoi], "final": cuoi}


def _cham(line, drive, cfg=CFG):
    return assert_check.check(line, {}, drive, {}, cfg=cfg)


def test_widget_tren_home_screen_theo_dumpsys():
    co = _drive({"n": 2, "step": "Xác nhận", "widget_xac_nhan": {"appwidget": widget_may.parse_appwidget(APPWIDGET, PKG)}})
    assert _cham("Widget xuất hiện trên home screen điện thoại.", co)["verdict"] == "PASS"
    khong = _drive({"n": 2, "step": "Xác nhận", "widget_xac_nhan": {"appwidget": []}})
    assert _cham("Widget xuất hiện trên home screen điện thoại.", khong)["verdict"] == "FAIL"


def test_toast_theo_vsl_widget_config():
    line = 'Toast "Widget added!" theo vsl_widget_config.'
    assert _cham(line, _drive({"n": 2, "widget_xac_nhan": {"toast": ["Widget added!"]}}))["verdict"] == "PASS"
    assert _cham(line, _drive({"n": 2, "widget_xac_nhan": {"toast": ["Lỗi"]}}))["verdict"] == "FAIL"
    assert _cham(line, _drive({"n": 2, "widget_xac_nhan": {"toast": []}}))["verdict"] == "NEEDS_HUMAN"


def test_popup_dong_khi_dump_sau_cung_man_khong_con_chu_popup():
    bam = {"n": 1, "step": 'Bấm "Custom CTA"', "activity": f"{PKG}.MainActivity", "dump": POPUP}
    assert _cham("Popup đóng.", _drive(bam))["verdict"] == "PASS"
    assert _cham("Popup đóng.", _drive(bam, final_dump=POPUP))["verdict"] == "FAIL"
    # Popup mac dinh (R02 khong dat vsl_widget_config) + ve man Home.
    mac_dinh = {"n": 1, "step": "Bấm X.", "activity": f"{PKG}.MainActivity",
                "dump": _dump(_node("Add Widget", pkg=PKG), _node("Add Widget Now", pkg=PKG))}
    ket = _cham("Popup đóng, về màn Home.", _drive(mac_dinh), cfg={"widget_screen_placement": "true"})
    assert ket["verdict"] == "PASS"


def test_popup_dong_o_tab_khac_khong_dung_luat_widget():
    bam = {"n": 1, "step": "Bấm X", "activity": f"{PKG}.MainActivity", "dump": POPUP}
    ket = _cham("Popup đóng.", _drive(bam), cfg={"rating_enable": "true"})
    assert "popup đã đóng" not in ket["reason"]


def test_mo_app_tu_splash_sau_tap_widget():
    line = "App mở từ Splash, luồng giống tap icon app."
    splash = {"tap": True, "displayed": [{"activity": ".AIPhotoVideoMakerSplashActivity", "ms": "369ms"},
                                         {"activity": ".MainActivity", "ms": ""}]}
    assert _cham(line, _drive({"n": 3, "mo_tu_widget": splash}))["verdict"] == "PASS"
    main = {"tap": True, "displayed": [{"activity": ".MainActivity", "ms": ""}]}
    assert _cham(line, _drive({"n": 3, "mo_tu_widget": main}))["verdict"] == "FAIL"


# --- precondition Android ----------------------------------------------------

def test_android_duoi_8_tren_may_android_12_thi_thieu():
    assert precond_android.thieu_android("1. Clear data.\n2. Thiết bị Android < 8.0 (vd Android 7.x).", "12", 31) == [
        "cần máy Android < 8.0, máy lượt này Android 12"]
    assert precond_android.thieu_android("2. Thiết bị Android ≥ 8.0.", "12", 31) == []
    assert precond_android.thieu_android("2. Thiết bị Android < 8.0.", "", 0) == []   # khong doc duoc -> khong chan


def test_case_android_7_blocked_ngay_khong_chay_ca_case_noi_tiep(monkeypatch):
    runnable = {
        "widget#WIDGET-R03-01": {"runs": ({"k": "v"},), "precondition": "1. Clear data.\n2. Thiết bị Android < 8.0.",
                                 "actions": (), "expects": ("Popup Tutorial hiện.", "Event widget_view fire 1 lần.")},
        "widget#WIDGET-R03-02": {"runs": ({"k": "v"},), "precondition": "1. Tiếp nối WIDGET-R03-01 (cùng lượt).",
                                 "actions": (), "expects": ("Popup đóng, về Home.",)},
        "widget#WIDGET-R04-01": {"runs": ({"k": "v"},), "precondition": "2. Thiết bị Android ≥ 8.0.",
                                 "actions": (), "expects": ()},
    }
    da_chay = []

    async def run_case(client, baseline, runs, pre, *a, **kw):
        da_chay.append(pre)
        return {"verdict": "PASS", "runs": [{"overrides": {}, "verdict": "PASS"}]}, baseline

    monkeypatch.setattr(case_run, "run_case", run_case)
    monkeypatch.setattr(rc_patch, "restore", lambda *a: _async(None))
    monkeypatch.setattr(precond_android, "doc", lambda client, serial: _async(("12", 31)))
    args = types.SimpleNamespace(case=",".join(runnable), no_actions=True, no_walk=True, full_walk=False, keep=False,
                                 out_dir=".", no_dex_check=True, report="", app_label="", tab="", sdk="")
    base = types.SimpleNamespace(serial="S", package=PKG, configs={"k": "v"}, mirrored_keys=frozenset())
    rows = [{"key": k, "tab": "TC SDK widget", "label": k} for k in runnable]
    recs = asyncio.run(run_batch.run_cases(None, base, args, runnable, rows, {"sdk": ""}))
    assert [r["verdict"] for r in recs] == ["BLOCKED", "BLOCKED", "PASS"]
    assert len(da_chay) == 1                                   # chi R04 chay
    assert recs[0]["precondition_thieu"] == ["cần máy Android < 8.0, máy lượt này Android 12"]
    assert [l["v"] for l in recs[0]["lines"]] == ["BLOCKED", "BLOCKED"]
