"""Tests for widget serializers."""

import json

import numpy as np
import pandas as pd
import pytest

from dream_heatmap.core.matrix import MatrixData
from dream_heatmap.core.color_scale import ColorScale
from dream_heatmap.core.id_mapper import IDMapper
from dream_heatmap.layout.composer import LayoutComposer
from dream_heatmap.widget.serializers import (
    serialize_matrix,
    serialize_color_lut,
    serialize_layout,
    serialize_id_mappers,
    serialize_config,
)
from dream_heatmap.widget.selection import SelectionState


class TestSerializeMatrix:
    def test_roundtrip(self, small_matrix_df):
        m = MatrixData(small_matrix_df)
        b = serialize_matrix(m)
        restored = np.frombuffer(b, dtype=np.float64).reshape(m.shape)
        np.testing.assert_array_equal(restored, m.values)


class TestSerializeColorLUT:
    def test_length(self):
        cs = ColorScale()
        b = serialize_color_lut(cs)
        assert len(b) == 1024


class TestSerializeLayout:
    def test_json_roundtrip(self):
        row_mapper = IDMapper.from_ids(["r1", "r2"])
        col_mapper = IDMapper.from_ids(["c1", "c2"])
        composer = LayoutComposer(cell_size=10.0, padding=20.0)
        layout = composer.compute(row_mapper, col_mapper)
        s = serialize_layout(layout)
        d = json.loads(s)
        assert d["nRows"] == 2
        assert d["nCols"] == 2
        assert "rowPositions" in d
        assert "colPositions" in d


class TestSerializeIDMappers:
    def test_json_roundtrip(self):
        row_mapper = IDMapper.from_ids(["r1", "r2", "r3"])
        col_mapper = IDMapper.from_ids(["c1", "c2"])
        s = serialize_id_mappers(row_mapper, col_mapper)
        d = json.loads(s)
        assert d["row"]["visual_order"] == ["r1", "r2", "r3"]
        assert d["col"]["visual_order"] == ["c1", "c2"]
        assert d["row"]["size"] == 3
        assert d["col"]["size"] == 2


class TestSerializeConfig:
    def test_basic(self):
        s = serialize_config(
            vmin=0.0, vmax=100.0, nan_color=(200, 200, 200, 255)
        )
        d = json.loads(s)
        assert d["vmin"] == 0.0
        assert d["vmax"] == 100.0
        assert d["nanColor"] == [200, 200, 200, 255]

    def test_extra_keys(self):
        s = serialize_config(
            vmin=0.0, vmax=1.0, nan_color=(0, 0, 0, 255),
            custom_key="hello",
        )
        d = json.loads(s)
        assert d["custom_key"] == "hello"

    def test_cmap_name_default(self):
        s = serialize_config(
            vmin=0.0, vmax=1.0, nan_color=(0, 0, 0, 255),
        )
        d = json.loads(s)
        assert d["cmapName"] == "viridis"

    def test_cmap_name_custom(self):
        s = serialize_config(
            vmin=0.0, vmax=1.0, nan_color=(0, 0, 0, 255),
            cmap_name="plasma",
        )
        d = json.loads(s)
        assert d["cmapName"] == "plasma"


class TestSelectionState:
    def test_initial_empty(self):
        ss = SelectionState()
        assert ss.value == {"row_ids": [], "col_ids": []}

    def test_update(self):
        ss = SelectionState()
        ss.update(["r1", "r2"], ["c1"])
        assert ss.row_ids == ["r1", "r2"]
        assert ss.col_ids == ["c1"]

    def test_clear(self):
        ss = SelectionState()
        ss.update(["r1"], ["c1"])
        ss.clear()
        assert ss.value == {"row_ids": [], "col_ids": []}

    def test_callback_called(self):
        ss = SelectionState()
        results = []
        ss.on_select(lambda rows, cols: results.append((rows, cols)))
        ss.update(["r1"], ["c1", "c2"])
        assert len(results) == 1
        assert results[0] == (["r1"], ["c1", "c2"])

    def test_multiple_callbacks(self):
        ss = SelectionState()
        r1, r2 = [], []
        ss.on_select(lambda rows, cols: r1.append(len(rows)))
        ss.on_select(lambda rows, cols: r2.append(len(cols)))
        ss.update(["a", "b"], ["x"])
        assert r1 == [2]
        assert r2 == [1]

    def test_repr(self):
        ss = SelectionState()
        ss.update(["r1", "r2"], ["c1"])
        assert "rows=2" in repr(ss)
        assert "cols=1" in repr(ss)
