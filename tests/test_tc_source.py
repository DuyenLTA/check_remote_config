"""Link sheet TC: tai ve / dung lai file da tai."""

from rcr import tc_source



def test_file_da_tai_dung_lai_cho_luot_noi_tiep(tmp_path):
    """Sheet TC chi tai mot lan moi luot check: --gop/--tiep dung lai file nay (user chot 03/11/2026)."""
    link = "https://docs.google.com/spreadsheets/d/1sNFXM7oGzx_addpimZL7RYk2rXpRs_We6YUHpdtWSqU/edit"
    assert tc_source.file_da_tai(link, tmp_path) is None
    f = tmp_path / "tc-1sNFXM7oGzx_addpimZL7RYk2rXpRs_We6YUHpdtWSqU.xlsx"
    f.write_bytes(b"")
    assert tc_source.file_da_tai(link, tmp_path) is None          # file rong = chua tai xong
    f.write_bytes(b"PK\x03\x04")
    assert tc_source.file_da_tai(link, tmp_path) == f
    assert tc_source.file_da_tai(str(f), tmp_path) is None         # duong dan file, khong phai link
