"""Tests for Phase 5: Annotations, labels, and layout integration."""

import numpy as np
import pandas as pd
import pytest

from dream_heatmap.annotation.base import AnnotationTrack, VALID_EDGES, DEFAULT_TRACK_WIDTH
from dream_heatmap.annotation.categorical import CategoricalAnnotation, DEFAULT_CATEGORY_COLORS
from dream_heatmap.annotation.label import LabelAnnotation
from dream_heatmap.annotation.minigraph import (
    BarChartAnnotation,
    SparklineAnnotation,
    BoxPlotAnnotation,
    ViolinPlotAnnotation,
)
from dream_heatmap.layout.annotation_layout import (
    AnnotationLayoutEngine,
    AnnotationTrackSpec,
    MAX_TRACKS_PER_EDGE,
)
from dream_heatmap.layout.label_layout import LabelLayoutEngine, LabelSpec
from dream_heatmap.layout.cell_layout import CellLayout
from dream_heatmap.core.id_mapper import IDMapper


# --- Fixtures ---

@pytest.fixture
def row_ids():
    return np.array(["gene_A", "gene_B", "gene_C", "gene_D"], dtype=object)


@pytest.fixture
def categorical_series():
    return pd.Series(
        ["T-cell", "B-cell", "T-cell", "NK-cell"],
        index=["gene_A", "gene_B", "gene_C", "gene_D"],
    )


@pytest.fixture
def numeric_series():
    return pd.Series(
        [1.5, 3.0, 2.0, 4.5],
        index=["gene_A", "gene_B", "gene_C", "gene_D"],
    )


@pytest.fixture
def replicate_df():
    """DataFrame where each row is a distribution (3 replicates per gene)."""
    return pd.DataFrame(
        {
            "rep1": [1.0, 4.0, 7.0, 10.0],
            "rep2": [2.0, 5.0, 8.0, 11.0],
            "rep3": [3.0, 6.0, 9.0, 12.0],
        },
        index=["gene_A", "gene_B", "gene_C", "gene_D"],
    )


@pytest.fixture
def cell_layout_4():
    """CellLayout for 4 items with no gaps."""
    return CellLayout(n_cells=4, cell_size=12.0, gap_positions=set(), gap_size=6.0, offset=40.0)


# --- CategoricalAnnotation ---

class TestDefaultCategoryColors:
    def test_set2_palette(self):
        """Default colors should be RColorBrewer Set2 (8 colors)."""
        assert len(DEFAULT_CATEGORY_COLORS) == 8
        assert DEFAULT_CATEGORY_COLORS[0] == "#66c2a5"
        assert DEFAULT_CATEGORY_COLORS[-1] == "#b3b3b3"


class TestCategoricalAnnotation:
    def test_basic_creation(self, categorical_series):
        ann = CategoricalAnnotation("cell_type", categorical_series)
        assert ann.name == "cell_type"
        assert ann.annotation_type == "categorical"
        assert ann.track_width == DEFAULT_TRACK_WIDTH

    def test_categories_detected(self, categorical_series):
        ann = CategoricalAnnotation("cell_type", categorical_series)
        assert "T-cell" in ann.categories
        assert "B-cell" in ann.categories
        assert "NK-cell" in ann.categories

    def test_auto_colors(self, categorical_series):
        ann = CategoricalAnnotation("cell_type", categorical_series)
        colors = ann.colors
        assert len(colors) == 3  # 3 unique categories
        for cat in ann.categories:
            assert cat in colors

    def test_custom_colors(self, categorical_series):
        custom = {"T-cell": "#ff0000", "B-cell": "#00ff00", "NK-cell": "#0000ff"}
        ann = CategoricalAnnotation("cell_type", categorical_series, colors=custom)
        assert ann.colors == custom

    def test_render_data_visual_order(self, categorical_series, row_ids):
        ann = CategoricalAnnotation("cell_type", categorical_series)
        data = ann.get_render_data(row_ids)
        assert data["type"] == "categorical"
        assert len(data["cellColors"]) == 4
        # Same category → same color
        assert data["cellColors"][0] == data["cellColors"][2]  # gene_A and gene_C are T-cell

    def test_render_data_reordered(self, categorical_series):
        ann = CategoricalAnnotation("cell_type", categorical_series)
        reordered = np.array(["gene_D", "gene_A", "gene_C", "gene_B"], dtype=object)
        data = ann.get_render_data(reordered)
        assert len(data["cellColors"]) == 4
        # gene_D (NK-cell) first, gene_A (T-cell) second
        assert data["cellColors"][0] != data["cellColors"][1]

    def test_missing_id_gets_grey(self, categorical_series):
        ann = CategoricalAnnotation("cell_type", categorical_series)
        data = ann.get_render_data(np.array(["gene_A", "unknown_gene"], dtype=object))
        assert data["cellColors"][1] == "#cccccc"

    def test_legend(self, categorical_series):
        ann = CategoricalAnnotation("cell_type", categorical_series)
        data = ann.get_render_data(np.array(["gene_A"], dtype=object))
        assert "legend" in data
        assert len(data["legend"]) == 3

    def test_show_labels_default_true(self, categorical_series, row_ids):
        ann = CategoricalAnnotation("cell_type", categorical_series)
        data = ann.get_render_data(row_ids)
        assert data["showLabels"] is True

    def test_show_labels_false(self, categorical_series, row_ids):
        ann = CategoricalAnnotation("cell_type", categorical_series, show_labels=False)
        data = ann.get_render_data(row_ids)
        assert data["showLabels"] is False


