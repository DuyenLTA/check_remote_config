"""rcr-iaa chay tiep mot phan bien the: cham phai dung ca log bien the da lai o lan truoc."""

from types import SimpleNamespace

from rcr import cli_iaa


def test_log_cu_bo_sung_bien_the_chua_lai_lan_nay(tmp_path):
    pkg = "com.a.b"
    for b, noi_dung in (("bat", "x"), ("thuong", "x"), ("high", "x"), ("tat", "")):
        (tmp_path / f"iaa-{pkg}-{b}.log").write_text(noi_dung)
    args = SimpleNamespace(out_dir=str(tmp_path), package=pkg)
    ra = cli_iaa._log_cu(args, {"high": {}, "tat": {}})
    assert ra == [f"bat={tmp_path / f'iaa-{pkg}-bat.log'}", f"thuong={tmp_path / f'iaa-{pkg}-thuong.log'}"]
    assert cli_iaa._log_cu(args, {"bat": {}, "thuong": {}, "high": {}, "tat": {}}) == []
