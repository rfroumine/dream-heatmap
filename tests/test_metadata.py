"""Tests for MetadataFrame."""

import pandas as pd
import pytest

from dream_heatmap.core.metadata import MetadataFrame


class TestMetadataFrameInit:
    def test_basic_creation(self, small_matrix_df, small_row_metadata):
        mf = MetadataFrame(small_row_metadata, small_matrix_df.index, "row")
        assert mf.columns == ["cell_type"]

    def test_reindexes_to_match_expected(self, small_matrix_df):
        meta = pd.DataFrame(
            {"group": ["B", "A", "D", "C"]},
            index=["gene_B", "gene_A", "gene_D", "gene_C"],
        )
        mf = MetadataFrame(meta, small_matrix_df.index, "row")
        # Should be reindexed to gene_A, gene_B, gene_C, gene_D order
        assert list(mf.df.index) == ["gene_A", "gene_B", "gene_C", "gene_D"]
        assert list(mf.df["group"]) == ["A", "B", "C", "D"]


class TestMetadataFrameValidation:
    def test_rejects_non_dataframe(self, small_matrix_df):
        with pytest.raises(TypeError, match="DataFrame"):
            MetadataFrame({"a": [1]}, small_matrix_df.index, "row")

    def test_rejects_missing_ids(self, small_matrix_df):
        meta = pd.DataFrame(
            {"group": ["A", "B"]},
            index=["gene_A", "gene_B"],
        )
        with pytest.raises(ValueError, match="missing"):
            MetadataFrame(meta, small_matrix_df.index, "row")

    def test_rejects_extra_ids(self, small_matrix_df):
        meta = pd.DataFrame(
            {"group": ["A", "B", "C", "D", "E"]},
            index=["gene_A", "gene_B", "gene_C", "gene_D", "gene_E"],
        )
        with pytest.raises(ValueError, match="not present"):
            MetadataFrame(meta, small_matrix_df.index, "row")

    def test_rejects_duplicate_ids(self, small_matrix_df):
        meta = pd.DataFrame(
            {"group": ["A", "B", "C", "D"]},
            index=["gene_A", "gene_A", "gene_C", "gene_D"],
        )
        with pytest.raises(ValueError, match="duplicate"):
            MetadataFrame(meta, small_matrix_df.index, "row")


class TestMetadataFrameAccess:
    def test_get_column(self, small_matrix_df, small_row_metadata):
        mf = MetadataFrame(small_row_metadata, small_matrix_df.index, "row")
        series = mf.get_column("cell_type")
        assert len(series) == 4
        assert series["gene_A"] == "T-cell"

    def test_get_column_missing(self, small_matrix_df, small_row_metadata):
        mf = MetadataFrame(small_row_metadata, small_matrix_df.index, "row")
        with pytest.raises(KeyError, match="not found"):
            mf.get_column("nonexistent")

    def test_get_categories(self, small_matrix_df, small_row_metadata):
        mf = MetadataFrame(small_row_metadata, small_matrix_df.index, "row")
        cats = mf.get_categories("cell_type")
        assert set(cats.keys()) == {"T-cell", "B-cell", "NK-cell"}
        assert set(cats["T-cell"]) == {"gene_A", "gene_C"}
