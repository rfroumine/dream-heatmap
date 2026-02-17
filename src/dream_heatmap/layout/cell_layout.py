"""Cell pixel position computation, accounting for gaps from splits."""

from __future__ import annotations

import numpy as np


class CellLayout:
    """Computes pixel positions for heatmap cells.

    Cells are uniform size. Gaps (from splits) insert extra whitespace
    at specified visual indices.
    """

    def __init__(
        self,
        n_cells: int,
        cell_size: float,
        gap_positions: frozenset[int] = frozenset(),
        gap_size: float = 6.0,
        offset: float = 0.0,
    ) -> None:
        self._n_cells = n_cells
        self._cell_size = cell_size
        self._gap_positions = gap_positions
        self._gap_size = gap_size
        self._offset = offset
        self._positions = self._compute_positions()

    def _compute_positions(self) -> np.ndarray:
        """Compute the pixel start position of each cell."""
        positions = np.empty(self._n_cells, dtype=np.float64)
        current = self._offset
        for i in range(self._n_cells):
            if i in self._gap_positions:
                current += self._gap_size
            positions[i] = current
            current += self._cell_size
        return positions

    @property
    def positions(self) -> np.ndarray:
        """Pixel start positions for each cell (read-only)."""
        return self._positions

    @property
    def cell_size(self) -> float:
        return self._cell_size

    @property
    def total_size(self) -> float:
        """Total pixel span including all cells and gaps."""
        if self._n_cells == 0:
            return 0.0
        return self._positions[-1] + self._cell_size - self._offset

    def pixel_to_index(self, pixel: float) -> int | None:
        """Map a pixel coordinate to a cell index via binary search.

        Returns None if the pixel falls in a gap or outside the grid.
        """
        if self._n_cells == 0:
            return None
        # Binary search for the cell whose start position is <= pixel
        idx = int(np.searchsorted(self._positions, pixel, side="right")) - 1
        if idx < 0 or idx >= self._n_cells:
            return None
        # Check the pixel is within this cell (not in a trailing gap)
        if pixel < self._positions[idx] + self._cell_size:
            return idx
        return None  # in a gap

    def to_list(self) -> list[float]:
        """Serialize positions as a list for JSON transfer."""
        return self._positions.tolist()
