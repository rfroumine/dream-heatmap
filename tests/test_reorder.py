"""Tests for Phase 6: ReorderEngine, TransformPipeline, and order API."""

import numpy as np
import pandas as pd
import pytest

from dream_heatmap.core.id_mapper import IDMapper
from dream_heatmap.core.metadata import MetadataFrame
from dream_heatmap.transform.reorder import ReorderEngine
from dream_heatmap.transform.pipeline import TransformPipeline, TransformResult


# --- Fixtures ---

@pytest.fixture
def row_ids():
    return np.array(["gene_A", "gene_B", "gene_C", "gene_D"], dtype=object)


@pytest.fixture
def row_metadata(row_ids):
    df = pd.DataFrame(
        {
            "cell_type": ["T-cell", "B-cell", "T-cell", "NK-cell"],
            "score": [3.0, 1.0, 4.0, 2.0],
        },
        index=row_ids,
    )
    return MetadataFrame(df, pd.Index(row_ids), axis_name="row")


@pytest.fixture
def col_ids():
    return np.array(["s1", "s2", "s3"], dtype=object)


@pytest.fixture
def col_metadata(col_ids):
    df = pd.DataFrame(
        {
            "treatment": ["drug", "control", "drug"],
            "priority": [2, 1, 3],
        },
        index=col_ids,
    )
    return MetadataFrame(df, pd.Index(col_ids), axis_name="col")


@pytest.fixture
def matrix_4x3():
    return np.array([
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0],
        [10.0, 11.0, 12.0],
    ])


# --- ReorderEngine ---

class TestReorderEngine:
    def test_single_column_sort(self, row_ids, row_metadata):
        result = ReorderEngine.compute_order(row_ids, row_metadata, by="score")
        assert result.tolist() == ["gene_B", "gene_D", "gene_A", "gene_C"]

    def test_single_column_descending(self, row_ids, row_metadata):
        result = ReorderEngine.compute_order(
            row_ids, row_metadata, by="score", ascending=False
        )
        assert result.tolist() == ["gene_C", "gene_A", "gene_D", "gene_B"]

    def test_multi_column_sort(self, row_ids, row_metadata):
        result = ReorderEngine.compute_order(
            row_ids, row_metadata, by=["cell_type", "score"]
        )
        # B-cell(1.0), NK-cell(2.0), T-cell(3.0), T-cell(4.0)
        assert result.tolist() == ["gene_B", "gene_D", "gene_A", "gene_C"]

    def test_multi_ascending(self, row_ids, row_metadata):
        result = ReorderEngine.compute_order(
            row_ids, row_metadata,
            by=["cell_type", "score"],
            ascending=[True, False],
        )
        # B-cell, NK-cell, T-cell(4.0 desc), T-cell(3.0 desc)
        assert result.tolist() == ["gene_B", "gene_D", "gene_C", "gene_A"]

    def test_ascending_length_mismatch(self, row_ids, row_metadata):
        with pytest.raises(ValueError, match="Length of 'ascending'"):
            ReorderEngine.compute_order(
                row_ids, row_metadata,
                by=["cell_type", "score"],
                ascending=[True],
            )

    def test_missing_column(self, row_ids, row_metadata):
        with pytest.raises(KeyError):
            ReorderEngine.compute_order(
                row_ids, row_metadata, by="nonexistent"
            )

    def test_subset_of_ids(self, row_metadata):
        subset = np.array(["gene_A", "gene_C"], dtype=object)
        result = ReorderEngine.compute_order(
            subset, row_metadata, by="score"
        )
        assert result.tolist() == ["gene_A", "gene_C"]  # 3.0, 4.0


# --- TransformPipeline ---

