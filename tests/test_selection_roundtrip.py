"""Tests for selection round-trip: pixel → visual index → original IDs.

Simulates the full path from pixel coordinates through CellLayout and
IDMapper to verify the correct row/col IDs are returned.
"""

import numpy as np
import pytest

from dream_heatmap.core.id_mapper import IDMapper
from dream_heatmap.layout.cell_layout import CellLayout
from dream_heatmap.layout.composer import LayoutComposer


class TestPixelToIDRoundTrip:
    """Simulate the JS ID resolution path in Python."""

    def _resolve_pixel_range(self, cell_layout, mapper, px_start, px_end):
        """Python equivalent of IDResolver.snapRange + visualRangeToIds."""
        start_idx = None
        end_idx = None
        # Find first cell overlapping px_start
        for i in range(cell_layout._n_cells):
            if cell_layout.positions[i] + cell_layout.cell_size > px_start:
                start_idx = i
                break
        # Find last cell overlapping px_end
        for i in range(cell_layout._n_cells - 1, -1, -1):
            if cell_layout.positions[i] < px_end:
                end_idx = i
                break
        if start_idx is None or end_idx is None or start_idx > end_idx:
            return []
        return mapper.resolve_range(start_idx, end_idx + 1)

    def test_select_single_cell(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        layout = CellLayout(n_cells=4, cell_size=10.0, offset=0.0)

        # Click in the middle of cell 1 ("b")
        result = self._resolve_pixel_range(layout, mapper, 12.0, 18.0)
        assert result == ["b"]

    def test_select_two_cells(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        layout = CellLayout(n_cells=4, cell_size=10.0, offset=0.0)

        # Drag from middle of cell 0 to middle of cell 1
        result = self._resolve_pixel_range(layout, mapper, 5.0, 15.0)
        assert result == ["a", "b"]

    def test_select_all_cells(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        layout = CellLayout(n_cells=4, cell_size=10.0, offset=0.0)

        result = self._resolve_pixel_range(layout, mapper, 0.0, 40.0)
        assert result == ["a", "b", "c", "d"]

    def test_select_with_offset(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        layout = CellLayout(n_cells=3, cell_size=10.0, offset=20.0)

        # cell 0 at 20-30, cell 1 at 30-40, cell 2 at 40-50
        result = self._resolve_pixel_range(layout, mapper, 25.0, 35.0)
        assert result == ["a", "b"]

    def test_select_outside_grid(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        layout = CellLayout(n_cells=3, cell_size=10.0, offset=0.0)

        result = self._resolve_pixel_range(layout, mapper, 50.0, 60.0)
        assert result == []

    def test_select_across_gap(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split_mapper = mapper.apply_splits({
            "g1": ["a", "b"],
            "g2": ["c", "d"],
        })
        layout = CellLayout(
            n_cells=4, cell_size=10.0,
            gap_positions=split_mapper.gap_positions,
            gap_size=6.0, offset=0.0,
        )
        # positions: [0, 10, 26, 36]
        # Select from cell 1 through the gap into cell 2
        result = self._resolve_pixel_range(layout, split_mapper, 12.0, 30.0)
        assert result == ["b", "c"]

    def test_select_within_single_group(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split_mapper = mapper.apply_splits({
            "g1": ["a", "b"],
            "g2": ["c", "d"],
        })
        layout = CellLayout(
            n_cells=4, cell_size=10.0,
            gap_positions=split_mapper.gap_positions,
            gap_size=6.0, offset=0.0,
        )
        # Select only within group 1
        result = self._resolve_pixel_range(layout, split_mapper, 0.0, 20.0)
        assert result == ["a", "b"]

    def test_select_after_reorder(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        reordered = mapper.apply_reorder(np.array(["d", "c", "b", "a"]))
        layout = CellLayout(n_cells=4, cell_size=10.0, offset=0.0)

        # First two visual positions are now "d" and "c"
        result = self._resolve_pixel_range(layout, reordered, 0.0, 20.0)
        assert result == ["d", "c"]


class TestCellLayoutEdgeCases:
    def test_single_cell(self):
        layout = CellLayout(n_cells=1, cell_size=10.0)
        assert layout.pixel_to_index(0.0) == 0
        assert layout.pixel_to_index(9.99) == 0
        assert layout.pixel_to_index(10.0) is None

    def test_very_small_cells(self):
        layout = CellLayout(n_cells=100, cell_size=1.0)
        assert layout.pixel_to_index(0.0) == 0
        assert layout.pixel_to_index(50.0) == 50
        assert layout.pixel_to_index(99.5) == 99

    def test_multiple_gaps(self):
        layout = CellLayout(
            n_cells=6, cell_size=10.0,
            gap_positions=frozenset({2, 4}), gap_size=5.0,
        )
        # positions: [0, 10, 25, 35, 50, 60]
        assert layout.positions[0] == 0.0
        assert layout.positions[1] == 10.0
        assert layout.positions[2] == 25.0   # 20 + 5 gap
        assert layout.positions[3] == 35.0
        assert layout.positions[4] == 50.0   # 45 + 5 gap
        assert layout.positions[5] == 60.0

        # In first gap (20-25)
        assert layout.pixel_to_index(22.0) is None
        # In second gap (45-50)
        assert layout.pixel_to_index(47.0) is None
        # Valid cells
        assert layout.pixel_to_index(0.0) == 0
        assert layout.pixel_to_index(25.0) == 2
        assert layout.pixel_to_index(50.0) == 4

    def test_gap_at_position_zero_does_nothing_weird(self):
        # gap_position=0 means gap before the first cell
        layout = CellLayout(
            n_cells=3, cell_size=10.0,
            gap_positions=frozenset({0}), gap_size=5.0,
        )
        # positions: [5, 15, 25] (gap before first cell)
        assert layout.positions[0] == 5.0
        assert layout.pixel_to_index(0.0) is None
        assert layout.pixel_to_index(5.0) == 0


class TestComposerWithSplitsRoundTrip:
    def test_layout_positions_match_cell_layout(self):
        row_mapper = IDMapper.from_ids(["r1", "r2", "r3", "r4"])
        row_mapper = row_mapper.apply_splits({
            "g1": ["r1", "r2"],
            "g2": ["r3", "r4"],
        })
        col_mapper = IDMapper.from_ids(["c1", "c2", "c3"])

        composer = LayoutComposer(cell_size=10.0, gap_size=6.0, padding=20.0)
        spec = composer.compute(row_mapper, col_mapper)

        # Verify layout positions are consistent
        assert len(spec.to_dict()["rowPositions"]) == 4
        assert len(spec.to_dict()["colPositions"]) == 3

        # Row positions should have gap at index 2
        # Auto-scaling: cell_size 10 → 50 for small matrix
        rp = spec.to_dict()["rowPositions"]
        assert rp[0] == 20.0   # padding
        assert rp[1] == 70.0   # 20 + 50
        assert rp[2] == 126.0  # 120 + 6 gap
        assert rp[3] == 176.0  # 126 + 50
