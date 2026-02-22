/**
 * ColorBarRenderer: renders a horizontal color bar inline within the legend panel.
 */

class ColorBarRenderer {
  constructor(svg) {
    this._svg = svg;
    this._group = null;
  }

  /**
   * Render an inline horizontal color bar at (x, y).
   * @param {number} x - Left position
   * @param {number} y - Top position
   * @param {Uint8Array} lut - 1024-byte RGBA lookup table
   * @param {number} vmin
   * @param {number} vmax
   * @param {string|null} title - Optional title above the bar
   * @param {SVGElement} parentGroup - SVG group to append into
   * @returns {{width: number, height: number}} bounding box of rendered content
   */
  renderInline(x, y, lut, vmin, vmax, title, parentGroup) {
    var ns = "http://www.w3.org/2000/svg";
    var fontFamily = '"Outfit", system-ui, -apple-system, sans-serif';
    var barWidth = 120;
    var barHeight = 12;
    var curY = y;

    // Title (if provided)
    if (title) {
      var titleEl = document.createElementNS(ns, "text");
      titleEl.textContent = title;
      titleEl.setAttribute("x", x);
      titleEl.setAttribute("y", curY + 10);
      titleEl.setAttribute("font-size", "10");
      titleEl.setAttribute("font-weight", "600");
      titleEl.setAttribute("font-family", fontFamily);
      titleEl.setAttribute("fill", "#334155");
      parentGroup.appendChild(titleEl);
      curY += 16;
    }

    // Horizontal linear gradient
    var gradId = "dh-cb-grad-" + Math.random().toString(36).slice(2, 8);
    var defs = document.createElementNS(ns, "defs");
    var grad = document.createElementNS(ns, "linearGradient");
    grad.setAttribute("id", gradId);
    grad.setAttribute("x1", "0");
    grad.setAttribute("y1", "0");
    grad.setAttribute("x2", "1");
    grad.setAttribute("y2", "0");

    // Sample ~20 stops from the LUT
    var nStops = 20;
    for (var i = 0; i <= nStops; i++) {
      var t = i / nStops;
      var lutIdx = Math.round(t * 255);
      var off = lutIdx * 4;
      var r = lut[off], g = lut[off + 1], b = lut[off + 2];
      var stop = document.createElementNS(ns, "stop");
      stop.setAttribute("offset", (t * 100).toFixed(1) + "%");
      stop.setAttribute("stop-color", "rgb(" + r + "," + g + "," + b + ")");
      grad.appendChild(stop);
    }
    defs.appendChild(grad);
    parentGroup.appendChild(defs);

    // Gradient rect
    var rect = document.createElementNS(ns, "rect");
    rect.setAttribute("x", x);
    rect.setAttribute("y", curY);
    rect.setAttribute("width", barWidth);
    rect.setAttribute("height", barHeight);
    rect.setAttribute("fill", "url(#" + gradId + ")");
    rect.setAttribute("stroke", "#e2e8f0");
    rect.setAttribute("stroke-width", "0.5");
    parentGroup.appendChild(rect);

    // Tick labels below the bar
    var ticks = this._niceTicks(vmin, vmax, 5);
    var tickY = curY + barHeight + 12;
    for (var ti = 0; ti < ticks.length; ti++) {
      var tick = ticks[ti];
      var tNorm = (tick - vmin) / (vmax - vmin || 1);
      var tickX = x + tNorm * barWidth;

      // Tick line
      var line = document.createElementNS(ns, "line");
      line.setAttribute("x1", tickX);
      line.setAttribute("x2", tickX);
      line.setAttribute("y1", curY + barHeight);
      line.setAttribute("y2", curY + barHeight + 3);
      line.setAttribute("stroke", "#94a3b8");
      line.setAttribute("stroke-width", "1");
      parentGroup.appendChild(line);

      // Label
      var text = document.createElementNS(ns, "text");
      text.textContent = this._formatTick(tick);
      text.setAttribute("x", tickX);
      text.setAttribute("y", tickY);
      text.setAttribute("font-size", "9");
      text.setAttribute("font-family", fontFamily);
      text.setAttribute("fill", "#475569");
      text.setAttribute("text-anchor", "middle");
      parentGroup.appendChild(text);
    }

    var totalHeight = (curY - y) + barHeight + 14;
    return { width: barWidth + 20, height: totalHeight };
  }

  clear() {
    if (this._group && this._group.parentNode) {
      this._group.parentNode.removeChild(this._group);
    }
    this._group = null;
  }

  /**
   * Compute human-friendly tick values.
   */
  _niceTicks(min, max, count) {
    if (max <= min || !isFinite(min) || !isFinite(max)) return [min, max];
    var range = max - min;
    var rawStep = range / (count - 1);
    var mag = Math.pow(10, Math.floor(Math.log10(rawStep)));
    var norm = rawStep / mag;
    var step;
    if (norm <= 1.5) step = 1 * mag;
    else if (norm <= 3.5) step = 2 * mag;
    else if (norm <= 7.5) step = 5 * mag;
    else step = 10 * mag;

    var start = Math.ceil(min / step) * step;
    var ticks = [];
    for (var v = start; v <= max + step * 0.001; v += step) {
      ticks.push(v);
    }
    // Ensure min and max are included
    if (ticks.length === 0 || ticks[0] > min + step * 0.5) ticks.unshift(min);
    if (ticks[ticks.length - 1] < max - step * 0.5) ticks.push(max);
    return ticks;
  }

  _formatTick(v) {
    if (Math.abs(v) >= 1000 || (Math.abs(v) < 0.01 && v !== 0)) {
      return v.toExponential(1);
    }
    // Remove trailing zeros
    return parseFloat(v.toPrecision(4)).toString();
  }
}
