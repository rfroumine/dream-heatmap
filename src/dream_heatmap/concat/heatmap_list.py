"""HeatmapList: multi-heatmap container for concatenated display."""

from __future__ import annotations

from typing import Any

from .composite_id_mapper import CompositeIDMapper
from .composite_layout import CompositeLayoutComposer, CompositeLayoutSpec


class HeatmapList:
    """Container for horizontally or vertically concatenated heatmaps.

    Usage::

        combined = HeatmapList([hm1, hm2], direction="horizontal")
        combined.show()

    For horizontal concatenation, all heatmaps must share the same row IDs.
    For vertical concatenation, all heatmaps must share the same column IDs.
    """

    def __init__(
        self,
        heatmaps: list,
        direction: str = "horizontal",
    ) -> None:
        if len(heatmaps) < 2:
            raise ValueError("HeatmapList requires at least 2 heatmaps.")
        if direction not in ("horizontal", "vertical"):
            raise ValueError(
                f"direction must be 'horizontal' or 'vertical', got '{direction}'"
            )

        self._heatmaps = list(heatmaps)
        self._direction = direction
        self._validate_shared_axis()

        # Build composite mappers for the concatenated axis
        if direction == "horizontal":
            # Panels share rows, each has own cols
            col_mappers = [hm._col_mapper for hm in self._heatmaps]
            self._composite_mapper = CompositeIDMapper(col_mappers, direction)
        else:
            # Panels share cols, each has own rows
            row_mappers = [hm._row_mapper for hm in self._heatmaps]
            self._composite_mapper = CompositeIDMapper(row_mappers, direction)

        self._layout_composer = CompositeLayoutComposer()

    def _validate_shared_axis(self) -> None:
        """Validate that panels share the correct axis."""
        if self._direction == "horizontal":
            ref_rows = set(self._heatmaps[0]._row_mapper.visual_order.tolist())
            for i, hm in enumerate(self._heatmaps[1:], 1):
                other_rows = set(hm._row_mapper.visual_order.tolist())
                if ref_rows != other_rows:
                    raise ValueError(
                        f"Horizontal concatenation requires all heatmaps to have "
                        f"the same row IDs. Heatmap 0 and {i} differ."
                    )
        else:
            ref_cols = set(self._heatmaps[0]._col_mapper.visual_order.tolist())
            for i, hm in enumerate(self._heatmaps[1:], 1):
                other_cols = set(hm._col_mapper.visual_order.tolist())
                if ref_cols != other_cols:
                    raise ValueError(
                        f"Vertical concatenation requires all heatmaps to have "
                        f"the same column IDs. Heatmap 0 and {i} differ."
                    )

    @property
    def direction(self) -> str:
        return self._direction

    @property
    def heatmaps(self) -> list:
        return list(self._heatmaps)

    @property
    def composite_mapper(self) -> CompositeIDMapper:
        return self._composite_mapper

    def compute_layout(self) -> CompositeLayoutSpec:
        """Compute layouts for all panels and composite layout."""
        panel_layouts = []
        for hm in self._heatmaps:
            hm._compute_layout()
            panel_layouts.append(hm._layout)

        if self._direction == "horizontal":
            return self._layout_composer.compute_horizontal(panel_layouts)
        else:
            return self._layout_composer.compute_vertical(panel_layouts)

    def show(self) -> Any:
        """Render the concatenated heatmap in Jupyter.

        Returns the first heatmap's widget for now.
        Full multi-panel widget rendering is a future enhancement.
        """
        composite_layout = self.compute_layout()
        # For now, show each panel individually
        # A proper CompositeWidget would render all panels in one container
        widgets = []
        for hm in self._heatmaps:
            widgets.append(hm.show())
        return widgets
