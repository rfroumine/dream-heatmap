"""DashboardState: centralized reactive state for the dashboard."""

from __future__ import annotations

import json
import traceback
from typing import Any

import param
import numpy as np
import pandas as pd

from ..api import Heatmap
from ..annotation.categorical import CategoricalAnnotation
from ..annotation.minigraph import BarChartAnnotation
from ..layout.annotation_layout import AnnotationLayoutEngine


class DashboardState(param.Parameterized):
    """Centralized reactive state for the dashboard.

    Holds all user-controlled parameters and rebuilds the Heatmap
    object whenever any control param changes. The rebuilt heatmap
    data is pushed to the HeatmapPane for JS rendering.
    """

    # --- Data (set once at init) ---
    data = param.DataFrame(doc="Expression matrix (rows=markers, cols=cells)")
    row_metadata = param.DataFrame(default=None, allow_None=True)
    col_metadata = param.DataFrame(default=None, allow_None=True)

    # --- Color scale ---
    colormap = param.String(default="viridis")
    vmin = param.Number(default=None, allow_None=True)
    vmax = param.Number(default=None, allow_None=True)

    # --- Splits ---
    split_rows_by = param.String(default="")
    split_cols_by = param.String(default="")

    # --- Clustering ---
    cluster_rows = param.Boolean(default=False)
    cluster_cols = param.Boolean(default=False)
    cluster_method = param.String(default="average")
    cluster_metric = param.String(default="euclidean")

    # --- Ordering ---
    order_rows_by = param.String(default="")
    order_cols_by = param.String(default="")

    # --- Labels ---
    row_labels = param.String(default="auto")
    col_labels = param.String(default="auto")

    # --- Annotations (list of config dicts) ---
    annotations = param.List(default=[])

    # --- Selection (set by JS selection bridge) ---
    selected_row_ids = param.List(default=[])
    selected_col_ids = param.List(default=[])

    # --- Chart configs (list of dicts) ---
    chart_configs = param.List(default=[])

    # --- Internal: reference to HeatmapPane (set by app) ---
    _heatmap_pane = param.Parameter(default=None, allow_None=True)

    # --- Internal: last built Heatmap (for selection resolution) ---
    _current_hm = param.Parameter(default=None, allow_None=True)

    def get_row_metadata_columns(self) -> list[str]:
        """Return available row metadata column names."""
        if self.row_metadata is not None:
            return list(self.row_metadata.columns)
        return []

    def get_col_metadata_columns(self) -> list[str]:
        """Return available column metadata column names."""
        if self.col_metadata is not None:
            return list(self.col_metadata.columns)
        return []

    def get_expression_row_names(self) -> list[str]:
        """Return expression matrix row names (markers)."""
        if self.data is not None:
            return list(self.data.index)
        return []

    def get_col_metadata_categorical_columns(self) -> list[str]:
        """Return col metadata columns that are categorical/string."""
        if self.col_metadata is None:
            return []
        return [
            col for col in self.col_metadata.columns
            if self.col_metadata[col].dtype == "object"
            or self.col_metadata[col].dtype.name == "category"
        ]

    def get_col_metadata_numeric_columns(self) -> list[str]:
        """Return col metadata columns that are numeric."""
        if self.col_metadata is None:
            return []
        return [
            col for col in self.col_metadata.columns
            if np.issubdtype(self.col_metadata[col].dtype, np.number)
        ]

    @param.depends(
        "colormap", "vmin", "vmax",
        "split_rows_by", "split_cols_by",
        "cluster_rows", "cluster_cols", "cluster_method", "cluster_metric",
        "order_rows_by", "order_cols_by",
        "row_labels", "col_labels",
        "annotations",
        watch=True,
    )
    def _rebuild_heatmap(self):
        """Rebuild the Heatmap object from current state and push to pane."""
        if self.data is None or self._heatmap_pane is None:
            return

        try:
            hm = Heatmap(self.data)

            # Metadata
            if self.row_metadata is not None:
                hm.set_row_metadata(self.row_metadata)
            if self.col_metadata is not None:
                hm.set_col_metadata(self.col_metadata)

            # Color scale
            hm.set_colormap(self.colormap, vmin=self.vmin, vmax=self.vmax)

            # Splits (empty string = no split)
            if self.split_rows_by:
                hm.split_rows(by=self.split_rows_by)
            if self.split_cols_by:
                hm.split_cols(by=self.split_cols_by)

            # Clustering vs ordering (mutually exclusive per axis)
            if self.cluster_rows:
                hm.cluster_rows(
                    method=self.cluster_method,
                    metric=self.cluster_metric,
                )
            elif self.order_rows_by:
                hm.order_rows(by=self.order_rows_by)

            if self.cluster_cols:
                hm.cluster_cols(
                    method=self.cluster_method,
                    metric=self.cluster_metric,
                )
            elif self.order_cols_by:
                hm.order_cols(by=self.order_cols_by)

            # Annotations
            for ann_cfg in self.annotations:
                annotation = self._build_annotation(ann_cfg)
                if annotation is not None:
                    hm.add_annotation(ann_cfg["edge"], annotation)

            # Labels
            hm.set_label_display(rows=self.row_labels, cols=self.col_labels)

            # Compute layout and push to pane
            hm._compute_layout()
            self._heatmap_pane.set_data(
                matrix=hm._matrix,
                color_scale=hm._color_scale,
                row_mapper=hm._row_mapper,
                col_mapper=hm._col_mapper,
                layout=hm._layout,
                dendrograms=hm._build_dendrogram_data(),
                annotations=hm._build_annotation_data(),
                labels=hm._build_label_data(),
                legends=hm._build_legend_data(),
                color_bar_title=hm._color_bar_title,
            )

            self._current_hm = hm

        except Exception:
            traceback.print_exc()

    def _build_annotation(self, cfg: dict) -> Any:
        """Build an AnnotationTrack from a config dict."""
        ann_type = cfg.get("type", "")
        column = cfg.get("column", "")
        edge = cfg.get("edge", "")

        if not ann_type or not column or not edge:
            return None

        # Determine which metadata to use based on edge
        is_row_edge = edge in ("left", "right")
        metadata = self.row_metadata if is_row_edge else self.col_metadata

        if ann_type == "categorical":
            if metadata is None or column not in metadata.columns:
                return None
            values = metadata[column]
            return CategoricalAnnotation(values, name=column)

        elif ann_type == "bar":
            # For bar charts: use metadata numeric cols or expression row
            if metadata is not None and column in metadata.columns:
                values = metadata[column]
                return BarChartAnnotation(values, name=column)
            # Check expression matrix rows (markers)
            if self.data is not None and column in self.data.index:
                values = self.data.loc[column]
                return BarChartAnnotation(values, name=column)
            return None

        return None

    def update_selection(self, selection_json: str) -> None:
        """Parse selection JSON from JS and update selected IDs."""
        try:
            data = json.loads(selection_json)
            self.selected_row_ids = data.get("row_ids", [])
            self.selected_col_ids = data.get("col_ids", [])
        except (json.JSONDecodeError, TypeError):
            pass

    def handle_zoom(self, zoom_range_json: str) -> None:
        """Handle zoom events from JS. Recomputes layout with zoomed mappers."""
        hm = self._current_hm
        if hm is None or self._heatmap_pane is None:
            return

        try:
            zoom_range = json.loads(zoom_range_json)
        except (json.JSONDecodeError, TypeError):
            return

        try:
            if zoom_range is None:
                # Reset: use original mappers and full matrix
                zoomed_row = hm._row_mapper
                zoomed_col = hm._col_mapper
                zoomed_matrix = hm._matrix
            else:
                zoomed_row = hm._row_mapper.apply_zoom(
                    zoom_range["row_start"], zoom_range["row_end"]
                )
                zoomed_col = hm._col_mapper.apply_zoom(
                    zoom_range["col_start"], zoom_range["col_end"]
                )
                zoomed_matrix = hm._matrix.slice(
                    zoomed_row.visual_order, zoomed_col.visual_order,
                )

            # Recompute layout for zoomed view
            legend_w, legend_h = hm._estimate_legend_dimensions()
            row_lbl_w, col_lbl_h = hm._estimate_label_space(zoomed_row, zoomed_col)
            zoomed_layout = hm._layout_composer.compute(
                zoomed_row,
                zoomed_col,
                has_row_dendro=hm._row_cluster is not None,
                has_col_dendro=hm._col_cluster is not None,
                left_annotation_width=AnnotationLayoutEngine.total_edge_width(
                    hm._annotations["left"]
                ),
                right_annotation_width=AnnotationLayoutEngine.total_edge_width(
                    hm._annotations["right"]
                ),
                top_annotation_height=AnnotationLayoutEngine.total_edge_width(
                    hm._annotations["top"]
                ),
                bottom_annotation_height=AnnotationLayoutEngine.total_edge_width(
                    hm._annotations["bottom"]
                ),
                legend_panel_width=legend_w,
                legend_panel_height=legend_h,
                row_label_width=row_lbl_w,
                col_label_height=col_lbl_h,
            )

            # Rebuild annotations and labels for zoomed mappers
            zoomed_annotations = hm._build_annotation_data(
                row_mapper=zoomed_row, col_mapper=zoomed_col,
            )
            zoomed_labels = hm._build_label_data(
                row_mapper=zoomed_row, col_mapper=zoomed_col,
                layout=zoomed_layout,
            )
            # Dendrograms not meaningful after zoom
            zoomed_dendrograms = None if zoom_range is not None else hm._build_dendrogram_data()

            self._heatmap_pane.set_data(
                matrix=zoomed_matrix,
                color_scale=hm._color_scale,
                row_mapper=zoomed_row,
                col_mapper=zoomed_col,
                layout=zoomed_layout,
                dendrograms=zoomed_dendrograms,
                annotations=zoomed_annotations,
                labels=zoomed_labels,
                legends=hm._build_legend_data(),
                color_bar_title=hm._color_bar_title,
            )
        except Exception:
            traceback.print_exc()

    def trigger_rebuild(self) -> None:
        """Manually trigger a heatmap rebuild."""
        self._rebuild_heatmap()
