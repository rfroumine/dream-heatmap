"""Tests for Phase 7: Zoom functionality."""

import numpy as np
import pandas as pd
import pytest

from dream_heatmap.core.id_mapper import IDMapper
from dream_heatmap.core.matrix import MatrixData


# --- IDMapper.apply_zoom ---

class TestIDMapperZoom:
    def test_zoom_basic(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d", "e"])
        zoomed = mapper.apply_zoom(1, 4)
        assert zoomed.visual_order.tolist() == ["b", "c", "d"]
        assert zoomed.size == 3

    def test_zoom_preserves_subset(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d", "e"])
        zoomed = mapper.apply_zoom(0, 3)
        assert set(zoomed.visual_order.tolist()) == {"a", "b", "c"}

    def test_zoom_clamps_range(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        zoomed = mapper.apply_zoom(-1, 100)
        assert zoomed.visual_order.tolist() == ["a", "b", "c"]

    def test_zoom_empty_range_raises(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        with pytest.raises(ValueError, match="Invalid zoom range"):
            mapper.apply_zoom(2, 1)

    def test_zoom_with_gaps(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split = mapper.apply_splits({"g1": ["a", "b"], "g2": ["c", "d"]})
        assert 2 in split.gap_positions  # gap at index 2

        # Zoom that includes the gap
        zoomed = split.apply_zoom(1, 4)
        assert zoomed.visual_order.tolist() == ["b", "c", "d"]
        # Gap should be adjusted: was at 2, now at 2-1=1
        assert 1 in zoomed.gap_positions

    def test_zoom_gap_excluded(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split = mapper.apply_splits({"g1": ["a", "b"], "g2": ["c", "d"]})
        # Zoom only within first group — no gap in range
        zoomed = split.apply_zoom(0, 2)
        assert zoomed.visual_order.tolist() == ["a", "b"]
        assert len(zoomed.gap_positions) == 0

    def test_zoom_single_element(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        zoomed = mapper.apply_zoom(1, 2)
        assert zoomed.visual_order.tolist() == ["b"]
        assert zoomed.size == 1

    def test_zoom_then_resolve(self):
        """Zoom then resolve_range should return correct IDs."""
        mapper = IDMapper.from_ids(["a", "b", "c", "d", "e"])
        zoomed = mapper.apply_zoom(1, 4)  # ["b", "c", "d"]
        assert zoomed.resolve_range(0, 2) == ["b", "c"]
        assert zoomed.resolve_range(0, 3) == ["b", "c", "d"]

    def test_zoom_serialization(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d", "e"])
        zoomed = mapper.apply_zoom(1, 4)
        d = zoomed.to_dict()
        assert d["visual_order"] == ["b", "c", "d"]
        assert d["size"] == 3


# --- Heatmap zoom handler ---

class TestHeatmapZoom:
    def test_handle_zoom_creates_zoomed_layout(self, small_matrix_df):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        hm._compute_layout()
        original_rows = hm._row_mapper.size
        original_cols = hm._col_mapper.size

        # Simulate zoom
        zoom_range = {
            "row_start": 0, "row_end": 2,
            "col_start": 0, "col_end": 2,
        }
        # Can't fully test widget update without Jupyter, but we can
        # test that apply_zoom works on the mappers
        zoomed_row = hm._row_mapper.apply_zoom(0, 2)
        zoomed_col = hm._col_mapper.apply_zoom(0, 2)
        assert zoomed_row.size == 2
        assert zoomed_col.size == 2
        assert zoomed_row.size < original_rows
        assert zoomed_col.size < original_cols

    def test_zoom_reset(self, small_matrix_df):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        hm._compute_layout()
        # Original mappers are unchanged after zoom reset (None)
        assert hm._row_mapper.size == 4
        assert hm._col_mapper.size == 3


# --- MatrixData.slice ---

class TestMatrixSlice:
    def test_slice_basic(self, small_matrix_df):
        mat = MatrixData(small_matrix_df)
        row_ids = np.array(["gene_A", "gene_C"])
        col_ids = np.array(["sample_2", "sample_3"])
        sliced = mat.slice(row_ids, col_ids)

        assert sliced.shape == (2, 2)
        assert sliced.row_ids.tolist() == ["gene_A", "gene_C"]
        assert sliced.col_ids.tolist() == ["sample_2", "sample_3"]
        # gene_A: [1, 2, 3] → cols 2,3 → [2, 3]
        # gene_C: [7, 8, 9] → cols 2,3 → [8, 9]
        np.testing.assert_array_equal(sliced.values, [[2.0, 3.0], [8.0, 9.0]])

    def test_slice_single_cell(self, small_matrix_df):
        mat = MatrixData(small_matrix_df)
        sliced = mat.slice(np.array(["gene_B"]), np.array(["sample_1"]))
        assert sliced.shape == (1, 1)
        assert sliced.values[0, 0] == 4.0

    def test_slice_preserves_contiguous_bytes(self, small_matrix_df):
        mat = MatrixData(small_matrix_df)
        row_ids = np.array(["gene_A", "gene_B"])
        col_ids = np.array(["sample_1", "sample_3"])
        sliced = mat.slice(row_ids, col_ids)
        # Verify bytes have correct stride (row-major)
        b = sliced.to_bytes()
        arr = np.frombuffer(b, dtype=np.float64).reshape(2, 2)
        np.testing.assert_array_equal(arr, [[1.0, 3.0], [4.0, 6.0]])

    def test_from_submatrix(self):
        values = np.array([[10.0, 20.0], [30.0, 40.0]])
        row_ids = np.array(["r1", "r2"])
        col_ids = np.array(["c1", "c2"])
        mat = MatrixData.from_submatrix(values, row_ids, col_ids)
        assert mat.shape == (2, 2)
        assert mat.n_rows == 2
        assert mat.n_cols == 2
        np.testing.assert_array_equal(mat.values, values)

    def test_slice_full_matrix(self, small_matrix_df):
        mat = MatrixData(small_matrix_df)
        sliced = mat.slice(mat.row_ids, mat.col_ids)
        np.testing.assert_array_equal(sliced.values, mat.values)
        assert sliced.shape == mat.shape
