"""DashboardState: centralized reactive state for the dashboard."""

from __future__ import annotations

import json
import traceback
from typing import Any

import param
import pandas as pd

from ..api import Heatmap
from ..annotation.categorical import CategoricalAnnotation
from ..annotation.minigraph import BarChartAnnotation
from ..layout.annotation_layout import AnnotationLayoutEngine
from ..display_utils import prettify_name


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

    # --- Value scaling (per-axis) ---
    row_scale_method = param.String(default="none")   # "none", "zscore", "center", "minmax"
    col_scale_method = param.String(default="none")   # "none", "zscore", "center", "minmax"

    # --- Grouping (replaces order_rows_by/order_cols_by) ---
    row_group_by = param.List(default=[])    # 0-2 metadata column names
    col_group_by = param.List(default=[])    # 0-2 metadata column names

    # --- Cluster mode (replaces cluster_rows/cluster_cols booleans) ---
    # "none" | "global" | "within_groups"
    row_cluster_mode = param.String(default="none")
    col_cluster_mode = param.String(default="none")

    # --- Clustering params (shared, synced between axes) ---
    cluster_method = param.String(default="average")
    cluster_metric = param.String(default="euclidean")

    # --- Labels ---
    row_labels = param.String(default="auto")
    col_labels = param.String(default="auto")
    row_label_side = param.String(default="right")
    col_label_side = param.String(default="bottom")

    # --- Dendrogram visibility ---
    show_row_dendro = param.Boolean(default=True)
    show_col_dendro = param.Boolean(default=True)

    # --- Annotations (list of config dicts) ---
    annotations = param.List(default=[])

    # --- Selection (set by JS selection bridge) ---
    selected_row_ids = param.List(default=[])
    selected_col_ids = param.List(default=[])
    selection_label = param.String(default="Selected")

    # --- Chart configs (list of dicts) ---
    chart_configs = param.List(default=[])

    # --- Title & value description ---
    title = param.String(default="")
    value_description = param.String(default="")

    # --- Status text ---
    _status_text = param.String(default="")

    # --- Internal: reference to HeatmapPane (set by app) ---
    _heatmap_pane = param.Parameter(default=None, allow_None=True)

    # --- Internal: last built Heatmap (for selection resolution) ---
    _current_hm = param.Parameter(default=None, allow_None=True)

    def __init__(self, **params):
        super().__init__(**params)
        # Per-axis cluster caches: {cache_key: (cluster_results, mapper)}
        # Multi-entry so switching grouping A→B→A reuses cached results.
        self._row_cluster_cache: dict[tuple, tuple] = {}
        self._col_cluster_cache: dict[tuple, tuple] = {}
        self._MAX_CLUSTER_CACHE = 8

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

    def get_row_metadata_categorical_columns(self) -> list[str]:
        """Return row metadata columns that are categorical/string."""
        if self.row_metadata is None:
            return []
        return [
            col for col in self.row_metadata.columns
            if not pd.api.types.is_numeric_dtype(self.row_metadata[col])
        ]

    def get_row_metadata_numeric_columns(self) -> list[str]:
        """Return row metadata columns that are numeric."""
        if self.row_metadata is None:
            return []
        return [
            col for col in self.row_metadata.columns
            if pd.api.types.is_numeric_dtype(self.row_metadata[col])
        ]

    def get_col_metadata_categorical_columns(self) -> list[str]:
        """Return col metadata columns that are categorical/string."""
        if self.col_metadata is None:
            return []
        return [
            col for col in self.col_metadata.columns
            if not pd.api.types.is_numeric_dtype(self.col_metadata[col])
        ]

    def get_col_metadata_numeric_columns(self) -> list[str]:
        """Return col metadata columns that are numeric."""
        if self.col_metadata is None:
            return []
        return [
            col for col in self.col_metadata.columns
            if pd.api.types.is_numeric_dtype(self.col_metadata[col])
        ]

    @param.depends(
        "colormap", "vmin", "vmax",
        "row_scale_method", "col_scale_method",
        "row_group_by", "col_group_by",
        "row_cluster_mode", "col_cluster_mode",
        "cluster_method", "cluster_metric",
        "row_labels", "col_labels",
        "row_label_side", "col_label_side",
        "show_row_dendro", "show_col_dendro",
        "annotations",
        "title", "value_description",
        watch=True,
    )
    def _rebuild_heatmap(self):
        """Rebuild the Heatmap object from current state and push to pane.

        Follows the 4-step workflow:
        1. Grouping — structural groups via split_rows/split_cols (gap=0 by default)
        2. Clustering — none / global / within_groups
        3. Annotations — add annotation tracks
        4. Splits — visual gaps only for annotations with split=True on grouping vars
        """
        if self.data is None or self._heatmap_pane is None:
            return

        self._heatmap_pane.loading = True
        self._status_text = "Building..."

        try:
            # Apply value scaling (two-pass: row first, then column)
            from ..transform.scaler import apply_scaling

            scaled_data = self.data
            if self.row_scale_method != "none":
                scaled_data = apply_scaling(scaled_data, self.row_scale_method, 1)
            if self.col_scale_method != "none":
                scaled_data = apply_scaling(scaled_data, self.col_scale_method, 0)

            hm = Heatmap(scaled_data)

            # Metadata
            if self.row_metadata is not None:
                hm.set_row_metadata(self.row_metadata)
            if self.col_metadata is not None:
                hm.set_col_metadata(self.col_metadata)

            # Color bar title reflecting scaling
            scale_labels = {
                "none": None,
                "zscore": "Z-score",
                "center": "Centered",
                "minmax": "Min-Max [0,1]",
            }
            row_label = scale_labels.get(self.row_scale_method)
            col_label = scale_labels.get(self.col_scale_method)
            parts = []
            if row_label:
                parts.append(f"{row_label} (row-wise)")
            if col_label:
                parts.append(f"{col_label} (col-wise)")
            color_bar_title = " + ".join(parts) if parts else None

            # Title
            if self.title:
                hm.set_title(self.title)

            # Value description
            if self.value_description:
                hm.set_value_description(self.value_description)

            # Color scale
            hm.set_colormap(
                self.colormap, vmin=self.vmin, vmax=self.vmax,
                color_bar_title=color_bar_title,
            )

            # ── Step 1: Grouping ──
            # Apply structural groups (always, even without visual gaps).
            # Groups create split boundaries that sort data by group values.
            if self.row_group_by:
                by = self.row_group_by if len(self.row_group_by) > 1 else self.row_group_by[0]
                hm.split_rows(by=by)
            if self.col_group_by:
                by = self.col_group_by if len(self.col_group_by) > 1 else self.col_group_by[0]
                hm.split_cols(by=by)

            # ── Step 2: Clustering ──
            # Cache keys include scaling params since scaling affects the matrix
            row_cache_key = (
                tuple(self.row_group_by), self.row_cluster_mode,
                self.cluster_method, self.cluster_metric,
                self.row_scale_method, self.col_scale_method,
            )
            col_cache_key = (
                tuple(self.col_group_by), self.col_cluster_mode,
                self.cluster_method, self.cluster_metric,
                self.row_scale_method, self.col_scale_method,
            )

            if self.row_cluster_mode in ("global", "within_groups"):
                if row_cache_key in self._row_cluster_cache:
                    hm._row_cluster, hm._row_mapper = self._row_cluster_cache[row_cache_key]
                else:
                    self._status_text = "Clustering rows..."
                    hm.cluster_rows(
                        method=self.cluster_method,
                        metric=self.cluster_metric,
                    )
                    self._row_cluster_cache[row_cache_key] = (hm._row_cluster, hm._row_mapper)
                    if len(self._row_cluster_cache) > self._MAX_CLUSTER_CACHE:
                        del self._row_cluster_cache[next(iter(self._row_cluster_cache))]

            if self.col_cluster_mode in ("global", "within_groups"):
                if col_cache_key in self._col_cluster_cache:
                    hm._col_cluster, hm._col_mapper = self._col_cluster_cache[col_cache_key]
                else:
                    self._status_text = "Clustering columns..."
                    hm.cluster_cols(
                        method=self.cluster_method,
                        metric=self.cluster_metric,
                    )
                    self._col_cluster_cache[col_cache_key] = (hm._col_cluster, hm._col_mapper)
                    if len(self._col_cluster_cache) > self._MAX_CLUSTER_CACHE:
                        del self._col_cluster_cache[next(iter(self._col_cluster_cache))]

            # ── Step 3: Annotations ──
            for ann_cfg in self.annotations:
                annotation = self._build_annotation(ann_cfg)
                if annotation is not None:
                    hm.add_annotation(ann_cfg["edge"], annotation)

            # ── Step 4: Visual gaps (splits) ──
            # By default, all group boundaries have gap_size=0 (invisible).
            # Only annotations with split=True on a grouping variable get non-zero gaps.
            row_split_cols = {
                cfg["column"] for cfg in self.annotations
                if cfg.get("split") and cfg["edge"] in ("left", "right")
                and cfg["column"] in self.row_group_by
            }
            col_split_cols = {
                cfg["column"] for cfg in self.annotations
                if cfg.get("split") and cfg["edge"] in ("top", "bottom")
                and cfg["column"] in self.col_group_by
            }

            # Set gap sizes: 0 for non-split boundaries, PRIMARY/SECONDARY for split ones
            if self.row_group_by and hm._row_mapper.gap_positions:
                hm._row_gap_sizes = self._compute_visual_gap_sizes(
                    hm._row_mapper, self.row_group_by, row_split_cols,
                )
            if self.col_group_by and hm._col_mapper.gap_positions:
                hm._col_gap_sizes = self._compute_visual_gap_sizes(
                    hm._col_mapper, self.col_group_by, col_split_cols,
                )

            # Labels (mode + side)
            hm.set_label_display(
                rows=self.row_labels,
                cols=self.col_labels,
                row_side=self.row_label_side,
                col_side=self.col_label_side,
            )

            # Dendrogram visibility flags
            hm._show_row_dendro = self.show_row_dendro
            hm._show_col_dendro = self.show_col_dendro

            # Compute layout and push to pane
            hm._compute_layout()

            # Build original (unscaled) matrix if scaling is active
            is_scaled = (self.row_scale_method != "none" or self.col_scale_method != "none")
            original_matrix = None
            if is_scaled:
                from ..core.matrix import MatrixData as _MD
                original_md = _MD(self.data)
                original_matrix = original_md.slice(
                    hm._row_mapper.visual_order, hm._col_mapper.visual_order,
                )

            # Determine color bar title/subtitle
            cb_title = hm._value_description or hm._color_bar_title
            cb_subtitle = hm._color_bar_title if hm._value_description else None

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
                color_bar_title=cb_title,
                color_bar_subtitle=cb_subtitle,
                title=hm._title,
                original_matrix=original_matrix,
            )

            self._current_hm = hm
            self._status_text = ""

        except Exception as e:
            traceback.print_exc()
            self._status_text = f"Error: {e}"
        finally:
            self._heatmap_pane.loading = False

    @staticmethod
    def _compute_visual_gap_sizes(
        mapper, group_by: list[str], split_cols: set[str],
    ) -> dict[int, float]:
        """Compute per-boundary gap sizes for the 4-step workflow.

        Boundaries whose grouping variable is in split_cols get visible gaps;
        all others get gap_size=0 (invisible structural groups).
        """
        groups = mapper.groups
        if not groups:
            return {}
        gap_sizes: dict[int, float] = {}
        running = 0
        has_two_levels = len(group_by) >= 2
        prev_primary = None

        for group in groups:
            if running > 0:
                # Determine which level this boundary represents
                current_primary = group.name.split("|")[0]
                if has_two_levels and current_primary != prev_primary:
                    # Primary boundary — visible if primary grouping var is a split col
                    if group_by[0] in split_cols:
                        gap_sizes[running] = Heatmap.PRIMARY_GAP_PX
                    else:
                        gap_sizes[running] = 0.0
                elif has_two_levels:
                    # Secondary boundary — visible if secondary grouping var is a split col
                    if group_by[1] in split_cols:
                        gap_sizes[running] = Heatmap.SECONDARY_GAP_PX
                    else:
                        gap_sizes[running] = 0.0
                else:
                    # Single-level grouping — visible if that var is a split col
                    if group_by[0] in split_cols:
                        gap_sizes[running] = Heatmap.PRIMARY_GAP_PX
                    else:
                        gap_sizes[running] = 0.0
            prev_primary = group.name.split("|")[0]
            running += len(group.ids)
        return gap_sizes

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
            return CategoricalAnnotation(name=prettify_name(column), values=values)

        elif ann_type == "bar":
            # For bar charts: use metadata numeric cols or expression row
            if metadata is not None and column in metadata.columns:
                values = metadata[column]
                return BarChartAnnotation(name=prettify_name(column), values=values)
            # Check expression matrix rows (markers)
            if self.data is not None and column in self.data.index:
                values = self.data.loc[column]
                return BarChartAnnotation(name=prettify_name(column), values=values)
            return None

        return None

    def update_selection(self, selection_json: str) -> None:
        """Parse selection JSON from JS and update selected IDs."""
        try:
            data = json.loads(selection_json)
            self.selection_label = data.get("label", "Selected")
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
            elif "row_ids" in zoom_range:
                # ID-based zoom (annotation click): filter to specific IDs
                zoomed_row = hm._row_mapper.apply_zoom_by_ids(zoom_range["row_ids"])
                zoomed_col = hm._col_mapper.apply_zoom_by_ids(zoom_range["col_ids"])
                zoomed_matrix = hm._matrix.slice(
                    zoomed_row.visual_order, zoomed_col.visual_order,
                )
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

            # Remap gap sizes for zoomed coordinate space
            if zoom_range is not None and "row_ids" not in zoom_range:
                zoomed_row_gap_sizes = Heatmap._remap_gap_sizes(
                    hm._row_gap_sizes,
                    zoom_range["row_start"], zoom_range["row_end"],
                )
                zoomed_col_gap_sizes = Heatmap._remap_gap_sizes(
                    hm._col_gap_sizes,
                    zoom_range["col_start"], zoom_range["col_end"],
                )
            elif zoom_range is not None:
                # ID-based zoom: no gap remapping needed
                zoomed_row_gap_sizes = None
                zoomed_col_gap_sizes = None
            else:
                zoomed_row_gap_sizes = hm._row_gap_sizes
                zoomed_col_gap_sizes = hm._col_gap_sizes

            # Recompute layout for zoomed view
            legend_w, legend_h = hm._estimate_legend_dimensions()
            left_lbl_w, right_lbl_w, top_lbl_h, bottom_lbl_h = hm._estimate_label_space(zoomed_row, zoomed_col)
            zoomed_layout = hm._layout_composer.compute(
                zoomed_row,
                zoomed_col,
                has_row_dendro=(hm._row_cluster is not None and hm._show_row_dendro),
                has_col_dendro=(hm._col_cluster is not None and hm._show_col_dendro),
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
                left_label_width=left_lbl_w,
                right_label_width=right_lbl_w,
                top_label_height=top_lbl_h,
                bottom_label_height=bottom_lbl_h,
                row_gap_sizes=zoomed_row_gap_sizes,
                col_gap_sizes=zoomed_col_gap_sizes,
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

            cb_title = hm._value_description or hm._color_bar_title
            cb_subtitle = hm._color_bar_title if hm._value_description else None

            # Build original matrix for zoom view (if scaling active)
            is_scaled = (self.row_scale_method != "none" or self.col_scale_method != "none")
            zoomed_original = None
            if is_scaled:
                from ..core.matrix import MatrixData as _MD
                original_md = _MD(self.data)
                zoomed_original = original_md.slice(
                    zoomed_row.visual_order, zoomed_col.visual_order,
                )

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
                color_bar_title=cb_title,
                color_bar_subtitle=cb_subtitle,
                title=hm._title,
                original_matrix=zoomed_original,
            )
        except Exception:
            traceback.print_exc()

    def trigger_rebuild(self) -> None:
        """Manually trigger a heatmap rebuild."""
        self._rebuild_heatmap()
