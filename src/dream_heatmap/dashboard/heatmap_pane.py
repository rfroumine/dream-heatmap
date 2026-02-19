"""HeatmapPane: Panel JSComponent wrapping the D3/canvas heatmap renderer."""

from __future__ import annotations

import base64
import pathlib

import param
import panel as pn

from ..core.matrix import MatrixData
from ..core.color_scale import ColorScale
from ..core.id_mapper import IDMapper
from ..layout.composer import LayoutSpec
from ..widget.serializers import (
    serialize_matrix,
    serialize_color_lut,
    serialize_layout,
    serialize_id_mappers,
    serialize_config,
)

_JS_DIR = pathlib.Path(__file__).parent.parent / "js"

# CSS for the heatmap container (same as HeatmapWidget but standalone)
_HEATMAP_CSS = """
.dh-container {
  position: relative;
  display: inline-block;
  font-family: "Open Sans", verdana, arial, sans-serif;
}
.dh-tooltip {
  position: absolute;
  display: none;
  background: #fff;
  color: #333;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 11px;
  font-family: "Open Sans", verdana, arial, sans-serif;
  pointer-events: none;
  z-index: 100;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(0,0,0,0.18);
  border: 1px solid #e0e0e0;
  line-height: 1.6;
}
.dh-tooltip .dh-tip-label {
  color: #888;
  font-size: 10px;
}
.dh-tooltip .dh-tip-value {
  font-weight: normal;
}
.dh-tooltip .dh-tip-swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  border: 1px solid #ccc;
  vertical-align: middle;
  margin-right: 4px;
}
.dh-toolbar {
  position: absolute;
  top: 4px;
  right: 4px;
  display: flex;
  gap: 2px;
  background: rgba(255,255,255,0.9);
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 2px;
  opacity: 0;
  transition: opacity 0.2s;
  z-index: 200;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}
.dh-container:hover .dh-toolbar {
  opacity: 1;
}
.dh-toolbar button {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 3px;
  color: #666;
  display: flex;
  align-items: center;
  justify-content: center;
}
.dh-toolbar button:hover {
  background: #f0f0f0;
  color: #333;
}
.dh-toolbar button.active {
  background: #e3edf7;
  color: #1f77b4;
}
.dh-toolbar button svg {
  width: 16px;
  height: 16px;
}
.dh-show-all-labels .dh-label-auto-hidden {
  display: inline !important;
}
"""

# Panel render entry point JS (mirrors anywidget index.js but uses PanelModelSync)
_PANEL_ENTRY_JS = """
// === Panel entry point ===
export function render({ model, el }) {
  // Create container
  const container = document.createElement("div");
  container.className = "dh-container";
  el.appendChild(container);

  // Create canvas for heatmap cells
  const canvas = document.createElement("canvas");
  container.appendChild(canvas);

  // Create SVG overlay for interactivity
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.style.position = "absolute";
  svg.style.top = "0";
  svg.style.left = "0";
  container.appendChild(svg);

  // Tooltip element
  const tooltip = document.createElement("div");
  tooltip.className = "dh-tooltip";
  container.appendChild(tooltip);

  // Initialize components using PanelModelSync adapter
  const sync = new PanelModelSync(model);
  const canvasRenderer = new CanvasRenderer(canvas);
  const svgOverlay = new SVGOverlay(svg);
  svgOverlay.setTooltip(tooltip);
  const colorBarRenderer = new ColorBarRenderer(svg);
  const legendRenderer = new LegendRenderer(svg);
  const hoverHandler = new HoverHandler(svg, tooltip, svgOverlay, container);
  const selectionHandler = new SelectionHandler(svg, svgOverlay, sync, hoverHandler);
  const dendroClickHandler = new DendrogramClickHandler(svgOverlay, sync);
  const viewport = new Viewport();
  const zoomHandler = new ZoomHandler(svg, sync, viewport);
  selectionHandler.setZoomHandler(zoomHandler);
  dendroClickHandler.setZoomHandler(zoomHandler);

  // Toolbar
  const toolbar = new Toolbar(container);
  toolbar.addButton("zoomToSelection", TOOLBAR_ICONS.zoomToSelection, "Zoom to selection", () => {
    zoomHandler.zoomToSelection();
  });
  toolbar.addButton("resetZoom", TOOLBAR_ICONS.resetZoom, "Reset zoom", () => {
    zoomHandler.resetZoom();
  });
  toolbar.addButton("downloadPng", TOOLBAR_ICONS.downloadPng, "Download as PNG", () => {
    try {
      const link = document.createElement("a");
      link.download = "heatmap.png";
      link.href = canvas.toDataURL("image/png");
      link.click();
    } catch (e) {
      console.warn("Download failed:", e);
    }
  });
  toolbar.addButton("crosshairToggle", TOOLBAR_ICONS.crosshairToggle, "Toggle crosshair", () => {
    const enabled = !hoverHandler.getCrosshairEnabled();
    hoverHandler.setCrosshairEnabled(enabled);
    toolbar.setActive("crosshairToggle", enabled);
  });
  toolbar.setActive("crosshairToggle", true);

  function fullRender() {
    // Clear stale selection rect and zoom bounds
    svgOverlay.hideSelection();
    zoomHandler.setLastSelectionBounds(null);

    // Decode data from model via PanelModelSync
    const matrixBytes = sync.getMatrixBytes();
    const lutBytes = sync.getColorLUT();
    const layout = sync.getLayout();
    const idMappers = sync.getIDMappers();
    const config = sync.getConfig();

    if (!layout || !layout.nRows || !layout.nCols) return;

    const matrix = decodeMatrixBytes(matrixBytes);
    const lut = decodeColorLUT(lutBytes);
    const colorMapper = new ColorMapper(lut, config.vmin, config.vmax, config.nanColor);

    // Create ID resolvers
    const rowResolver = idMappers.row
      ? new IDResolver(idMappers.row, layout.rowPositions, layout.rowCellSize)
      : null;
    const colResolver = idMappers.col
      ? new IDResolver(idMappers.col, layout.colPositions, layout.colCellSize)
      : null;

    // Render heatmap cells
    canvasRenderer.render(matrix, layout, colorMapper);
    svgOverlay.resize(layout);

    // Render dendrograms
    const dendrograms = config.dendrograms || null;
    dendroClickHandler.setContext(layout, rowResolver, colResolver);
    svgOverlay.renderDendrograms(dendrograms, layout, (memberIds, axis) => {
      dendroClickHandler.onBranchClick(memberIds, axis);
    });

    // Render annotations
    const annotations = config.annotations || null;
    svgOverlay.renderAnnotations(annotations, layout);

    // Render color bar + categorical legends
    const legends = config.legends || null;
    const colorBarTitle = config.colorBarTitle || null;
    if (layout.legendPanel || layout.hasColorBar) {
      legendRenderer.render(
        legends, layout.legendPanel,
        colorBarRenderer, lut, config.vmin, config.vmax, colorBarTitle
      );
    } else {
      legendRenderer.clear();
      colorBarRenderer.clear();
    }

    // Render axis labels
    const labels = config.labels || null;
    svgOverlay.renderLabels(labels, layout);

    // Update handler contexts
    hoverHandler.setContext(layout, matrix, rowResolver, colResolver, colorMapper);
    selectionHandler.setContext(layout, rowResolver, colResolver);
    zoomHandler.setContext(layout, rowResolver, colResolver);

    // Size container
    container.style.width = layout.totalWidth + "px";
    container.style.height = layout.totalHeight + "px";
  }

  // Initial render
  fullRender();

  // Re-render on data changes
  sync.onChange(fullRender);
}
"""


