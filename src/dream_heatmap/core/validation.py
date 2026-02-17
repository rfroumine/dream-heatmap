"""Input validation with clear error messages for bioinformaticians."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def validate_dataframe_matrix(data: Any) -> pd.DataFrame:
    """Validate that data is a numeric DataFrame suitable for heatmap display.

    Returns the validated DataFrame (unchanged).
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError(
            f"Expected a pandas DataFrame, got {type(data).__name__}. "
            "Wrap your data with pd.DataFrame(data, index=row_ids, columns=col_ids)."
        )
    if data.empty:
        raise ValueError("DataFrame is empty. Provide at least one row and one column.")
    if data.index.has_duplicates:
        dupes = data.index[data.index.duplicated()].unique().tolist()
        raise ValueError(
            f"Row IDs must be unique. Found duplicates: {dupes[:5]}"
            + (f" (and {len(dupes) - 5} more)" if len(dupes) > 5 else "")
        )
    if data.columns.has_duplicates:
        dupes = data.columns[data.columns.duplicated()].unique().tolist()
        raise ValueError(
            f"Column IDs must be unique. Found duplicates: {dupes[:5]}"
            + (f" (and {len(dupes) - 5} more)" if len(dupes) > 5 else "")
        )
    # Check numeric
    numeric_df = data.select_dtypes(include=[np.number])
    if numeric_df.shape[1] != data.shape[1]:
        non_numeric = [c for c in data.columns if c not in numeric_df.columns]
        raise TypeError(
            f"All columns must be numeric. Non-numeric columns: {non_numeric[:5]}"
            + (f" (and {len(non_numeric) - 5} more)" if len(non_numeric) > 5 else "")
        )
    return data


def validate_metadata(
    metadata: Any,
    expected_ids: pd.Index,
    axis_name: str,
) -> pd.DataFrame:
    """Validate that metadata DataFrame aligns 1:1 with expected IDs.

    Parameters
    ----------
    metadata : DataFrame to validate
    expected_ids : row or column IDs from the matrix
    axis_name : 'row' or 'col' for error messages
    """
    if not isinstance(metadata, pd.DataFrame):
        raise TypeError(
            f"{axis_name} metadata must be a pandas DataFrame, "
            f"got {type(metadata).__name__}."
        )
    if metadata.index.has_duplicates:
        dupes = metadata.index[metadata.index.duplicated()].unique().tolist()
        raise ValueError(
            f"{axis_name} metadata has duplicate IDs: {dupes[:5]}"
        )
    missing = expected_ids.difference(metadata.index)
    if len(missing) > 0:
        raise ValueError(
            f"{axis_name} metadata is missing IDs present in the matrix: "
            f"{missing.tolist()[:5]}"
            + (f" (and {len(missing) - 5} more)" if len(missing) > 5 else "")
        )
    extra = metadata.index.difference(expected_ids)
    if len(extra) > 0:
        raise ValueError(
            f"{axis_name} metadata has IDs not present in the matrix: "
            f"{extra.tolist()[:5]}"
            + (f" (and {len(extra) - 5} more)" if len(extra) > 5 else "")
        )
    return metadata


def validate_colormap_name(name: str) -> str:
    """Validate that a matplotlib colormap name exists."""
    import matplotlib.pyplot as plt

    try:
        plt.get_cmap(name)
    except ValueError:
        raise ValueError(
            f"Unknown colormap '{name}'. Use a matplotlib colormap name "
            f"like 'viridis', 'plasma', 'RdBu_r', etc."
        ) from None
    return name
