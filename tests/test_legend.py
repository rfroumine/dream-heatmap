"""Tests for categorical annotation legend collection and layout."""

import numpy as np
import pandas as pd
import pytest

from dream_heatmap.api import Heatmap
from dream_heatmap.annotation.categorical import CategoricalAnnotation
from dream_heatmap.annotation.minigraph import BarChartAnnotation


@pytest.fixture
def matrix_df():
    data = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    return pd.DataFrame(data, index=["g1", "g2", "g3"], columns=["s1", "s2"])


@pytest.fixture
def row_series():
    return pd.Series(["T cell", "B cell", "NK cell"], index=["g1", "g2", "g3"])


@pytest.fixture
def col_series():
    return pd.Series(["control", "drug_A"], index=["s1", "s2"])


class TestBuildLegendData:
    def test_no_annotations(self, matrix_df):
        hm = Heatmap(matrix_df)
        assert hm._build_legend_data() is None

    def test_single_categorical(self, matrix_df, row_series):
        hm = Heatmap(matrix_df)
        ann = CategoricalAnnotation("Cell Type", row_series)
        hm.add_annotation("left", ann)

        legends = hm._build_legend_data()
        assert legends is not None
        assert len(legends) == 1
        assert legends[0]["name"] == "Cell Type"
        labels = [e["label"] for e in legends[0]["entries"]]
        assert labels == ["T cell", "B cell", "NK cell"]

    def test_deduplication_same_annotation_two_edges(self, matrix_df, row_series):
        """Same name + same colorMap on two edges → one legend."""
        hm = Heatmap(matrix_df)
        ann1 = CategoricalAnnotation("Cell Type", row_series)
        ann2 = CategoricalAnnotation("Cell Type", row_series)
        hm.add_annotation("left", ann1)
        hm.add_annotation("right", ann2)

        legends = hm._build_legend_data()
        assert len(legends) == 1

    def test_different_annotations(self, matrix_df, row_series, col_series):
        """Two different categorical annotations → two legends."""
        hm = Heatmap(matrix_df)
        hm.add_annotation("left", CategoricalAnnotation("Cell Type", row_series))
        hm.add_annotation("top", CategoricalAnnotation("Treatment", col_series))

        legends = hm._build_legend_data()
        assert len(legends) == 2
        names = {l["name"] for l in legends}
        assert names == {"Cell Type", "Treatment"}

    def test_same_name_different_colors(self, matrix_df, row_series):
        """Same name but different colorMap → separate legends."""
        hm = Heatmap(matrix_df)
        ann1 = CategoricalAnnotation("Cell Type", row_series)
        custom_colors = {"T cell": "#ff0000", "B cell": "#00ff00", "NK cell": "#0000ff"}
        ann2 = CategoricalAnnotation("Cell Type", row_series, colors=custom_colors)
        hm.add_annotation("left", ann1)
        hm.add_annotation("right", ann2)

        legends = hm._build_legend_data()
        assert len(legends) == 2

    def test_non_categorical_ignored(self, matrix_df):
        """Bar/sparkline annotations produce no legends."""
        hm = Heatmap(matrix_df)
        values = pd.Series([1.0, 2.0, 3.0], index=["g1", "g2", "g3"])
        hm.add_annotation("left", BarChartAnnotation("score", values))

        assert hm._build_legend_data() is None


