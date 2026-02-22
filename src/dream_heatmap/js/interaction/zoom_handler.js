/**
 * ZoomHandler: zoom into selection, double-click to reset.
 *
 * After a selection is made, pressing 'z' or calling zoomToSelection()
 * zooms into the selected range. Double-clicking resets to full view.
 * Zoom events are communicated to Python via ModelSync, which triggers
 * a re-render with the zoomed IDMappers and layout.
 */

class ZoomHandler {
  /**
   * @param {SVGElement} svg - the SVG overlay element
   * @param {ModelSync} modelSync - for sending zoom range to Python
   * @param {Viewport} viewport - tracks current zoom state
   * @param {SVGOverlay} svgOverlay - for immediately hiding selection overlay
   */
  constructor(svg, modelSync, viewport, svgOverlay) {
    this._svg = svg;
    this._modelSync = modelSync;
    this._viewport = viewport;
    this._svgOverlay = svgOverlay;

    this._layout = null;
    this._rowResolver = null;
    this._colResolver = null;

    // Last selection bounds (set by SelectionHandler)
    this._lastSelectionBounds = null;

    this._bindEvents();
  }

  /**
   * Update the data context (called after each render).
   */
  setContext(layout, rowResolver, colResolver) {
    this._layout = layout;
    this._rowResolver = rowResolver;
    this._colResolver = colResolver;
  }

  /**
   * Store the last selection's visual index bounds for zoom.
   * Called by SelectionHandler after a successful selection.
   * @param {{rowStart: number, rowEnd: number, colStart: number, colEnd: number}} bounds
   */
  setLastSelectionBounds(bounds) {
    this._lastSelectionBounds = bounds;
  }

  _bindEvents() {
    // Double-click to reset zoom
    this._svg.addEventListener("dblclick", (e) => {
      e.preventDefault();
      if (this._viewport.isZoomed) {
        this._resetZoom();
      }
    });

    // 'z' key to zoom into current selection
    document.addEventListener("keydown", (e) => {
      if (e.key === "z" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        if (!this._svg.isConnected) return;
        if (this._lastSelectionBounds) {
          this._zoomToSelection();
        } else {
          this._showFeedback("Select a region first, then press Z to zoom");
        }
      }
    });
  }

  /** Public wrapper for toolbar use. */
  zoomToSelection() { this._zoomToSelection(); }
  /** Public wrapper for toolbar use. */
  resetZoom() { this._resetZoom(); }

  _zoomToSelection() {
    if (!this._lastSelectionBounds) return;

    const { rowStart, rowEnd, colStart, colEnd } = this._lastSelectionBounds;
    if (rowStart >= rowEnd || colStart >= colEnd) return;

    // Hide selection overlay immediately (don't wait for Python round-trip)
    this._svgOverlay.hideSelection();

    this._viewport.setRange(rowStart, rowEnd, colStart, colEnd);

    // Send zoom range to Python
    this._modelSync.setZoomRange({
      row_start: rowStart,
      row_end: rowEnd,
      col_start: colStart,
      col_end: colEnd,
    });
  }

  _resetZoom() {
    this._svgOverlay.hideSelection();
    this._viewport.reset();
    this._lastSelectionBounds = null;
    this._modelSync.setZoomRange(null);
  }

  _showFeedback(message) {
    // Show a brief toast overlay that auto-dismisses after 2s
    const container = this._svg.parentElement;
    if (!container) return;
    const toast = document.createElement("div");
    toast.textContent = message;
    toast.style.cssText =
      "position:absolute;bottom:12px;left:50%;transform:translateX(-50%);" +
      "background:rgba(15,23,42,0.8);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);" +
      "color:#f8fafc;padding:7px 16px;border-radius:8px;" +
      "font-size:12px;font-family:'Outfit',system-ui,-apple-system,sans-serif;font-weight:500;" +
      "pointer-events:none;z-index:300;white-space:nowrap;opacity:1;transition:opacity 0.3s;" +
      "box-shadow:0 4px 12px rgba(0,0,0,0.15);letter-spacing:-0.01em;";
    container.appendChild(toast);
    setTimeout(() => { toast.style.opacity = "0"; }, 1700);
    setTimeout(() => { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 2000);
  }
}
