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
    node_label: str
    x: int
    y: int
    matched: str

    @property
    def summary(self) -> dict:
        return {"kind": "tap", "node": self.node_label, "x": self.x, "y": self.y,
                "matched": self.matched}


@dataclass(frozen=True, slots=True)
class Swipe:
    """Vuot mot chieu tren man. `matched` noi huong nay lay tu dau trong cau."""

    direction: str
    matched: str

    @property
    def summary(self) -> dict:
        return {"kind": "swipe", "direction": self.direction, "matched": self.matched}


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
    """Lai qua ca luong First Open toi mot man hinh, do `fo_flow` lo."""

    target: str
    reason: str

    @property
    def summary(self) -> dict:
        return {"kind": "goto", "target": self.target, "reason": self.reason}


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


Action = Tap | Swipe | Wait | NoOp | GoTo | Net | NeedsHuman
