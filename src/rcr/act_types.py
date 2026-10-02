"""Cac thao tac ma mot buoc Action co the tro thanh.

Tach khoi `act_resolver` de moi file duoi 200 dong: file nay noi mot thao tac
LA GI, `act_resolver` noi lam sao doc ra no tu mot cau tieng Viet.

`summary` la thu di thang vao report va vao JSON stdout - doi ten khoa trong do
la doi giao dien voi nguoi dung, khong phai doi chi tiet noi bo.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Tap:
    """`lan` > 1: bam lien tuc ("Tap button X nhanh lien tuc 4-5 lan")."""

    node_label: str
    x: int
    y: int
    matched: str
    lan: int = 1

    @property
    def summary(self) -> dict:
        ra = {"kind": "tap", "node": self.node_label, "x": self.x, "y": self.y,
              "matched": self.matched}
        return ra | {"lan": self.lan} if self.lan > 1 else ra


@dataclass(frozen=True, slots=True)
class Swipe:
    """Vuot mot chieu tren man. `matched` noi huong nay lay tu dau trong cau."""

    direction: str
    matched: str
    lan: int = 1

    @property
    def summary(self) -> dict:
        ra = {"kind": "swipe", "direction": self.direction, "matched": self.matched}
        return ra | {"lan": self.lan} if self.lan > 1 else ra


@dataclass(frozen=True, slots=True)
class Wait:
    seconds: float

    @property
    def summary(self) -> dict:
        return {"kind": "wait", "seconds": self.seconds}


@dataclass(frozen=True, slots=True)
class NoOp:
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "noop", "reason": self.reason}


@dataclass(frozen=True, slots=True)
class GoTo:
    """Lai qua ca luong First Open toi mot man hinh, do `fo_flow` lo.

    `cho` la so giay phai dung yen SAU khi toi noi: buoc "Vao man OB2, cho het
    timeout load ad" vua la mot chuyen di vua la mot cu cho. Bo ve cho di thi
    cham ngay luc vua toi man, truoc khi ad kip fail.
    """

    target: str
    reason: str
    cho: float = 0.0

    @property
    def summary(self) -> dict:
        ra = {"kind": "goto", "target": self.target, "reason": self.reason}
        return ra | {"cho": self.cho} if self.cho else ra


@dataclass(frozen=True, slots=True)
class Net:
    """Bat/tat mang tren may. `on=False` la ngat wifi + data."""

    on: bool
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "net", "on": self.on, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class NeedsHuman:
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "needs_human", "reason": self.reason}


@dataclass(frozen=True, slots=True)
class Background:
    """Nhan Home, de app nam nen `seconds` giay. Buoc "Mo lai app" sau do moi
    dua app len lai - TC hoi ca luc o nen lan luc resume, nen khong gop lam mot."""

    seconds: float
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "background", "seconds": self.seconds, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class Rotate:
    """Xoay man lan luot theo `orientations` ("ngang"/"doc"), xong tra lai che
    do xoay cua may nhu cu."""

    orientations: tuple[str, ...]
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "rotate", "orientations": list(self.orientations),
                "reason": self.reason}


@dataclass(frozen=True, slots=True)
class Seq:
    """Nhieu thao tac trong mot cau: "Vuot phai ve OB2, roi vuot trai lai OB3"."""

    actions: tuple
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "seq", "actions": [a.summary for a in self.actions],
                "reason": self.reason}


Action = Tap | Swipe | Wait | NoOp | GoTo | Net | NeedsHuman | Background | Rotate | Seq
