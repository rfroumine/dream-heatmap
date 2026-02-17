"""Tests for MatrixData."""

import numpy as np
import pandas as pd
import pytest

from dream_heatmap.core.matrix import MatrixData


class TestMatrixDataInit:
    def test_basic_creation(self, small_matrix_df):
        m = MatrixData(small_matrix_df)
        assert m.shape == (4, 3)
        assert m.n_rows == 4
        assert m.n_cols == 3

    def test_row_ids(self, small_matrix_df):
        m = MatrixData(small_matrix_df)
        assert list(m.row_ids) == ["gene_A", "gene_B", "gene_C", "gene_D"]

    def test_col_ids(self, small_matrix_df):
        m = MatrixData(small_matrix_df)
        assert list(m.col_ids) == ["sample_1", "sample_2", "sample_3"]

    def test_values_are_float64(self, small_matrix_df):
        m = MatrixData(small_matrix_df)
        assert m.values.dtype == np.float64

    def test_values_are_readonly(self, small_matrix_df):
        m = MatrixData(small_matrix_df)
        with pytest.raises(ValueError):
            m.values[0, 0] = 999.0

    def test_values_contiguous(self, small_matrix_df):
        m = MatrixData(small_matrix_df)
        assert m.values.flags["C_CONTIGUOUS"]


class TestMatrixDataValidation:
    def test_rejects_non_dataframe(self):
        with pytest.raises(TypeError, match="pandas DataFrame"):
            MatrixData(np.array([[1, 2], [3, 4]]))

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="empty"):
            MatrixData(pd.DataFrame())

    def test_rejects_duplicate_rows(self):
        df = pd.DataFrame(
            [[1, 2], [3, 4]],
            index=["a", "a"],
            columns=["x", "y"],
        )
        with pytest.raises(ValueError, match="duplicate"):
            MatrixData(df)

    def test_rejects_duplicate_cols(self):
        df = pd.DataFrame(
            [[1, 2], [3, 4]],
            index=["a", "b"],
            columns=["x", "x"],
        )
        with pytest.raises(ValueError, match="duplicate"):
            MatrixData(df)

    def test_rejects_non_numeric(self):
        df = pd.DataFrame(
            {"a": [1, 2], "b": ["x", "y"]},
            index=["r1", "r2"],
        )
        with pytest.raises(TypeError, match="numeric"):
            MatrixData(df)


class TestMatrixDataSerialization:
    def test_to_bytes_length(self, small_matrix_df):
        m = MatrixData(small_matrix_df)
        b = m.to_bytes()
        assert len(b) == 4 * 3 * 8  # 12 float64 values

    def test_to_bytes_roundtrip(self, small_matrix_df):
        m = MatrixData(small_matrix_df)
        b = m.to_bytes()
        restored = np.frombuffer(b, dtype=np.float64).reshape(4, 3)
        np.testing.assert_array_equal(restored, m.values)


class TestMatrixDataRange:
    def test_finite_range(self, small_matrix_df):
        m = MatrixData(small_matrix_df)
        vmin, vmax = m.finite_range()
        assert vmin == 1.0
        assert vmax == 12.0

    def test_finite_range_with_nan(self, nan_matrix_df):
        m = MatrixData(nan_matrix_df)
        vmin, vmax = m.finite_range()
        assert vmin == 1.0
        assert vmax == 6.0

    def test_finite_range_all_nan(self):
        df = pd.DataFrame(
            [[np.nan, np.nan]],
            index=["r1"],
            columns=["c1", "c2"],
        )
        m = MatrixData(df)
        assert m.finite_range() == (0.0, 1.0)
