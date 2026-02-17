"""Geometric primitives for layout computation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    """An axis-aligned rectangle in pixel space."""

    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.right and self.y <= py <= self.bottom

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass(frozen=True)
class LayoutBox:
    """A named rectangular region in the overall layout."""

    name: str
    rect: Rect

    def to_dict(self) -> dict:
        return {"name": self.name, **self.rect.to_dict()}
