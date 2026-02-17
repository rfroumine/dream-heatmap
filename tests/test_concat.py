"""Tests for Phase 8: Concatenation system."""

import numpy as np
import pandas as pd
import pytest

from dream_heatmap.core.id_mapper import IDMapper
from dream_heatmap.concat.composite_id_mapper import CompositeIDMapper, PanelMapping
from dream_heatmap.concat.composite_layout import CompositeLayoutComposer
from dream_heatmap.concat.heatmap_list import HeatmapList
from dream_heatmap.layout.composer import LayoutComposer


# --- Fixtures ---

@pytest.fixture
def shared_rows_df1():
    """4x3 matrix — shares rows with df2."""
    return pd.DataFrame(
        np.arange(12, dtype=float).reshape(4, 3),
        index=["g1", "g2", "g3", "g4"],
        columns=["s1", "s2", "s3"],
    )


@pytest.fixture
def shared_rows_df2():
    """4x2 matrix — shares rows with df1."""
    return pd.DataFrame(
        np.arange(8, dtype=float).reshape(4, 2),
        index=["g1", "g2", "g3", "g4"],
        columns=["s4", "s5"],
    )


@pytest.fixture
def shared_cols_df1():
    """3x3 matrix — shares cols with df2."""
    return pd.DataFrame(
        np.arange(9, dtype=float).reshape(3, 3),
        index=["g1", "g2", "g3"],
        columns=["s1", "s2", "s3"],
    )


@pytest.fixture
def shared_cols_df2():
    """2x3 matrix — shares cols with df1."""
    return pd.DataFrame(
        np.arange(6, dtype=float).reshape(2, 3),
        index=["g4", "g5"],
        columns=["s1", "s2", "s3"],
    )


# --- CompositeIDMapper ---

class TestCompositeIDMapper:
    def test_basic_horizontal(self):
        m1 = IDMapper.from_ids(["s1", "s2", "s3"])
        m2 = IDMapper.from_ids(["s4", "s5"])
        comp = CompositeIDMapper([m1, m2], "horizontal")
        assert comp.total_size == 5
        assert comp.direction == "horizontal"
        assert len(comp.panels) == 2

    def test_resolve_range_single_panel(self):
        m1 = IDMapper.from_ids(["s1", "s2", "s3"])
        m2 = IDMapper.from_ids(["s4", "s5"])
        comp = CompositeIDMapper([m1, m2], "horizontal")
        # Range within first panel
        result = comp.resolve_range(0, 2)
        assert result == {0: ["s1", "s2"]}

    def test_resolve_range_cross_boundary(self):
        m1 = IDMapper.from_ids(["s1", "s2", "s3"])
        m2 = IDMapper.from_ids(["s4", "s5"])
        comp = CompositeIDMapper([m1, m2], "horizontal")
        # Range spanning both panels
        result = comp.resolve_range(1, 5)
        assert result == {0: ["s2", "s3"], 1: ["s4", "s5"]}

    def test_resolve_range_second_panel_only(self):
        m1 = IDMapper.from_ids(["s1", "s2", "s3"])
        m2 = IDMapper.from_ids(["s4", "s5"])
        comp = CompositeIDMapper([m1, m2], "horizontal")
        result = comp.resolve_range(3, 5)
        assert result == {1: ["s4", "s5"]}

    def test_resolve_range_empty(self):
        m1 = IDMapper.from_ids(["s1", "s2"])
        comp = CompositeIDMapper([m1], "horizontal")
        result = comp.resolve_range(5, 10)
        assert result == {}

    def test_panel_gap_positions(self):
        m1 = IDMapper.from_ids(["a", "b"])
        m2 = IDMapper.from_ids(["c", "d"])
        m3 = IDMapper.from_ids(["e"])
        comp = CompositeIDMapper([m1, m2, m3], "horizontal")
        gaps = comp.panel_gap_positions()
        assert gaps == frozenset({2, 4})

    def test_invalid_direction(self):
        m1 = IDMapper.from_ids(["a"])
        with pytest.raises(ValueError, match="direction"):
            CompositeIDMapper([m1], "diagonal")


# --- CompositeLayoutComposer ---

