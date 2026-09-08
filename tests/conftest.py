"""FakeAdb: tang adb gia, ghi lai lenh da goi. Suite chay duoc khi khong cam may.

Du lieu trong `fixtures/` la NOI DUNG THAT doc tu may (Pixel 4 / Pixel 7,
2026-09-07), rut gon so key cho de doc. Nho vay test gac dung schema that chu
khong phai schema tu tuong tuong ra.
"""

from __future__ import annotations

import json
import pathlib

import pytest

PKG = "com.ai.videogenerator.photocreator.aiart"
SERIAL = "29301FDH2006K7"
APP_ID = "1:310944273102:android:c1649cae37e57475f4b69f"
ACTIVATE = f"frc_{APP_ID}_firebase_activate.json"
SETTINGS = f"frc_{APP_ID}_firebase_settings.xml"

# --- noi dung file that (rut gon) -------------------------------------------

ACTIVATE_JSON = json.dumps(
    {
        "configs_key": {
            "enable_onb3_screen": "true",
            "splash_banner_change": "true",
            "ad_load_timeout": "20",
            "banner_fail_time": "3",
            "paywall_config": '{"a":1}',
            "ad_positions_high_rank": '["LFO1","LFO2"]',
        },
        "fetch_time_key": 1781492084614,
        "abt_experiments_key": [],
        "personalization_metadata_key": {},
        "template_version_number_key": 232,
        "rollout_metadata_key": [],
    },
    separators=(",", ":"),
)

SETTINGS_XML = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="last_fetch_etag">etag-310944273102-firebase-fetch-781665809</string>
    <long name="backoff_end_time_in_millis" value="-1" />
    <long name="last_template_version" value="232" />
    <int name="last_fetch_status" value="-1" />
    <long name="last_fetch_time_in_millis" value="1781492084614" />
    <int name="num_failed_fetches" value="0" />
</map>
"""

# Mirror THAT: ten key y het RC.
MIRROR_FIRST_OPEN = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <boolean name="enable_onb3_screen" value="true" />
    <boolean name="splash_banner_change" value="true" />
    <string name="layout_onb2_screen">layout1</string>
    <int name="banner_fail_time" value="3" />
</map>
"""

MIRROR_BILLING = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="paywall_config">{&quot;a&quot;:1}</string>
</map>
"""

# 0 key giao voi RC -> STATE NOI BO app, tuyet doi khong duoc ghi vao.
LOCAL_PREFS = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <boolean name="ARG_KEY_SHOW_LFO" value="true" />
    <boolean name="ARG_KEY_SHOW_ONBOARDING" value="false" />
    <string name="ARG_KEY_SELECTED_LANGUAGE">vi</string>
</map>
"""

