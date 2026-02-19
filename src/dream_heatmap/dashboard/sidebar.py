"""SidebarControls: Panel widgets for configuring the heatmap."""

from __future__ import annotations

import param
import panel as pn

from .state import DashboardState
from .code_export import generate_code


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

LABEL_MODES = ["all", "auto", "none"]

ANNOTATION_TYPES = ["categorical", "bar"]
ANNOTATION_EDGES = ["top", "bottom", "left", "right"]


class SidebarControls:
    """Builds and manages the sidebar Panel widgets.

    Links widgets to DashboardState params so changes automatically
    trigger heatmap rebuilds.
    """

    def __init__(self, state: DashboardState) -> None:
        self.state = state
        self._annotation_list_col = pn.Column(sizing_mode="stretch_width")
        self._code_display = pn.pane.Markdown("", sizing_mode="stretch_width")
        self._build_widgets()

    def _build_widgets(self) -> None:
        """Create all sidebar widgets."""
        s = self.state

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

        # --- Split section ---
        row_meta_cols = [""] + s.get_row_metadata_columns() if s.row_metadata is not None else [""]
        col_meta_cols = [""] + s.get_col_metadata_columns() if s.col_metadata is not None else [""]

        self.split_rows_select = pn.widgets.Select(
            name="Split rows by", value=s.split_rows_by,
            options=row_meta_cols, sizing_mode="stretch_width",
        )
        self.split_cols_select = pn.widgets.Select(
            name="Split cols by", value=s.split_cols_by,
            options=col_meta_cols, sizing_mode="stretch_width",
        )

        # --- Clustering section ---
        self.cluster_rows_toggle = pn.widgets.Toggle(
            name="Cluster rows", value=s.cluster_rows,
            sizing_mode="stretch_width",
        )
        self.cluster_cols_toggle = pn.widgets.Toggle(
            name="Cluster cols", value=s.cluster_cols,
            sizing_mode="stretch_width",
        )
        self.cluster_method_select = pn.widgets.Select(
            name="Method", value=s.cluster_method,
            options=CLUSTER_METHODS, sizing_mode="stretch_width",
        )
        self.cluster_metric_select = pn.widgets.Select(
            name="Metric", value=s.cluster_metric,
            options=CLUSTER_METRICS, sizing_mode="stretch_width",
        )

        # --- Ordering section ---
        self.order_rows_select = pn.widgets.Select(
            name="Order rows by", value=s.order_rows_by,
            options=row_meta_cols, sizing_mode="stretch_width",
        )
        self.order_cols_select = pn.widgets.Select(
            name="Order cols by", value=s.order_cols_by,
            options=col_meta_cols, sizing_mode="stretch_width",
        )

        # Disable row-related widgets when no row metadata
        if s.row_metadata is None:
            self.split_rows_select.disabled = True
            self.order_rows_select.disabled = True
        if s.col_metadata is None:
            self.split_cols_select.disabled = True
            self.order_cols_select.disabled = True

        # --- Labels section ---
        self.row_labels_radio = pn.widgets.RadioButtonGroup(
            name="Row labels", value=s.row_labels,
            options=LABEL_MODES, sizing_mode="stretch_width",
        )
        self.col_labels_radio = pn.widgets.RadioButtonGroup(
            name="Col labels", value=s.col_labels,
            options=LABEL_MODES, sizing_mode="stretch_width",
        )

        # --- Annotation builder ---
        self.ann_type_select = pn.widgets.Select(
            name="Type", options=ANNOTATION_TYPES,
            value=ANNOTATION_TYPES[0],
            sizing_mode="stretch_width",
        )
        self.ann_edge_select = pn.widgets.Select(
            name="Edge", options=ANNOTATION_EDGES,
            value=ANNOTATION_EDGES[0],
            sizing_mode="stretch_width",
        )
        ann_col_options = self._get_annotation_columns()
        self.ann_column_select = pn.widgets.Select(
            name="Column", options=ann_col_options,
            value=ann_col_options[0] if ann_col_options else "",
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

        # Wire up widget → state bindings
        self._wire_bindings()

        # Wire annotation builder
        self.ann_add_button.on_click(self._on_add_annotation)
        self.ann_type_select.param.watch(
            lambda e: self._update_annotation_columns(), "value",
        )
        self.ann_edge_select.param.watch(
            lambda e: self._update_annotation_columns(), "value",
        )

        # Build initial annotation list display
        self._refresh_annotation_list()

    def _wire_bindings(self) -> None:
        """Link widget values to DashboardState params."""
        s = self.state

        self.colormap_select.param.watch(
            lambda e: setattr(s, "colormap", e.new), "value",
        )
        self.vmin_input.param.watch(
            lambda e: setattr(s, "vmin", e.new), "value",
        )
        self.vmax_input.param.watch(
            lambda e: setattr(s, "vmax", e.new), "value",
        )
        self.split_rows_select.param.watch(
            lambda e: setattr(s, "split_rows_by", e.new), "value",
        )
        self.split_cols_select.param.watch(
            lambda e: setattr(s, "split_cols_by", e.new), "value",
        )
        self.cluster_rows_toggle.param.watch(
            lambda e: setattr(s, "cluster_rows", e.new), "value",
        )
        self.cluster_cols_toggle.param.watch(
            lambda e: setattr(s, "cluster_cols", e.new), "value",
        )
        self.cluster_method_select.param.watch(
            lambda e: setattr(s, "cluster_method", e.new), "value",
        )
        self.cluster_metric_select.param.watch(
            lambda e: setattr(s, "cluster_metric", e.new), "value",
        )
        self.order_rows_select.param.watch(
            lambda e: setattr(s, "order_rows_by", e.new), "value",
        )
        self.order_cols_select.param.watch(
            lambda e: setattr(s, "order_cols_by", e.new), "value",
        )
        self.row_labels_radio.param.watch(
            lambda e: setattr(s, "row_labels", e.new), "value",
        )
        self.col_labels_radio.param.watch(
            lambda e: setattr(s, "col_labels", e.new), "value",
        )

    def _get_annotation_columns(self) -> list[str]:
        """Get available columns for the current annotation type/edge."""
        ann_type = getattr(self, "ann_type_select", None)
        ann_edge = getattr(self, "ann_edge_select", None)
        if ann_type is None or ann_edge is None:
            return []

        edge = ann_edge.value
        atype = ann_type.value
        is_row_edge = edge in ("left", "right")
        s = self.state

        if atype == "categorical":
            if is_row_edge:
                return s.get_row_metadata_columns()
            else:
                return s.get_col_metadata_categorical_columns()
        elif atype == "bar":
            cols = []
            if is_row_edge:
                cols.extend(s.get_row_metadata_columns())
            else:
                # Numeric metadata columns + expression row names (markers)
                cols.extend(s.get_col_metadata_numeric_columns())
                cols.extend(s.get_expression_row_names())
            return cols
        return []

    def _update_annotation_columns(self) -> None:
        """Update the annotation column dropdown when type/edge changes."""
        new_options = self._get_annotation_columns()
        self.ann_column_select.options = new_options
        self.ann_column_select.value = new_options[0] if new_options else ""

    def _on_add_annotation(self, event) -> None:
        """Handle the Add annotation button click."""
        column = self.ann_column_select.value
        if not column:
            return

        cfg = {
            "type": self.ann_type_select.value,
            "edge": self.ann_edge_select.value,
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

    def _refresh_annotation_list(self) -> None:
        """Rebuild the annotation list display."""
        items = []
        for i, cfg in enumerate(self.state.annotations):
            label = f"{cfg['type']}: {cfg['column']} ({cfg['edge']})"
            idx = i  # capture for closure
            remove_btn = pn.widgets.Button(
                name="\u00d7", width=30, button_type="danger",
                margin=(0, 0, 0, 5),
            )
            remove_btn.on_click(lambda e, idx=idx: self._on_remove_annotation(idx))
            row = pn.Row(
                pn.pane.Str(label, sizing_mode="stretch_width"),
                remove_btn,
                sizing_mode="stretch_width",
            )
            items.append(row)
        self._annotation_list_col.objects = items

    def build_panel(self) -> pn.Column:
        """Build the complete sidebar panel."""
        return pn.Column(
            pn.pane.Markdown("## Controls", margin=(0, 0, 10, 0)),

            self.export_button,
            pn.layout.Divider(),

            pn.Card(
                self.colormap_select,
                pn.Row(self.vmin_input, self.vmax_input, sizing_mode="stretch_width"),
                title="Color Scale", collapsed=False,
                sizing_mode="stretch_width",
            ),

            pn.Card(
                self.split_rows_select,
                self.split_cols_select,
                title="Splits", collapsed=True,
                sizing_mode="stretch_width",
            ),

            pn.Card(
                pn.Row(
                    self.cluster_rows_toggle,
                    self.cluster_cols_toggle,
                    sizing_mode="stretch_width",
                ),
                self.cluster_method_select,
                self.cluster_metric_select,
                title="Clustering", collapsed=True,
                sizing_mode="stretch_width",
            ),

            pn.Card(
                self.order_rows_select,
                self.order_cols_select,
                title="Ordering", collapsed=True,
                sizing_mode="stretch_width",
            ),

            pn.Card(
                pn.pane.Str("Row labels:", margin=(5, 0, 0, 0)),
                self.row_labels_radio,
                pn.pane.Str("Col labels:", margin=(10, 0, 0, 0)),
                self.col_labels_radio,
                title="Labels", collapsed=True,
                sizing_mode="stretch_width",
            ),

            pn.Card(
                self.ann_type_select,
                self.ann_edge_select,
                self.ann_column_select,
                self.ann_add_button,
                pn.layout.Divider(),
                self._annotation_list_col,
                title="Annotations", collapsed=True,
                sizing_mode="stretch_width",
            ),

            sizing_mode="stretch_width",
            scroll=True,
        )