class TestTransformPipeline:
    def test_no_transforms(self, row_ids, matrix_4x3, col_ids):
        mapper = IDMapper.from_ids(row_ids)
        result = TransformPipeline.run(
            mapper=mapper,
            matrix_values=matrix_4x3,
            row_ids=row_ids,
            col_ids=col_ids,
            axis="row",
        )
        assert isinstance(result, TransformResult)
        assert result.mapper.visual_order.tolist() == row_ids.tolist()
        assert result.cluster_results is None

    def test_split_only(self, row_ids, matrix_4x3, col_ids, row_metadata):
        mapper = IDMapper.from_ids(row_ids)
        result = TransformPipeline.run(
            mapper=mapper,
            matrix_values=matrix_4x3,
            row_ids=row_ids,
            col_ids=col_ids,
            axis="row",
            split_metadata=row_metadata,
            split_by="cell_type",
        )
        # Should have gap positions from splitting
        assert len(result.mapper.gap_positions) > 0
        assert result.cluster_results is None

    def test_cluster_only(self, row_ids, matrix_4x3, col_ids):
        mapper = IDMapper.from_ids(row_ids)
        result = TransformPipeline.run(
            mapper=mapper,
            matrix_values=matrix_4x3,
            row_ids=row_ids,
            col_ids=col_ids,
            axis="row",
            cluster=True,
        )
        assert result.cluster_results is not None
        assert "__all__" in result.cluster_results
        # All IDs still present
        assert set(result.mapper.visual_order.tolist()) == set(row_ids.tolist())

    def test_reorder_only(self, row_ids, matrix_4x3, col_ids, row_metadata):
        mapper = IDMapper.from_ids(row_ids)
        result = TransformPipeline.run(
            mapper=mapper,
            matrix_values=matrix_4x3,
            row_ids=row_ids,
            col_ids=col_ids,
            axis="row",
            reorder_metadata=row_metadata,
            reorder_by="score",
        )
        assert result.mapper.visual_order.tolist() == [
            "gene_B", "gene_D", "gene_A", "gene_C"
        ]
        assert result.cluster_results is None

    def test_split_then_cluster(self, row_ids, matrix_4x3, col_ids, row_metadata):
        mapper = IDMapper.from_ids(row_ids)
        result = TransformPipeline.run(
            mapper=mapper,
            matrix_values=matrix_4x3,
            row_ids=row_ids,
            col_ids=col_ids,
            axis="row",
            split_metadata=row_metadata,
            split_by="cell_type",
            cluster=True,
        )
        # Split + cluster
        assert result.cluster_results is not None
        assert len(result.mapper.gap_positions) > 0
        # All IDs preserved
        assert set(result.mapper.visual_order.tolist()) == set(row_ids.tolist())

    def test_split_then_reorder(self, row_ids, matrix_4x3, col_ids, row_metadata):
        mapper = IDMapper.from_ids(row_ids)
        result = TransformPipeline.run(
            mapper=mapper,
            matrix_values=matrix_4x3,
            row_ids=row_ids,
            col_ids=col_ids,
            axis="row",
            split_metadata=row_metadata,
            split_by="cell_type",
            reorder_metadata=row_metadata,
            reorder_by="score",
        )
        # Within each group, IDs should be sorted by score
        assert result.cluster_results is None
        assert set(result.mapper.visual_order.tolist()) == set(row_ids.tolist())

    def test_cluster_beats_reorder(self, row_ids, matrix_4x3, col_ids, row_metadata):
        """When both cluster and reorder are requested, clustering wins."""
        mapper = IDMapper.from_ids(row_ids)
        result = TransformPipeline.run(
            mapper=mapper,
            matrix_values=matrix_4x3,
            row_ids=row_ids,
            col_ids=col_ids,
            axis="row",
            cluster=True,
            reorder_metadata=row_metadata,
            reorder_by="score",
        )
        # Cluster results should exist (cluster ran, reorder skipped)
        assert result.cluster_results is not None

    def test_col_axis(self, row_ids, matrix_4x3, col_ids):
        mapper = IDMapper.from_ids(col_ids)
        result = TransformPipeline.run(
            mapper=mapper,
            matrix_values=matrix_4x3,
            row_ids=row_ids,
            col_ids=col_ids,
            axis="col",
            cluster=True,
        )
        assert result.cluster_results is not None
        assert set(result.mapper.visual_order.tolist()) == set(col_ids.tolist())

    def test_split_no_metadata_raises(self, row_ids, matrix_4x3, col_ids):
        mapper = IDMapper.from_ids(row_ids)
        with pytest.raises(ValueError, match="no metadata"):
            TransformPipeline.run(
                mapper=mapper,
                matrix_values=matrix_4x3,
                row_ids=row_ids,
                col_ids=col_ids,
                axis="row",
                split_by="cell_type",
            )

    def test_reorder_no_metadata_raises(self, row_ids, matrix_4x3, col_ids):
        mapper = IDMapper.from_ids(row_ids)
        with pytest.raises(ValueError, match="no metadata"):
            TransformPipeline.run(
                mapper=mapper,
                matrix_values=matrix_4x3,
                row_ids=row_ids,
                col_ids=col_ids,
                axis="row",
                reorder_by="score",
            )


# --- Heatmap API ---

class TestHeatmapOrderAPI:
    def test_order_rows(self, small_matrix_df, small_row_metadata):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        hm.set_row_metadata(small_row_metadata)
        result = hm.order_rows(by="cell_type")
        assert result is hm  # builder pattern

    def test_order_rows_no_metadata_raises(self, small_matrix_df):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        with pytest.raises(ValueError, match="set_row_metadata"):
            hm.order_rows(by="cell_type")

    def test_order_cols(self, small_matrix_df, small_col_metadata):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        hm.set_col_metadata(small_col_metadata)
        result = hm.order_cols(by="treatment")
        assert result is hm

    def test_order_cols_no_metadata_raises(self, small_matrix_df):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        with pytest.raises(ValueError, match="set_col_metadata"):
            hm.order_cols(by="treatment")

    def test_order_after_split(self, small_matrix_df, small_row_metadata):
        """Reorder within split groups."""
        from dream_heatmap.api import Heatmap
        meta = small_row_metadata.copy()
        meta["score"] = [3.0, 1.0, 4.0, 2.0]
        hm = Heatmap(small_matrix_df)
        hm.set_row_metadata(meta)
        hm.split_rows(by="cell_type")
        hm.order_rows(by="score")
        # All IDs still present
        assert set(hm._row_mapper.visual_order.tolist()) == set(small_matrix_df.index.tolist())

    def test_order_preserves_ids(self, small_matrix_df, small_row_metadata):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        hm.set_row_metadata(small_row_metadata)
        hm.order_rows(by="cell_type")
        assert set(hm._row_mapper.visual_order.tolist()) == set(small_matrix_df.index.tolist())
