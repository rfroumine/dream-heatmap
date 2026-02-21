"""Tests for dream_heatmap.transform.scaler."""

import numpy as np
import pandas as pd
import pytest

from dream_heatmap.transform.scaler import (
    apply_scaling,
    scale_center,
    scale_minmax,
    scale_zscore,
)


@pytest.fixture
def sample_df():
    """A small DataFrame for testing."""
    return pd.DataFrame(
        {"A": [1.0, 2.0, 3.0], "B": [4.0, 5.0, 6.0], "C": [7.0, 8.0, 9.0]},
        index=["gene1", "gene2", "gene3"],
    )


@pytest.fixture
def df_with_constant_row():
    """DataFrame where one row has all identical values (std=0)."""
    return pd.DataFrame(
        {"A": [5.0, 2.0, 3.0], "B": [5.0, 5.0, 6.0], "C": [5.0, 8.0, 9.0]},
        index=["const", "gene2", "gene3"],
    )


@pytest.fixture
def df_with_constant_col():
    """DataFrame where one column has all identical values (std=0)."""
    return pd.DataFrame(
        {"A": [1.0, 2.0, 3.0], "B": [5.0, 5.0, 5.0], "C": [7.0, 8.0, 9.0]},
        index=["gene1", "gene2", "gene3"],
    )


class TestZscore:
    def test_row_wise_mean_zero(self, sample_df):
        result = scale_zscore(sample_df, axis=1)
        row_means = result.mean(axis=1)
        np.testing.assert_allclose(row_means, 0.0, atol=1e-10)

    def test_row_wise_std_one(self, sample_df):
        result = scale_zscore(sample_df, axis=1)
        row_stds = result.std(axis=1)
        np.testing.assert_allclose(row_stds, 1.0, atol=1e-10)

    def test_col_wise_mean_zero(self, sample_df):
        result = scale_zscore(sample_df, axis=0)
        col_means = result.mean(axis=0)
        np.testing.assert_allclose(col_means, 0.0, atol=1e-10)

    def test_col_wise_std_one(self, sample_df):
        result = scale_zscore(sample_df, axis=0)
        col_stds = result.std(axis=0)
        np.testing.assert_allclose(col_stds, 1.0, atol=1e-10)

    def test_preserves_shape(self, sample_df):
        result = scale_zscore(sample_df, axis=1)
        assert result.shape == sample_df.shape

    def test_preserves_index_columns(self, sample_df):
        result = scale_zscore(sample_df, axis=1)
        assert list(result.index) == list(sample_df.index)
        assert list(result.columns) == list(sample_df.columns)

    def test_constant_row_no_crash(self, df_with_constant_row):
        result = scale_zscore(df_with_constant_row, axis=1)
        # Constant row should have 0 values (mean subtracted, divided by 1)
        np.testing.assert_allclose(result.loc["const"], 0.0, atol=1e-10)

    def test_constant_col_no_crash(self, df_with_constant_col):
        result = scale_zscore(df_with_constant_col, axis=0)
        np.testing.assert_allclose(result["B"], 0.0, atol=1e-10)


class TestCenter:
    def test_row_wise_mean_zero(self, sample_df):
        result = scale_center(sample_df, axis=1)
        row_means = result.mean(axis=1)
        np.testing.assert_allclose(row_means, 0.0, atol=1e-10)

    def test_col_wise_mean_zero(self, sample_df):
        result = scale_center(sample_df, axis=0)
        col_means = result.mean(axis=0)
        np.testing.assert_allclose(col_means, 0.0, atol=1e-10)

    def test_preserves_variance(self, sample_df):
        """Centering should not change the variance."""
        result = scale_center(sample_df, axis=1)
        np.testing.assert_allclose(
            result.std(axis=1).values, sample_df.std(axis=1).values, atol=1e-10,
        )

    def test_preserves_shape(self, sample_df):
        result = scale_center(sample_df, axis=0)
        assert result.shape == sample_df.shape


class TestMinmax:
    def test_row_wise_range(self, sample_df):
        result = scale_minmax(sample_df, axis=1)
        assert result.min(axis=1).min() == pytest.approx(0.0)
        assert result.max(axis=1).max() == pytest.approx(1.0)

    def test_col_wise_range(self, sample_df):
        result = scale_minmax(sample_df, axis=0)
        assert result.min(axis=0).min() == pytest.approx(0.0)
        assert result.max(axis=0).max() == pytest.approx(1.0)

    def test_constant_row_no_crash(self, df_with_constant_row):
        result = scale_minmax(df_with_constant_row, axis=1)
        # Constant row: (val - min) / 1 = 0
        np.testing.assert_allclose(result.loc["const"], 0.0, atol=1e-10)

    def test_constant_col_no_crash(self, df_with_constant_col):
        result = scale_minmax(df_with_constant_col, axis=0)
        np.testing.assert_allclose(result["B"], 0.0, atol=1e-10)

    def test_preserves_shape(self, sample_df):
        result = scale_minmax(sample_df, axis=1)
        assert result.shape == sample_df.shape


class TestApplyScaling:
    def test_none_returns_unchanged(self, sample_df):
        result = apply_scaling(sample_df, "none", axis=1)
        pd.testing.assert_frame_equal(result, sample_df)

    def test_dispatches_zscore(self, sample_df):
        result = apply_scaling(sample_df, "zscore", axis=1)
        expected = scale_zscore(sample_df, axis=1)
        pd.testing.assert_frame_equal(result, expected)

    def test_dispatches_center(self, sample_df):
        result = apply_scaling(sample_df, "center", axis=0)
        expected = scale_center(sample_df, axis=0)
        pd.testing.assert_frame_equal(result, expected)

    def test_dispatches_minmax(self, sample_df):
        result = apply_scaling(sample_df, "minmax", axis=1)
        expected = scale_minmax(sample_df, axis=1)
        pd.testing.assert_frame_equal(result, expected)

    def test_invalid_method_raises(self, sample_df):
        with pytest.raises(KeyError):
            apply_scaling(sample_df, "invalid", axis=1)
