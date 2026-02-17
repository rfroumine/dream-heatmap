"""AnnotationTrack: base class for all annotation types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np


# Valid edges for annotation placement
VALID_EDGES = {"left", "right", "top", "bottom"}

# Default track dimensions
DEFAULT_TRACK_WIDTH = 15.0  # pixels for categorical/minigraph tracks
DEFAULT_TRACK_GAP = 3.0     # gap between adjacent tracks


class AnnotationTrack(ABC):
    """Base class for annotation tracks placed alongside the heatmap.

    Each annotation track corresponds to one edge (left, right, top, bottom)
    and maps to either row IDs (left/right) or column IDs (top/bottom).
    """

    def __init__(
        self,
        name: str,
        track_width: float = DEFAULT_TRACK_WIDTH,
    ) -> None:
        self._name = name
        self._track_width = track_width

    @property
    def name(self) -> str:
        return self._name

    @property
    def track_width(self) -> float:
        return self._track_width

    @abstractmethod
    def get_render_data(self, visual_order: np.ndarray) -> dict:
        """Return serializable render data for JS.

        Parameters
        ----------
        visual_order : array of IDs in current visual order

        Returns dict consumed by SVGOverlay annotation rendering.
        """
        ...

    @property
    @abstractmethod
    def annotation_type(self) -> str:
        """String identifier for the annotation type (e.g., 'categorical')."""
        ...
