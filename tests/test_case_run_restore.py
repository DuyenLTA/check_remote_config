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


def test_do_gif_xong_tra_id_inter_splash_ve_goc(monkeypatch):
    ghi = []

    async def patch(client, baseline, overrides):
        ghi.append(overrides)

    monkeypatch.setattr(case_run.rc_patch, "patch", patch)
    bl = SimpleNamespace(configs={"id_102_spl_o_inter_high": "ca-app-pub-1/3083132989"})
    asyncio.run(case_run.tra_id_inter_splash(None, bl, {"a": "1"},
                                             {"id_102_spl_o_inter_high": "ca-app-pub-1/0000000001"}))
    assert ghi == [{"a": "1", "id_102_spl_o_inter_high": "ca-app-pub-1/3083132989"}]
    asyncio.run(case_run.tra_id_inter_splash(None, bl, {"a": "1"}, {}))
    assert len(ghi) == 1
