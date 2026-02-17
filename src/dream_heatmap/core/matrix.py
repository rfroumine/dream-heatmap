"""MatrixData: validated, immutable matrix container."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .validation import validate_dataframe_matrix


class MatrixData:
    """Immutable container for a validated numeric matrix.

    Stores the matrix as a contiguous float64 numpy array (row-major)
    alongside the original row and column IDs.
    """

    __slots__ = ("_values", "_row_ids", "_col_ids")

    def __init__(self, df: pd.DataFrame) -> None:
        df = validate_dataframe_matrix(df)
        self._values: np.ndarray = np.ascontiguousarray(df.values, dtype=np.float64)
        self._row_ids: np.ndarray = np.array(df.index, dtype=object)
        self._col_ids: np.ndarray = np.array(df.columns, dtype=object)

    @property
    def values(self) -> np.ndarray:
        """Float64 matrix (n_rows, n_cols), read-only view."""
        v = self._values.view()
        v.flags.writeable = False
        return v

    @property
    def row_ids(self) -> np.ndarray:
        """Original row IDs as object array."""
        return self._row_ids

    @property
    def col_ids(self) -> np.ndarray:
        """Original column IDs as object array."""
        return self._col_ids

    @property
    def shape(self) -> tuple[int, int]:
        return self._values.shape

    @property
    def n_rows(self) -> int:
        return self._values.shape[0]

    @property
    def n_cols(self) -> int:
        return self._values.shape[1]

    def to_bytes(self) -> bytes:
        """Serialize the matrix as row-major float64 bytes for JS transfer."""
        return self._values.tobytes()

    def finite_range(self) -> tuple[float, float]:
        """Return (min, max) of all finite values. Used for color scale defaults."""
        finite = self._values[np.isfinite(self._values)]
        if len(finite) == 0:
            return (0.0, 1.0)
        return (float(finite.min()), float(finite.max()))

    @classmethod
    def from_submatrix(
        cls,
        values: np.ndarray,
        row_ids: np.ndarray,
        col_ids: np.ndarray,
    ) -> MatrixData:
        """Create a MatrixData from pre-validated arrays (bypasses DataFrame validation)."""
        obj = object.__new__(cls)
        obj._values = np.ascontiguousarray(values, dtype=np.float64)
        obj._row_ids = np.asarray(row_ids, dtype=object)
        obj._col_ids = np.asarray(col_ids, dtype=object)
        return obj

    def slice(self, row_ids: np.ndarray, col_ids: np.ndarray) -> MatrixData:
        """Extract a submatrix for the given row/col IDs. Returns a new MatrixData."""
        row_id_to_idx = {rid: i for i, rid in enumerate(self._row_ids)}
        col_id_to_idx = {cid: i for i, cid in enumerate(self._col_ids)}
        row_indices = np.array([row_id_to_idx[rid] for rid in row_ids])
        col_indices = np.array([col_id_to_idx[cid] for cid in col_ids])
        sub_values = self._values[np.ix_(row_indices, col_indices)]
        return MatrixData.from_submatrix(sub_values, row_ids, col_ids)
