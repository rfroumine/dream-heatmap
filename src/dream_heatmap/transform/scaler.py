"""Value scaling functions for expression matrices."""

from __future__ import annotations

import numpy as np
import pandas as pd


def scale_zscore(df: pd.DataFrame, axis: int) -> pd.DataFrame:
    """Center and scale (z-score): subtract mean, divide by std.

    axis=0 -> column-wise, axis=1 -> row-wise.
    """
    mean = df.mean(axis=axis)
    std = df.std(axis=axis)
    std = std.replace(0, 1)  # avoid division by zero
    if axis == 1:
        return df.sub(mean, axis=0).div(std, axis=0)
    return df.sub(mean, axis=1).div(std, axis=1)


def scale_center(df: pd.DataFrame, axis: int) -> pd.DataFrame:
    """Center only: subtract mean.

    axis=0 -> column-wise, axis=1 -> row-wise.
    """
    mean = df.mean(axis=axis)
    if axis == 1:
        return df.sub(mean, axis=0)
    return df.sub(mean, axis=1)


def scale_minmax(df: pd.DataFrame, axis: int) -> pd.DataFrame:
    """Min-max scaling to [0, 1].

    axis=0 -> column-wise, axis=1 -> row-wise.
    """
    mn = df.min(axis=axis)
    mx = df.max(axis=axis)
    rng = mx - mn
    rng = rng.replace(0, 1)  # avoid division by zero
    if axis == 1:
        return df.sub(mn, axis=0).div(rng, axis=0)
    return df.sub(mn, axis=1).div(rng, axis=1)


def apply_scaling(df: pd.DataFrame, method: str, axis: int) -> pd.DataFrame:
    """Dispatch to the appropriate scaling function.

    method: "none", "zscore", "center", "minmax"
    axis: 0 (column-wise) or 1 (row-wise)
    """
    if method == "none":
        return df
    funcs = {"zscore": scale_zscore, "center": scale_center, "minmax": scale_minmax}
    return funcs[method](df, axis)
