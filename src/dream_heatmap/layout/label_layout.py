"""Label placement and collision avoidance for row/column labels."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .cell_layout import CellLayout


@dataclass(frozen=True)
class LabelSpec:
    """A single label to render."""

    text: str
    position: float   # pixel position on the label axis (cell center)
    visible: bool     # whether to render (after collision avoidance)


class LabelLayoutEngine:
    """Computes which labels to show based on display mode.

    Modes:
    - 'all': show every label
    - 'none': show no labels
    - 'auto': show labels with collision avoidance (skip overlapping ones)
    """

    @staticmethod
    def compute(
        ids: np.ndarray,
        cell_layout: CellLayout,
        mode: str = "auto",
        font_size: float = 10.0,
        min_spacing: float | None = None,
    ) -> list[LabelSpec]:
        """Compute label specs for an axis.

        Parameters
        ----------
        ids : array of IDs (in visual order)
        cell_layout : CellLayout for pixel positions
        mode : 'all', 'auto', or 'none'
        font_size : font size in pixels
        min_spacing : minimum pixel distance between labels.
                      Defaults to font_size * 1.2.
        """
        if mode == "none":
            return []

        if min_spacing is None:
            min_spacing = font_size * 1.2

        n = len(ids)
        labels = []

        if mode == "all":
            for i in range(n):
                pos = cell_layout.positions[i] + cell_layout.cell_size / 2
                labels.append(LabelSpec(
                    text=str(ids[i]),
                    position=pos,
                    visible=True,
                ))
        elif mode == "auto":
            last_pos = -float("inf")
            for i in range(n):
                pos = cell_layout.positions[i] + cell_layout.cell_size / 2
                visible = (pos - last_pos) >= min_spacing
                labels.append(LabelSpec(
                    text=str(ids[i]),
                    position=pos,
                    visible=visible,
                ))
                if visible:
                    last_pos = pos
        else:
            raise ValueError(
                f"Unknown label mode '{mode}'. Use 'all', 'auto', or 'none'."
            )

        return labels

    @staticmethod
    def serialize(labels: list[LabelSpec], font_size: float = 10.0) -> list[dict]:
        """Serialize label specs for JSON transfer to JS.
        
        Parameters
        ----------
        labels : list[LabelSpec]
            Label specs to serialize
        font_size : float
            Font size in pixels (default 10.0)
        """
        return [
            {
                "text": label.text,
                "position": float(label.position),
                "visible": bool(label.visible),
                "fontSize": float(font_size),
            }
            for label in labels
        ]