# --- LabelAnnotation ---

class TestLabelAnnotation:
    def test_with_values(self, row_ids):
        values = pd.Series(
            ["Alpha", "Beta", "Gamma", "Delta"],
            index=["gene_A", "gene_B", "gene_C", "gene_D"],
        )
        ann = LabelAnnotation("names", values)
        data = ann.get_render_data(row_ids)
        assert data["type"] == "label"
        assert data["labels"] == ["Alpha", "Beta", "Gamma", "Delta"]

    def test_without_values_uses_ids(self, row_ids):
        ann = LabelAnnotation("ids")
        data = ann.get_render_data(row_ids)
        assert data["labels"] == ["gene_A", "gene_B", "gene_C", "gene_D"]

    def test_font_size(self):
        ann = LabelAnnotation("test", font_size=14.0)
        data = ann.get_render_data(np.array(["a"], dtype=object))
        assert data["fontSize"] == 14.0


# --- BarChartAnnotation ---

class TestBarChartAnnotation:
    def test_basic(self, numeric_series, row_ids):
        ann = BarChartAnnotation("expr", numeric_series)
        assert ann.annotation_type == "bar"
        data = ann.get_render_data(row_ids)
        assert data["type"] == "bar"
        assert len(data["values"]) == 4
        assert data["values"][0] == 1.5
        assert data["vmin"] == 1.5
        assert data["vmax"] == 4.5

    def test_custom_range(self, numeric_series, row_ids):
        ann = BarChartAnnotation("expr", numeric_series, vmin=0.0, vmax=10.0)
        data = ann.get_render_data(row_ids)
        assert data["vmin"] == 0.0
        assert data["vmax"] == 10.0

    def test_nan_handling(self):
        values = pd.Series([1.0, np.nan, 3.0], index=["a", "b", "c"])
        ann = BarChartAnnotation("test", values)
        data = ann.get_render_data(np.array(["a", "b", "c"], dtype=object))
        assert data["values"][1] == 0.0  # NaN → 0


# --- SparklineAnnotation ---

class TestSparklineAnnotation:
    def test_basic(self, replicate_df, row_ids):
        ann = SparklineAnnotation("trend", replicate_df)
        assert ann.annotation_type == "sparkline"
        data = ann.get_render_data(row_ids)
        assert data["type"] == "sparkline"
        assert len(data["series"]) == 4
        assert data["series"][0] == [1.0, 2.0, 3.0]

    def test_missing_id(self, replicate_df):
        ann = SparklineAnnotation("trend", replicate_df)
        data = ann.get_render_data(np.array(["gene_A", "missing"], dtype=object))
        assert data["series"][1] == []


# --- BoxPlotAnnotation ---

