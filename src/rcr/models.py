"""Kieu du lieu dung chung. Thuan du lieu, khong logic I/O."""

from __future__ import annotations

from dataclasses import dataclass, field


class RcError(Exception):
    """Loi doc/ghi remote config - thong bao da doc duoc de hien len UI."""


@dataclass(frozen=True, slots=True)
class MirrorNode:
    """1 node trong file prefs mirror cua SDK Apero.

    `kind` la kieu XML that (`boolean`/`string`/`long`/`int`/`float`). Ghi lai
    PHAI giu dung kieu: RC luu moi thu la string, mirror luu co kieu.
    """

    key: str
    kind: str
    value: str


@dataclass(frozen=True, slots=True)
class RcBaseline:
    """Anh chup remote config cua 1 app tai 1 thoi diem.

    Nen cua moi thu sau: whitelist key lay tu `configs`, kieu XML mirror lay tu
    `mirrors`, gia tri goc de restore cung lay tu day.
    """

    package: str
    serial: str
    app_id: str
    activate_name: str          # ten file frc_<app_id>_firebase_activate.json
    settings_name: str          # ten file frc_<app_id>_firebase_settings.xml
    activate_raw: str           # nguyen van JSON - de restore byte-for-byte
    settings_raw: str           # nguyen van XML - phase 2 chi sua 1 so bang regex
    configs: dict[str, str] = field(default_factory=dict)
    fetch_time_ms: int = 0
    template_version: str = ""
    # ten file -> {key: MirrorNode}. CHI chua key giao voi `configs`.
    mirrors: dict[str, dict[str, MirrorNode]] = field(default_factory=dict)
    mirror_raw: dict[str, str] = field(default_factory=dict)
    # file vsl_* co 0 key giao -> state noi bo app, TUYET DOI khong ghi vao.
    non_mirror_files: tuple[str, ...] = ()
    write_mode: str = "run-as"  # run-as | su

    @property
    def mirrored_keys(self) -> frozenset[str]:
        out: set[str] = set()
        for nodes in self.mirrors.values():
            out.update(nodes)
        return frozenset(out)

    @property
    def summary(self) -> dict:
        """Rut gon de tra ve UI - khong keo theo noi dung file."""
        return {
            "package": self.package,
            "app_id": self.app_id,
            "keys": len(self.configs),
            "mirrored_keys": len(self.mirrored_keys),
            "mirrors": {n: len(k) for n, k in self.mirrors.items()},
            "non_mirror_files": list(self.non_mirror_files),
            "write_mode": self.write_mode,
            "template_version": self.template_version,
            "fetch_time_ms": self.fetch_time_ms,
        }
