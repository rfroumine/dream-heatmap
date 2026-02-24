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
  render(legends, legendPanel, colorBarRenderer, lut, vmin, vmax, colorBarTitle, colorBarSubtitle) {
    this.clear();
    if (colorBarRenderer) colorBarRenderer.clear();
    if (!legendPanel) return;

    var ns = "http://www.w3.org/2000/svg";
    this._group = document.createElementNS(ns, "g");
    this._group.setAttribute("class", "dh-legend-panel");
    this._group.style.pointerEvents = "none";

    var swatchSize = 11;
    var swatchLabelGap = 7;
    var rowHeight = 16;
    var titleHeight = 18;
    var blockGap = 20;
    var columnGap = 12;
    var charWidth = 6.5;
    var SINGLE_COL_MAX = 8;
    var MAX_COLUMNS = 3;
    var MULTI_COL_MAX = 24;
    var MAX_VISIBLE = MAX_COLUMNS * 6;  // 18
    var fontFamily = '"Outfit", system-ui, -apple-system, sans-serif';

    var panelX = legendPanel.x;
    var curY = legendPanel.y;

    // --- Color bar block (always first, on top) ---
    if (colorBarRenderer && lut) {
      var cbResult = colorBarRenderer.renderInline(
        panelX, curY, lut, vmin, vmax, colorBarTitle || null, this._group, colorBarSubtitle || null
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
        title.setAttribute("font-weight", "600");
        title.setAttribute("font-family", fontFamily);
        title.setAttribute("fill", "#334155");
        this._group.appendChild(title);

        // Compute column layout
        var n = entries.length;
        var numCols, rowsPerCol, visibleEntries, overflowCount;
        if (n <= SINGLE_COL_MAX) {
          numCols = 1;
          rowsPerCol = n;
          visibleEntries = entries;
          overflowCount = 0;
        } else if (n <= MULTI_COL_MAX) {
          numCols = Math.min(MAX_COLUMNS, Math.ceil(n / 8));
          rowsPerCol = Math.ceil(n / numCols);
          visibleEntries = entries;
          overflowCount = 0;
        } else {
          numCols = MAX_COLUMNS;
          rowsPerCol = 6;
          visibleEntries = entries.slice(0, MAX_VISIBLE);
          overflowCount = n - MAX_VISIBLE;
        }

        // Compute per-column widths
        var colWidths = [];
        for (var c = 0; c < numCols; c++) {
          var maxLabelW = 0;
          var start = c * rowsPerCol;
          var end = Math.min(start + rowsPerCol, visibleEntries.length);
          for (var k = start; k < end; k++) {
            var lw = visibleEntries[k].label.length * charWidth;
            if (lw > maxLabelW) maxLabelW = lw;
          }
          colWidths.push(swatchSize + swatchLabelGap + maxLabelW);
        }

        // Render entries in columns
        var colX = panelX;
        for (var c = 0; c < numCols; c++) {
          var entryY = curY + titleHeight;
          var start = c * rowsPerCol;
          var end = Math.min(start + rowsPerCol, visibleEntries.length);
          for (var ei = start; ei < end; ei++) {
            var entry = visibleEntries[ei];

            // Color swatch
            var rect = document.createElementNS(ns, "rect");
            rect.setAttribute("x", colX);
            rect.setAttribute("y", entryY);
            rect.setAttribute("width", swatchSize);
            rect.setAttribute("height", swatchSize);
            rect.setAttribute("fill", entry.color);
            rect.setAttribute("rx", "2");
            this._group.appendChild(rect);

            // Label
            var label = document.createElementNS(ns, "text");
            label.textContent = entry.label;
            label.setAttribute("x", colX + swatchSize + swatchLabelGap);
            label.setAttribute("y", entryY + swatchSize * 0.8);
            label.setAttribute("font-size", "10");
            label.setAttribute("font-family", fontFamily);
            label.setAttribute("fill", "#475569");
            this._group.appendChild(label);

            entryY += rowHeight;
          }
          colX += colWidths[c] + columnGap;
        }

        // "+N more" overflow text
        var truncated = overflowCount > 0;
        if (truncated) {
          var moreText = document.createElementNS(ns, "text");
          moreText.textContent = "+" + overflowCount + " more";
          moreText.setAttribute("x", panelX);
          moreText.setAttribute("y", curY + titleHeight + rowsPerCol * rowHeight + 10);
          moreText.setAttribute("font-size", "9");
          moreText.setAttribute("font-style", "italic");
          moreText.setAttribute("font-family", fontFamily);
          moreText.setAttribute("fill", "#94a3b8");
          this._group.appendChild(moreText);
        }

        var blockH = titleHeight + rowsPerCol * rowHeight + (truncated ? 14 : 0);
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