class TestCompositeLayoutComposer:
    def _make_layout(self, n_rows, n_cols):
        row_mapper = IDMapper.from_ids([f"r{i}" for i in range(n_rows)])
        col_mapper = IDMapper.from_ids([f"c{i}" for i in range(n_cols)])
        composer = LayoutComposer()
        return composer.compute(row_mapper, col_mapper)

    def test_horizontal(self):
        l1 = self._make_layout(4, 3)
        l2 = self._make_layout(4, 2)
        composer = CompositeLayoutComposer()
        result = composer.compute_horizontal([l1, l2])
        assert result.direction == "horizontal"
        assert len(result.panel_layouts) == 2
        assert result.total_width > l1.total_width
        assert result.total_height == max(l1.total_height, l2.total_height)

    def test_vertical(self):
        l1 = self._make_layout(3, 3)
        l2 = self._make_layout(2, 3)
        composer = CompositeLayoutComposer()
        result = composer.compute_vertical([l1, l2])
        assert result.direction == "vertical"
        assert result.total_height > l1.total_height
        assert result.total_width == max(l1.total_width, l2.total_width)

    def test_empty_raises(self):
        composer = CompositeLayoutComposer()
        with pytest.raises(ValueError):
            composer.compute_horizontal([])

    def test_serialization(self):
        l1 = self._make_layout(3, 3)
        l2 = self._make_layout(3, 2)
        composer = CompositeLayoutComposer()
        result = composer.compute_horizontal([l1, l2])
        d = result.to_dict()
        assert "panels" in d
        assert len(d["panels"]) == 2
        assert d["direction"] == "horizontal"


# --- HeatmapList ---

class TestHeatmapList:
    def test_hconcat(self, shared_rows_df1, shared_rows_df2):
        from dream_heatmap.api import Heatmap
        hm1 = Heatmap(shared_rows_df1)
        hm2 = Heatmap(shared_rows_df2)
        hl = HeatmapList([hm1, hm2], direction="horizontal")
        assert hl.direction == "horizontal"
        assert len(hl.heatmaps) == 2

    def test_vconcat(self, shared_cols_df1, shared_cols_df2):
        from dream_heatmap.api import Heatmap
        hm1 = Heatmap(shared_cols_df1)
        hm2 = Heatmap(shared_cols_df2)
        hl = HeatmapList([hm1, hm2], direction="vertical")
        assert hl.direction == "vertical"

    def test_hconcat_mismatched_rows(self, shared_rows_df1):
        from dream_heatmap.api import Heatmap
        df_bad = pd.DataFrame(
            np.zeros((3, 2)),
            index=["g1", "g2", "g99"],
            columns=["s4", "s5"],
        )
        hm1 = Heatmap(shared_rows_df1)
        hm2 = Heatmap(df_bad)
        with pytest.raises(ValueError, match="same row IDs"):
            HeatmapList([hm1, hm2], direction="horizontal")

    def test_vconcat_mismatched_cols(self, shared_cols_df1):
        from dream_heatmap.api import Heatmap
        df_bad = pd.DataFrame(
            np.zeros((2, 2)),
            index=["g4", "g5"],
            columns=["s1", "s99"],
        )
        hm1 = Heatmap(shared_cols_df1)
        hm2 = Heatmap(df_bad)
        with pytest.raises(ValueError, match="same column IDs"):
            HeatmapList([hm1, hm2], direction="vertical")

    def test_too_few_heatmaps(self, shared_rows_df1):
        from dream_heatmap.api import Heatmap
        hm1 = Heatmap(shared_rows_df1)
        with pytest.raises(ValueError, match="at least 2"):
            HeatmapList([hm1], direction="horizontal")

    def test_compute_layout(self, shared_rows_df1, shared_rows_df2):
        from dream_heatmap.api import Heatmap
        hm1 = Heatmap(shared_rows_df1)
        hm2 = Heatmap(shared_rows_df2)
        hl = HeatmapList([hm1, hm2], direction="horizontal")
        layout = hl.compute_layout()
        assert layout.direction == "horizontal"
        assert len(layout.panel_layouts) == 2

    def test_composite_mapper_cross_boundary(self, shared_rows_df1, shared_rows_df2):
        from dream_heatmap.api import Heatmap
        hm1 = Heatmap(shared_rows_df1)
        hm2 = Heatmap(shared_rows_df2)
        hl = HeatmapList([hm1, hm2], direction="horizontal")
        # Composite mapper covers col axis
        comp = hl.composite_mapper
        assert comp.total_size == 5  # 3 + 2 columns
        # Select across boundary
        result = comp.resolve_range(2, 4)
        assert 0 in result  # last col of panel 0
        assert 1 in result  # first col of panel 1


# --- Heatmap.hconcat / vconcat API ---

class TestHeatmapConcatAPI:
    def test_hconcat_classmethod(self, shared_rows_df1, shared_rows_df2):
        from dream_heatmap.api import Heatmap
        hm1 = Heatmap(shared_rows_df1)
        hm2 = Heatmap(shared_rows_df2)
        result = Heatmap.hconcat(hm1, hm2)
        assert isinstance(result, HeatmapList)
        assert result.direction == "horizontal"

    def test_vconcat_classmethod(self, shared_cols_df1, shared_cols_df2):
        from dream_heatmap.api import Heatmap
        hm1 = Heatmap(shared_cols_df1)
        hm2 = Heatmap(shared_cols_df2)
        result = Heatmap.vconcat(hm1, hm2)
        assert isinstance(result, HeatmapList)
        assert result.direction == "vertical"
