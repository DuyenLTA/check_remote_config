"""Report HTML tu chua cho mot luot check sub (file luot JSON do `/sub-check` ghi).

File luot: {package, app, version, may, bat_dau, cases: [{so, nhom, kich_ban, expected, verdict, thuc_te, anh: [path]}]}
verdict: PASS | FAIL | BLOCKED | NEEDS_HUMAN | CAN_TEST_TAY | CHUA_CHAY. Ket luan dua len dau, case gom theo nhom.
"""

from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path

from . import screencap

NHAN = {"PASS": ("Đạt", "ok"), "FAIL": ("Lỗi", "bad"), "BLOCKED": ("Bị chặn", "warn"),
        "NEEDS_HUMAN": ("Cần người xem", "warn"), "CAN_TEST_TAY": ("Cần test tay", "mute"),
        "CHUA_CHAY": ("Chưa chạy", "mute")}
CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#14181f;--soft:#5b6472;--rule:#dde2e8;--ok:#0a7d4f;--okb:#e2f5ec;
--bad:#c4213b;--badb:#fde8ec;--warn:#9a6200;--warnb:#fdf2dc;--mute:#5b6472;--muteb:#eef0f3}
@media (prefers-color-scheme:dark){:root{--bg:#0f141b;--card:#171e28;--ink:#e6ebf2;--soft:#9aa6b6;--rule:#2a3442;
--okb:#0f2a20;--badb:#33141c;--warnb:#2e2410;--muteb:#1e2632;--ok:#4cd39b;--bad:#ff7d90;--warn:#f2b84b;--mute:#9aa6b6}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:960px;margin:auto;padding:28px 16px 60px;display:flex;flex-direction:column;gap:22px}
h1{font-size:26px;margin:0}h2{font-size:15px;text-transform:uppercase;letter-spacing:.08em;color:var(--soft);margin:8px 0 0}
.meta{color:var(--soft);font-size:13px}.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}
.tile{background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:12px}.tile b{font-size:26px;display:block}
.case{background:var(--card);border:1px solid var(--rule);border-left:4px solid var(--rule);border-radius:10px;padding:14px 16px}
.case.ok{border-left-color:var(--ok)}.case.bad{border-left-color:var(--bad)}.case.warn{border-left-color:var(--warn)}
.top{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}.so{font-family:ui-monospace,monospace;color:var(--soft)}
.st{font-size:12px;font-weight:600;border-radius:999px;padding:2px 10px}
.st.ok{color:var(--ok);background:var(--okb)}.st.bad{color:var(--bad);background:var(--badb)}
.st.warn{color:var(--warn);background:var(--warnb)}.st.mute{color:var(--mute);background:var(--muteb)}
.k{color:var(--soft);font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-top:8px}
pre{white-space:pre-wrap;margin:2px 0 0;font:inherit}.imgs{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.imgs img{width:150px;border:1px solid var(--rule);border-radius:6px}
"""


def _anh(path: str) -> str:
    try:
        uri = screencap.to_thumb(Path(path).read_bytes())
    except OSError:
        return ""
    return f'<img src="{uri}" alt="ảnh màn">' if uri else ""


def render(luot: dict) -> str:
    cases = luot.get("cases") or []
    dem = Counter(c.get("verdict") or "CHUA_CHAY" for c in cases)
    e = html.escape
    tiles = "".join(f'<div class="tile"><b class="{NHAN[k][1]}">{dem.get(k, 0)}</b>{NHAN[k][0]}</div>'
                    for k in NHAN if dem.get(k))
    khoi, nhom = [], None
    # FAIL / can nguoi xem len truoc trong moi nhom de nguoi doc thay ngay
    for c in cases:
        if c.get("nhom") != nhom:
            nhom = c.get("nhom")
            khoi.append(f"<h2>{e(nhom or '')}</h2>")
        v = c.get("verdict") or "CHUA_CHAY"
        nhan, lop = NHAN.get(v, (v, "mute"))
        anh = "".join(_anh(a) for a in c.get("anh") or [])
        khoi.append(
            f'<div class="case {lop}"><div class="top"><span class="so">TC{e(str(c.get("so")))}</span>'
            f'<b>{e(c.get("kich_ban") or "")}</b><span class="st {lop}">{nhan}</span></div>'
            f'<div class="k">Kỳ vọng</div><pre>{e(c.get("expected") or "")}</pre>'
            f'<div class="k">Thực tế</div><pre>{e(c.get("thuc_te") or "")}</pre>'
            + (f'<div class="imgs">{anh}</div>' if anh else "") + "</div>")
    tieu_de = f"Check sub — {luot.get('app') or luot.get('package', '')}"
    return (f"<!doctype html><html lang=vi><head><meta charset=utf-8><meta name=viewport "
            f"content='width=device-width,initial-scale=1'><title>{e(tieu_de)}</title><style>{CSS}</style></head>"
            f"<body><div class=wrap><h1>{e(tieu_de)}</h1><div class=meta>{e(luot.get('package', ''))} · "
            f"{e(str(luot.get('version', '')))} · máy {e(str(luot.get('may', '')))} · {e(str(luot.get('bat_dau', '')))}</div>"
            f"<div class=tiles>{tiles}</div>{''.join(khoi)}</div></body></html>")


def ghi(luot_json: Path, out: Path) -> Path:
    out.write_text(render(json.loads(Path(luot_json).read_text(encoding="utf-8"))), encoding="utf-8")
    return out
