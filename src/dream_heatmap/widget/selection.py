"""SelectionState: reactive container + callback registry for selections."""

from __future__ import annotations

from typing import Callable, Any


SelectionCallback = Callable[[list, list], Any]


class SelectionState:
    """Holds the current selection and notifies registered callbacks.

    The selection is a dict with 'row_ids' and 'col_ids' lists.
    """

    def __init__(self) -> None:
        self._row_ids: list = []
        self._col_ids: list = []
        self._callbacks: list[SelectionCallback] = []

    @property
    def value(self) -> dict[str, list]:
        """Current selection as {row_ids: [...], col_ids: [...]}."""
        return {"row_ids": list(self._row_ids), "col_ids": list(self._col_ids)}

    @property
    def row_ids(self) -> list:
        return list(self._row_ids)

    @property
    def col_ids(self) -> list:
        return list(self._col_ids)

    def update(self, row_ids: list, col_ids: list) -> None:
        """Update the selection and notify all callbacks."""
        self._row_ids = list(row_ids)
        self._col_ids = list(col_ids)
        for cb in self._callbacks:
            cb(self._row_ids, self._col_ids)

    def clear(self) -> None:
        """Clear the selection."""
        self.update([], [])

    def on_select(self, callback: SelectionCallback) -> None:
        """Register a callback: fn(row_ids, col_ids)."""
        self._callbacks.append(callback)

    def __repr__(self) -> str:
        return (
            f"SelectionState(rows={len(self._row_ids)}, "
            f"cols={len(self._col_ids)})"
        )
