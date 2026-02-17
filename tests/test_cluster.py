"""Tests for ClusterEngine, reorder_within_groups, and clustering API."""

import numpy as np
import pandas as pd
import pytest

from dream_heatmap.core.id_mapper import IDMapper
from dream_heatmap.transform.cluster import ClusterEngine, ClusterResult


class TestClusterEngineBasic:
    def test_cluster_simple(self):
        data = np.array([
            [1.0, 0.0],
            [1.1, 0.1],
            [5.0, 5.0],
            [5.1, 5.1],
        ])
        ids = np.array(["a", "b", "c", "d"])
        result = ClusterEngine.cluster(data, ids)

        assert isinstance(result, ClusterResult)
        assert set(result.leaf_order.tolist()) == {"a", "b", "c", "d"}
        assert len(result.leaf_order) == 4

    def test_similar_items_adjacent(self):
        """Items with similar values should be adjacent in leaf order."""
        data = np.array([
            [0.0, 0.0],   # a - close to b
            [0.1, 0.1],   # b - close to a
            [10.0, 10.0], # c - close to d
            [10.1, 10.1], # d - close to c
        ])
        ids = np.array(["a", "b", "c", "d"])
        result = ClusterEngine.cluster(data, ids)

        order = result.leaf_order.tolist()
        a_idx = order.index("a")
        b_idx = order.index("b")
        c_idx = order.index("c")
        d_idx = order.index("d")

        # a and b should be adjacent
        assert abs(a_idx - b_idx) == 1
        # c and d should be adjacent
        assert abs(c_idx - d_idx) == 1

    def test_single_item(self):
        data = np.array([[1.0, 2.0]])
        ids = np.array(["only"])
        result = ClusterEngine.cluster(data, ids)
        assert list(result.leaf_order) == ["only"]
        assert len(result.dendrogram_nodes) == 0

    def test_two_items(self):
        data = np.array([[1.0, 2.0], [3.0, 4.0]])
        ids = np.array(["x", "y"])
        result = ClusterEngine.cluster(data, ids)
        assert set(result.leaf_order.tolist()) == {"x", "y"}
        assert len(result.dendrogram_nodes) == 1

    def test_deterministic(self):
        """Same input should always produce same output."""
        data = np.array([
            [1, 2, 3],
            [4, 5, 6],
            [1, 2, 4],
            [4, 5, 7],
        ], dtype=float)
        ids = np.array(["a", "b", "c", "d"])

        result1 = ClusterEngine.cluster(data, ids)
        result2 = ClusterEngine.cluster(data, ids)
        assert list(result1.leaf_order) == list(result2.leaf_order)


class TestClusterEngineMetrics:
    def test_ward_method(self):
        data = np.random.default_rng(42).standard_normal((10, 5))
        ids = np.array([f"r{i}" for i in range(10)])
        result = ClusterEngine.cluster(data, ids, method="ward", metric="euclidean")
        assert len(result.leaf_order) == 10

    def test_correlation_metric(self):
        data = np.random.default_rng(42).standard_normal((10, 5))
        ids = np.array([f"r{i}" for i in range(10)])
        result = ClusterEngine.cluster(data, ids, method="average", metric="correlation")
        assert len(result.leaf_order) == 10

    def test_invalid_method_raises(self):
        data = np.array([[1.0, 2.0], [3.0, 4.0]])
        ids = np.array(["a", "b"])
        with pytest.raises(ValueError, match="Unknown linkage"):
            ClusterEngine.cluster(data, ids, method="invalid")

    def test_invalid_metric_raises(self):
        data = np.array([[1.0, 2.0], [3.0, 4.0]])
        ids = np.array(["a", "b"])
        with pytest.raises(ValueError, match="Unknown distance"):
            ClusterEngine.cluster(data, ids, metric="invalid")


class TestClusterEngineNaN:
    def test_handles_nan(self):
        data = np.array([
            [1.0, np.nan, 3.0],
            [1.1, 2.0, 3.1],
            [5.0, 5.0, np.nan],
        ])
        ids = np.array(["a", "b", "c"])
        result = ClusterEngine.cluster(data, ids)
        assert len(result.leaf_order) == 3

    def test_all_nan_row(self):
        data = np.array([
            [np.nan, np.nan],
            [1.0, 2.0],
            [1.1, 2.1],
        ])
        ids = np.array(["a", "b", "c"])
        result = ClusterEngine.cluster(data, ids)
        assert len(result.leaf_order) == 3


