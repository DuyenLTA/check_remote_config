"""Dat gia tri remote config vao app, va tra ve nguyen trang.

HAI CHO PHAI GHI, THIEU MOT LA VO (da do thuc te ca 2 chieu):
  1. files/frc_<id>_firebase_activate.json  -> gia tri + fetch_time_key
  2. shared_prefs/frc_<id>_firebase_settings.xml -> last_fetch_time_in_millis
Chi ghi (1) thi app fetch that de mat patch ngay lan mo app dau tien. Dat moc
throttle = now o (2) la mượn chinh co che 12h cua SDK de app tra cache cua minh.

KHONG cat mang de chan fetch: app under test can mang cho ads/API/analytics,
cat mang la lam hong chinh case dang test roi bao FAIL oan.

THU TU GHI: mirror -> settings -> activate SAU CUNG. Neu mirror loi giua duong
thi config chinh chua bi doi -> trang thai app con nhat quan, khong nua doi.

CHI GHI FILE NAM TRONG baseline.mirrors. File o non_mirror_files la state noi bo
app (`vsl_template4_prefs.xml` chua ARG_KEY_SHOW_ONBOARDING...) - ghi vao la lam
hong trang thai app, khong phai doi config.
"""

from __future__ import annotations

import json
import time

from . import rc_write
from .mirror_xml import set_long, set_value
from .models import PatchResult, RcBaseline, RcError

FETCH_TIME_KEY = "fetch_time_key"
CONFIGS_KEY = "configs_key"
THROTTLE_KEY = "last_fetch_time_in_millis"


def build_writes(
    baseline: RcBaseline, overrides: dict[str, str], now_ms: int
) -> list[tuple[str, str]]:
    """Dung noi dung 3 nhom file. Tra [(dest_rel, content)] DUNG THU TU GHI.

    Thuan ham -> test duoc het cac luat khong can device.
    """
    unknown = sorted(k for k in overrides if k not in baseline.configs)
    if unknown:
        raise RcError(
            "Key khong co trong remote config cua app: " + ", ".join(unknown) + ".\n"
            "Kiem tra lai ten key, hoac app nay khong dung key do."
        )

    writes: list[tuple[str, str]] = []

    # 1. mirror - chi file nao that su chua key can doi
    for name, nodes in baseline.mirrors.items():
        touched = {k: v for k, v in overrides.items() if k in nodes}
        if not touched:
            continue
        xml = baseline.mirror_raw[name]
        for key, value in touched.items():
            try:
                xml = set_value(xml, nodes[key], value)
            except ValueError as exc:
                raise RcError(f"{name}: khong dat duoc {key}={value!r} - {exc}") from exc
        writes.append((f"shared_prefs/{name}", xml))

    # 2. settings - moc throttle, de app khong fetch de mat patch
    try:
        settings = set_long(baseline.settings_raw, THROTTLE_KEY, now_ms)
    except ValueError as exc:
        raise RcError(f"{baseline.settings_name}: {exc}") from exc
    writes.append((f"shared_prefs/{baseline.settings_name}", settings))

    # 3. activate - SAU CUNG
    writes.append((f"files/{baseline.activate_name}", _build_activate(baseline, overrides, now_ms)))
    return writes


def _build_activate(baseline: RcBaseline, overrides: dict[str, str], now_ms: int) -> str:
    data = json.loads(baseline.activate_raw)
    data[CONFIGS_KEY] = {**data.get(CONFIGS_KEY, {}), **overrides}
    data[FETCH_TIME_KEY] = now_ms
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


async def patch(
    client, baseline: RcBaseline, overrides: dict[str, str], now_ms: int | None = None
) -> PatchResult:
    """Ghi `overrides` vao app. Raise RcError neu bat ky file nao ghi that bai."""
    if not overrides:
        raise RcError("Khong co key nao de dat.")
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    writes = build_writes(baseline, overrides, now)
    written = await _apply(client, baseline, writes)
    return PatchResult(applied=dict(overrides), written=tuple(written), fetch_time_ms=now)


async def restore(client, baseline: RcBaseline) -> PatchResult:
    """Tra app ve nguyen van baseline, KEM moc fetch cu.

    Moc cu (khong phai now) la co y: app se tu fetch lai config THAT o lan mo
    sau, nen may tro ve dung trang thai truoc khi test.
    """
    writes: list[tuple[str, str]] = [
        (f"shared_prefs/{name}", raw) for name, raw in baseline.mirror_raw.items()
    ]
    writes.append((f"shared_prefs/{baseline.settings_name}", baseline.settings_raw))
    writes.append((f"files/{baseline.activate_name}", baseline.activate_raw))
    written = await _apply(client, baseline, writes)
    return PatchResult(
        applied={}, written=tuple(written), fetch_time_ms=baseline.fetch_time_ms, restored=True
    )


async def _apply(client, baseline: RcBaseline, writes: list[tuple[str, str]]) -> list[str]:
    written: list[str] = []
    for dest_rel, content in writes:
        _assert_writable(baseline, dest_rel)
        await rc_write.write_file(
            client, baseline.serial, baseline.package, baseline.write_mode, dest_rel, content
        )
        written.append(dest_rel)
    return written


def _assert_writable(baseline: RcBaseline, dest_rel: str) -> None:
    """Chan tu trong code, khong dua vao goi dung: chi 3 nhom file duoc ghi."""
    allowed = {
        f"files/{baseline.activate_name}",
        f"shared_prefs/{baseline.settings_name}",
        *(f"shared_prefs/{n}" for n in baseline.mirrors),
    }
    if dest_rel in allowed:
        return
    name = dest_rel.split("/", 1)[-1]
    if name in baseline.non_mirror_files:
        raise RcError(
            f"{name} la state noi bo cua app (0 key trung remote config) - "
            "khong duoc ghi vao. Ghi vao la lam hong trang thai app."
        )
    raise RcError(f"{dest_rel} khong nam trong danh sach file duoc ghi.")
