"""Serializers: convert Python objects to JS-transferable formats."""

from __future__ import annotations

import json
from typing import Any

from ..core.matrix import MatrixData
from ..core.color_scale import ColorScale
from ..core.id_mapper import IDMapper
from ..layout.composer import LayoutSpec


def serialize_matrix(matrix: MatrixData) -> bytes:
    """Serialize matrix as row-major float64 bytes."""
    return matrix.to_bytes()


def serialize_color_lut(color_scale: ColorScale) -> bytes:
    """Serialize color LUT as 1024 bytes (256 x RGBA)."""
    return color_scale.to_bytes()


def serialize_layout(layout: LayoutSpec) -> str:
    """Serialize layout spec as JSON string."""
    return json.dumps(layout.to_dict())


def serialize_id_mappers(
    row_mapper: IDMapper,
    col_mapper: IDMapper,
) -> str:
    """Serialize row and col IDMappers as JSON string."""
    return json.dumps({
        "row": row_mapper.to_dict(),
        "col": col_mapper.to_dict(),
    })


def serialize_config(
    vmin: float,
    vmax: float,
    nan_color: tuple[int, int, int, int],
    cmap_name: str = "viridis",
    **extra: Any,
) -> str:
    """Serialize rendering config as JSON string."""
    config = {
        "vmin": vmin,
        "vmax": vmax,
        "nanColor": list(nan_color),
        "cmapName": cmap_name,
        **extra,
    }
    return json.dumps(config)
