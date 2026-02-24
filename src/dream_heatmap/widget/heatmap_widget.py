"""HeatmapWidget: anywidget bridge for Jupyter rendering.

Requires the [jupyter] optional extra: pip install dream-heatmap[jupyter]
"""

from __future__ import annotations

import pathlib

try:
    import anywidget
    import traitlets
    _HAS_ANYWIDGET = True
except ImportError:
    _HAS_ANYWIDGET = False

    # Minimal shim so the class body doesn't crash at definition time.
    # The __init__ guard (_check_anywidget) prevents actual usage.
    class _ShimDescriptor:
        def __init__(self, *a, **kw): pass
        def tag(self, **kw): return self

    class traitlets:  # type: ignore[no-redef]
        Bytes = _ShimDescriptor
        Unicode = _ShimDescriptor

from ..core.matrix import MatrixData
from ..core.color_scale import ColorScale
from ..core.id_mapper import IDMapper
from ..layout.composer import LayoutSpec
from .serializers import (
    serialize_matrix,
    serialize_color_lut,
    serialize_layout,
    serialize_id_mappers,
    serialize_config,
)
from .selection import SelectionState

_JS_DIR = pathlib.Path(__file__).parent.parent / "js"


def _check_anywidget():
    if not _HAS_ANYWIDGET:
        raise ImportError(
            "anywidget is required for Jupyter rendering. "
            "Install it with: pip install dream-heatmap[jupyter]"
        )


# Only define the widget class if anywidget is available
if _HAS_ANYWIDGET:
    _BaseWidget = anywidget.AnyWidget
else:
    _BaseWidget = object


