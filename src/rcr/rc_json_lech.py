"""TC dat gia tri JSON cho mot key: ten truong co khop gia tri server cua chinh key do khong.

Do 24/10/2026 (Piclux 2.4.0): TC SDK 3.4.0 dat `splash_ui_config` voi `image_url`,
server cua app dung `media_url` (+ `video_loop`, `video_mute`). App doc truong nao thi
tool khong biet, nhung lech ten la dau hieu TC viet theo mot ban spec khac - case co
the PASS/FAIL tren mot gia tri app khong he doc. Chi canh bao, khong doi verdict.
"""

from __future__ import annotations

import json


def _obj(value) -> dict | None:
    try:
        got = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError):
        return None
    return got if isinstance(got, dict) else None


def lech(overrides: dict, configs: dict) -> list[str]:
    """Moi key co ca hai ben la JSON object -> mot dong canh bao neu ten truong lech."""
    ra = []
    for key, value in (overrides or {}).items():
        tc, server = _obj(value), _obj((configs or {}).get(key))
        if tc is None or server is None:
            continue
        thua = sorted(set(tc) - set(server))
        if not thua:
            continue
        thieu = sorted(set(server) - set(tc))
        ra.append(f"`{key}`: TC đặt trường {', '.join(thua)} mà giá trị server không có"
                  + (f" (server có {', '.join(thieu)})" if thieu else "")
                  + " — kiểm lại tên trường với spec trước khi tin kết quả")
    return ra
