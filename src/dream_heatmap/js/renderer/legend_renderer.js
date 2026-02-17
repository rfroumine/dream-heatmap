/**
 * LegendRenderer: renders color bar + categorical legends in a horizontal
 * flow layout (wrapping to new rows when needed).
 */

class LegendRenderer {
  constructor(svg) {
    this._svg = svg;
    this._group = null;
  }

  /**
   * Render legend entries with horizontal flow.
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
    var itemGap = 24;
    var rowGap = 12;
    var fontFamily = '"Open Sans", verdana, arial, sans-serif';
    var charWidth = 6.5;

    var panelX = legendPanel.x;
    var panelY = legendPanel.y;
    var panelW = legendPanel.width;
    var curX = panelX;
    var curY = panelY;
    var rowMaxH = 0;
    var firstOnRow = true;

    // --- Color bar block (always first) ---
    if (colorBarRenderer && lut) {
      var cbResult = colorBarRenderer.renderInline(
        curX, curY, lut, vmin, vmax, colorBarTitle || null, this._group
      );
      curX += cbResult.width + itemGap;
      rowMaxH = Math.max(rowMaxH, cbResult.height);
      firstOnRow = false;
    }

    // --- Categorical legend blocks ---
    if (legends && legends.length) {
      for (var li = 0; li < legends.length; li++) {
        var legend = legends[li];
        var entries = legend.entries || [];

        // Estimate block dimensions
        var titleW = legend.name.length * charWidth;
        var maxEntryW = 0;
        for (var ei = 0; ei < entries.length; ei++) {
          var ew = swatchSize + swatchLabelGap + entries[ei].label.length * charWidth;
          if (ew > maxEntryW) maxEntryW = ew;
        }
        var blockW = Math.max(titleW, maxEntryW) + 10;
        var blockH = titleHeight + entries.length * rowHeight;

        // Wrap check
        if (!firstOnRow && curX + blockW > panelX + panelW) {
          curY += rowMaxH + rowGap;
          curX = panelX;
          rowMaxH = 0;
          firstOnRow = true;
        }

        // Render title
        var title = document.createElementNS(ns, "text");
        title.textContent = legend.name;
        title.setAttribute("x", curX);
        title.setAttribute("y", curY + 10);
        title.setAttribute("font-size", "10");
        title.setAttribute("font-weight", "bold");
        title.setAttribute("font-family", fontFamily);
        title.setAttribute("fill", "#444");
        this._group.appendChild(title);

        var entryY = curY + titleHeight;

        // Render entries
        for (var ei2 = 0; ei2 < entries.length; ei2++) {
          var entry = entries[ei2];

          // Color swatch
          var rect = document.createElementNS(ns, "rect");
          rect.setAttribute("x", curX);
          rect.setAttribute("y", entryY);
          rect.setAttribute("width", swatchSize);
          rect.setAttribute("height", swatchSize);
          rect.setAttribute("fill", entry.color);
          rect.setAttribute("rx", "1");
          this._group.appendChild(rect);

          // Label
          var label = document.createElementNS(ns, "text");
          label.textContent = entry.label;
          label.setAttribute("x", curX + swatchSize + swatchLabelGap);
          label.setAttribute("y", entryY + swatchSize * 0.8);
          label.setAttribute("font-size", "10");
          label.setAttribute("font-family", fontFamily);
          label.setAttribute("fill", "#444");
          this._group.appendChild(label);

          entryY += rowHeight;
        }

        curX += blockW + itemGap;
        rowMaxH = Math.max(rowMaxH, blockH);
        firstOnRow = false;
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