WIDGET_LOCAL = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <boolean name="widget_fetch_successful" value="true" />
</map>
"""

FILES_LS = f"""PersistedInstallation.W0RFRkFVTFRd.json
{ACTIVATE}
frc_{APP_ID}_fireperf_activate.json
frc_{APP_ID}_firebase_defaults.json
generatefid.lock
profileInstalled
"""

PREFS_LS = """admin.xml
com.google.firebase.crashlytics.xml
vsl_billing_remote_config.xml
vsl_template4_prefs.xml
vsl_template4_remote_first_open.xml
vsl_widget_local_prefs.xml
""" + f"{SETTINGS}\n"

DEVICES_OUT = f"""List of devices attached
{SERIAL}         device usb:1-1 product:panther model:Pixel_7 device:panther
99261FFAZ0077C         unauthorized usb:1-2
"""

PACKAGES_OUT = f"package:{PKG}\npackage:ai.photogenerator.aivideo.aivideogenerator.aiart\n"


class FakeAdb:
    """Tang adb gia. `files` map duong-dan-tren-device -> noi dung.

    `fails` khop theo chuoi con trong dong lenh -> tra (stdout, stderr, code).
    """

    def __init__(self, *, files=None, fails=None, debuggable=True, rooted=False):
        self.calls: list[str] = []
        self.fails = fails or {}
        self.debuggable = debuggable
        self.rooted = rooted
        self.tmp: dict[str, str] = {}  # /data/local/tmp/... -> noi dung
        self.files = dict(files) if files is not None else {
            f"files/{ACTIVATE}": ACTIVATE_JSON,
            f"shared_prefs/{SETTINGS}": SETTINGS_XML,
            "shared_prefs/vsl_template4_remote_first_open.xml": MIRROR_FIRST_OPEN,
            "shared_prefs/vsl_billing_remote_config.xml": MIRROR_BILLING,
            "shared_prefs/vsl_template4_prefs.xml": LOCAL_PREFS,
            "shared_prefs/vsl_widget_local_prefs.xml": WIDGET_LOCAL,
        }

    # --- interface ma app_sandbox / rc_baseline / rc_write dung --------------

    async def _run(self, *args, timeout=None):
        """rc_write goi truc tiep de `adb push`."""
        cmd = " ".join(args)
        self.calls.append(cmd)
        for needle, res in self.fails.items():
            if needle in cmd:
                return res
        if "push" in args:
            i = args.index("push")
            local, remote = args[i + 1], args[i + 2]
            self.tmp[remote] = pathlib.Path(local).read_text(encoding="utf-8")
            return f"1 file pushed to {remote}\n", "", 0
        if "shell" in args:
            i = args.index("shell")
            return self._dispatch(f"-s {args[1]} shell " + " ".join(args[i + 1:]))
        return "", "", 0

    async def shell(self, serial, *args, timeout=None):
        return self._dispatch(f"-s {serial} shell " + " ".join(args))

    async def shell_line(self, serial, line, timeout=None):
        return self._dispatch(f"-s {serial} shell {line}")

    async def devices(self):
        from rcr.adb_parsers import parse_devices

        return parse_devices(DEVICES_OUT)

    async def packages(self, serial):
        from rcr.adb_parsers import parse_packages

        return parse_packages(PACKAGES_OUT)

    async def is_debuggable(self, serial, package):
        return self.debuggable

    # --- dieu phoi -----------------------------------------------------------

    def _dispatch(self, cmd: str) -> tuple[str, str, int]:
        self.calls.append(cmd)
        for needle, res in self.fails.items():
            if needle in cmd:
                return res
        if " rm -f /data/local/tmp/" in cmd:
            self.tmp.pop(cmd.rsplit(" ", 1)[1], None)
            return "", "", 0
        if " run-as " in f" {cmd} " or cmd.endswith("run-as"):
            if not self.debuggable:
                return "", f"run-as: package not debuggable: {PKG}", 1
            return self._as_app(cmd)
        if "su -c" in cmd:
            if not self.rooted:
                return "", "/system/bin/sh: su: not found", 127
            return self._as_app(cmd)
        return "", "", 0

    @staticmethod
    def _unquote(cmd: str) -> str:
        """Bo lop nhay cua shell - tren may that `sh` tu boc.

        app_sandbox.quote() boc nhay don va escape nhay trong thanh `'\''`.
        Fake phai boc lai de match duoc lenh, giong `sh` tren device.
        """
        # `su -c '<inner>'` co HAI lop nhay (sh boc 1 lop, roi arg boc lop nua)
        # -> boc den khi on dinh, giong `sh` tren device.
        prev = None
        while prev != cmd:
            prev = cmd
            cmd = cmd.replace("'\\''", "\x00").replace("'", "").replace("\x00", "'")
        return cmd

    def _as_app(self, cmd: str) -> tuple[str, str, int]:
        cmd = self._unquote(cmd)
        if ">" in cmd and "cat " in cmd:
            # `cat <tmp> > <dest>` (ca duong su, run-as, va duong stdin)
            # Duong stdin co dang `cat <tmp> | run-as pkg sh -c cat > <dest>`
            # -> nguon nam TRUOC dau pipe. May that thi `sh` lo viec nay.
            head = cmd.split("|", 1)[0] if "|" in cmd else cmd
            src = head.split("cat ", 1)[1].split(">")[0].strip()
            dest = cmd.rsplit(">", 1)[1].strip()
            if src.startswith("/data/local/tmp/"):
                if src not in self.tmp:
                    return "", f"cat: {src}: No such file or directory", 1
                self.files[dest] = self.tmp[src]
            else:
                # duong stdin: noi dung den qua pipe -> lay tu tmp trong dong lenh
                for k in self.tmp:
                    if k in cmd:
                        self.files[dest] = self.tmp[k]
                        break
            return "", "", 0
        if " id" in cmd and " ls " not in cmd and " cat " not in cmd:
            return ("uid=0(root)\n" if "su -c" in cmd else f"uid=10123({PKG})\n"), "", 0
        if " ls " in cmd:
            sub = cmd.rsplit(" ls ", 1)[1].strip()
            if sub == "files":
                return FILES_LS, "", 0
            if sub == "shared_prefs":
                return PREFS_LS, "", 0
            return "", f"ls: {sub}: No such file or directory", 1
        if " cat " in cmd:
            path = cmd.rsplit(" cat ", 1)[1].strip()
            content = self.files.get(path)
            if content is None:
                return "", f"cat: {path}: No such file or directory", 1
            return content, "", 0
        return "", "", 0

    def cmds_with(self, needle: str) -> list[str]:
        return [c for c in self.calls if needle in c]


@pytest.fixture
def adb():
    return FakeAdb()
