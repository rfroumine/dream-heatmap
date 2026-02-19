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


def explore(data, row_metadata=None, col_metadata=None, port=0, show=True):
    """Launch interactive dashboard in browser.

    Parameters
    ----------
    data : pd.DataFrame
        Expression matrix (rows=markers/genes, columns=cells/samples).
    row_metadata : pd.DataFrame, optional
        Row metadata. Index must match matrix row IDs.
    col_metadata : pd.DataFrame, optional
        Column metadata. Index must match matrix column IDs.
    port : int
        Port number. 0 = auto-assign.
    show : bool
        Whether to open the browser automatically.
    """
    from .dashboard.app import DashboardApp

    app = DashboardApp(data, row_metadata=row_metadata, col_metadata=col_metadata)
    app.serve(port=port, show=show)


__all__ = [
    "__version__",
    "Heatmap",
    "explore",
    "CategoricalAnnotation",
    "LabelAnnotation",
    "BarChartAnnotation",
    "SparklineAnnotation",
    "BoxPlotAnnotation",
    "ViolinPlotAnnotation",
]