def _build_esm() -> str:
    """Read and concatenate all JS source files with Panel bridge."""
    js_files = [
        _JS_DIR / "bridge" / "binary_decoder.js",
        _JS_DIR / "bridge" / "panel_model_sync.js",
        _JS_DIR / "renderer" / "color_mapper.js",
        _JS_DIR / "renderer" / "canvas_renderer.js",
        _JS_DIR / "renderer" / "svg_overlay.js",
        _JS_DIR / "renderer" / "color_bar.js",
        _JS_DIR / "renderer" / "legend_renderer.js",
        _JS_DIR / "layout" / "id_resolver.js",
        _JS_DIR / "layout" / "viewport.js",
        _JS_DIR / "interaction" / "hover_handler.js",
        _JS_DIR / "interaction" / "selection_handler.js",
        _JS_DIR / "interaction" / "dendrogram_click.js",
        _JS_DIR / "interaction" / "zoom_handler.js",
        _JS_DIR / "interaction" / "toolbar.js",
    ]
    parts = []
    for f in js_files:
        if f.exists():
            parts.append(f"// === {f.name} ===\n{f.read_text(encoding='utf-8')}")

    # Append the Panel-specific entry point
    parts.append(_PANEL_ENTRY_JS)

    return "\n\n".join(parts)


class HeatmapPane(pn.custom.JSComponent):
    """Panel JSComponent wrapping the D3/canvas heatmap renderer.

    Data is transferred as base64 strings (matrix, color LUT) and
    JSON strings (layout, id_mappers, config). Selection flows back
    from JS via selection_json.
    """

    # Python -> JS (base64 for binary data, JSON strings for structured data)
    matrix_b64 = param.String(default="")
    color_lut_b64 = param.String(default="")
    layout_json = param.String(default="{}")
    id_mappers_json = param.String(default="{}")
    config_json = param.String(default="{}")

    # JS -> Python
    selection_json = param.String(default="{}")
    zoom_range_json = param.String(default="null")

    _esm = _build_esm()
    _stylesheets = [_HEATMAP_CSS]

    def set_data(
        self,
        matrix: MatrixData,
        color_scale: ColorScale,
        row_mapper: IDMapper,
        col_mapper: IDMapper,
        layout: LayoutSpec,
        dendrograms: dict | None = None,
        annotations: dict | None = None,
        labels: dict | None = None,
        legends: list[dict] | None = None,
        color_bar_title: str | None = None,
    ) -> None:
        """Serialize and push heatmap data to JS for rendering."""
        # Encode binary data as base64
        self.matrix_b64 = base64.b64encode(
            serialize_matrix(matrix)
        ).decode("ascii")
        self.color_lut_b64 = base64.b64encode(
            serialize_color_lut(color_scale)
        ).decode("ascii")

        # JSON strings
        self.layout_json = serialize_layout(layout)
        self.id_mappers_json = serialize_id_mappers(row_mapper, col_mapper)

        # Config with optional extras
        config_extra: dict = {}
        if dendrograms is not None:
            config_extra["dendrograms"] = dendrograms
        if annotations is not None:
            config_extra["annotations"] = annotations
        if labels is not None:
            config_extra["labels"] = labels
        if legends is not None:
            config_extra["legends"] = legends
        if color_bar_title is not None:
            config_extra["colorBarTitle"] = color_bar_title

        self.config_json = serialize_config(
            vmin=color_scale.vmin,
            vmax=color_scale.vmax,
            nan_color=color_scale.nan_color,
            cmap_name=color_scale.cmap_name,
            **config_extra,
        )
