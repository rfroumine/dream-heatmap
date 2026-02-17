"""Composite layout for concatenated heatmaps."""

from __future__ import annotations

from dataclasses import dataclass

from ..layout.composer import LayoutComposer, LayoutSpec
from ..layout.geometry import Rect
from ..layout.cell_layout import CellLayout
from ..core.id_mapper import IDMapper


@dataclass
class CompositeLayoutSpec:
    """Layout for a concatenated heatmap group."""

    panel_layouts: list[LayoutSpec]
    total_width: float
    total_height: float
    direction: str  # "horizontal" or "vertical"
    panel_gap: float  # gap between panels

    def to_dict(self) -> dict:
        return {
            "panels": [pl.to_dict() for pl in self.panel_layouts],
            "totalWidth": self.total_width,
            "totalHeight": self.total_height,
            "direction": self.direction,
            "panelGap": self.panel_gap,
        }


class CompositeLayoutComposer:
    """Computes layout for concatenated heatmaps.

    Arranges panels side-by-side (hconcat) or stacked (vconcat)
    with a gap between panels.
    """

    DEFAULT_PANEL_GAP = 20.0

    def __init__(self, panel_gap: float = DEFAULT_PANEL_GAP) -> None:
        self._panel_gap = panel_gap

    def compute_horizontal(
        self,
        panel_layouts: list[LayoutSpec],
    ) -> CompositeLayoutSpec:
        """Arrange panels left-to-right."""
        if not panel_layouts:
            raise ValueError("At least one panel layout required.")

        total_height = max(pl.total_height for pl in panel_layouts)
        total_width = sum(pl.total_width for pl in panel_layouts) + \
            self._panel_gap * (len(panel_layouts) - 1)

        return CompositeLayoutSpec(
            panel_layouts=panel_layouts,
            total_width=total_width,
            total_height=total_height,
            direction="horizontal",
            panel_gap=self._panel_gap,
        )

    def compute_vertical(
        self,
        panel_layouts: list[LayoutSpec],
    ) -> CompositeLayoutSpec:
        """Arrange panels top-to-bottom."""
        if not panel_layouts:
            raise ValueError("At least one panel layout required.")

        total_width = max(pl.total_width for pl in panel_layouts)
        total_height = sum(pl.total_height for pl in panel_layouts) + \
            self._panel_gap * (len(panel_layouts) - 1)

        return CompositeLayoutSpec(
            panel_layouts=panel_layouts,
            total_width=total_width,
            total_height=total_height,
            direction="vertical",
            panel_gap=self._panel_gap,
        )
