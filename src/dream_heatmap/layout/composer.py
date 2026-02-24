"""LayoutComposer: assembles all components into a final layout specification."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.id_mapper import IDMapper
from .geometry import Rect
from .cell_layout import CellLayout


# Default sizes
DEFAULT_CELL_SIZE = 12.0
DEFAULT_GAP_SIZE = 6.0
DEFAULT_PADDING = 40.0  # space for labels on each side
DEFAULT_DENDRO_HEIGHT = 80.0
MIN_CELL_SIZE = 0.05  # allow sub-pixel for large matrices
MAX_CELL_SIZE = 50.0
DEFAULT_MAX_WIDTH = 1000.0   # reasonable max for Jupyter
DEFAULT_MAX_HEIGHT = 500.0


@dataclass
class LayoutSpec:
    """Complete layout specification sent to JS for rendering."""

    # Heatmap grid
    heatmap_rect: Rect
    row_cell_layout: CellLayout
    col_cell_layout: CellLayout

    # Overall dimensions
    total_width: float
    total_height: float

    # Matrix dimensions
    n_rows: int
    n_cols: int

    # Dendrogram space
    row_dendro_width: float = 0.0
    col_dendro_height: float = 0.0
    row_dendro_side: str = "left"
    col_dendro_side: str = "top"

    # Color bar rendered in legend panel (flag only, no separate rect)
    has_color_bar: bool = True

    # Annotation edge sizes (so JS can offset labels past annotations)
    left_annotation_width: float = 0.0
    right_annotation_width: float = 0.0
    top_annotation_height: float = 0.0
    bottom_annotation_height: float = 0.0

    # Legend panel
    legend_panel_rect: Rect | None = None

    # Secondary gap indices (gaps smaller than primary — should be bridged in annotations)
    row_secondary_gap_indices: list[int] = field(default_factory=list)
    col_secondary_gap_indices: list[int] = field(default_factory=list)

    # Title position (y-coordinate for centered title text)
    title_y: float = 0.0

    def to_dict(self) -> dict:
        """Serialize to a dict for JSON transfer to JS."""
        d = {
            "heatmap": self.heatmap_rect.to_dict(),
            "rowPositions": self.row_cell_layout.to_list(),
            "colPositions": self.col_cell_layout.to_list(),
            "rowCellSize": self.row_cell_layout.cell_size,
            "colCellSize": self.col_cell_layout.cell_size,
            "totalWidth": self.total_width,
            "totalHeight": self.total_height,
            "nRows": self.n_rows,
            "nCols": self.n_cols,
            "rowDendroWidth": self.row_dendro_width,
            "colDendroHeight": self.col_dendro_height,
            "rowDendroSide": self.row_dendro_side,
            "colDendroSide": self.col_dendro_side,
            "hasColorBar": self.has_color_bar,
            "leftAnnotationWidth": self.left_annotation_width,
            "rightAnnotationWidth": self.right_annotation_width,
            "topAnnotationHeight": self.top_annotation_height,
            "bottomAnnotationHeight": self.bottom_annotation_height,
        }
        if self.legend_panel_rect is not None:
            d["legendPanel"] = self.legend_panel_rect.to_dict()
        if self.row_secondary_gap_indices:
            d["rowSecondaryGaps"] = self.row_secondary_gap_indices
        if self.col_secondary_gap_indices:
            d["colSecondaryGaps"] = self.col_secondary_gap_indices
        if self.title_y > 0:
            d["titleY"] = self.title_y
        return d


class LayoutComposer:
    """Computes the full layout for a heatmap.

    Accounts for dendrograms (left/top), annotations, and labels.
    """

    def __init__(
        self,
        cell_size: float = DEFAULT_CELL_SIZE,
        gap_size: float = DEFAULT_GAP_SIZE,
        padding: float = DEFAULT_PADDING,
        dendro_height: float = DEFAULT_DENDRO_HEIGHT,
        max_width: float = DEFAULT_MAX_WIDTH,
        max_height: float = DEFAULT_MAX_HEIGHT,
    ) -> None:
        self._cell_size = max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, cell_size))
        self._gap_size = gap_size
        self._padding = padding
        self._dendro_height = dendro_height
        self._max_width = max_width
        self._max_height = max_height

    def compute(
        self,
        row_mapper: IDMapper,
        col_mapper: IDMapper,
        has_row_dendro: bool = False,
        has_col_dendro: bool = False,
        left_annotation_width: float = 0.0,
        right_annotation_width: float = 0.0,
        top_annotation_height: float = 0.0,
        bottom_annotation_height: float = 0.0,
        legend_panel_width: float = 0.0,
        legend_panel_height: float = 0.0,
        left_label_width: float = 0.0,
        right_label_width: float = 0.0,
        top_label_height: float = 0.0,
        bottom_label_height: float = 0.0,
        # Per-gap sizing for hierarchical splits
        row_gap_sizes: dict[int, float] | None = None,
        col_gap_sizes: dict[int, float] | None = None,
        # Title above the heatmap
        title_height: float = 0.0,
        # Dendrogram placement side
        row_dendro_side: str = "left",
        col_dendro_side: str = "top",
        # Legacy compat: if callers still pass row_label_width/col_label_height
        row_label_width: float | None = None,
        col_label_height: float | None = None,
    ) -> LayoutSpec:
        """Compute the layout for the given row/col ID mappers."""
        # Legacy fallback: old callers may still pass row_label_width / col_label_height
        if row_label_width is not None and right_label_width == 0.0:
            right_label_width = row_label_width
        if col_label_height is not None and bottom_label_height == 0.0:
            bottom_label_height = col_label_height

        row_dendro_w = self._dendro_height if has_row_dendro else 0.0
        col_dendro_h = self._dendro_height if has_col_dendro else 0.0

        # Split dendro space based on side placement
        left_dendro_w = row_dendro_w if row_dendro_side == "left" else 0.0
        right_dendro_w = row_dendro_w if row_dendro_side == "right" else 0.0
        top_dendro_h = col_dendro_h if col_dendro_side == "top" else 0.0
        bottom_dendro_h = col_dendro_h if col_dendro_side == "bottom" else 0.0

        n_rows = row_mapper.size
        n_cols = col_mapper.size

        # Legend panel extends beyond max_width (not in cell budget)
        has_legend = legend_panel_width > 0 and legend_panel_height > 0
        legend_gap = 15.0
        right_padding = 0.0 if has_legend else self._padding

        # Fixed pixel components (everything except cell grid and gaps)
        fixed_width = (
            self._padding + right_padding
            + left_dendro_w
            + right_dendro_w
            + left_annotation_width
            + right_annotation_width
            + left_label_width
            + right_label_width
        )
        fixed_height = (
            self._padding * 2
            + title_height
            + top_dendro_h
            + bottom_dendro_h
            + top_annotation_height
            + bottom_annotation_height
            + top_label_height
            + bottom_label_height
        )
        # Legend panel is to the right — does not add to fixed_height

        # Gap pixel totals (use per-gap sizes if provided)
        if col_gap_sizes:
            col_gap_total = sum(
                col_gap_sizes.get(p, self._gap_size)
                for p in col_mapper.gap_positions
            )
        else:
            col_gap_total = len(col_mapper.gap_positions) * self._gap_size
        if row_gap_sizes:
            row_gap_total = sum(
                row_gap_sizes.get(p, self._gap_size)
                for p in row_mapper.gap_positions
            )
        else:
            row_gap_total = len(row_mapper.gap_positions) * self._gap_size

        # Budget-based cell sizes (independent per axis)
        if n_cols > 0:
            col_cell_size = (self._max_width - fixed_width - col_gap_total) / n_cols
        else:
            col_cell_size = self._cell_size
        if n_rows > 0:
            row_cell_size = (self._max_height - fixed_height - row_gap_total) / n_rows
        else:
            row_cell_size = self._cell_size

        col_cell_size = max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, col_cell_size))
        row_cell_size = max(MIN_CELL_SIZE, min(MAX_CELL_SIZE, row_cell_size))

        # Heatmap origin shifts right/down for dendrograms + left annotations + left labels
        heatmap_x = self._padding + left_dendro_w + left_annotation_width + left_label_width
        heatmap_y = self._padding + title_height + top_dendro_h + top_annotation_height + top_label_height

        row_layout = CellLayout(
            n_cells=n_rows,
            cell_size=row_cell_size,
            gap_positions=row_mapper.gap_positions,
            gap_size=self._gap_size,
            offset=heatmap_y,
            gap_sizes=row_gap_sizes,
        )
        col_layout = CellLayout(
            n_cells=n_cols,
            cell_size=col_cell_size,
            gap_positions=col_mapper.gap_positions,
            gap_size=self._gap_size,
            offset=heatmap_x,
            gap_sizes=col_gap_sizes,
        )

        heatmap_rect = Rect(
            x=heatmap_x,
            y=heatmap_y,
            width=col_layout.total_size,
            height=row_layout.total_size,
        )

        legend_panel_rect = None

        total_width = heatmap_x + col_layout.total_size + right_annotation_width + right_label_width + right_dendro_w + right_padding

        # Total height: heatmap + bottom annotations/labels + bottom dendro + padding
        heatmap_bottom = heatmap_y + row_layout.total_size + bottom_annotation_height + bottom_label_height + bottom_dendro_h

        # Legend panel to the right of the heatmap area
        if legend_panel_height > 0 and legend_panel_width > 0:
            lp_x = total_width + legend_gap
            lp_y = heatmap_y  # top-aligned with heatmap
            legend_panel_rect = Rect(
                x=lp_x, y=lp_y,
                width=legend_panel_width,
                height=legend_panel_height,
            )
            total_width = lp_x + legend_panel_width + 5.0

        legend_bottom = (lp_y + legend_panel_height) if legend_panel_rect else 0.0
        total_height = max(heatmap_bottom, legend_bottom) + self._padding

        # Compute secondary gap indices: positions where gap < max gap size
        row_secondary = self._secondary_gap_indices(row_gap_sizes)
        col_secondary = self._secondary_gap_indices(col_gap_sizes)

        # Title position: centered vertically in the title_height band
        title_y_pos = (self._padding + title_height * 0.7) if title_height > 0 else 0.0

        return LayoutSpec(
            heatmap_rect=heatmap_rect,
            row_cell_layout=row_layout,
            col_cell_layout=col_layout,
            total_width=total_width,
            total_height=total_height,
            n_rows=row_mapper.size,
            n_cols=col_mapper.size,
            row_dendro_width=row_dendro_w,
            col_dendro_height=col_dendro_h,
            row_dendro_side=row_dendro_side,
            col_dendro_side=col_dendro_side,
            has_color_bar=True,
            left_annotation_width=left_annotation_width,
            right_annotation_width=right_annotation_width,
            top_annotation_height=top_annotation_height,
            bottom_annotation_height=bottom_annotation_height,
            legend_panel_rect=legend_panel_rect,
            row_secondary_gap_indices=row_secondary,
            col_secondary_gap_indices=col_secondary,
            title_y=title_y_pos,
        )

    @staticmethod
    def _secondary_gap_indices(
        gap_sizes: dict[int, float] | None,
    ) -> list[int]:
        """Return gap positions whose size is strictly less than the maximum."""
        if not gap_sizes or len(gap_sizes) <= 1:
            return []
        max_size = max(gap_sizes.values())
        return sorted(pos for pos, size in gap_sizes.items() if size < max_size)
