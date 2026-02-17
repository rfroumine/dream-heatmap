"""Tests for layout modules (geometry, cell_layout, composer)."""

import pytest

from dream_heatmap.core.id_mapper import IDMapper
from dream_heatmap.layout.geometry import Rect, LayoutBox
from dream_heatmap.layout.cell_layout import CellLayout
from dream_heatmap.layout.composer import LayoutComposer


class TestRect:
    def test_properties(self):
        r = Rect(10, 20, 100, 50)
        assert r.right == 110
        assert r.bottom == 70

    def test_contains(self):
        r = Rect(10, 20, 100, 50)
        assert r.contains(50, 40)
        assert not r.contains(5, 40)
        assert not r.contains(50, 80)

    def test_to_dict(self):
        r = Rect(10, 20, 100, 50)
        d = r.to_dict()
        assert d == {"x": 10, "y": 20, "width": 100, "height": 50}


class TestLayoutBox:
    def test_to_dict(self):
        lb = LayoutBox("heatmap", Rect(0, 0, 100, 100))
        d = lb.to_dict()
        assert d["name"] == "heatmap"
        assert d["width"] == 100


class TestCellLayout:
    def test_basic_positions(self):
        cl = CellLayout(n_cells=4, cell_size=10.0)
        assert list(cl.positions) == [0.0, 10.0, 20.0, 30.0]

    def test_with_offset(self):
        cl = CellLayout(n_cells=3, cell_size=10.0, offset=5.0)
        assert list(cl.positions) == [5.0, 15.0, 25.0]

    def test_with_gap(self):
        cl = CellLayout(
            n_cells=4,
            cell_size=10.0,
            gap_positions=frozenset({2}),
            gap_size=6.0,
        )
        # positions: 0, 10, 26, 36 (gap of 6 before index 2)
        assert cl.positions[0] == 0.0
        assert cl.positions[1] == 10.0
        assert cl.positions[2] == 26.0  # 20 + 6 gap
        assert cl.positions[3] == 36.0

    def test_total_size_no_gap(self):
        cl = CellLayout(n_cells=4, cell_size=10.0)
        assert cl.total_size == 40.0

    def test_total_size_with_gap(self):
        cl = CellLayout(
            n_cells=4, cell_size=10.0,
            gap_positions=frozenset({2}), gap_size=6.0,
        )
        assert cl.total_size == 46.0

    def test_total_size_empty(self):
        cl = CellLayout(n_cells=0, cell_size=10.0)
        assert cl.total_size == 0.0

    def test_pixel_to_index(self):
        cl = CellLayout(n_cells=4, cell_size=10.0)
        assert cl.pixel_to_index(0) == 0
        assert cl.pixel_to_index(9.9) == 0
        assert cl.pixel_to_index(10) == 1
        assert cl.pixel_to_index(35) == 3

    def test_pixel_to_index_outside(self):
        cl = CellLayout(n_cells=4, cell_size=10.0)
        assert cl.pixel_to_index(-1) is None
        assert cl.pixel_to_index(40) is None

    def test_pixel_to_index_in_gap(self):
        cl = CellLayout(
            n_cells=4, cell_size=10.0,
            gap_positions=frozenset({2}), gap_size=6.0,
        )
        # Gap is at pixel 20-26
        assert cl.pixel_to_index(19.9) == 1
        assert cl.pixel_to_index(20) is None  # in gap
        assert cl.pixel_to_index(25.9) is None  # still in gap
        assert cl.pixel_to_index(26) == 2

    def test_to_list(self):
        cl = CellLayout(n_cells=3, cell_size=10.0)
        assert cl.to_list() == [0.0, 10.0, 20.0]


