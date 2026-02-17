"""ReorderEngine: metadata-based sorting within split groups."""

from __future__ import annotations

import numpy as np

from ..core.metadata import MetadataFrame


class ReorderEngine:
    """Sort IDs within groups based on metadata column values.

    Supports single or multi-column sorting. Sorts ascending by default.
    """

    @staticmethod
    def compute_order(
        ids: np.ndarray,
        metadata: MetadataFrame,
        by: str | list[str],
        ascending: bool | list[bool] = True,
    ) -> np.ndarray:
        """Return IDs sorted by the given metadata column(s).

        Parameters
        ----------
        ids : array of IDs to sort (subset of metadata index)
        metadata : MetadataFrame containing the sort columns
        by : column name or list of column names to sort by
        ascending : sort direction(s). Single bool or list matching ``by``.

        Returns
        -------
        Sorted array of IDs.
        """
        if isinstance(by, str):
            by = [by]
        if isinstance(ascending, bool):
            ascending = [ascending] * len(by)
        if len(ascending) != len(by):
            raise ValueError(
                f"Length of 'ascending' ({len(ascending)}) must match "
                f"'by' ({len(by)})."
            )

        # Validate columns exist
        for col in by:
            metadata.get_column(col)  # raises KeyError if missing

        # Build a sub-DataFrame for sorting
        df = metadata.df.loc[list(ids), by].copy()
        df = df.sort_values(by=by, ascending=ascending)
        return np.array(df.index.tolist(), dtype=object)
