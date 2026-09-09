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


@dataclass(frozen=True, slots=True)
class PatchResult:
    """Ket qua 1 lan ghi config. `written` theo DUNG thu tu da ghi."""

    applied: dict[str, str]
    written: tuple[str, ...]
    fetch_time_ms: int
    restored: bool = False

    @property
    def summary(self) -> dict:
        return {
            "applied": self.applied,
            "written": list(self.written),
            "fetch_time_ms": self.fetch_time_ms,
            "restored": self.restored,
        }


@dataclass(frozen=True, slots=True)
class Mismatch:
    """1 key lech giua gia tri muon dat va gia tri thuc te tren may."""

    key: str
    want: str
    got: str | None
    where: str  # "activate" | ten file mirror

    @property
    def summary(self) -> dict:
        return {"key": self.key, "want": self.want, "got": self.got, "where": self.where}


@dataclass(frozen=True, slots=True)
class VerifyResult:
    mismatches: tuple[Mismatch, ...]
    fetch_time_ms: int

    @property
    def ok(self) -> bool:
        return not self.mismatches

    @property
    def summary(self) -> dict:
        return {
            "ok": self.ok,
            "fetch_time_ms": self.fetch_time_ms,
            "mismatches": [m.summary for m in self.mismatches],
            # Lech -> BLOCKED, khong phai FAIL: chua test duoc, khong phai app sai.
            "verdict_hint": "ok" if self.ok else "BLOCKED",
        }


@dataclass(frozen=True, slots=True)
class Case:
    """1 dong case trong file testcase. `actions`/`expects` da split theo so."""

    n: str
    feature: str
    description: str
    sub_scenario: str
    precondition: str
    test_data: str
    actions: tuple[str, ...] = ()
    expects: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return f"#{self.n} {self.sub_scenario or self.description}".strip()


@dataclass(frozen=True, slots=True)
class RcCaseData:
    """Key/value boc duoc tu 1 case, sau khi loc bang whitelist.

    `needs_human` != "" nghia la case nay tool khong tu chay - kem LY DO de
    tester biet phai lam gi, thay vi im lang bo qua.
    """

    overrides: dict[str, str]
    needs_human: str = ""
    ignored: tuple[str, ...] = ()  # cap key=value bi loai vi khong thuoc RC

    @property
    def runnable(self) -> bool:
        return bool(self.overrides) and not self.needs_human

    @property
    def summary(self) -> dict:
        return {
            "overrides": self.overrides,
            "needs_human": self.needs_human,
            "ignored": list(self.ignored),
            "runnable": self.runnable,
        }
