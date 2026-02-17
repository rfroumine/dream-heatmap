"""CategoricalAnnotation: colored blocks showing category membership."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .base import AnnotationTrack, DEFAULT_TRACK_WIDTH


# Default color palette for categories (RColorBrewer Set2, 8 colors)
DEFAULT_CATEGORY_COLORS = [
    "#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3",
    "#a6d854", "#ffd92f", "#e5c494", "#b3b3b3",
]


class CategoricalAnnotation(AnnotationTrack):
    """Colored blocks showing category membership for each row/column.

    Usage::

        ann = CategoricalAnnotation("cell_type", metadata["cell_type"])
        hm.add_annotation("left", ann)
    """

    def __init__(
        self,
        name: str,
        values: pd.Series,
        colors: dict[str, str] | None = None,
        track_width: float = DEFAULT_TRACK_WIDTH,
        show_labels: bool = True,
    ) -> None:
        super().__init__(name=name, track_width=track_width)
        self._show_labels = show_labels
        self._values = values.copy()
        self._categories = list(dict.fromkeys(str(v) for v in values))

        if colors is not None:
            self._colors = colors
        else:
            self._colors = {
                cat: DEFAULT_CATEGORY_COLORS[i % len(DEFAULT_CATEGORY_COLORS)]
                for i, cat in enumerate(self._categories)
            }

    @property
    def annotation_type(self) -> str:
        return "categorical"

    @property
    def categories(self) -> list[str]:
        return self._categories

    @property
    def colors(self) -> dict[str, str]:
        return dict(self._colors)

    def get_render_data(self, visual_order: np.ndarray) -> dict:
        """Return per-cell color data in visual order."""
        cell_colors = []
        cell_labels = []
        for item_id in visual_order:
            if item_id in self._values.index:
                cat = str(self._values[item_id])
                cell_colors.append(self._colors.get(cat, "#cccccc"))
                cell_labels.append(cat)
            else:
                cell_colors.append("#cccccc")
                cell_labels.append("")

        return {
            "type": "categorical",
            "name": self._name,
            "trackWidth": self._track_width,
            "cellColors": cell_colors,
            "cellLabels": cell_labels,
            "colorMap": {cat: self._colors[cat] for cat in self._categories},
            "legend": {cat: self._colors[cat] for cat in self._categories},
            "showLabels": self._show_labels,
        }
