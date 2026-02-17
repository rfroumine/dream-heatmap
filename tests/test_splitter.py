"""Tests for SplitEngine and the split API."""

import numpy as np
import pandas as pd
import pytest

from dream_heatmap.core.metadata import MetadataFrame
from dream_heatmap.core.id_mapper import IDMapper
from dream_heatmap.transform.splitter import SplitEngine
from dream_heatmap.layout.cell_layout import CellLayout


class TestSplitEngineBySingleColumn:
    def test_basic_split(self, small_matrix_df, small_row_metadata):
        meta = MetadataFrame(small_row_metadata, small_matrix_df.index, "row")
        result = SplitEngine.split(meta, "cell_type")
        # Order follows first-seen: T-cell (gene_A), B-cell (gene_B), NK-cell (gene_D)
        assert list(result.keys()) == ["T-cell", "B-cell", "NK-cell"]
        assert set(result["T-cell"]) == {"gene_A", "gene_C"}
        assert result["B-cell"] == ["gene_B"]
        assert result["NK-cell"] == ["gene_D"]

    def test_all_same_category(self):
        df = pd.DataFrame(
            [[1, 2], [3, 4], [5, 6]],
            index=["r1", "r2", "r3"],
            columns=["c1", "c2"],
        )
        meta_df = pd.DataFrame({"grp": ["A", "A", "A"]}, index=["r1", "r2", "r3"])
        meta = MetadataFrame(meta_df, df.index, "row")
        result = SplitEngine.split(meta, "grp")
        assert list(result.keys()) == ["A"]
        assert result["A"] == ["r1", "r2", "r3"]

    def test_each_its_own_group(self):
        df = pd.DataFrame(
            [[1, 2], [3, 4], [5, 6]],
            index=["r1", "r2", "r3"],
            columns=["c1", "c2"],
        )
        meta_df = pd.DataFrame({"grp": ["A", "B", "C"]}, index=["r1", "r2", "r3"])
        meta = MetadataFrame(meta_df, df.index, "row")
        result = SplitEngine.split(meta, "grp")
        assert len(result) == 3
        for key in result:
            assert len(result[key]) == 1

    def test_invalid_column_raises(self, small_matrix_df, small_row_metadata):
        meta = MetadataFrame(small_row_metadata, small_matrix_df.index, "row")
        with pytest.raises(KeyError, match="not found"):
            SplitEngine.split(meta, "nonexistent_col")


class TestSplitEngineByMultipleColumns:
    def test_two_column_split(self):
        meta_df = pd.DataFrame(
            {"type": ["T", "T", "B", "B"], "batch": ["1", "2", "1", "2"]},
            index=["r1", "r2", "r3", "r4"],
        )
        expected_ids = pd.Index(["r1", "r2", "r3", "r4"])
        meta = MetadataFrame(meta_df, expected_ids, "row")
        result = SplitEngine.split(meta, ["type", "batch"])
        # Keys are "type|batch"
        assert "T|1" in result
        assert "T|2" in result
        assert "B|1" in result
        assert "B|2" in result
        assert result["T|1"] == ["r1"]
        assert result["T|2"] == ["r2"]


class TestSplitEngineByAssignments:
    def test_valid_assignments(self):
        all_ids = {"a", "b", "c", "d"}
        assignments = {"g1": ["a", "b"], "g2": ["c", "d"]}
        result = SplitEngine.split_by_assignments(assignments, all_ids)
        assert result == assignments

    def test_missing_ids_raises(self):
        all_ids = {"a", "b", "c", "d"}
        with pytest.raises(ValueError, match="not assigned"):
            SplitEngine.split_by_assignments({"g1": ["a", "b"]}, all_ids)

    def test_extra_ids_raises(self):
        all_ids = {"a", "b"}
        with pytest.raises(ValueError, match="Unknown"):
            SplitEngine.split_by_assignments(
                {"g1": ["a", "b", "c"]}, all_ids
            )

    def test_duplicate_ids_raises(self):
        all_ids = {"a", "b", "c"}
        with pytest.raises(ValueError, match="multiple"):
            SplitEngine.split_by_assignments(
                {"g1": ["a", "b"], "g2": ["b", "c"]}, all_ids
            )


class TestSplitAPI:
    """Test the Heatmap.split_rows() / split_cols() API."""

    def test_split_rows_by_metadata(self, small_matrix_df, small_row_metadata):
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        hm.set_row_metadata(small_row_metadata)
        hm.split_rows(by="cell_type")

        # Verify IDMapper has gaps
        assert len(hm._row_mapper.gap_positions) > 0
        # All IDs still present
        assert hm._row_mapper.original_ids == set(small_matrix_df.index)

    def test_split_rows_by_assignments(self, small_matrix_df):
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        hm.split_rows(assignments={
            "top": ["gene_A", "gene_B"],
            "bottom": ["gene_C", "gene_D"],
        })
        assert 2 in hm._row_mapper.gap_positions
        assert hm._row_mapper.size == 4

    def test_split_cols_by_metadata(self, small_matrix_df, small_col_metadata):
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        hm.set_col_metadata(small_col_metadata)
        hm.split_cols(by="treatment")

        assert len(hm._col_mapper.gap_positions) > 0
        assert hm._col_mapper.original_ids == set(small_matrix_df.columns)

    def test_split_without_metadata_raises(self, small_matrix_df):
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        with pytest.raises(ValueError, match="set_row_metadata"):
            hm.split_rows(by="cell_type")

    def test_split_both_args_raises(self, small_matrix_df, small_row_metadata):
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        hm.set_row_metadata(small_row_metadata)
        with pytest.raises(ValueError, match="not both"):
            hm.split_rows(by="cell_type", assignments={"g1": ["gene_A"]})

    def test_split_no_args_raises(self, small_matrix_df):
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        with pytest.raises(ValueError, match="Provide either"):
            hm.split_rows()


class TestSplitLayoutPipeline:
    """End-to-end: split → IDMapper → CellLayout → selection."""

    def test_split_creates_correct_gap_in_layout(
        self, small_matrix_df, small_row_metadata
    ):
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        hm.set_row_metadata(small_row_metadata)
        hm.split_rows(by="cell_type")
        hm._compute_layout()

        layout = hm._layout
        row_positions = layout.row_cell_layout.positions

        # Verify positions have gaps
        # Groups: T-cell (gene_A, gene_C), B-cell (gene_B), NK-cell (gene_D)
        # With gaps between groups, positions should not be uniformly spaced
        diffs = np.diff(row_positions)
        cell_size = layout.row_cell_layout.cell_size
        # At least one diff should be larger (cell_size + gap_size)
        assert any(d > cell_size for d in diffs)

    def test_selection_after_split(self, small_matrix_df, small_row_metadata):
        """Verify that selecting cells after split returns correct IDs."""
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        hm.set_row_metadata(small_row_metadata)
        hm.split_rows(by="cell_type")

        # The first group should be T-cell: gene_A, gene_C
        first_two = hm._row_mapper.resolve_range(0, 2)
        assert set(first_two) == {"gene_A", "gene_C"}

        # All IDs across all groups
        all_ids = hm._row_mapper.resolve_range(0, hm._row_mapper.size)
        assert set(all_ids) == {"gene_A", "gene_B", "gene_C", "gene_D"}
