"""Mini-graph annotations: bar, sparkline, box, violin plots."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import AnnotationTrack, DEFAULT_TRACK_WIDTH


class BarChartAnnotation(AnnotationTrack):
    """Bar chart showing a numeric value per row/column.

    Usage::

        ann = BarChartAnnotation("expression", metadata["mean_expr"])
        hm.add_annotation("right", ann)
    """

    def __init__(
        self,
        name: str,
        values: pd.Series,
        color: str = "#4e79a7",
        track_width: float = 40.0,
        vmin: float | None = None,
        vmax: float | None = None,
    ) -> None:
        super().__init__(name=name, track_width=track_width)
        self._values = values.copy()
        self._color = color
        finite = values[np.isfinite(values)]
        self._vmin = vmin if vmin is not None else (float(finite.min()) if len(finite) > 0 else 0.0)
        self._vmax = vmax if vmax is not None else (float(finite.max()) if len(finite) > 0 else 1.0)

    @property
    def annotation_type(self) -> str:
        return "bar"

    def get_render_data(self, visual_order: np.ndarray) -> dict:
        bar_values = []
        for item_id in visual_order:
            if item_id in self._values.index:
                v = float(self._values[item_id])
                bar_values.append(v if np.isfinite(v) else 0.0)
            else:
                bar_values.append(0.0)

        return {
            "type": "bar",
            "name": self._name,
            "trackWidth": self._track_width,
            "values": bar_values,
            "color": self._color,
            "vmin": self._vmin,
            "vmax": self._vmax,
        }


class SparklineAnnotation(AnnotationTrack):
    """Sparkline showing a series of values per row/column.

    Each row/col gets a small line chart. The data is a DataFrame
    where each row corresponds to one heatmap row/col ID and columns
    are the sparkline points.

    Usage::

        ann = SparklineAnnotation("trend", trend_df)
        hm.add_annotation("right", ann)
    """

    def __init__(
        self,
        name: str,
        data: pd.DataFrame,
        color: str = "#4e79a7",
        track_width: float = 50.0,
    ) -> None:
        super().__init__(name=name, track_width=track_width)
        self._data = data.copy()
        self._color = color

    @property
    def annotation_type(self) -> str:
        return "sparkline"

    def get_render_data(self, visual_order: np.ndarray) -> dict:
        all_values = self._data.values
        finite = all_values[np.isfinite(all_values)]
        vmin = float(finite.min()) if len(finite) > 0 else 0.0
        vmax = float(finite.max()) if len(finite) > 0 else 1.0

        series_list = []
        for item_id in visual_order:
            if item_id in self._data.index:
                row = self._data.loc[item_id].values.tolist()
                series_list.append([v if np.isfinite(v) else None for v in row])
            else:
                series_list.append([])

        return {
            "type": "sparkline",
            "name": self._name,
            "trackWidth": self._track_width,
            "series": series_list,
            "color": self._color,
            "vmin": vmin,
            "vmax": vmax,
        }


class BoxPlotAnnotation(AnnotationTrack):
    """Box plot showing distribution per row/column.

    Each row/col gets a mini box plot. Provide a DataFrame where
    each row's values form the distribution.

    Usage::

        ann = BoxPlotAnnotation("distribution", replicate_df)
        hm.add_annotation("right", ann)
    """

    def __init__(
        self,
        name: str,
        data: pd.DataFrame,
        color: str = "#4e79a7",
        track_width: float = 40.0,
    ) -> None:
        super().__init__(name=name, track_width=track_width)
        self._data = data.copy()
        self._color = color

    @property
    def annotation_type(self) -> str:
        return "boxplot"

    def get_render_data(self, visual_order: np.ndarray) -> dict:
        all_values = self._data.values
        finite = all_values[np.isfinite(all_values)]
        vmin = float(finite.min()) if len(finite) > 0 else 0.0
        vmax = float(finite.max()) if len(finite) > 0 else 1.0

        stats_list = []
        for item_id in visual_order:
            if item_id in self._data.index:
                row = self._data.loc[item_id].dropna().values
                if len(row) > 0:
                    stats_list.append({
                        "min": float(np.min(row)),
                        "q1": float(np.percentile(row, 25)),
                        "median": float(np.median(row)),
                        "q3": float(np.percentile(row, 75)),
                        "max": float(np.max(row)),
                    })
                else:
                    stats_list.append(None)
            else:
                stats_list.append(None)

        return {
            "type": "boxplot",
            "name": self._name,
            "trackWidth": self._track_width,
            "stats": stats_list,
            "color": self._color,
            "vmin": vmin,
            "vmax": vmax,
        }


class ViolinPlotAnnotation(AnnotationTrack):
    """Violin plot showing distribution per row/column.

    Similar to BoxPlot but rendered as a density shape.

    Usage::

        ann = ViolinPlotAnnotation("density", replicate_df)
        hm.add_annotation("right", ann)
    """

    def __init__(
        self,
        name: str,
        data: pd.DataFrame,
        color: str = "#4e79a7",
        track_width: float = 40.0,
        n_bins: int = 20,
    ) -> None:
        super().__init__(name=name, track_width=track_width)
        self._data = data.copy()
        self._color = color
        self._n_bins = n_bins

    @property
    def annotation_type(self) -> str:
        return "violin"

    def get_render_data(self, visual_order: np.ndarray) -> dict:
        all_values = self._data.values
        finite = all_values[np.isfinite(all_values)]
        vmin = float(finite.min()) if len(finite) > 0 else 0.0
        vmax = float(finite.max()) if len(finite) > 0 else 1.0

        density_list = []
        for item_id in visual_order:
            if item_id in self._data.index:
                row = self._data.loc[item_id].dropna().values
                if len(row) >= 2:
                    counts, edges = np.histogram(row, bins=self._n_bins, range=(vmin, vmax))
                    # Normalize to [0, 1]
                    max_count = counts.max()
                    if max_count > 0:
                        normed = (counts / max_count).tolist()
                    else:
                        normed = [0.0] * self._n_bins
                    centers = ((edges[:-1] + edges[1:]) / 2).tolist()
                    density_list.append({"counts": normed, "centers": centers})
                else:
                    density_list.append(None)
            else:
                density_list.append(None)

        return {
            "type": "violin",
            "name": self._name,
            "trackWidth": self._track_width,
            "densities": density_list,
            "color": self._color,
            "vmin": vmin,
            "vmax": vmax,
        }
