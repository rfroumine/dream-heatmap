"""MetadataFrame: validated row/col metadata aligned 1:1 with matrix IDs."""

from __future__ import annotations

import pandas as pd

from .validation import validate_metadata


class MetadataFrame:
    """Immutable metadata container aligned with matrix row or column IDs.

    Wraps a pandas DataFrame and guarantees that its index matches the
    matrix IDs exactly (same set, no duplicates).
    """

    __slots__ = ("_df", "_axis_name")

    def __init__(
        self,
        df: pd.DataFrame,
        expected_ids: pd.Index,
        axis_name: str = "row",
    ) -> None:
        df = validate_metadata(df, expected_ids, axis_name)
        # Reindex to match expected_ids order
        self._df = df.loc[expected_ids].copy()
        self._df.flags.writeable = False
        self._axis_name = axis_name

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def columns(self) -> list[str]:
        return list(self._df.columns)

    def get_column(self, col: str) -> pd.Series:
        if col not in self._df.columns:
            raise KeyError(
                f"Column '{col}' not found in {self._axis_name} metadata. "
                f"Available: {self.columns}"
            )
        return self._df[col]

    def get_categories(self, col: str) -> dict[str, list]:
        """Return {category: [ids]} mapping for a categorical column."""
        series = self.get_column(col)
        groups: dict[str, list] = {}
        for idx, val in series.items():
            groups.setdefault(str(val), []).append(idx)
        return groups