class HeatmapWidget(_BaseWidget):
    """Jupyter widget for rendering interactive heatmaps.

    Communicates with JS via traitlets:
    - matrix_bytes: row-major float64 matrix data
    - color_lut: 1024-byte RGBA lookup table
    - layout_json: JSON layout specification
    - id_mappers_json: JSON IDMapper data for row/col
    - config_json: rendering config (vmin, vmax, nanColor)
    - selection_json: JS→Python selection updates
    """

    _esm = traitlets.Unicode("").tag(sync=True)
    _css = traitlets.Unicode("").tag(sync=True)

    @staticmethod
    def _build_css() -> str:
        """Build CSS styles for the widget."""
        return """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
.dh-container {
  position: relative;
  display: inline-block;
  font-family: "Outfit", system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
.dh-tooltip {
  position: absolute;
  display: none;
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: #0f172a;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 12px;
  font-family: "Outfit", system-ui, -apple-system, sans-serif;
  pointer-events: none;
  z-index: 100;
  white-space: nowrap;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08), 0 1px 3px rgba(0,0,0,0.06);
  border: 1px solid rgba(0,0,0,0.06);
  line-height: 1.7;
  letter-spacing: -0.01em;
}
.dh-tooltip .dh-tip-label {
  color: #94a3b8;
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.dh-tooltip .dh-tip-value {
  font-weight: 500;
  font-family: "JetBrains Mono", "Cascadia Code", "Consolas", monospace;
  font-size: 11px;
  color: #0f172a;
}
.dh-tooltip .dh-tip-swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 3px;
  border: 1px solid rgba(0,0,0,0.1);
  vertical-align: middle;
  margin-right: 5px;
}
.dh-toolbar {
  position: absolute;
  top: 6px;
  right: 6px;
  display: flex;
  gap: 1px;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 8px;
  padding: 3px;
  opacity: 0;
  transition: opacity 0.25s ease;
  z-index: 200;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.dh-container:hover .dh-toolbar {
  opacity: 1;
}
.dh-toolbar button {
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px 7px;
  border-radius: 6px;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}
.dh-toolbar button:hover {
  background: rgba(0,0,0,0.04);
  color: #0f172a;
}
.dh-toolbar button.active {
  background: rgba(13,148,136,0.08);
  color: #0d9488;
}
.dh-toolbar button svg {
  width: 15px;
  height: 15px;
  stroke-width: 1.6;
}
.dh-show-all-labels .dh-label-auto-hidden {
  display: inline !important;
}
"""

    # Python → JS data
    matrix_bytes = traitlets.Bytes(b"").tag(sync=True)
    color_lut = traitlets.Bytes(b"").tag(sync=True)
    layout_json = traitlets.Unicode("{}").tag(sync=True)
    id_mappers_json = traitlets.Unicode("{}").tag(sync=True)
    config_json = traitlets.Unicode("{}").tag(sync=True)

    # JS → Python selection
    selection_json = traitlets.Unicode("{}").tag(sync=True)

    # JS → Python zoom range
    zoom_range_json = traitlets.Unicode("null").tag(sync=True)

    def __init__(
        self,
        matrix: MatrixData,
        color_scale: ColorScale,
        row_mapper: IDMapper,
        col_mapper: IDMapper,
        layout: LayoutSpec,
        selection_state: SelectionState,
        dendrograms: dict | None = None,
        annotations: dict | None = None,
        labels: dict | None = None,
        legends: list[dict] | None = None,
        color_bar_title: str | None = None,
        color_bar_subtitle: str | None = None,
        title: str | None = None,
        **kwargs,
    ) -> None:
        _check_anywidget()
        # Read JS source
        js_source = self._build_esm()

        # Build config with optional extra data
        config_extra = {}
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
        if color_bar_subtitle is not None:
            config_extra["colorBarSubtitle"] = color_bar_subtitle
        if title is not None:
            config_extra["title"] = title

        super().__init__(
            _esm=js_source,
            _css=self._build_css(),
            matrix_bytes=serialize_matrix(matrix),
            color_lut=serialize_color_lut(color_scale),
            layout_json=serialize_layout(layout),
            id_mappers_json=serialize_id_mappers(row_mapper, col_mapper),
            config_json=serialize_config(
                vmin=color_scale.vmin,
                vmax=color_scale.vmax,
                nan_color=color_scale.nan_color,
                cmap_name=color_scale.cmap_name,
                **config_extra,
            ),
            **kwargs,
        )

        self._selection_state = selection_state
        self._row_mapper = row_mapper
        self._col_mapper = col_mapper
        self._zoom_callback = None
        self.observe(self._on_selection_change, names=["selection_json"])
        self.observe(self._on_zoom_change, names=["zoom_range_json"])

    def _build_esm(self) -> str:
        """Read and bundle JS source files into a single ESM string."""
        js_files = [
            _JS_DIR / "bridge" / "binary_decoder.js",
            _JS_DIR / "bridge" / "model_sync.js",
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
            _JS_DIR / "interaction" / "annotation_click.js",
            _JS_DIR / "interaction" / "zoom_handler.js",
            _JS_DIR / "interaction" / "toolbar.js",
            _JS_DIR / "index.js",
        ]
        parts = []
        for f in js_files:
            if f.exists():
                parts.append(f"// === {f.name} ===\n{f.read_text(encoding='utf-8')}")
        return "\n\n".join(parts)

    def _on_selection_change(self, change: dict) -> None:
        """Handle selection updates from JS."""
        import json

        data = json.loads(change["new"])
        row_ids = data.get("row_ids", [])
        col_ids = data.get("col_ids", [])
        self._selection_state.update(row_ids, col_ids)

    def _on_zoom_change(self, change: dict) -> None:
        """Handle zoom range updates from JS."""
        import json

        data = json.loads(change["new"])
        if self._zoom_callback is not None:
            self._zoom_callback(data)

    def set_zoom_callback(self, callback) -> None:
        """Register a callback for zoom events: fn(zoom_range_dict_or_none)."""
        self._zoom_callback = callback

    def update_data(
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
        color_bar_subtitle: str | None = None,
        title: str | None = None,
    ) -> None:
        """Push updated data to JS (e.g., after zoom or reorder).

        Uses hold_sync() to batch all trait changes into a single comm
        message, preventing intermediate renders with mismatched data.
        """
        config_extra = {}
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
        if color_bar_subtitle is not None:
            config_extra["colorBarSubtitle"] = color_bar_subtitle
        if title is not None:
            config_extra["title"] = title

        with self.hold_sync():
            self.matrix_bytes = serialize_matrix(matrix)
            self.color_lut = serialize_color_lut(color_scale)
            self.layout_json = serialize_layout(layout)
            self.id_mappers_json = serialize_id_mappers(row_mapper, col_mapper)
            self.config_json = serialize_config(
                vmin=color_scale.vmin,
                vmax=color_scale.vmax,
                nan_color=color_scale.nan_color,
                cmap_name=color_scale.cmap_name,
                **config_extra,
            )
        self._row_mapper = row_mapper
        self._col_mapper = col_mapper
