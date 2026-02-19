"""Code export: generate a Python snippet from the current dashboard state."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import DashboardState


def generate_code(state: DashboardState) -> str:
    """Generate a self-contained Python snippet from the current dashboard state.

    Only includes non-default settings so the output stays clean.
    """
    lines: list[str] = []

    # Imports
    lines.append("import pandas as pd")
    lines.append("import dream_heatmap as dh")
    lines.append("")

    # Data loading (placeholder paths for user to customize)
    lines.append("# Load data — adjust paths to your files")
    lines.append('expr = pd.read_csv("data/tme_expression_matrix.csv", index_col=0)')
    if state.col_metadata is not None:
        lines.append('col_meta = pd.read_csv("data/tme_cell_metadata.csv").set_index("cell_id")')
    if state.row_metadata is not None:
        lines.append('row_meta = pd.read_csv("data/tme_marker_metadata.csv").set_index("marker")')
    lines.append("")

    # Build heatmap
    lines.append("# Build heatmap")
    lines.append("hm = dh.Heatmap(expr)")

    # Metadata
    if state.col_metadata is not None:
        lines.append("hm.set_col_metadata(col_meta)")
    if state.row_metadata is not None:
        lines.append("hm.set_row_metadata(row_meta)")

    # Colormap (only if non-default)
    if state.colormap != "viridis" or state.vmin is not None or state.vmax is not None:
        parts = [f'"{state.colormap}"']
        if state.vmin is not None:
            parts.append(f"vmin={state.vmin}")
        if state.vmax is not None:
            parts.append(f"vmax={state.vmax}")
        lines.append(f"hm.set_colormap({', '.join(parts)})")

    # Splits
    if state.split_rows_by:
        lines.append(f'hm.split_rows(by="{state.split_rows_by}")')
    if state.split_cols_by:
        lines.append(f'hm.split_cols(by="{state.split_cols_by}")')

    # Clustering vs ordering (mutually exclusive per axis)
    if state.cluster_rows:
        parts = []
        if state.cluster_method != "average":
            parts.append(f'method="{state.cluster_method}"')
        if state.cluster_metric != "euclidean":
            parts.append(f'metric="{state.cluster_metric}"')
        args = ", ".join(parts)
        lines.append(f"hm.cluster_rows({args})")
    elif state.order_rows_by:
        lines.append(f'hm.order_rows(by="{state.order_rows_by}")')

    if state.cluster_cols:
        parts = []
        if state.cluster_method != "average":
            parts.append(f'method="{state.cluster_method}"')
        if state.cluster_metric != "euclidean":
            parts.append(f'metric="{state.cluster_metric}"')
        args = ", ".join(parts)
        lines.append(f"hm.cluster_cols({args})")
    elif state.order_cols_by:
        lines.append(f'hm.order_cols(by="{state.order_cols_by}")')

    # Labels (only if non-default)
    if state.row_labels != "auto" or state.col_labels != "auto":
        lines.append(
            f'hm.set_label_display(rows="{state.row_labels}", cols="{state.col_labels}")'
        )

    # Annotations
    for ann_cfg in state.annotations:
        ann_type = ann_cfg.get("type", "")
        edge = ann_cfg.get("edge", "")
        column = ann_cfg.get("column", "")
        if not ann_type or not edge or not column:
            continue

        is_row_edge = edge in ("left", "right")

        if ann_type == "categorical":
            meta_var = "row_meta" if is_row_edge else "col_meta"
            lines.append(
                f'hm.add_annotation("{edge}", '
                f'dh.CategoricalAnnotation({meta_var}["{column}"], name="{column}"))'
            )
        elif ann_type == "bar":
            # Could be metadata column or expression row
            if is_row_edge:
                meta_var = "row_meta"
                lines.append(
                    f'hm.add_annotation("{edge}", '
                    f'dh.BarChartAnnotation({meta_var}["{column}"], name="{column}"))'
                )
            else:
                # Check if it's an expression row or metadata column
                if (
                    state.data is not None
                    and column in state.data.index
                ):
                    lines.append(
                        f'hm.add_annotation("{edge}", '
                        f'dh.BarChartAnnotation(expr.loc["{column}"], name="{column}"))'
                    )
                else:
                    meta_var = "col_meta"
                    lines.append(
                        f'hm.add_annotation("{edge}", '
                        f'dh.BarChartAnnotation({meta_var}["{column}"], name="{column}"))'
                    )

    lines.append("")
    lines.append("# Display")
    lines.append("hm.show()  # In Jupyter")
    lines.append('# hm.to_html("heatmap.html")  # Standalone HTML')

    return "\n".join(lines)
