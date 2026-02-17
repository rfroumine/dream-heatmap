"""Tests for Phase 9: HTML export."""

import pathlib

import numpy as np
import pandas as pd
import pytest

from dream_heatmap.core.matrix import MatrixData
from dream_heatmap.core.color_scale import ColorScale
from dream_heatmap.core.id_mapper import IDMapper
from dream_heatmap.layout.composer import LayoutComposer
from dream_heatmap.export.html_export import HTMLExporter


@pytest.fixture
def simple_matrix():
    df = pd.DataFrame(
        np.arange(12, dtype=float).reshape(4, 3),
        index=["g1", "g2", "g3", "g4"],
        columns=["s1", "s2", "s3"],
    )
    return MatrixData(df)


@pytest.fixture
def color_scale(simple_matrix):
    vmin, vmax = simple_matrix.finite_range()
    return ColorScale("viridis", vmin=vmin, vmax=vmax)


@pytest.fixture
def row_mapper(simple_matrix):
    return IDMapper.from_ids(simple_matrix.row_ids)


@pytest.fixture
def col_mapper(simple_matrix):
    return IDMapper.from_ids(simple_matrix.col_ids)


@pytest.fixture
def layout(row_mapper, col_mapper):
    return LayoutComposer().compute(row_mapper, col_mapper)


class TestHTMLExporter:
    def test_export_creates_file(self, tmp_path, simple_matrix, color_scale,
                                  row_mapper, col_mapper, layout):
        out = tmp_path / "test.html"
        HTMLExporter.export(
            path=out,
            matrix=simple_matrix,
            color_scale=color_scale,
            row_mapper=row_mapper,
            col_mapper=col_mapper,
            layout=layout,
        )
        assert out.exists()
        assert out.stat().st_size > 0

    def test_export_html_structure(self, tmp_path, simple_matrix, color_scale,
                                    row_mapper, col_mapper, layout):
        out = tmp_path / "test.html"
        HTMLExporter.export(
            path=out,
            matrix=simple_matrix,
            color_scale=color_scale,
            row_mapper=row_mapper,
            col_mapper=col_mapper,
            layout=layout,
            title="Test Heatmap",
        )
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "<title>Test Heatmap</title>" in content
        assert "heatmap-container" in content
        assert "dream-heatmap" in content

    def test_export_contains_data(self, tmp_path, simple_matrix, color_scale,
                                   row_mapper, col_mapper, layout):
        out = tmp_path / "test.html"
        HTMLExporter.export(
            path=out,
            matrix=simple_matrix,
            color_scale=color_scale,
            row_mapper=row_mapper,
            col_mapper=col_mapper,
            layout=layout,
        )
        content = out.read_text(encoding="utf-8")
        assert "MATRIX_B64" in content
        assert "COLOR_LUT_B64" in content
        assert "LAYOUT_DATA" in content
        assert "ID_MAPPERS_DATA" in content
        assert "CONFIG_DATA" in content

    def test_export_contains_js_classes(self, tmp_path, simple_matrix, color_scale,
                                         row_mapper, col_mapper, layout):
        out = tmp_path / "test.html"
        HTMLExporter.export(
            path=out,
            matrix=simple_matrix,
            color_scale=color_scale,
            row_mapper=row_mapper,
            col_mapper=col_mapper,
            layout=layout,
        )
        content = out.read_text(encoding="utf-8")
        assert "CanvasRenderer" in content
        assert "SVGOverlay" in content
        assert "IDResolver" in content
        assert "ColorMapper" in content
        assert "HoverHandler" in content
        assert "SelectionHandler" in content

    def test_export_self_contained(self, tmp_path, simple_matrix, color_scale,
                                    row_mapper, col_mapper, layout):
        """HTML should not reference external scripts/stylesheets."""
        out = tmp_path / "test.html"
        HTMLExporter.export(
            path=out,
            matrix=simple_matrix,
            color_scale=color_scale,
            row_mapper=row_mapper,
            col_mapper=col_mapper,
            layout=layout,
        )
        content = out.read_text(encoding="utf-8")
        assert '<script src=' not in content
        assert '<link rel="stylesheet"' not in content

    def test_build_js(self):
        js = HTMLExporter._build_js()
        assert "CanvasRenderer" in js
        assert "IDResolver" in js
        assert len(js) > 100


class TestHeatmapToHTML:
    def test_to_html(self, tmp_path, small_matrix_df):
        from dream_heatmap.api import Heatmap
        out = tmp_path / "heatmap.html"
        hm = Heatmap(small_matrix_df)
        hm.to_html(str(out))
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content

    def test_to_html_with_title(self, tmp_path, small_matrix_df):
        from dream_heatmap.api import Heatmap
        out = tmp_path / "heatmap.html"
        hm = Heatmap(small_matrix_df)
        hm.to_html(str(out), title="My Heatmap")
        content = out.read_text(encoding="utf-8")
        assert "<title>My Heatmap</title>" in content

    def test_to_html_with_annotations(self, tmp_path, small_matrix_df, small_row_metadata):
        from dream_heatmap.api import Heatmap
        from dream_heatmap.annotation.categorical import CategoricalAnnotation
        out = tmp_path / "heatmap.html"
        hm = Heatmap(small_matrix_df)
        ann = CategoricalAnnotation("ct", small_row_metadata["cell_type"])
        hm.add_annotation("left", ann)
        hm.to_html(str(out))
        assert out.exists()
