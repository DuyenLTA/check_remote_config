"""`--restore` ban release: khong co snapshot file thi go het gia tri testvsl tren Firebase (AIP862 11/11/2026)."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from rcr import case_run


def test_restore_ban_release_khong_snapshot_thi_go_testvsl(monkeypatch, tmp_path):
    goi = []

    async def doc(client, serial, package):
        return SimpleNamespace(firebase={"project": "p"})

    async def restore(client, baseline):
        goi.append(baseline.firebase["project"])
        return SimpleNamespace(written=("firebase:testvsl",))

    monkeypatch.setattr(case_run.rc_baseline, "read", doc)
    monkeypatch.setattr(case_run.rc_patch, "restore", restore)
    ra = asyncio.run(case_run.restore_saved(None, "com.a.b", "S1", tmp_path))
    assert goi == ["p"] and ra["restored"] and ra["written"] == ["firebase:testvsl"]
