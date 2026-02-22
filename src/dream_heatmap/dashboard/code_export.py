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

    # Value scaling (row-wise pass)
    if state.row_scale_method != "none":
        lines.append("# Scale values (row-wise)")
        if state.row_scale_method == "zscore":
            lines.append("expr = expr.sub(expr.mean(axis=1), axis=0).div(expr.std(axis=1).replace(0, 1), axis=0)")
        elif state.row_scale_method == "center":
            lines.append("expr = expr.sub(expr.mean(axis=1), axis=0)")
        elif state.row_scale_method == "minmax":
            lines.append("expr = expr.sub(expr.min(axis=1), axis=0).div((expr.max(axis=1) - expr.min(axis=1)).replace(0, 1), axis=0)")
        lines.append("")

    # Value scaling (column-wise pass)
    if state.col_scale_method != "none":
        lines.append("# Scale values (column-wise)")
        if state.col_scale_method == "zscore":
            lines.append("expr = (expr - expr.mean()) / expr.std().replace(0, 1)")
        elif state.col_scale_method == "center":
            lines.append("expr = expr - expr.mean()")
        elif state.col_scale_method == "minmax":
            lines.append("expr = (expr - expr.min()) / (expr.max() - expr.min()).replace(0, 1)")
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

    # Splits — derived from annotation split flags
    split_rows = [
        cfg["column"] for cfg in state.annotations
        if cfg.get("split") and cfg.get("edge") in ("left", "right")
    ][:2]
    if split_rows:
        if len(split_rows) == 1:
            lines.append(f'hm.split_rows(by="{split_rows[0]}")')
        else:
            lines.append(f'hm.split_rows(by={split_rows})')

    split_cols = [
        cfg["column"] for cfg in state.annotations
        if cfg.get("split") and cfg.get("edge") in ("top", "bottom")
    ][:2]
    if split_cols:
        if len(split_cols) == 1:
            lines.append(f'hm.split_cols(by="{split_cols[0]}")')
        else:
            lines.append(f'hm.split_cols(by={split_cols})')

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
        order_rows = [v for v in [state.order_rows_by, state.order_rows_by_2] if v]
        if len(order_rows) == 1:
            lines.append(f'hm.order_rows(by="{order_rows[0]}")')
        else:
            lines.append(f'hm.order_rows(by={order_rows})')

    if state.cluster_cols:
        parts = []
        if state.cluster_method != "average":
            parts.append(f'method="{state.cluster_method}"')
        if state.cluster_metric != "euclidean":
            parts.append(f'metric="{state.cluster_metric}"')
        args = ", ".join(parts)
        lines.append(f"hm.cluster_cols({args})")
    elif state.order_cols_by:
        order_cols = [v for v in [state.order_cols_by, state.order_cols_by_2] if v]
        if len(order_cols) == 1:
            lines.append(f'hm.order_cols(by="{order_cols[0]}")')
        else:
            lines.append(f'hm.order_cols(by={order_cols})')

    # Labels (mode + side, only if non-default)
    has_non_default_labels = (
        state.row_labels != "auto"
        or state.col_labels != "auto"
        or state.row_label_side != "right"
        or state.col_label_side != "bottom"
    )
    if has_non_default_labels:
        parts = []
        if state.row_labels != "auto":
            parts.append(f'rows="{state.row_labels}"')
        if state.col_labels != "auto":
            parts.append(f'cols="{state.col_labels}"')
        if state.row_label_side != "right":
            parts.append(f'row_side="{state.row_label_side}"')
        if state.col_label_side != "bottom":
            parts.append(f'col_side="{state.col_label_side}"')
        lines.append(f"hm.set_label_display({', '.join(parts)})")

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
                f'dh.CategoricalAnnotation("{column}", {meta_var}["{column}"]))'
            )
        elif ann_type == "bar":
            # Could be metadata column or expression row
            if is_row_edge:
                meta_var = "row_meta"
                lines.append(
                    f'hm.add_annotation("{edge}", '
                    f'dh.BarChartAnnotation("{column}", {meta_var}["{column}"]))'
                )
            else:
                # Check if it's an expression row or metadata column
                if (
                    state.data is not None
                    and column in state.data.index
                ):
                    lines.append(
                        f'hm.add_annotation("{edge}", '
                        f'dh.BarChartAnnotation("{column}", expr.loc["{column}"]))'
                    )
                else:
                    meta_var = "col_meta"
                    lines.append(
                        f'hm.add_annotation("{edge}", '
                        f'dh.BarChartAnnotation("{column}", {meta_var}["{column}"]))'
                    )

    # Dendrogram visibility (comment hint if non-default)
    if state.cluster_rows and not state.show_row_dendro:
        lines.append("# Note: row dendrogram hidden in dashboard (no API toggle yet)")
    if state.cluster_cols and not state.show_col_dendro:
        lines.append("# Note: col dendrogram hidden in dashboard (no API toggle yet)")

    lines.append("")
    lines.append("# Display")
    lines.append("hm.show()  # In Jupyter")
    lines.append('# hm.to_html("heatmap.html")  # Standalone HTML')

    return "\n".join(lines)
