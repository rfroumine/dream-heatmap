"""SidebarControls: Panel widgets for configuring the heatmap."""

from __future__ import annotations

import param
import panel as pn

from .state import DashboardState
from .code_export import generate_code

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .chart_panel import ChartPanelManager


# Colormaps relevant for bioinformatics heatmaps
COLORMAP_OPTIONS = [
    "viridis", "plasma", "inferno", "magma", "cividis",
    "hot", "YlOrRd", "YlGnBu", "Blues", "Reds", "Greens", "Purples",
    "RdBu_r", "coolwarm", "bwr", "seismic", "RdYlBu_r", "PiYG", "Spectral",
]

CLUSTER_METHODS = [
    "single", "complete", "average", "weighted",
    "centroid", "median", "ward",
]

CLUSTER_METRICS = [
    "euclidean", "correlation", "cosine", "cityblock",
]

ANNOTATION_AXES = ["Rows", "Columns"]
ANNOTATION_STYLES = ["Color track", "Bar chart"]
ANNOTATION_POSITIONS = ["Before", "After"]

# ---------------------------------------------------------------------------
# Shopify-inspired Card shadow-DOM CSS
# ---------------------------------------------------------------------------

_CARD_SHADOW_CSS = """
/* Hide default chevron toggle */
.card-button { display: none; }

/* Transparent card — no border, no shadow */
:host {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* Header row: rounded, hover highlight */
.card-header {
  border-radius: 8px;
  transition: background-color 0.12s ease;
  cursor: pointer;
  padding: 6px 10px;
}
.card-header:hover {
  background-color: #f6f6f7;
}

/* Card body padding */
.card-body, .card {
  padding: 4px 14px 12px 14px;
}
"""

# ---------------------------------------------------------------------------
# Section icons — monoline SVGs (20x20 viewBox, stroke-based)
# ---------------------------------------------------------------------------

_SECTION_ICONS = {
    "color": (  # paint palette
        '<circle cx="10" cy="10" r="8" fill="none"/>'
        '<circle cx="7" cy="7" r="1.2" fill="#637381" stroke="none"/>'
        '<circle cx="11" cy="6" r="1.2" fill="#637381" stroke="none"/>'
        '<circle cx="14" cy="9" r="1.2" fill="#637381" stroke="none"/>'
        '<circle cx="7" cy="11" r="1.2" fill="#637381" stroke="none"/>'
    ),
    "labels": (  # three horizontal lines (decreasing width)
        '<line x1="3" y1="6" x2="17" y2="6"/>'
        '<line x1="3" y1="10" x2="14" y2="10"/>'
        '<line x1="3" y1="14" x2="11" y2="14"/>'
    ),
    "annotations": (  # tag
        '<path d="M3 3h7l7 7-7 7-7-7V3z" fill="none"/>'
        '<circle cx="7.5" cy="7.5" r="1.5" fill="#637381" stroke="none"/>'
    ),
    "ordering": (  # up/down arrows
        '<polyline points="6,8 10,3 14,8" fill="none"/>'
        '<polyline points="6,12 10,17 14,12" fill="none"/>'
    ),
    "charts": (  # bar chart
        '<rect x="3" y="10" width="3" height="7" rx="0.5" fill="none"/>'
        '<rect x="8.5" y="6" width="3" height="11" rx="0.5" fill="none"/>'
        '<rect x="14" y="3" width="3" height="14" rx="0.5" fill="none"/>'
    ),
}


def _make_section_card(
    title: str,
    content,
    icon_key: str,
    collapsed: bool = True,
) -> pn.Card:
    """Build a Shopify-style collapsible section card."""
    svg_path = _SECTION_ICONS.get(icon_key, "")
    icon_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" '
        f'viewBox="0 0 20 20" fill="none" stroke="#637381" stroke-width="1.5" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'style="flex-shrink:0">{svg_path}</svg>'
    )
    header_html = (
        f'<div style="display:flex;align-items:center;gap:8px">'
        f'{icon_svg}'
        f'<span style="font-size:13px;font-weight:500;color:#202223">{title}</span>'
        f'</div>'
    )
    header = pn.pane.HTML(header_html, sizing_mode="stretch_width", margin=0)
    return pn.Card(
        content,
        header=header,
        stylesheets=[_CARD_SHADOW_CSS],
        active_header_background="#f4f5f8",
        header_background="#ffffff",
        collapsed=collapsed,
        margin=0,
        sizing_mode="stretch_width",
    )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _build_grouping_options(meta_cols: list[str]) -> dict[str, str]:
    """Build options for a grouping dropdown: None + metadata columns."""
    opts = {"None": ""}
    for col in meta_cols:
        opts[col] = col
    return opts


def _build_secondary_grouping_options(
    meta_cols: list[str], exclude: str = "",
) -> dict[str, str]:
    """Build options for secondary grouping, excluding the primary selection."""
    opts = {"None": ""}
    for col in meta_cols:
        if col != exclude:
            opts[col] = col
    return opts


