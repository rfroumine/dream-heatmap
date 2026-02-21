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

_CLUSTER_SENTINEL = "__cluster__"


def _build_order_options(meta_cols: list[str]) -> dict[str, str]:
    opts = {"None": "", "Cluster": _CLUSTER_SENTINEL}
    for col in meta_cols:
        opts[col] = col
    return opts


def _build_secondary_options(
    meta_cols: list[str], exclude: str = "",
) -> dict[str, str]:
    """Build options for a secondary dropdown, excluding the primary selection."""
    opts = {"None": ""}
    for col in meta_cols:
        if col != exclude:
            opts[col] = col
    return opts


class SidebarControls:
    """Builds and manages the sidebar Panel widgets.

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
        self._syncing = False  # Guard flag: suppresses widget→state callbacks
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

        # Populate vmin/vmax with actual data range if not set
        if s.vmin is None or s.vmax is None:
            self._update_color_range_for_scaling()

        # --- Value Scaling section ---
        self.scale_method_select = pn.widgets.Select(
            name="Method", value=s.scale_method,
            options={
                "None": "none",
                "Center & Scale (z-score)": "zscore",
                "Center only": "center",
                "Min-Max [0,1]": "minmax",
            },
            sizing_mode="stretch_width",
        )
        self.scale_axis_select = pn.widgets.Select(
            name="Apply", value=s.scale_axis,
            options={"Row-wise": "row", "Column-wise": "column"},
            sizing_mode="stretch_width",
        )
        self.scale_method_help = pn.pane.Markdown(
            "*Z-score: centers to 0, scales to unit variance. "
            "Center: shifts mean to 0. "
            "Min-Max: rescales values to 0\u20131.*",
            styles={"color": "#6b7280", "font-size": "11px"},
            margin=(0, 0, 5, 0),
        )
        self.scale_axis_help = pn.pane.Markdown(
            "*Row-wise: each gene independently. Column-wise: each sample independently.*",
            styles={"color": "#6b7280", "font-size": "11px"},
            margin=(0, 0, 5, 0),
        )

        # --- Labels section ---
        self.row_labels_select = pn.widgets.Select(
            name="Row labels", value=s.row_labels,
            options={"All": "all", "Auto": "auto", "None": "none"},
            sizing_mode="stretch_width",
        )
        self.col_labels_select = pn.widgets.Select(
            name="Col labels", value=s.col_labels,
            options={"All": "all", "Auto": "auto", "None": "none"},
            sizing_mode="stretch_width",
        )
        self.row_label_side_select = pn.widgets.Select(
            name="Row label side", value=s.row_label_side,
            options={"Left": "left", "Right": "right"},
            sizing_mode="stretch_width",
        )
        self.col_label_side_select = pn.widgets.Select(
            name="Col label side", value=s.col_label_side,
            options={"Top": "top", "Bottom": "bottom"},
            sizing_mode="stretch_width",
        )

        # --- Row Ordering section ---
        order_rows_init = _CLUSTER_SENTINEL if s.cluster_rows else (s.order_rows_by or "")
        self.order_rows_select = pn.widgets.Select(
            name="Order by", value=order_rows_init,
            options=_build_order_options(row_meta_cols), sizing_mode="stretch_width",
        )
        self.order_rows_2_select = pn.widgets.Select(
            name="Order by (2nd)", value=s.order_rows_by_2,
            options=_build_secondary_options(row_meta_cols, exclude=s.order_rows_by),
            visible=(bool(s.order_rows_by) and order_rows_init != _CLUSTER_SENTINEL),
            sizing_mode="stretch_width",
        )
        self.show_row_dendro_toggle = pn.widgets.Checkbox(
            name="Show dendrogram", value=s.show_row_dendro,
            visible=(order_rows_init == _CLUSTER_SENTINEL),
        )
        self.row_cluster_method_select = pn.widgets.Select(
            name="Method", value=s.cluster_method,
            options=CLUSTER_METHODS,
            visible=(order_rows_init == _CLUSTER_SENTINEL),
            sizing_mode="stretch_width",
        )
        self.row_cluster_metric_select = pn.widgets.Select(
            name="Metric", value=s.cluster_metric,
            options=CLUSTER_METRICS,
            visible=(order_rows_init == _CLUSTER_SENTINEL),
            sizing_mode="stretch_width",
        )
        self.row_ordering_help_text = pn.pane.Markdown(
            "*Ordering is applied within each split group.*",
            styles={"color": "#6b7280", "font-size": "11px"},
            margin=(0, 0, 5, 0),
        )

        # --- Column Ordering section ---
        order_cols_init = _CLUSTER_SENTINEL if s.cluster_cols else (s.order_cols_by or "")
        self.order_cols_select = pn.widgets.Select(
            name="Order by", value=order_cols_init,
            options=_build_order_options(col_meta_cols), sizing_mode="stretch_width",
        )
        self.order_cols_2_select = pn.widgets.Select(
            name="Order by (2nd)", value=s.order_cols_by_2,
            options=_build_secondary_options(col_meta_cols, exclude=s.order_cols_by),
            visible=(bool(s.order_cols_by) and order_cols_init != _CLUSTER_SENTINEL),
            sizing_mode="stretch_width",
        )
        self.show_col_dendro_toggle = pn.widgets.Checkbox(
            name="Show dendrogram", value=s.show_col_dendro,
            visible=(order_cols_init == _CLUSTER_SENTINEL),
        )
        self.col_cluster_method_select = pn.widgets.Select(
            name="Method", value=s.cluster_method,
            options=CLUSTER_METHODS,
            visible=(order_cols_init == _CLUSTER_SENTINEL),
            sizing_mode="stretch_width",
        )
        self.col_cluster_metric_select = pn.widgets.Select(
            name="Metric", value=s.cluster_metric,
            options=CLUSTER_METRICS,
            visible=(order_cols_init == _CLUSTER_SENTINEL),
            sizing_mode="stretch_width",
        )
        self.col_ordering_help_text = pn.pane.Markdown(
            "*Ordering is applied within each split group.*",
            styles={"color": "#6b7280", "font-size": "11px"},
            margin=(0, 0, 5, 0),
        )

        # Disable ordering widgets when no metadata
        if s.row_metadata is None:
            self.order_rows_select.disabled = True
        if s.col_metadata is None:
            self.order_cols_select.disabled = True

        # --- Annotation builder ---
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
            name="Style", options=ANNOTATION_STYLES,
            value=ANNOTATION_STYLES[0],
            sizing_mode="stretch_width",
        )
        self.ann_position_select = pn.widgets.Select(
            name="Position", options=ANNOTATION_POSITIONS,
            value=ANNOTATION_POSITIONS[0],
            sizing_mode="stretch_width",
        )
        self.ann_add_button = pn.widgets.Button(
            name="+ Add", button_type="primary",
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

        # Wire up widget → state bindings
        self._wire_bindings()

        # Wire annotation builder
        self.ann_add_button.on_click(self._on_add_annotation)
        self.ann_axis_select.param.watch(
            lambda e: self._update_annotation_columns(e.new), "value",
        )
        self.ann_column_select.param.watch(
            lambda e: self._auto_detect_style(), "value",
        )

        # Build initial annotation list display
        self._refresh_annotation_list()

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

        # Value scaling
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

        # Row ordering
        self.order_rows_select.param.watch(self._on_order_rows_changed, "value")
        self.order_rows_2_select.param.watch(
            lambda e: self._set_state("order_rows_by_2", e.new), "value",
        )
        self.show_row_dendro_toggle.param.watch(
            lambda e: self._set_state("show_row_dendro", e.new), "value",
        )
        self.row_cluster_method_select.param.watch(
            lambda e: self._set_state("cluster_method", e.new), "value",
        )
        self.row_cluster_metric_select.param.watch(
            lambda e: self._set_state("cluster_metric", e.new), "value",
        )

        # Column ordering
        self.order_cols_select.param.watch(self._on_order_cols_changed, "value")
        self.order_cols_2_select.param.watch(
            lambda e: self._set_state("order_cols_by_2", e.new), "value",
        )
        self.show_col_dendro_toggle.param.watch(
            lambda e: self._set_state("show_col_dendro", e.new), "value",
        )
        self.col_cluster_method_select.param.watch(
            lambda e: self._set_state("cluster_method", e.new), "value",
        )
        self.col_cluster_metric_select.param.watch(
            lambda e: self._set_state("cluster_metric", e.new), "value",
        )

        # Status text: watch state._status_text and update the pane
        s.param.watch(
            lambda e: setattr(self.status_text, "object", e.new), "_status_text",
        )

    # --- Scaling change handlers ---

    def _on_scaling_changed(self, event) -> None:
        """Handle scaling method or axis change — single batched rebuild."""
        new_method = self.scale_method_select.value
        new_axis = self.scale_axis_select.value
        new_vmin, new_vmax = self._compute_scaled_range(new_method, new_axis)

        # Update widgets under guard so their watch callbacks don't fire
        self._syncing = True
        try:
            self.vmin_input.value = new_vmin
            self.vmax_input.value = new_vmax
        finally:
            self._syncing = False

        # Single atomic state update → one rebuild with correct values
        self.state.param.update(
            scale_method=new_method,
            scale_axis=new_axis,
            vmin=new_vmin,
            vmax=new_vmax,
        )

    def _compute_scaled_range(
        self, method: str, axis: str,
    ) -> tuple[float, float]:
        """Compute vmin/vmax from the (possibly scaled) data."""
        import numpy as np
        from ..transform.scaler import apply_scaling

        s = self.state
        if s.data is None:
            return (0.0, 1.0)
        axis_int = 1 if axis == "row" else 0
        scaled = apply_scaling(s.data, method, axis_int)
        finite = scaled.values[np.isfinite(scaled.values)]
        if len(finite) > 0:
            return (float(np.round(finite.min(), 2)), float(np.round(finite.max(), 2)))
        return (0.0, 1.0)

    def _update_color_range_for_scaling(self) -> None:
        """Set vmin/vmax widgets from current state. Used at init before watches exist."""
        new_vmin, new_vmax = self._compute_scaled_range(
            self.state.scale_method, self.state.scale_axis,
        )
        self.vmin_input.value = new_vmin
        self.vmax_input.value = new_vmax

    # --- Ordering change handlers ---

    def _on_order_rows_changed(self, event) -> None:
        s = self.state
        is_cluster = event.new == _CLUSTER_SENTINEL
        if is_cluster:
            s.param.update(cluster_rows=True, order_rows_by="", order_rows_by_2="")
        else:
            s.param.update(cluster_rows=False, order_rows_by=event.new, order_rows_by_2="")

        # Toggle visibility (no state impact)
        self.show_row_dendro_toggle.visible = is_cluster
        self.row_cluster_method_select.visible = is_cluster
        self.row_cluster_metric_select.visible = is_cluster

        # Reset secondary dropdown under guard so its watch doesn't fire
        show_secondary = bool(event.new) and not is_cluster
        self._syncing = True
        try:
            self.order_rows_2_select.param.update(
                options=_build_secondary_options(
                    s.get_row_metadata_columns(), exclude=event.new,
                ),
                value="",
                visible=show_secondary,
            )
        finally:
            self._syncing = False

        self._sync_cluster_widgets()

    def _on_order_cols_changed(self, event) -> None:
        s = self.state
        is_cluster = event.new == _CLUSTER_SENTINEL
        if is_cluster:
            s.param.update(cluster_cols=True, order_cols_by="", order_cols_by_2="")
        else:
            s.param.update(cluster_cols=False, order_cols_by=event.new, order_cols_by_2="")

        self.show_col_dendro_toggle.visible = is_cluster
        self.col_cluster_method_select.visible = is_cluster
        self.col_cluster_metric_select.visible = is_cluster

        show_secondary = bool(event.new) and not is_cluster
        self._syncing = True
        try:
            self.order_cols_2_select.param.update(
                options=_build_secondary_options(
                    s.get_col_metadata_columns(), exclude=event.new,
                ),
                value="",
                visible=show_secondary,
            )
        finally:
            self._syncing = False

        self._sync_cluster_widgets()

    def _sync_cluster_widgets(self) -> None:
        """Keep the cluster method/metric widgets in sync between both cards."""
        self._syncing = True
        try:
            s = self.state
            self.row_cluster_method_select.value = s.cluster_method
            self.row_cluster_metric_select.value = s.cluster_metric
            self.col_cluster_method_select.value = s.cluster_method
            self.col_cluster_metric_select.value = s.cluster_metric
        finally:
            self._syncing = False

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

    def _on_split_toggled(self, idx: int, checked: bool) -> None:
        """Handle split checkbox toggle on an annotation."""
        anns = list(self.state.annotations)
        anns[idx] = {**anns[idx], "split": checked}
        self.state.annotations = anns  # triggers _rebuild via param
        self._refresh_annotation_list()  # update disabled states

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
        """Rebuild the annotation list display with split toggles."""
        # Pre-compute split rank per axis for Primary/Secondary labels
        row_edges = ("left", "right")
        col_edges = ("top", "bottom")
        row_split_indices = [
            i for i, cfg in enumerate(self.state.annotations)
            if cfg.get("split") and cfg["edge"] in row_edges
        ]
        col_split_indices = [
            i for i, cfg in enumerate(self.state.annotations)
            if cfg.get("split") and cfg["edge"] in col_edges
        ]

        def _split_label(idx: int, edge: str) -> str:
            target = row_split_indices if edge in row_edges else col_split_indices
            if idx not in target:
                return "Split"
            rank = target.index(idx)
            if rank == 0 and len(target) > 1:
                return "Split (Primary)"
            elif rank == 1:
                return "Split (Secondary)"
            return "Split"

        items = []
        for i, cfg in enumerate(self.state.annotations):
            style_label = "Color track" if cfg["type"] == "categorical" else "Bar chart"
            edge = cfg["edge"]
            edge_label = {"left": "Rows, before", "right": "Rows, after",
                          "top": "Columns, before", "bottom": "Columns, after"}.get(edge, edge)
            label = f"{cfg['column']} \u2014 {style_label} ({edge_label})"

            is_split = cfg.get("split", False)
            splits_on_axis = self._count_splits_for_axis(edge)
            # Disable if already 2 splits on this axis and this one isn't checked
            split_disabled = (splits_on_axis >= 2 and not is_split)

            cb_name = _split_label(i, edge)
            split_cb = pn.widgets.Checkbox(
                name=cb_name, value=is_split,
                width=120, disabled=split_disabled,
                margin=(0, 5, 0, 5),
            )
            idx = i
            split_cb.param.watch(
                lambda e, idx=idx: self._on_split_toggled(idx, e.new), "value",
            )

            remove_btn = pn.widgets.Button(
                name="\u00d7", width=30, button_type="danger",
                margin=(0, 0, 0, 5),
            )
            remove_btn.on_click(lambda e, idx=idx: self._on_remove_annotation(idx))
            row = pn.Row(
                pn.pane.Str(label, sizing_mode="stretch_width"),
                split_cb,
                remove_btn,
                sizing_mode="stretch_width",
            )
            items.append(row)
        self._annotation_list_col.objects = items

    def _build_charts_card(self) -> list:
        """Return the Charts card for the sidebar, or empty list if no chart_manager."""
        if self.chart_manager is None:
            return []
        cm = self.chart_manager
        return [pn.Card(
            cm.chart_type_select,
            cm.chart_column_select,
            cm.chart_y_column_select,
            cm.chart_add_button,
            title="Charts", collapsed=True,
            sizing_mode="stretch_width",
        )]

    def build_panel(self) -> pn.Column:
        """Build the complete sidebar panel."""
        return pn.Column(
            pn.Card(
                self.scale_method_select,
                self.scale_method_help,
                self.scale_axis_select,
                self.scale_axis_help,
                title="Value Scaling", collapsed=False,
                sizing_mode="stretch_width",
            ),

            pn.Card(
                self.colormap_select,
                pn.Row(self.vmin_input, self.vmax_input, sizing_mode="stretch_width"),
                title="Color Scale", collapsed=False,
                sizing_mode="stretch_width",
            ),

            pn.Card(
                self.row_labels_select,
                self.row_label_side_select,
                self.col_labels_select,
                self.col_label_side_select,
                title="Labels", collapsed=True,
                sizing_mode="stretch_width",
            ),

            pn.Card(
                self.ann_axis_select,
                self.ann_column_select,
                self.ann_style_select,
                self.ann_position_select,
                self.ann_add_button,
                pn.layout.Divider(),
                self._annotation_list_col,
                title="Annotations & Splits", collapsed=True,
                sizing_mode="stretch_width",
            ),

            pn.Card(
                self.order_rows_select,
                self.order_rows_2_select,
                self.show_row_dendro_toggle,
                self.row_cluster_method_select,
                self.row_cluster_metric_select,
                self.row_ordering_help_text,
                title="Row Ordering", collapsed=True,
                sizing_mode="stretch_width",
            ),

            pn.Card(
                self.order_cols_select,
                self.order_cols_2_select,
                self.show_col_dendro_toggle,
                self.col_cluster_method_select,
                self.col_cluster_metric_select,
                self.col_ordering_help_text,
                title="Column Ordering", collapsed=True,
                sizing_mode="stretch_width",
            ),

            *(self._build_charts_card()),

            self.status_text,

            sizing_mode="stretch_width",
            scroll=True,
        )
