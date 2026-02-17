"""LabelAnnotation: text labels alongside the heatmap."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import AnnotationTrack


class LabelAnnotation(AnnotationTrack):
    """Text labels for each row or column.

    By default, uses the row/column IDs as labels. Can also use a
    metadata Series for custom label text.

    Usage::

        ann = LabelAnnotation("gene_name", metadata["gene_symbol"])
        hm.add_annotation("left", ann)
    """

    def __init__(
        self,
        name: str,
        values: pd.Series | None = None,
        font_size: float = 10.0,
        track_width: float = 60.0,
    ) -> None:
        super().__init__(name=name, track_width=track_width)
        self._values = values.copy() if values is not None else None
        self._font_size = font_size

    @property
    def annotation_type(self) -> str:
        return "label"

    def get_render_data(self, visual_order: np.ndarray) -> dict:
        """Return label text in visual order."""
        labels = []
        for item_id in visual_order:
            if self._values is not None and item_id in self._values.index:
                labels.append(str(self._values[item_id]))
            else:
                labels.append(str(item_id))

        return {
            "type": "label",
            "name": self._name,
            "trackWidth": self._track_width,
            "labels": labels,
            "fontSize": self._font_size,
        }