class SidebarControls:
    """Builds and manages the sidebar Panel widgets.

    Implements a 4-step workflow:
    1. Grouping (per-axis, in tabs) — structural groups
    2. Clustering (per-axis, in tabs) — within or global
    3. Annotations (shared) — add/remove annotation tracks
    4. Splits (shared) — visual gaps for grouping-column annotations

    Links widgets to DashboardState params so changes automatically
    trigger heatmap rebuilds.
    """

    def __init__(
        self,
        state: DashboardState,
        chart_manager: ChartPanelManager | None = None,
    ) -> None:
        self.state = state
        self.chart_manager = chart_manager
        self._syncing = False  # Guard flag: suppresses widget->state callbacks
        self._annotation_list_col = pn.Column(sizing_mode="stretch_width")
        self._code_display = pn.pane.Markdown("", sizing_mode="stretch_width")
        self._build_widgets()

    def _build_widgets(self) -> None:
        """Create all sidebar widgets."""
        s = self.state

        row_meta_cols = s.get_row_metadata_columns() if s.row_metadata is not None else []
        col_meta_cols = s.get_col_metadata_columns() if s.col_metadata is not None else []

        # --- Color scale section ---
        self.colormap_select = pn.widgets.Select(
            name="Colormap", value=s.colormap,
            options=COLORMAP_OPTIONS, sizing_mode="stretch_width",
        )
        self.vmin_input = pn.widgets.FloatInput(
            name="Min value", value=s.vmin,
            step=0.1, sizing_mode="stretch_width",
        )
        self.vmax_input = pn.widgets.FloatInput(
            name="Max value", value=s.vmax,
            step=0.1, sizing_mode="stretch_width",
        )

        # --- Per-axis scaling (single method, pick axis) ---
        _scale_options = {
            "None": "none",
            "Center & Scale (z-score)": "zscore",
            "Center only": "center",
            "Min-Max [0,1]": "minmax",
        }
        # Derive initial values from state
        if s.row_scale_method != "none":
            _init_method = s.row_scale_method
            _init_axis = "Rows"
        elif s.col_scale_method != "none":
            _init_method = s.col_scale_method
            _init_axis = "Columns"
        else:
            _init_method = "none"
            _init_axis = "Rows"

        self.scale_method_select = pn.widgets.Select(
            name="Scale method", value=_init_method,
            options=_scale_options, sizing_mode="stretch_width",
        )
        self.scale_axis_select = pn.widgets.Select(
            name="Apply", value=_init_axis,
            options={"Row-wise": "Rows", "Column-wise": "Columns"},
            visible=(_init_method != "none"),
            sizing_mode="stretch_width",
        )

        # Populate vmin/vmax with actual data range if not set
        if s.vmin is None or s.vmax is None:
            self._update_color_range_for_scaling()

        # --- Labels section ---
        self.row_labels_select = pn.widgets.Select(
            name="Rows", value=s.row_labels,
            options={"All": "all", "Auto": "auto", "None": "none"},
            sizing_mode="stretch_width",
        )
        self.col_labels_select = pn.widgets.Select(
            name="Columns", value=s.col_labels,
            options={"All": "all", "Auto": "auto", "None": "none"},
            sizing_mode="stretch_width",
        )
        self.row_label_side_select = pn.widgets.Select(
            name="Side", value=s.row_label_side,
            options={"Left": "left", "Right": "right"},
            sizing_mode="stretch_width",
            visible=(s.row_labels != "none"),
        )
        self.col_label_side_select = pn.widgets.Select(
            name="Side", value=s.col_label_side,
            options={"Top": "top", "Bottom": "bottom"},
            sizing_mode="stretch_width",
            visible=(s.col_labels != "none"),
        )

        # ── Step 1+2: Grouping & Clustering (per-axis, in tabs) ──

        # ROW grouping
        row_primary_init = s.row_group_by[0] if len(s.row_group_by) >= 1 else ""
        row_secondary_init = s.row_group_by[1] if len(s.row_group_by) >= 2 else ""

        self.row_group_primary = pn.widgets.Select(
            name="Primary", value=row_primary_init,
            options=_build_grouping_options(row_meta_cols),
            sizing_mode="stretch_width",
            disabled=(s.row_metadata is None),
        )
        self.row_group_secondary = pn.widgets.Select(
            name="Secondary", value=row_secondary_init,
            options=_build_secondary_grouping_options(row_meta_cols, exclude=row_primary_init),
            visible=bool(row_primary_init),
            sizing_mode="stretch_width",
        )

        # ROW clustering
        row_cluster_options = self._cluster_options_for(s.row_group_by)
        self.row_cluster_mode = pn.widgets.RadioButtonGroup(
            name="Clustering", value=s.row_cluster_mode,
            options=row_cluster_options,
            sizing_mode="stretch_width",
        )
        is_row_clustering = s.row_cluster_mode != "none"
        self.row_cluster_method_select = pn.widgets.Select(
            name="Method", value=s.cluster_method,
            options=CLUSTER_METHODS,
            visible=is_row_clustering,
            sizing_mode="stretch_width",
        )
        self.row_cluster_metric_select = pn.widgets.Select(
            name="Metric", value=s.cluster_metric,
            options=CLUSTER_METRICS,
            visible=is_row_clustering,
            sizing_mode="stretch_width",
        )
        self.show_row_dendro_toggle = pn.widgets.Checkbox(
            name="Show dendrogram", value=s.show_row_dendro,
            visible=is_row_clustering,
        )

        # COL grouping
        col_primary_init = s.col_group_by[0] if len(s.col_group_by) >= 1 else ""
        col_secondary_init = s.col_group_by[1] if len(s.col_group_by) >= 2 else ""

        self.col_group_primary = pn.widgets.Select(
            name="Primary", value=col_primary_init,
            options=_build_grouping_options(col_meta_cols),
            sizing_mode="stretch_width",
            disabled=(s.col_metadata is None),
        )
        self.col_group_secondary = pn.widgets.Select(
            name="Secondary", value=col_secondary_init,
            options=_build_secondary_grouping_options(col_meta_cols, exclude=col_primary_init),
            visible=bool(col_primary_init),
            sizing_mode="stretch_width",
        )

        # COL clustering
        col_cluster_options = self._cluster_options_for(s.col_group_by)
        self.col_cluster_mode = pn.widgets.RadioButtonGroup(
            name="Clustering", value=s.col_cluster_mode,
            options=col_cluster_options,
            sizing_mode="stretch_width",
        )
        is_col_clustering = s.col_cluster_mode != "none"
        self.col_cluster_method_select = pn.widgets.Select(
            name="Method", value=s.cluster_method,
            options=CLUSTER_METHODS,
            visible=is_col_clustering,
            sizing_mode="stretch_width",
        )
        self.col_cluster_metric_select = pn.widgets.Select(
            name="Metric", value=s.cluster_metric,
            options=CLUSTER_METRICS,
            visible=is_col_clustering,
            sizing_mode="stretch_width",
        )
        self.show_col_dendro_toggle = pn.widgets.Checkbox(
            name="Show dendrogram", value=s.show_col_dendro,
            visible=is_col_clustering,
        )

        # ── Step 3: Annotation builder ──
        self.ann_axis_select = pn.widgets.Select(
            name="Axis", options=ANNOTATION_AXES,
            value=ANNOTATION_AXES[0],
            sizing_mode="stretch_width",
        )
        ann_col_options = self._get_annotation_columns()
        self.ann_column_select = pn.widgets.Select(
            name="Column", options=ann_col_options,
            value=ann_col_options[0] if ann_col_options else "",
            sizing_mode="stretch_width",
        )
        self.ann_style_select = pn.widgets.Select(
            name="Type", options=ANNOTATION_STYLES,
            value=ANNOTATION_STYLES[0],
            sizing_mode="stretch_width",
        )
        self.ann_position_select = pn.widgets.Select(
            name="Position", options=ANNOTATION_POSITIONS,
            value=ANNOTATION_POSITIONS[0],
            sizing_mode="stretch_width",
        )
        self.ann_add_button = pn.widgets.Button(
            name="Add annotation", button_type="primary",
            sizing_mode="stretch_width",
        )

        # --- Export button ---
        self.export_button = pn.widgets.Button(
            name="Export as Code",
            button_type="success",
            sizing_mode="stretch_width",
        )
        self.export_button.on_click(self._on_export_code)

        # --- Status text ---
        self.status_text = pn.pane.Markdown(
            "", styles={"color": "#6b7280", "font-size": "11px", "font-style": "italic"},
            sizing_mode="stretch_width",
        )

        # Wire up widget -> state bindings
        self._wire_bindings()

        # Wire annotation builder
        self.ann_add_button.on_click(self._on_add_annotation)
        self.ann_axis_select.param.watch(
            lambda e: self._update_annotation_columns(e.new), "value",
        )
        self.ann_column_select.param.watch(
            lambda e: self._auto_detect_style(), "value",
        )

        # Build initial annotation list
        self._refresh_annotation_list()

    # --- Static helpers ---

    @staticmethod
    def _cluster_options_for(group_by: list[str]) -> dict[str, str]:
        """Return clustering radio options based on whether groups exist."""
        if group_by:
            return {"None": "none", "Within groups": "within_groups"}
        return {"None": "none", "Global": "global"}

    def _set_state(self, attr: str, value) -> None:
        """Set state param only if not in a programmatic sync."""
        if not self._syncing:
            setattr(self.state, attr, value)

    def _wire_bindings(self) -> None:
        """Link widget values to DashboardState params."""
        s = self.state

        # Color scale
        self.colormap_select.param.watch(
            lambda e: self._set_state("colormap", e.new), "value",
        )
        self.vmin_input.param.watch(
            lambda e: self._set_state("vmin", e.new), "value",
        )
        self.vmax_input.param.watch(
            lambda e: self._set_state("vmax", e.new), "value",
        )

        # Per-axis scaling (single method + axis toggle)
        self.scale_method_select.param.watch(self._on_scaling_changed, "value")
        self.scale_axis_select.param.watch(self._on_scaling_changed, "value")

        # Labels
        self.row_labels_select.param.watch(
            lambda e: self._set_state("row_labels", e.new), "value",
        )
        self.col_labels_select.param.watch(
            lambda e: self._set_state("col_labels", e.new), "value",
        )
        self.row_label_side_select.param.watch(
            lambda e: self._set_state("row_label_side", e.new), "value",
        )
        self.col_label_side_select.param.watch(
            lambda e: self._set_state("col_label_side", e.new), "value",
        )
        self.row_labels_select.param.watch(
            lambda e: setattr(self.row_label_side_select, "visible", e.new != "none"), "value",
        )
        self.col_labels_select.param.watch(
            lambda e: setattr(self.col_label_side_select, "visible", e.new != "none"), "value",
        )

        # Row grouping
        self.row_group_primary.param.watch(self._on_row_grouping_changed, "value")
        self.row_group_secondary.param.watch(self._on_row_grouping_changed, "value")

        # Row clustering
        self.row_cluster_mode.param.watch(self._on_row_cluster_mode_changed, "value")
        self.row_cluster_method_select.param.watch(
            lambda e: self._on_cluster_param_changed("cluster_method", e.new), "value",
        )
        self.row_cluster_metric_select.param.watch(
            lambda e: self._on_cluster_param_changed("cluster_metric", e.new), "value",
        )
        self.show_row_dendro_toggle.param.watch(
            lambda e: self._set_state("show_row_dendro", e.new), "value",
        )

        # Col grouping
        self.col_group_primary.param.watch(self._on_col_grouping_changed, "value")
        self.col_group_secondary.param.watch(self._on_col_grouping_changed, "value")

        # Col clustering
        self.col_cluster_mode.param.watch(self._on_col_cluster_mode_changed, "value")
        self.col_cluster_method_select.param.watch(
            lambda e: self._on_cluster_param_changed("cluster_method", e.new), "value",
        )
        self.col_cluster_metric_select.param.watch(
            lambda e: self._on_cluster_param_changed("cluster_metric", e.new), "value",
        )
        self.show_col_dendro_toggle.param.watch(
            lambda e: self._set_state("show_col_dendro", e.new), "value",
        )

        # Status text: watch state._status_text and update the pane
        s.param.watch(
            lambda e: setattr(self.status_text, "object", e.new), "_status_text",
        )

    # --- Scaling change handlers ---

    def _on_scaling_changed(self, event) -> None:
        """Handle per-axis scaling change -- single batched rebuild."""
        method = self.scale_method_select.value
        axis = self.scale_axis_select.value

        # Show/hide axis toggle based on whether a method is selected
        self.scale_axis_select.visible = (method != "none")

        if method == "none":
            row_method, col_method = "none", "none"
        elif axis == "Rows":
            row_method, col_method = method, "none"
        else:
            row_method, col_method = "none", method

        new_vmin, new_vmax = self._compute_scaled_range(row_method, col_method)

        # Update widgets under guard so their watch callbacks don't fire
        self._syncing = True
        try:
            self.vmin_input.value = new_vmin
            self.vmax_input.value = new_vmax
        finally:
            self._syncing = False

        # Single atomic state update -> one rebuild with correct values
        self.state.param.update(
            row_scale_method=row_method,
            col_scale_method=col_method,
            vmin=new_vmin,
            vmax=new_vmax,
        )

    def _compute_scaled_range(
        self, row_method: str, col_method: str,
    ) -> tuple[float, float]:
        """Compute vmin/vmax from the (possibly scaled) data — two-pass."""
        import numpy as np
        from ..transform.scaler import apply_scaling

        s = self.state
        if s.data is None:
            return (0.0, 1.0)
        scaled = s.data
        if row_method != "none":
            scaled = apply_scaling(scaled, row_method, 1)
        if col_method != "none":
            scaled = apply_scaling(scaled, col_method, 0)
        finite = scaled.values[np.isfinite(scaled.values)]
        if len(finite) > 0:
            return (float(np.round(finite.min(), 2)), float(np.round(finite.max(), 2)))
        return (0.0, 1.0)

    def _update_color_range_for_scaling(self) -> None:
        """Set vmin/vmax widgets from current state. Used at init before watches exist."""
        method = self.scale_method_select.value
        axis = self.scale_axis_select.value
        if method == "none":
            row_m, col_m = "none", "none"
        elif axis == "Rows":
            row_m, col_m = method, "none"
        else:
            row_m, col_m = "none", method
        new_vmin, new_vmax = self._compute_scaled_range(row_m, col_m)
        self.vmin_input.value = new_vmin
        self.vmax_input.value = new_vmax

    # --- Grouping change handlers ---

    def _collect_group_by(self, primary_widget, secondary_widget) -> list[str]:
        """Collect the current group_by list from the primary + secondary widgets."""
        result = []
        if primary_widget.value:
            result.append(primary_widget.value)
        if secondary_widget.visible and secondary_widget.value:
            result.append(secondary_widget.value)
        return result

    def _on_row_grouping_changed(self, event) -> None:
        """Handle row grouping primary or secondary change."""
        if self._syncing:
            return

        primary = self.row_group_primary.value

        # Show/hide secondary based on primary
        self._syncing = True
        try:
            if primary:
                row_meta_cols = self.state.get_row_metadata_columns()
                self.row_group_secondary.param.update(
                    options=_build_secondary_grouping_options(row_meta_cols, exclude=primary),
                    visible=True,
                )
            else:
                self.row_group_secondary.param.update(value="", visible=False)
        finally:
            self._syncing = False

        new_group_by = self._collect_group_by(self.row_group_primary, self.row_group_secondary)

        # Update cluster mode options (dynamic based on groups)
        new_cluster_opts = self._cluster_options_for(new_group_by)
        self._syncing = True
        try:
            self.row_cluster_mode.param.update(options=new_cluster_opts, value="none")
            self.row_cluster_method_select.visible = False
            self.row_cluster_metric_select.visible = False
            self.show_row_dendro_toggle.visible = False
        finally:
            self._syncing = False

        # Remove stale auto-annotations, then add new ones
        self._remove_auto_annotations_for_axis("row")
        self._auto_add_grouping_annotations("row", new_group_by)

        # Clear splits for row axis annotations that no longer match grouping
        self._clear_stale_splits_for_axis("row", new_group_by)

        # Atomic state update: grouping + clustering reset
        self.state.param.update(
            row_group_by=new_group_by,
            row_cluster_mode="none",
        )
        self._refresh_annotation_list()

    def _on_col_grouping_changed(self, event) -> None:
        """Handle col grouping primary or secondary change."""
        if self._syncing:
            return

        primary = self.col_group_primary.value

        # Show/hide secondary based on primary
        self._syncing = True
        try:
            if primary:
                col_meta_cols = self.state.get_col_metadata_columns()
                self.col_group_secondary.param.update(
                    options=_build_secondary_grouping_options(col_meta_cols, exclude=primary),
                    visible=True,
                )
            else:
                self.col_group_secondary.param.update(value="", visible=False)
        finally:
            self._syncing = False

        new_group_by = self._collect_group_by(self.col_group_primary, self.col_group_secondary)

        # Update cluster mode options (dynamic based on groups)
        new_cluster_opts = self._cluster_options_for(new_group_by)
        self._syncing = True
        try:
            self.col_cluster_mode.param.update(options=new_cluster_opts, value="none")
            self.col_cluster_method_select.visible = False
            self.col_cluster_metric_select.visible = False
            self.show_col_dendro_toggle.visible = False
        finally:
            self._syncing = False

        # Remove stale auto-annotations, then add new ones
        self._remove_auto_annotations_for_axis("col")
        self._auto_add_grouping_annotations("col", new_group_by)

        # Clear splits for col axis annotations that no longer match grouping
        self._clear_stale_splits_for_axis("col", new_group_by)

        # Atomic state update: grouping + clustering reset
        self.state.param.update(
            col_group_by=new_group_by,
            col_cluster_mode="none",
        )
        self._refresh_annotation_list()

    def _remove_auto_annotations_for_axis(self, axis: str) -> None:
        """Remove all auto-added annotations for the given axis.

        Parameters
        ----------
        axis : str
            ``"row"`` or ``"col"``.
        """
        row_edges = ("left", "right")
        col_edges = ("top", "bottom")
        target_edges = row_edges if axis == "row" else col_edges

        filtered = [
            cfg for cfg in self.state.annotations
            if not (cfg.get("auto") and cfg["edge"] in target_edges)
        ]
        if len(filtered) != len(self.state.annotations):
            self.state.annotations = filtered
            self._refresh_annotation_list()

    def _auto_add_grouping_annotations(self, axis: str, group_by: list[str]) -> None:
        """Auto-add categorical annotations for grouping columns if not already present.

        Parameters
        ----------
        axis : str
            ``"row"`` or ``"col"``.
        group_by : list[str]
            Current grouping columns for this axis.
        """
        if not group_by:
            return

        row_edges = ("left", "right")
        col_edges = ("top", "bottom")
        target_edges = row_edges if axis == "row" else col_edges
        default_edge = "left" if axis == "row" else "top"

        # Collect columns already annotated on this axis
        existing_cols = {
            cfg["column"]
            for cfg in self.state.annotations
            if cfg["edge"] in target_edges
        }

        new_anns = []
        for col in reversed(group_by):
            if col not in existing_cols:
                new_anns.append({
                    "type": "categorical",
                    "edge": default_edge,
                    "column": col,
                    "name": col,
                    "auto": True,
                })

        if new_anns:
            self.state.annotations = self.state.annotations + new_anns
            self._refresh_annotation_list()

    def _clear_stale_splits_for_axis(self, axis: str, new_group_by: list[str]) -> None:
        """Remove split=True from annotations whose column is not in new_group_by."""
        row_edges = ("left", "right")
        col_edges = ("top", "bottom")
        target_edges = row_edges if axis == "row" else col_edges

        anns = list(self.state.annotations)
        changed = False
        for i, cfg in enumerate(anns):
            if cfg.get("split") and cfg["edge"] in target_edges:
                if cfg["column"] not in new_group_by:
                    anns[i] = {**cfg, "split": False}
                    changed = True
        if changed:
            self.state.annotations = anns

    # --- Clustering change handlers ---

    def _on_row_cluster_mode_changed(self, event) -> None:
        if self._syncing:
            return
        mode = event.new
        is_clustering = mode != "none"
        self.row_cluster_method_select.visible = is_clustering
        self.row_cluster_metric_select.visible = is_clustering
        self.show_row_dendro_toggle.visible = is_clustering
        self._set_state("row_cluster_mode", mode)

    def _on_col_cluster_mode_changed(self, event) -> None:
        if self._syncing:
            return
        mode = event.new
        is_clustering = mode != "none"
        self.col_cluster_method_select.visible = is_clustering
        self.col_cluster_metric_select.visible = is_clustering
        self.show_col_dendro_toggle.visible = is_clustering
        self._set_state("col_cluster_mode", mode)

    def _on_cluster_param_changed(self, param_name: str, value: str) -> None:
        """Handle cluster method/metric change — synced between axes."""
        if self._syncing:
            return
        self._syncing = True
        try:
            # Sync the other axis's widget
            if param_name == "cluster_method":
                self.row_cluster_method_select.value = value
                self.col_cluster_method_select.value = value
            elif param_name == "cluster_metric":
                self.row_cluster_metric_select.value = value
                self.col_cluster_metric_select.value = value
        finally:
            self._syncing = False
        self._set_state(param_name, value)

    # --- Annotation helpers ---

    def _get_annotation_columns(self, axis: str | None = None) -> list[str]:
        """Get available metadata columns for the selected axis."""
        if axis is None:
            ann_axis = getattr(self, "ann_axis_select", None)
            if ann_axis is None:
                return []
            axis = ann_axis.value

        s = self.state
        if axis == "Rows":
            return s.get_row_metadata_columns()
        else:
            return s.get_col_metadata_columns()

    def _update_annotation_columns(self, axis: str | None = None) -> None:
        """Update the annotation column dropdown when axis changes."""
        new_options = self._get_annotation_columns(axis)
        new_value = new_options[0] if new_options else ""
        self.ann_column_select.param.update(options=new_options, value=new_value)

    def _auto_detect_style(self) -> None:
        """Auto-detect style (Color track vs Bar chart) from column dtype."""
        column = self.ann_column_select.value
        if not column:
            return

        is_rows = self.ann_axis_select.value == "Rows"
        s = self.state
        metadata = s.row_metadata if is_rows else s.col_metadata
        if metadata is None or column not in metadata.columns:
            return

        import pandas as pd
        if pd.api.types.is_numeric_dtype(metadata[column]):
            self.ann_style_select.value = "Bar chart"
        else:
            self.ann_style_select.value = "Color track"

    def _on_add_annotation(self, event) -> None:
        """Handle the Add annotation button click."""
        column = self.ann_column_select.value
        if not column:
            return

        # Map axis + position to edge
        is_rows = self.ann_axis_select.value == "Rows"
        is_before = self.ann_position_select.value == "Before"
        if is_rows:
            edge = "left" if is_before else "right"
        else:
            edge = "top" if is_before else "bottom"

        # Guard: max 3 annotations per edge
        edge_count = sum(1 for a in self.state.annotations if a["edge"] == edge)
        if edge_count >= 3:
            return

        # Map style to internal type
        style = self.ann_style_select.value
        ann_type = "categorical" if style == "Color track" else "bar"

        cfg = {
            "type": ann_type,
            "edge": edge,
            "column": column,
            "name": column,
        }
        # Append to the annotations list (trigger param update)
        self.state.annotations = self.state.annotations + [cfg]
        self._refresh_annotation_list()

    def _on_remove_annotation(self, index: int) -> None:
        """Remove an annotation by index."""
        anns = list(self.state.annotations)
        if 0 <= index < len(anns):
            anns.pop(index)
            self.state.annotations = anns
            self._refresh_annotation_list()

    # --- Export ---

    def _on_export_code(self, event) -> None:
        """Generate code from current state and show it in a modal."""
        code = generate_code(self.state)
        # Update the code display pane with syntax-highlighted markdown
        self._code_display.object = f"```python\n{code}\n```"
        # Copy to clipboard via JS
        escaped = code.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        js = f"navigator.clipboard.writeText(`{escaped}`)"
        try:
            pn.state.execute(js)
        except Exception:
            pass  # clipboard may not be available in all contexts
        # Open the modal
        self._template.open_modal()

    def set_template(self, template: pn.template.MaterialTemplate) -> None:
        """Set reference to the template so we can open its modal."""
        self._template = template

    def build_modal_content(self) -> list:
        """Return content to place inside the template modal."""
        copy_btn = pn.widgets.Button(
            name="Copy to Clipboard",
            button_type="primary",
            sizing_mode="stretch_width",
        )
        copy_btn.on_click(self._on_copy_clipboard)
        return [
            pn.pane.Markdown("## Export as Code", margin=(0, 0, 5, 0)),
            pn.pane.Markdown(
                "*Copied to clipboard! Paste into a notebook or script.*",
                styles={"color": "#6b7280", "font-size": "12px"},
                margin=(0, 0, 10, 0),
            ),
            self._code_display,
            copy_btn,
        ]

    def _on_copy_clipboard(self, event) -> None:
        """Copy the current code to clipboard again."""
        code = generate_code(self.state)
        escaped = code.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        js = f"navigator.clipboard.writeText(`{escaped}`)"
        try:
            pn.state.execute(js)
        except Exception:
            pass

    # --- Step 4: Splits ---

    def _on_split_toggled(self, idx: int, new_value: bool) -> None:
        """Handle split toggle on an annotation card."""
        anns = list(self.state.annotations)
        anns[idx] = {**anns[idx], "split": new_value}
        self.state.annotations = anns  # triggers heatmap rebuild via param
        self._refresh_annotation_list()  # re-render cards with updated button states

    def _is_split_eligible(self, cfg: dict) -> bool:
        """Check if annotation's column matches a grouping variable on its axis."""
        edge = cfg["edge"]
        col = cfg["column"]
        if edge in ("left", "right"):
            return col in set(self.state.row_group_by)
        elif edge in ("top", "bottom"):
            return col in set(self.state.col_group_by)
        return False

    def _count_splits_for_axis(self, edge: str) -> int:
        """Count how many annotations have split=True for the same axis as edge."""
        row_edges = ("left", "right")
        col_edges = ("top", "bottom")
        target = row_edges if edge in row_edges else col_edges
        return sum(
            1 for cfg in self.state.annotations
            if cfg.get("split") and cfg["edge"] in target
        )

    def _refresh_annotation_list(self) -> None:
        """Rebuild the annotation list display with inline split toggles and grouping badges."""
        import html as _html

        anns = self.state.annotations
        if not anns:
            self._annotation_list_col.objects = [
                pn.pane.Str(
                    "No annotations added yet.",
                    styles={"color": "#94a3b8", "font-size": "11px", "font-style": "italic"},
                    margin=(4, 0),
                ),
            ]
            return

        items = []
        n = len(anns)
        for i, cfg in enumerate(anns):
            style_label = "Color track" if cfg["type"] == "categorical" else "Bar chart"
            edge = cfg["edge"]
            edge_label = {"left": "Rows, before", "right": "Rows, after",
                          "top": "Columns, before", "bottom": "Columns, after"}.get(edge, edge)
            subtitle = f"{style_label} \u00b7 {edge_label}"
            esc_col = _html.escape(cfg["column"])

            # Determine grouping role badge
            role_badge = ""
            if edge in ("left", "right"):
                group_list = self.state.row_group_by
            else:
                group_list = self.state.col_group_by
            if cfg["column"] in group_list:
                rank = group_list.index(cfg["column"])
                role = "Primary" if rank == 0 else "Secondary"
                role_badge = (
                    f' <span style="background:#eef2ff;color:#5c6ac4;font-size:9px;'
                    f'padding:1px 5px;border-radius:3px;font-weight:500">{role}</span>'
                )

            label_html = pn.pane.HTML(
                f'<div style="font-size:12px;font-weight:500;color:#1e293b;overflow:hidden;'
                f'text-overflow:ellipsis;white-space:nowrap">{esc_col}</div>'
                f'<div style="font-size:10px;color:#94a3b8">{subtitle}{role_badge}</div>',
                sizing_mode="stretch_width", margin=0,
            )

            # Split toggle (only for grouping-column annotations)
            is_eligible = self._is_split_eligible(cfg)
            split_btn = None
            if is_eligible:
                is_split = cfg.get("split", False)
                splits_on_axis = self._count_splits_for_axis(edge)
                split_disabled = (splits_on_axis >= 2 and not is_split)
                split_btn = pn.widgets.Button(
                    name="Split", width=46, height=24,
                    button_type="primary" if is_split else "light",
                    disabled=split_disabled,
                    margin=(0, 0, 0, 0),
                )
                _is_split = is_split  # capture for closure
                split_btn.on_click(lambda e, idx=i, s=_is_split: self._on_split_toggled(idx, not s))

            remove_btn = pn.widgets.Button(
                name="\u00d7", width=24, height=24, button_type="light",
                margin=(0, 0, 0, 0),
            )
            remove_btn.on_click(lambda e, idx=i: self._on_remove_annotation(idx))

            buttons = [b for b in [split_btn, remove_btn] if b is not None]
            row = pn.Row(
                label_html,
                *buttons,
                sizing_mode="stretch_width",
                styles={"background": "#f8fafc", "border-radius": "6px", "padding": "4px 6px"},
                margin=(2, 0),
            )
            items.append(row)
        self._annotation_list_col.objects = items

    def _build_charts_card(self) -> list:
        """Return the Charts card for the sidebar, or empty list if no chart_manager."""
        if self.chart_manager is None:
            return []
        cm = self.chart_manager
        return [_make_section_card(
            "Charts",
            pn.Column(
                cm.chart_type_select,
                cm.chart_column_select,
                cm.chart_y_column_select,
                cm.chart_add_button,
                sizing_mode="stretch_width",
            ),
            "charts",
            collapsed=True,
        )]

    def build_panel(self) -> pn.Column:
        """Build the complete sidebar panel."""
        branding = pn.pane.Markdown(
            "**dream-heatmap**",
            styles={"font-size": "15px", "color": "#202223", "white-space": "nowrap"},
            margin=(0, 0, 0, 0),
        )
        header_row = pn.Row(
            branding, self.status_text,
            sizing_mode="stretch_width",
            margin=(0, 0, 8, 0),
        )

        # --- Step headers (small, muted) ---
        def _step_label(num: int, text: str) -> pn.pane.HTML:
            return pn.pane.HTML(
                f'<div style="font-size:11px;font-weight:500;color:#919eab;'
                f'margin:4px 0 2px 0">Step {num}: {text}</div>',
                sizing_mode="stretch_width", margin=0,
            )

        # --- Tabbed Rows/Columns section (Steps 1+2) ---
        rows_tab_content = pn.Column(
            _step_label(1, "Group and order"),
            self.row_group_primary,
            self.row_group_secondary,
            _step_label(2, "Cluster"),
            self.row_cluster_mode,
            self.row_cluster_method_select,
            self.row_cluster_metric_select,
            self.show_row_dendro_toggle,
            sizing_mode="stretch_width",
        )

        cols_tab_content = pn.Column(
            _step_label(1, "Group and order"),
            self.col_group_primary,
            self.col_group_secondary,
            _step_label(2, "Cluster"),
            self.col_cluster_mode,
            self.col_cluster_method_select,
            self.col_cluster_metric_select,
            self.show_col_dendro_toggle,
            sizing_mode="stretch_width",
        )

        grouping_tabs = pn.Tabs(
            ("Rows", rows_tab_content),
            ("Columns", cols_tab_content),
            sizing_mode="stretch_width",
            margin=(0, 0, 0, 0),
            dynamic=True,
        )

        return pn.Column(
            header_row,

            _make_section_card("Scale & Colour", pn.Column(
                self.scale_method_select,
                self.scale_axis_select,
                self.colormap_select,
                pn.Row(self.vmin_input, self.vmax_input, sizing_mode="stretch_width"),
                sizing_mode="stretch_width",
            ), "color", collapsed=False),

            _make_section_card("Labels", pn.Column(
                pn.Row(self.row_labels_select, self.row_label_side_select, sizing_mode="stretch_width"),
                pn.Row(self.col_labels_select, self.col_label_side_select, sizing_mode="stretch_width"),
                sizing_mode="stretch_width",
            ), "labels"),

            _make_section_card("Group, Order & Cluster", pn.Column(
                grouping_tabs,
                sizing_mode="stretch_width",
            ), "ordering", collapsed=False),

            _make_section_card("Annotations & Splits", pn.Column(
                self.ann_axis_select,
                self.ann_column_select,
                self.ann_style_select,
                self.ann_position_select,
                self.ann_add_button,
                pn.layout.Divider(),
                self._annotation_list_col,
                sizing_mode="stretch_width",
            ), "annotations"),

            *(self._build_charts_card()),

            sizing_mode="stretch_width",
            scroll=True,
        )
