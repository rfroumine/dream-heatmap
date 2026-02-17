"""ColorScale: matplotlib colormap → 256-entry RGBA lookup table."""

from __future__ import annotations

import numpy as np

from .validation import validate_colormap_name


class ColorScale:
    """Maps scalar values to colors via a 256-entry RGBA lookup table.

    The LUT is pre-computed from a matplotlib colormap and transferred
    to JS as 1024 bytes (256 entries x 4 bytes RGBA).
    """

    __slots__ = ("_lut", "_vmin", "_vmax", "_cmap_name", "_nan_color")

    LUT_SIZE = 256

    def __init__(
        self,
        cmap_name: str = "viridis",
        vmin: float = 0.0,
        vmax: float = 1.0,
        nan_color: tuple[int, int, int, int] = (200, 200, 200, 255),
    ) -> None:
        validate_colormap_name(cmap_name)
        self._cmap_name = cmap_name
        self._vmin = float(vmin)
        self._vmax = float(vmax)
        self._nan_color = nan_color
        self._lut = self._build_lut()

    def _build_lut(self) -> np.ndarray:
        """Build a (256, 4) uint8 RGBA lookup table from the matplotlib cmap."""
        import matplotlib.pyplot as plt
        cmap = plt.get_cmap(self._cmap_name)
        positions = np.linspace(0.0, 1.0, self.LUT_SIZE)
        rgba_float = cmap(positions)  # (256, 4) float in [0, 1]
        lut = (rgba_float * 255).astype(np.uint8)
        return lut

    @property
    def lut(self) -> np.ndarray:
        """(256, 4) uint8 RGBA lookup table."""
        return self._lut

    @property
    def vmin(self) -> float:
        return self._vmin

    @property
    def vmax(self) -> float:
        return self._vmax

    @property
    def cmap_name(self) -> str:
        return self._cmap_name

    def to_bytes(self) -> bytes:
        """Serialize LUT as 1024 bytes (256 * 4 RGBA) for JS transfer."""
        return self._lut.tobytes()

    def value_to_index(self, value: float) -> int:
        """Map a scalar value to a LUT index [0, 255]."""
        if self._vmax == self._vmin:
            return 127
        normalized = (value - self._vmin) / (self._vmax - self._vmin)
        clamped = max(0.0, min(1.0, normalized))
        return int(clamped * 255)

    @property
    def nan_color(self) -> tuple[int, int, int, int]:
        return self._nan_color
