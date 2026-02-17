/**
 * HoverHandler: manages hover tooltip, cell highlight, and crosshair.
 *
 * Shows a rich tooltip with row ID, col ID, value, and color swatch
 * when the mouse hovers over a cell. Highlights the hovered cell
 * and draws crosshair lines through it.
 */

class HoverHandler {
  /**
   * @param {SVGElement} svg - the SVG overlay element for mouse events
   * @param {HTMLElement} tooltip - the tooltip DOM element
   * @param {SVGOverlay} svgOverlay - for cell highlight rendering
   * @param {HTMLElement} container - the container element (for tooltip positioning)
   */
  constructor(svg, tooltip, svgOverlay, container) {
    this._svg = svg;
    this._tooltip = tooltip;
    this._svgOverlay = svgOverlay;
    this._container = container;
    this._enabled = true;
    this._crosshairEnabled = true;
    this._showingCellTooltip = false;

    // References set externally via setContext
    this._layout = null;
    this._matrix = null;
    this._rowResolver = null;
    this._colResolver = null;
    this._colorMapper = null;

    this._bindEvents();
  }

  /**
   * Update the data context (called after each render).
   */
  setContext(layout, matrix, rowResolver, colResolver, colorMapper) {
    this._layout = layout;
    this._matrix = matrix;
    this._rowResolver = rowResolver;
    this._colResolver = colResolver;
    this._colorMapper = colorMapper || null;
  }

  /** Toggle crosshair on/off. */
  setCrosshairEnabled(enabled) { this._crosshairEnabled = enabled; }
  getCrosshairEnabled() { return this._crosshairEnabled; }

  /** Temporarily suppress hover (e.g. during drag). */
  suppress() { this._enabled = false; this._hide(); }

  /** Re-enable hover. */
  resume() { this._enabled = true; }

  _bindEvents() {
    this._svg.addEventListener("mousemove", (e) => this._onMove(e));
    this._svg.addEventListener("mouseleave", () => this._hide());
  }

  _onMove(e) {
    if (!this._enabled || !this._layout || !this._matrix ||
        !this._rowResolver || !this._colResolver) {
      this._hide();
      return;
    }

    // Get coordinates relative to container (tooltip is positioned relative to container)
    const containerRect = this._container.getBoundingClientRect();
    const x = e.clientX - containerRect.left;
    const y = e.clientY - containerRect.top;

    const colIdx = this._colResolver.pixelToVisualIndex(x);
    const rowIdx = this._rowResolver.pixelToVisualIndex(y);

    if (colIdx !== null && rowIdx !== null) {
      const rowId = this._rowResolver.visualOrder[rowIdx];
      const colId = this._colResolver.visualOrder[colIdx];
      const value = this._matrix[rowIdx * this._layout.nCols + colIdx];
      const displayVal = isFinite(value) ? value.toPrecision(4) : "NaN";

      // Build rich tooltip HTML with color swatch
      let swatchHtml = "";
      if (this._colorMapper && isFinite(value)) {
        const rgba = this._colorMapper.map(value);
        if (rgba) {
          const c = `rgb(${rgba[0]},${rgba[1]},${rgba[2]})`;
          swatchHtml = `<span class="dh-tip-swatch" style="background:${c}"></span>`;
        }
      }
      this._tooltip.innerHTML =
        `<span class="dh-tip-label">Row</span> <span class="dh-tip-value">${this._escHtml(rowId)}</span><br>` +
        `<span class="dh-tip-label">Col</span> <span class="dh-tip-value">${this._escHtml(colId)}</span><br>` +
        `<span class="dh-tip-label">Value</span> ${swatchHtml}<span class="dh-tip-value">${displayVal}</span>`;
      this._tooltip.style.display = "block";
      this._showingCellTooltip = true;

      // Smart positioning: flip when near edges
      const tipW = this._tooltip.offsetWidth;
      const tipH = this._tooltip.offsetHeight;
      const cW = this._container.offsetWidth;
      const cH = this._container.offsetHeight;
      let tipX = x + 14;
      let tipY = y - 10;
      if (tipX + tipW > cW - 4) tipX = x - tipW - 14;
      if (tipY + tipH > cH - 4) tipY = y - tipH - 4;
      if (tipY < 4) tipY = 4;
      this._tooltip.style.left = tipX + "px";
      this._tooltip.style.top = tipY + "px";

      // Show cell highlight
      const colBounds = this._colResolver.getCellBounds(colIdx);
      const rowBounds = this._rowResolver.getCellBounds(rowIdx);
      if (colBounds && rowBounds) {
        const cx = colBounds.start;
        const cy = rowBounds.start;
        const cw = colBounds.end - colBounds.start;
        const ch = rowBounds.end - rowBounds.start;
        this._svgOverlay.showHoverHighlight(cx, cy, cw, ch);

        // Crosshair
        if (this._crosshairEnabled) {
          this._svgOverlay.showCrosshair(cx, cy, cw, ch, this._layout, rowId, colId);
        } else {
          this._svgOverlay.hideCrosshair();
        }
      }
    } else {
      this._hide();
    }
  }

  _hide() {
    if (this._showingCellTooltip) {
      this._tooltip.style.display = "none";
      this._showingCellTooltip = false;
    }
    this._svgOverlay.hideHoverHighlight();
    this._svgOverlay.hideCrosshair();
  }

  _escHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
}