class TestClusterEngineDendrogramNodes:
    def test_nodes_have_member_ids(self):
        data = np.array([
            [0, 0],
            [0, 1],
            [10, 10],
            [10, 11],
        ], dtype=float)
        ids = np.array(["a", "b", "c", "d"])
        result = ClusterEngine.cluster(data, ids)

        # The root node should have all members
        root = result.dendrogram_nodes[-1]
        assert set(root.member_ids) == {"a", "b", "c", "d"}

    def test_leaf_nodes_have_correct_members(self):
        data = np.array([
            [0, 0],
            [0, 1],
            [10, 10],
        ], dtype=float)
        ids = np.array(["a", "b", "c"])
        result = ClusterEngine.cluster(data, ids)

        # First merge should be a+b (closest)
        first = result.dendrogram_nodes[0]
        assert len(first.member_ids) == 2

    def test_heights_increasing(self):
        data = np.random.default_rng(42).standard_normal((8, 4))
        ids = np.array([f"r{i}" for i in range(8)])
        result = ClusterEngine.cluster(data, ids)

        heights = [n.height for n in result.dendrogram_nodes]
        # Heights should be non-decreasing
        for i in range(1, len(heights)):
            assert heights[i] >= heights[i - 1] - 1e-10


class TestReorderWithinGroups:
    def test_basic_reorder(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split = mapper.apply_splits({
            "g1": ["a", "b"],
            "g2": ["c", "d"],
        })
        reordered = split.apply_reorder_within_groups({
            "g1": np.array(["b", "a"]),
            "g2": np.array(["d", "c"]),
        })
        assert list(reordered.visual_order) == ["b", "a", "d", "c"]
        # Gap positions preserved
        assert reordered.gap_positions == split.gap_positions

    def test_partial_reorder(self):
        """Only reorder one group, leave the other unchanged."""
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split = mapper.apply_splits({
            "g1": ["a", "b"],
            "g2": ["c", "d"],
        })
        reordered = split.apply_reorder_within_groups({
            "g1": np.array(["b", "a"]),
        })
        assert list(reordered.visual_order) == ["b", "a", "c", "d"]

    def test_reorder_preserves_ids(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split = mapper.apply_splits({"g1": ["a", "b"], "g2": ["c", "d"]})
        reordered = split.apply_reorder_within_groups({
            "g1": np.array(["b", "a"]),
        })
        assert reordered.original_ids == mapper.original_ids

    def test_reorder_wrong_ids_raises(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split = mapper.apply_splits({"g1": ["a", "b"], "g2": ["c", "d"]})
        with pytest.raises(ValueError, match="doesn't match"):
            split.apply_reorder_within_groups({
                "g1": np.array(["a", "c"]),  # c is not in g1
            })


class TestClusterAPI:
    def test_cluster_rows(self, small_matrix_df):
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        hm.cluster_rows()

        # All IDs still present
        assert hm._row_mapper.original_ids == set(small_matrix_df.index)
        # Cluster results stored
        assert hm._row_cluster is not None

    def test_cluster_cols(self, small_matrix_df):
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        hm.cluster_cols()

        assert hm._col_mapper.original_ids == set(small_matrix_df.columns)
        assert hm._col_cluster is not None

    def test_cluster_with_custom_params(self, small_matrix_df):
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        hm.cluster_rows(method="ward", metric="euclidean")
        assert hm._row_cluster is not None

    def test_split_then_cluster(self, small_matrix_df, small_row_metadata):
        """Clustering should work independently within each split group."""
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        hm.set_row_metadata(small_row_metadata)
        hm.split_rows(by="cell_type")
        hm.cluster_rows()

        # All IDs still present
        assert hm._row_mapper.original_ids == set(small_matrix_df.index)
        # Each group should have a cluster result
        assert len(hm._row_cluster) == 3  # T-cell, B-cell, NK-cell

    def test_cluster_layout_has_dendro_space(self, small_matrix_df):
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        hm.cluster_rows()
        hm._compute_layout()

        assert hm._layout.row_dendro_width > 0
        assert hm._layout.col_dendro_height == 0  # no col clustering

    def test_cluster_both_axes(self, small_matrix_df):
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        hm.cluster_rows()
        hm.cluster_cols()
        hm._compute_layout()

        assert hm._layout.row_dendro_width > 0
        assert hm._layout.col_dendro_height > 0

    def test_dendrogram_data_generated(self, small_matrix_df):
        from dream_heatmap.api import Heatmap

        hm = Heatmap(small_matrix_df)
        hm.cluster_rows()
        hm._compute_layout()
        dendro = hm._build_dendrogram_data()

        assert dendro is not None
        assert "row" in dendro
        assert len(dendro["row"]["links"]) > 0

    def test_selection_correct_after_clustering(self, large_matrix_df):
        """After clustering, selection should return original IDs."""
        from dream_heatmap.api import Heatmap

        hm = Heatmap(large_matrix_df)
        hm.cluster_rows()

        # Select first 10 visual positions
        first_10 = hm._row_mapper.resolve_range(0, 10)
        assert len(first_10) == 10
        # All should be valid gene IDs
        all_ids = set(large_matrix_df.index)
        assert all(gid in all_ids for gid in first_10)
        # No duplicates
        assert len(set(first_10)) == 10
