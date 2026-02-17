"""dream-heatmap: Interactive, table-driven heatmaps that solve the ruler problem."""

from ._version import __version__
from .api import Heatmap
from .annotation import (
    CategoricalAnnotation,
    LabelAnnotation,
    BarChartAnnotation,
    SparklineAnnotation,
    BoxPlotAnnotation,
    ViolinPlotAnnotation,
)

__all__ = [
    "__version__",
    "Heatmap",
    "CategoricalAnnotation",
    "LabelAnnotation",
    "BarChartAnnotation",
    "SparklineAnnotation",
    "BoxPlotAnnotation",
    "ViolinPlotAnnotation",
]
