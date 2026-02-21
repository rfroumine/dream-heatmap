/**
 * LegendRenderer: renders color bar + categorical legends in a vertical
 * stack layout (color bar on top, categorical legends stacked below).
 */

class LegendRenderer {
  constructor(svg) {
    this._svg = svg;
    this._group = null;
  }

  /**
   * Render legend entries with vertical stacking.
   * @param {Array|null} legends - [{name, entries: [{label, color}]}]
   * @param {object} legendPanel - {x, y, width, height} from layout
   * @param {ColorBarRenderer} colorBarRenderer - renders the inline color bar
   * @param {Uint8Array} lut - color LUT
   * @param {number} vmin
   * @param {number} vmax
   * @param {string|null} colorBarTitle
   */
  render(legends, legendPanel, colorBarRenderer, lut, vmin, vmax, colorBarTitle) {
    this.clear();
    if (colorBarRenderer) colorBarRenderer.clear();
    if (!legendPanel) return;

    var ns = "http://www.w3.org/2000/svg";
    this._group = document.createElementNS(ns, "g");
    this._group.setAttribute("class", "dh-legend-panel");
    this._group.style.pointerEvents = "none";

    var swatchSize = 10;
    var swatchLabelGap = 6;
    var rowHeight = 14;
    var titleHeight = 16;
    var blockGap = 16;
    var fontFamily = '"Open Sans", verdana, arial, sans-serif';

    var panelX = legendPanel.x;
    var curY = legendPanel.y;

    // --- Color bar block (always first, on top) ---
    if (colorBarRenderer && lut) {
      var cbResult = colorBarRenderer.renderInline(
        panelX, curY, lut, vmin, vmax, colorBarTitle || null, this._group
      );
      curY += cbResult.height + blockGap;
    }

    // --- Categorical legend blocks (stacked vertically) ---
    if (legends && legends.length) {
      for (var li = 0; li < legends.length; li++) {
        var legend = legends[li];
        var entries = legend.entries || [];

        // Render title
        var title = document.createElementNS(ns, "text");
        title.textContent = legend.name;
        title.setAttribute("x", panelX);
        title.setAttribute("y", curY + 10);
        title.setAttribute("font-size", "10");
        title.setAttribute("font-weight", "bold");
        title.setAttribute("font-family", fontFamily);
        title.setAttribute("fill", "#444");
        this._group.appendChild(title);

        var entryY = curY + titleHeight;

        // Render entries
        for (var ei = 0; ei < entries.length; ei++) {
          var entry = entries[ei];

          // Color swatch
          var rect = document.createElementNS(ns, "rect");
          rect.setAttribute("x", panelX);
          rect.setAttribute("y", entryY);
          rect.setAttribute("width", swatchSize);
          rect.setAttribute("height", swatchSize);
          rect.setAttribute("fill", entry.color);
          rect.setAttribute("rx", "1");
          this._group.appendChild(rect);

          // Label
          var label = document.createElementNS(ns, "text");
          label.textContent = entry.label;
          label.setAttribute("x", panelX + swatchSize + swatchLabelGap);
          label.setAttribute("y", entryY + swatchSize * 0.8);
          label.setAttribute("font-size", "10");
          label.setAttribute("font-family", fontFamily);
          label.setAttribute("fill", "#444");
          this._group.appendChild(label);

          entryY += rowHeight;
        }

        var blockH = titleHeight + entries.length * rowHeight;
        curY += blockH + blockGap;
      }
    }

    this._svg.appendChild(this._group);
  }

  clear() {
    if (this._group && this._group.parentNode) {
      this._group.parentNode.removeChild(this._group);
    }
    this._group = null;
  }
}
