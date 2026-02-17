"""Tests for IDMapper — THE critical test suite."""

import numpy as np
import pytest

from dream_heatmap.core.id_mapper import IDMapper, SplitGroup


class TestIDMapperCreation:
    def test_from_ids_list(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        assert mapper.size == 3
        assert list(mapper.visual_order) == ["a", "b", "c"]

    def test_from_ids_array(self):
        mapper = IDMapper.from_ids(np.array(["x", "y", "z"]))
        assert mapper.size == 3

    def test_from_ids_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            IDMapper.from_ids([])

    def test_from_ids_duplicates_raises(self):
        with pytest.raises(ValueError, match="unique"):
            IDMapper.from_ids(["a", "b", "a"])

    def test_no_gaps_initially(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        assert mapper.gap_positions == frozenset()

    def test_single_group_initially(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        assert len(mapper.groups) == 1
        assert mapper.groups[0].name == "__all__"


class TestIDMapperOriginalIds:
    def test_original_ids_set(self):
        mapper = IDMapper.from_ids(["gene_A", "gene_B", "gene_C"])
        assert mapper.original_ids == {"gene_A", "gene_B", "gene_C"}


class TestIDMapperVisualIndex:
    def test_visual_index_of_existing(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        assert mapper.visual_index_of("a") == 0
        assert mapper.visual_index_of("b") == 1
        assert mapper.visual_index_of("c") == 2

    def test_visual_index_of_missing(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        assert mapper.visual_index_of("z") is None


class TestIDMapperResolveRange:
    """Core ruler-problem tests."""

    def test_full_range(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        assert mapper.resolve_range(0, 4) == ["a", "b", "c", "d"]

    def test_partial_range(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        assert mapper.resolve_range(1, 3) == ["b", "c"]

    def test_single_element(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        assert mapper.resolve_range(1, 2) == ["b"]

    def test_empty_range(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        assert mapper.resolve_range(2, 2) == []

    def test_out_of_bounds_clamped(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        assert mapper.resolve_range(-5, 100) == ["a", "b", "c"]

    def test_reversed_range_empty(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        assert mapper.resolve_range(3, 1) == []


class TestIDMapperReorder:
    def test_reorder(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        new = mapper.apply_reorder(np.array(["c", "a", "b"]))
        assert list(new.visual_order) == ["c", "a", "b"]

    def test_reorder_preserves_completeness(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        new = mapper.apply_reorder(np.array(["c", "a", "b"]))
        assert new.original_ids == mapper.original_ids

    def test_reorder_wrong_ids_raises(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        with pytest.raises(ValueError, match="same IDs"):
            mapper.apply_reorder(np.array(["a", "b", "z"]))

    def test_reorder_then_resolve(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        new = mapper.apply_reorder(np.array(["d", "c", "b", "a"]))
        assert new.resolve_range(0, 2) == ["d", "c"]
        assert new.resolve_range(2, 4) == ["b", "a"]


class TestIDMapperSplits:
    def test_split_basic(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split = mapper.apply_splits({
            "group1": ["a", "b"],
            "group2": ["c", "d"],
        })
        assert split.size == 4
        assert list(split.visual_order) == ["a", "b", "c", "d"]

    def test_split_creates_gap(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split = mapper.apply_splits({
            "group1": ["a", "b"],
            "group2": ["c", "d"],
        })
        assert 2 in split.gap_positions

    def test_split_three_groups(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d", "e", "f"])
        split = mapper.apply_splits({
            "g1": ["a", "b"],
            "g2": ["c", "d"],
            "g3": ["e", "f"],
        })
        assert split.gap_positions == frozenset({2, 4})
        assert list(split.visual_order) == ["a", "b", "c", "d", "e", "f"]

    def test_split_preserves_ids(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split = mapper.apply_splits({
            "group1": ["a", "c"],
            "group2": ["b", "d"],
        })
        assert split.original_ids == {"a", "b", "c", "d"}

    def test_split_preserves_relative_order(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split = mapper.apply_splits({
            "group1": ["c", "a"],  # order in input doesn't matter
            "group2": ["d", "b"],  # visual_order within group is from original
        })
        # Within group1, "a" comes before "c" in original order
        assert list(split.visual_order) == ["a", "c", "b", "d"]

    def test_split_missing_ids_raises(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        with pytest.raises(ValueError, match="don't match"):
            mapper.apply_splits({"g1": ["a", "b"]})  # missing "c"

    def test_split_extra_ids_raises(self):
        mapper = IDMapper.from_ids(["a", "b"])
        with pytest.raises(ValueError, match="don't match"):
            mapper.apply_splits({"g1": ["a", "b", "c"]})

    def test_split_duplicate_ids_raises(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        with pytest.raises(ValueError, match="multiple"):
            mapper.apply_splits({
                "g1": ["a", "b"],
                "g2": ["b", "c"],
            })

    def test_resolve_range_across_gap(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split = mapper.apply_splits({
            "group1": ["a", "b"],
            "group2": ["c", "d"],
        })
        # Range [1, 3) spans across the gap
        assert split.resolve_range(1, 3) == ["b", "c"]


class TestIDMapperZoom:
    def test_zoom_basic(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d", "e"])
        zoomed = mapper.apply_zoom(1, 4)
        assert zoomed.size == 3
        assert list(zoomed.visual_order) == ["b", "c", "d"]

    def test_zoom_resolve(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d", "e"])
        zoomed = mapper.apply_zoom(1, 4)
        assert zoomed.resolve_range(0, 3) == ["b", "c", "d"]
        assert zoomed.resolve_range(1, 2) == ["c"]

    def test_zoom_adjusts_gap_positions(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d", "e", "f"])
        split = mapper.apply_splits({
            "g1": ["a", "b"],
            "g2": ["c", "d"],
            "g3": ["e", "f"],
        })
        # Gaps at 2 and 4. Zoom to [1, 5) => items b, c, d, e
        # Gap at 2 -> adjusted to 2-1=1
        # Gap at 4 -> adjusted to 4-1=3
        zoomed = split.apply_zoom(1, 5)
        assert zoomed.size == 4
        assert 1 in zoomed.gap_positions
        assert 3 in zoomed.gap_positions

    def test_zoom_invalid_range_raises(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        with pytest.raises(ValueError, match="Invalid zoom"):
            mapper.apply_zoom(3, 3)

    def test_zoom_clamps_bounds(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        zoomed = mapper.apply_zoom(-1, 100)
        assert zoomed.size == 3


class TestIDMapperSerialization:
    def test_to_dict(self):
        mapper = IDMapper.from_ids(["a", "b", "c"])
        d = mapper.to_dict()
        assert d["visual_order"] == ["a", "b", "c"]
        assert d["gap_positions"] == []
        assert d["size"] == 3

    def test_to_dict_with_gaps(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split = mapper.apply_splits({
            "g1": ["a", "b"],
            "g2": ["c", "d"],
        })
        d = split.to_dict()
        assert d["gap_positions"] == [2]


class TestIDMapperInvariant:
    """After any transform, the set of IDs must be preserved."""

    def test_reorder_invariant(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        new = mapper.apply_reorder(np.array(["d", "c", "b", "a"]))
        assert set(new.visual_order.tolist()) == set(mapper.visual_order.tolist())
        assert len(new.visual_order) == len(set(new.visual_order.tolist()))

    def test_split_invariant(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d"])
        split = mapper.apply_splits({"g1": ["a", "c"], "g2": ["b", "d"]})
        assert set(split.visual_order.tolist()) == set(mapper.visual_order.tolist())
        assert len(split.visual_order) == len(set(split.visual_order.tolist()))

    def test_zoom_is_subset(self):
        mapper = IDMapper.from_ids(["a", "b", "c", "d", "e"])
        zoomed = mapper.apply_zoom(1, 4)
        assert set(zoomed.visual_order.tolist()).issubset(mapper.original_ids)
