"""Shared test fixtures for dream-heatmap."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def small_matrix_df():
    """4x3 matrix DataFrame for basic tests."""
    data = np.array([
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0],
        [10.0, 11.0, 12.0],
    ])
    return pd.DataFrame(
        data,
        index=["gene_A", "gene_B", "gene_C", "gene_D"],
        columns=["sample_1", "sample_2", "sample_3"],
    )


@pytest.fixture
def small_row_metadata():
    """Row metadata for the 4x3 matrix."""
    return pd.DataFrame(
        {"cell_type": ["T-cell", "B-cell", "T-cell", "NK-cell"]},
        index=["gene_A", "gene_B", "gene_C", "gene_D"],
    )


@pytest.fixture
def small_col_metadata():
    """Column metadata for the 4x3 matrix."""
    return pd.DataFrame(
        {"treatment": ["control", "drug_A", "drug_A"]},
        index=["sample_1", "sample_2", "sample_3"],
    )


@pytest.fixture
def nan_matrix_df():
    """Matrix with NaN values."""
    data = np.array([
        [1.0, np.nan, 3.0],
        [np.nan, 5.0, 6.0],
    ])
    return pd.DataFrame(
        data,
        index=["row_1", "row_2"],
        columns=["col_1", "col_2", "col_3"],
    )


@pytest.fixture
def large_matrix_df():
    """100x50 matrix for performance-related tests."""
    rng = np.random.default_rng(42)
    data = rng.standard_normal((100, 50))
    rows = [f"gene_{i:03d}" for i in range(100)]
    cols = [f"sample_{j:03d}" for j in range(50)]
    return pd.DataFrame(data, index=rows, columns=cols)