class TestBoxPlotAnnotation:
    def test_basic(self, replicate_df, row_ids):
        ann = BoxPlotAnnotation("dist", replicate_df)
        assert ann.annotation_type == "boxplot"
        data = ann.get_render_data(row_ids)
        assert data["type"] == "boxplot"
        assert len(data["stats"]) == 4
        stats = data["stats"][0]
        assert stats["min"] == 1.0
        assert stats["max"] == 3.0
        assert stats["median"] == 2.0

    def test_missing_id(self, replicate_df):
        ann = BoxPlotAnnotation("dist", replicate_df)
        data = ann.get_render_data(np.array(["missing"], dtype=object))
        assert data["stats"][0] is None


# --- ViolinPlotAnnotation ---

class TestViolinPlotAnnotation:
    def test_basic(self, replicate_df, row_ids):
        ann = ViolinPlotAnnotation("density", replicate_df)
        assert ann.annotation_type == "violin"
        data = ann.get_render_data(row_ids)
        assert data["type"] == "violin"
        assert len(data["densities"]) == 4
        # Each density should have counts and centers
        d = data["densities"][0]
        assert "counts" in d
        assert "centers" in d

    def test_single_value_returns_none(self):
        """Single-value row can't form distribution."""
        df = pd.DataFrame({"rep1": [5.0]}, index=["a"])
        ann = ViolinPlotAnnotation("v", df)
        data = ann.get_render_data(np.array(["a"], dtype=object))
        assert data["densities"][0] is None


# --- AnnotationLayoutEngine ---

class TestAnnotationLayoutEngine:
    def test_compute_edge_tracks(self, categorical_series, row_ids):
        tracks = [CategoricalAnnotation("ct", categorical_series)]
        specs = AnnotationLayoutEngine.compute_edge_tracks(tracks, "left", row_ids)
        assert len(specs) == 1
        assert specs[0].edge == "left"
        assert specs[0].name == "ct"
        assert specs[0].offset > 0  # starts with a gap

    def test_stacking(self, categorical_series, numeric_series, row_ids):
        tracks = [
            CategoricalAnnotation("ct", categorical_series),
            BarChartAnnotation("expr", numeric_series),
        ]
        specs = AnnotationLayoutEngine.compute_edge_tracks(tracks, "left", row_ids)
        assert len(specs) == 2
        # Second track offset > first track offset + first track width
        assert specs[1].offset > specs[0].offset + specs[0].track_width

    def test_total_edge_width_empty(self):
        assert AnnotationLayoutEngine.total_edge_width([]) == 0.0

    def test_total_edge_width(self, categorical_series):
        tracks = [CategoricalAnnotation("ct", categorical_series)]
        width = AnnotationLayoutEngine.total_edge_width(tracks)
        assert width > tracks[0].track_width

    def test_max_tracks_constant(self):
        assert MAX_TRACKS_PER_EDGE == 3


# --- LabelLayoutEngine ---

class TestLabelLayoutEngine:
    def test_mode_all(self, row_ids, cell_layout_4):
        labels = LabelLayoutEngine.compute(row_ids, cell_layout_4, mode="all")
        assert len(labels) == 4
        assert all(l.visible for l in labels)

    def test_mode_none(self, row_ids, cell_layout_4):
        labels = LabelLayoutEngine.compute(row_ids, cell_layout_4, mode="none")
        assert labels == []

    def test_mode_auto_small_cells(self, cell_layout_4):
        """With small cells, auto mode should skip some labels."""
        ids = np.array([f"g{i}" for i in range(20)], dtype=object)
        layout = CellLayout(n_cells=20, cell_size=3.0, gap_positions=set(), gap_size=6.0, offset=0.0)
        labels = LabelLayoutEngine.compute(ids, layout, mode="auto")
        visible_count = sum(1 for l in labels if l.visible)
        assert visible_count < 20  # Should skip some

    def test_mode_auto_large_cells(self, cell_layout_4):
        """With large cells, auto mode should show all."""
        ids = np.array(["a", "b", "c"], dtype=object)
        layout = CellLayout(n_cells=3, cell_size=30.0, gap_positions=set(), gap_size=6.0, offset=0.0)
        labels = LabelLayoutEngine.compute(ids, layout, mode="auto")
        assert all(l.visible for l in labels)

    def test_serialize(self, row_ids, cell_layout_4):
        labels = LabelLayoutEngine.compute(row_ids, cell_layout_4, mode="all")
        serialized = LabelLayoutEngine.serialize(labels)
        assert len(serialized) == 4
        assert all("text" in s and "position" in s and "visible" in s for s in serialized)

    def test_invalid_mode(self, row_ids, cell_layout_4):
        with pytest.raises(ValueError, match="Unknown label mode"):
            LabelLayoutEngine.compute(row_ids, cell_layout_4, mode="invalid")


