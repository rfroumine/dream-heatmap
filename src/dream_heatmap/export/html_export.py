"""HTMLExporter: generate standalone HTML files with full interactivity."""

from __future__ import annotations

import base64
import json
import pathlib

import jinja2

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

_TEMPLATE_DIR = pathlib.Path(__file__).parent / "templates"
_JS_DIR = pathlib.Path(__file__).parent.parent / "js"


class HTMLExporter:
    """Export a heatmap as a standalone HTML file.

    The output HTML is fully self-contained: all JS code and data
    are embedded inline. No external dependencies or CDN required.
    """

    @staticmethod
    def export(
        path: str | pathlib.Path,
        matrix: MatrixData,
        color_scale: ColorScale,
        row_mapper: IDMapper,
        col_mapper: IDMapper,
        layout: LayoutSpec,
        title: str = "dream-heatmap",
        dendrograms: dict | None = None,
        annotations: dict | None = None,
        labels: dict | None = None,
        legends: list[dict] | None = None,
        color_bar_title: str | None = None,
        color_bar_subtitle: str | None = None,
        heatmap_title: str | None = None,
    ) -> None:
        """Write a standalone HTML file.

        Parameters
        ----------
        path : str or Path
            Output file path.
        matrix : MatrixData
        color_scale : ColorScale
        row_mapper, col_mapper : IDMapper
        layout : LayoutSpec
        title : str
            HTML page title.
        dendrograms, annotations, labels : dict, optional
            Extra config data.
        """
        path = pathlib.Path(path)

        # Serialize data
        matrix_bytes = serialize_matrix(matrix)
        lut_bytes = serialize_color_lut(color_scale)

        matrix_b64 = base64.b64encode(matrix_bytes).decode("ascii")
        lut_b64 = base64.b64encode(lut_bytes).decode("ascii")

        layout_json = serialize_layout(layout)
        id_mappers_json = serialize_id_mappers(row_mapper, col_mapper)

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
        if heatmap_title is not None:
            config_extra["title"] = heatmap_title

        config_json = serialize_config(
            vmin=color_scale.vmin,
            vmax=color_scale.vmax,
            nan_color=color_scale.nan_color,
            cmap_name=color_scale.cmap_name,
            **config_extra,
        )

        # Build JS source (same as widget ESM but without export)
        js_source = HTMLExporter._build_js()

        # Build CSS (reuse widget CSS)
        from ..widget.heatmap_widget import HeatmapWidget
        css_source = HeatmapWidget._build_css()

        # Render template
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=False,  # We're generating JS, not user content
        )
        template = env.get_template("standalone.html.j2")

        html = template.render(
            title=title,
            matrix_b64=matrix_b64,
            color_lut_b64=lut_b64,
            layout_json=layout_json,
            id_mappers_json=id_mappers_json,
            config_json=config_json,
            js_source=js_source,
            css_source=css_source,
        )

        path.write_text(html, encoding="utf-8")

    @staticmethod
    def _build_js() -> str:
        """Concatenate all JS source files for standalone use."""
        js_files = [
            _JS_DIR / "bridge" / "binary_decoder.js",
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
        ]
        parts = []
        for f in js_files:
            if f.exists():
                parts.append(f"// === {f.name} ===\n{f.read_text(encoding='utf-8')}")
        return "\n\n".join(parts)