class TestEstimateLegendDimensions:
    def test_no_legends_still_has_color_bar(self, matrix_df):
        """Even without categorical legends, the color bar needs space."""
        hm = Heatmap(matrix_df)
        w, h = hm._estimate_legend_dimensions()
        assert w > 0
        assert h > 0  # color bar block

    def test_single_legend_vertical_stack(self, matrix_df, row_series):
        """Color bar and one legend stacked: height = sum of both + gap."""
        hm = Heatmap(matrix_df)
        hm.add_annotation("left", CategoricalAnnotation("Cell Type", row_series))
        w, h = hm._estimate_legend_dimensions()
        assert w > 0
        assert h > 0
        # Height should be sum of color bar + legend + gap (vertical stack)
        legend_h = 16.0 + 3 * 14.0  # title + 3 entries = 58
        color_bar_h = 26.0  # no title
        block_gap = 16.0
        assert h == color_bar_h + legend_h + block_gap

    def test_two_legends_vertical_stack(self, matrix_df, row_series, col_series):
        """Two legends + color bar: all stacked vertically."""
        hm = Heatmap(matrix_df)
        hm.add_annotation("left", CategoricalAnnotation("Cell Type", row_series))
        hm.add_annotation("top", CategoricalAnnotation("Treatment", col_series))
        w, h = hm._estimate_legend_dimensions()
        assert w > 0
        assert h > 0

    def test_color_bar_title_increases_height(self, matrix_df):
        """Color bar title adds 16px to the color bar block height."""
        hm_no_title = Heatmap(matrix_df)
        _, h_no = hm_no_title._estimate_legend_dimensions()

        hm_title = Heatmap(matrix_df)
        hm_title.set_colormap("viridis", color_bar_title="Expression")
        _, h_title = hm_title._estimate_legend_dimensions()

        assert h_title > h_no


class TestLayoutWithLegends:
    def test_legend_panel_in_layout(self, matrix_df, row_series):
        hm = Heatmap(matrix_df)
        hm.add_annotation("left", CategoricalAnnotation("Cell Type", row_series))
        hm._compute_layout()
        layout = hm._layout

        assert layout is not None
        assert layout.legend_panel_rect is not None
        d = layout.to_dict()
        assert "legendPanel" in d
        assert d["legendPanel"]["width"] > 0
        assert d["legendPanel"]["height"] > 0

    def test_legend_panel_even_without_annotations(self, matrix_df):
        """Color bar always creates a legend panel."""
        hm = Heatmap(matrix_df)
        hm._compute_layout()
        layout = hm._layout

        assert layout.legend_panel_rect is not None
        d = layout.to_dict()
        assert "legendPanel" in d

    def test_no_color_bar_in_layout_dict(self, matrix_df, row_series):
        """Color bar is no longer a separate rect in the layout."""
        hm = Heatmap(matrix_df)
        hm.add_annotation("left", CategoricalAnnotation("Cell Type", row_series))
        hm._compute_layout()
        d = hm._layout.to_dict()
        assert "colorBar" not in d
        assert d["hasColorBar"] is True


class TestLegendDataInConfig:
    def test_legends_in_serialized_config(self, matrix_df, row_series):
        """Legends should appear in the config JSON passed to JS."""
        import json
        from dream_heatmap.widget.serializers import serialize_config
        from dream_heatmap.core.color_scale import ColorScale

        hm = Heatmap(matrix_df)
        hm.add_annotation("left", CategoricalAnnotation("Cell Type", row_series))
        legends = hm._build_legend_data()

        cs = ColorScale("viridis", vmin=0, vmax=10)
        config_str = serialize_config(
            vmin=cs.vmin, vmax=cs.vmax, nan_color=cs.nan_color,
            legends=legends,
        )
        config = json.loads(config_str)
        assert "legends" in config
        assert len(config["legends"]) == 1
        assert config["legends"][0]["name"] == "Cell Type"

    def test_color_bar_title_in_serialized_config(self, matrix_df):
        """colorBarTitle should appear in the config JSON."""
        import json
        from dream_heatmap.widget.serializers import serialize_config
        from dream_heatmap.core.color_scale import ColorScale

        cs = ColorScale("viridis", vmin=0, vmax=10)
        config_str = serialize_config(
            vmin=cs.vmin, vmax=cs.vmax, nan_color=cs.nan_color,
            colorBarTitle="Expression",
        )
        config = json.loads(config_str)
        assert config["colorBarTitle"] == "Expression"