# --- Heatmap API integration ---

class TestHeatmapAnnotationAPI:
    def test_add_annotation(self, small_matrix_df, small_row_metadata):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        ann = CategoricalAnnotation("cell_type", small_row_metadata["cell_type"])
        result = hm.add_annotation("left", ann)
        assert result is hm  # builder pattern returns self

    def test_add_annotation_invalid_edge(self, small_matrix_df):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        ann = CategoricalAnnotation("test", pd.Series(["a"], index=["gene_A"]))
        with pytest.raises(ValueError, match="Invalid edge"):
            hm.add_annotation("center", ann)

    def test_add_annotation_max_per_edge(self, small_matrix_df, small_row_metadata):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        for i in range(MAX_TRACKS_PER_EDGE):
            ann = CategoricalAnnotation(f"ct_{i}", small_row_metadata["cell_type"])
            hm.add_annotation("left", ann)
        # Adding one more should fail
        with pytest.raises(ValueError, match="Maximum"):
            ann = CategoricalAnnotation("extra", small_row_metadata["cell_type"])
            hm.add_annotation("left", ann)

    def test_set_label_display(self, small_matrix_df):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        result = hm.set_label_display(rows="all", cols="none")
        assert result is hm

    def test_set_label_display_invalid(self, small_matrix_df):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        with pytest.raises(ValueError):
            hm.set_label_display(rows="invalid")

    def test_build_annotation_data(self, small_matrix_df, small_row_metadata):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        ann = CategoricalAnnotation("cell_type", small_row_metadata["cell_type"])
        hm.add_annotation("left", ann)
        hm._compute_layout()
        data = hm._build_annotation_data()
        assert data is not None
        assert "left" in data
        assert len(data["left"]) == 1
        assert data["left"][0]["name"] == "cell_type"
        assert "renderData" in data["left"][0]

    def test_build_annotation_data_none_when_empty(self, small_matrix_df):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        hm._compute_layout()
        data = hm._build_annotation_data()
        assert data is None

    def test_build_label_data(self, small_matrix_df):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        hm.set_label_display(rows="all", cols="all")
        hm._compute_layout()
        data = hm._build_label_data()
        assert data is not None
        assert "row" in data
        assert "col" in data
        assert len(data["row"]["labels"]) == 4  # 4 rows
        assert len(data["col"]["labels"]) == 3  # 3 cols

    def test_build_label_data_none_mode(self, small_matrix_df):
        from dream_heatmap.api import Heatmap
        hm = Heatmap(small_matrix_df)
        hm.set_label_display(rows="none", cols="none")
        hm._compute_layout()
        data = hm._build_label_data()
        assert data is None

    def test_layout_accounts_for_annotations(self, small_matrix_df, small_row_metadata):
        """Layout should allocate space for annotation tracks."""
        from dream_heatmap.api import Heatmap
        hm_plain = Heatmap(small_matrix_df)
        hm_plain._compute_layout()
        plain_x = hm_plain._layout.heatmap_rect.x

        hm_ann = Heatmap(small_matrix_df)
        ann = CategoricalAnnotation("cell_type", small_row_metadata["cell_type"])
        hm_ann.add_annotation("left", ann)
        hm_ann._compute_layout()
        ann_x = hm_ann._layout.heatmap_rect.x

        # Heatmap should shift right to make room for left annotation
        assert ann_x > plain_x


# --- Package exports ---

class TestPackageExports:
    def test_annotation_classes_exported(self):
        import dream_heatmap as dh
        assert hasattr(dh, "CategoricalAnnotation")
        assert hasattr(dh, "LabelAnnotation")
        assert hasattr(dh, "BarChartAnnotation")
        assert hasattr(dh, "SparklineAnnotation")
        assert hasattr(dh, "BoxPlotAnnotation")
        assert hasattr(dh, "ViolinPlotAnnotation")