class TestLayoutComposer:
    def test_basic_layout(self):
        row_mapper = IDMapper.from_ids(["r1", "r2", "r3"])
        col_mapper = IDMapper.from_ids(["c1", "c2"])
        composer = LayoutComposer(cell_size=10.0, padding=20.0)
        spec = composer.compute(row_mapper, col_mapper)

        assert spec.n_rows == 3
        assert spec.n_cols == 2
        assert spec.heatmap_rect.x == 20.0
        assert spec.heatmap_rect.y == 20.0
        # Auto-scaling: small matrix → cell_size scales up to MAX_CELL_SIZE (50)
        assert spec.heatmap_rect.width == 100.0  # 2 cols * 50px
        assert spec.heatmap_rect.height == 150.0  # 3 rows * 50px

    def test_layout_to_dict(self):
        row_mapper = IDMapper.from_ids(["r1", "r2"])
        col_mapper = IDMapper.from_ids(["c1", "c2"])
        composer = LayoutComposer(cell_size=12.0, padding=40.0)
        spec = composer.compute(row_mapper, col_mapper)
        d = spec.to_dict()
        assert "heatmap" in d
        assert "rowPositions" in d
        assert "colPositions" in d
        assert d["nRows"] == 2
        assert d["nCols"] == 2

    def test_layout_with_gaps(self):
        row_mapper = IDMapper.from_ids(["r1", "r2", "r3", "r4"])
        row_mapper = row_mapper.apply_splits({
            "g1": ["r1", "r2"],
            "g2": ["r3", "r4"],
        })
        col_mapper = IDMapper.from_ids(["c1", "c2"])
        composer = LayoutComposer(cell_size=10.0, gap_size=6.0, padding=0.0)
        spec = composer.compute(row_mapper, col_mapper)
        # Auto-scaling: cell_size → 50. Total height: 4*50 + 6 = 206
        assert spec.heatmap_rect.height == 206.0

    def test_layout_has_color_bar_flag(self):
        row_mapper = IDMapper.from_ids(["r1", "r2"])
        col_mapper = IDMapper.from_ids(["c1", "c2"])
        composer = LayoutComposer(cell_size=10.0, padding=20.0)
        spec = composer.compute(row_mapper, col_mapper)
        d = spec.to_dict()
        assert "colorBar" not in d
        assert d["hasColorBar"] is True

    def test_layout_no_right_side_color_bar(self):
        """Color bar is now in the legend panel, not on the right side."""
        row_mapper = IDMapper.from_ids(["r1", "r2", "r3"])
        col_mapper = IDMapper.from_ids(["c1", "c2"])
        composer = LayoutComposer(cell_size=10.0, padding=20.0)
        spec = composer.compute(row_mapper, col_mapper)
        assert spec.has_color_bar is True
        d = spec.to_dict()
        assert "colorBar" not in d
        # Total width: padding(20) + heatmap(100) + row_label(0) + padding(20)
        assert spec.total_width == 20.0 + 100.0 + 0.0 + 20.0

    def test_layout_annotation_widths_in_dict(self):
        row_mapper = IDMapper.from_ids(["r1", "r2"])
        col_mapper = IDMapper.from_ids(["c1", "c2"])
        composer = LayoutComposer(cell_size=10.0, padding=20.0)
        spec = composer.compute(
            row_mapper, col_mapper,
            right_annotation_width=15.0,
            bottom_annotation_height=25.0,
        )
        d = spec.to_dict()
        assert d["rightAnnotationWidth"] == 15.0
        assert d["bottomAnnotationHeight"] == 25.0

    def test_layout_grows_with_row_label_width(self):
        row_mapper = IDMapper.from_ids(["r1", "r2"])
        col_mapper = IDMapper.from_ids(["c1", "c2"])
        composer = LayoutComposer(cell_size=10.0, padding=20.0)
        spec_no_labels = composer.compute(row_mapper, col_mapper)
        spec_with_labels = composer.compute(
            row_mapper, col_mapper, row_label_width=100.0,
        )
        assert spec_with_labels.total_width > spec_no_labels.total_width

    def test_layout_grows_with_col_label_height(self):
        row_mapper = IDMapper.from_ids(["r1", "r2"])
        col_mapper = IDMapper.from_ids(["c1", "c2"])
        composer = LayoutComposer(cell_size=10.0, padding=20.0)
        spec_no_labels = composer.compute(row_mapper, col_mapper)
        spec_with_labels = composer.compute(
            row_mapper, col_mapper, col_label_height=80.0,
        )
        assert spec_with_labels.total_height > spec_no_labels.total_height

    def test_layout_label_space_increases_width(self):
        row_mapper = IDMapper.from_ids(["r1", "r2", "r3"])
        col_mapper = IDMapper.from_ids(["c1", "c2"])
        composer = LayoutComposer(cell_size=10.0, padding=20.0)
        spec = composer.compute(
            row_mapper, col_mapper,
            row_label_width=120.0,
        )
        spec_no_label = composer.compute(row_mapper, col_mapper)
        assert spec.total_width > spec_no_label.total_width
