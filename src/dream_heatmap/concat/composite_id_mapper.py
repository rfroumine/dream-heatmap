"""CompositeIDMapper: chained ID mapping across concatenated heatmap panels."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.id_mapper import IDMapper


@dataclass(frozen=True)
class PanelMapping:
    """Tracks which panel owns which range of the composite visual order."""

    panel_index: int
    start: int    # inclusive start in composite visual order
    end: int      # exclusive end
    mapper: IDMapper


class CompositeIDMapper:
    """ID resolution across multiple concatenated heatmap panels.

    For horizontal concatenation (hconcat): panels share rows, each panel
    has its own column mapper. The composite maps a rectangle selection
    across panel boundaries.

    For vertical concatenation (vconcat): panels share columns, each panel
    has its own row mapper.
    """

    def __init__(
        self,
        panel_mappers: list[IDMapper],
        direction: str,
    ) -> None:
        """
        Parameters
        ----------
        panel_mappers : list of IDMapper
            One mapper per panel for the concatenated axis.
        direction : "horizontal" or "vertical"
        """
        if direction not in ("horizontal", "vertical"):
            raise ValueError(
                f"direction must be 'horizontal' or 'vertical', got '{direction}'"
            )
        self._direction = direction
        self._panels: list[PanelMapping] = []

        offset = 0
        for i, mapper in enumerate(panel_mappers):
            self._panels.append(PanelMapping(
                panel_index=i,
                start=offset,
                end=offset + mapper.size,
                mapper=mapper,
            ))
            offset += mapper.size

        self._total_size = offset

    @property
    def direction(self) -> str:
        return self._direction

    @property
    def total_size(self) -> int:
        return self._total_size

    @property
    def panels(self) -> list[PanelMapping]:
        return list(self._panels)

    def resolve_range(self, start: int, end: int) -> dict[int, list]:
        """Resolve a visual index range across panels.

        Returns {panel_index: [ids]} for each panel that overlaps the range.
        """
        start = max(0, start)
        end = min(self._total_size, end)
        result: dict[int, list] = {}

        for panel in self._panels:
            if panel.end <= start or panel.start >= end:
                continue
            # Overlap region
            local_start = max(0, start - panel.start)
            local_end = min(panel.mapper.size, end - panel.start)
            ids = panel.mapper.resolve_range(local_start, local_end)
            if ids:
                result[panel.panel_index] = ids

        return result

    def panel_gap_positions(self) -> frozenset[int]:
        """Return gap positions at panel boundaries (for layout)."""
        gaps = set()
        for panel in self._panels[1:]:
            gaps.add(panel.start)
        return frozenset(gaps)
