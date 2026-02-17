/**
 * SelectionHandler: rectangle selection with cell-snapping.
 *
 * User drags a rectangle on the heatmap. The rectangle snaps to
 * cell boundaries so it always selects whole cells. On release,
 * the selected row/col IDs are sent to Python via ModelSync.
 */

class SelectionHandler {
  /**
   * @param {SVGElement} svg - the SVG overlay element for mouse events
   * @param {SVGOverlay} svgOverlay - for selection rectangle rendering
   * @param {ModelSync} modelSync - for sending selection to Python
   * @param {HoverHandler} hoverHandler - to suppress hover during drag
   */
  constructor(svg, svgOverlay, modelSync, hoverHandler) {
    this._svg = svg;
    this._svgOverlay = svgOverlay;
    this._modelSync = modelSync;
    this._hoverHandler = hoverHandler;

    this._isDragging = false;
    this._dragStart = null;

    // References set externally via setContext
    this._layout = null;
    this._rowResolver = null;
    this._colResolver = null;

    // Optional zoom handler to notify of selection bounds
    this._zoomHandler = null;

    this._bindEvents();
  }

  /**
   * Attach a ZoomHandler to receive selection bounds.
   * @param {ZoomHandler} zoomHandler
   */
  setZoomHandler(zoomHandler) {
    this._zoomHandler = zoomHandler;
  }

  /**
   * Update the data context (called after each render).
   */
  setContext(layout, rowResolver, colResolver) {
    this._layout = layout;
    this._rowResolver = rowResolver;
    this._colResolver = colResolver;
  }

  /** @returns {boolean} whether a drag is in progress */
  get isDragging() { return this._isDragging; }

  _bindEvents() {
    this._svg.addEventListener("mousedown", (e) => this._onDown(e));
    this._svg.addEventListener("mousemove", (e) => this._onMove(e));
    this._svg.addEventListener("mouseup", (e) => this._onUp(e));
    this._svg.addEventListener("mouseleave", (e) => {
      if (this._isDragging) this._onUp(e);
    });
  }

  _getLocalCoords(e) {
    const rect = this._svg.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  _onDown(e) {
    if (e.button !== 0) return;
    this._dragStart = this._getLocalCoords(e);
    this._isDragging = true;
    this._hoverHandler.suppress();
    e.preventDefault();
  }

  _onMove(e) {
    if (!this._isDragging || !this._dragStart || !this._layout ||
        !this._rowResolver || !this._colResolver) return;

    const pos = this._getLocalCoords(e);
    const rawX1 = Math.min(this._dragStart.x, pos.x);
    const rawY1 = Math.min(this._dragStart.y, pos.y);
    const rawX2 = Math.max(this._dragStart.x, pos.x);
    const rawY2 = Math.max(this._dragStart.y, pos.y);

    // Only show selection if dragged far enough
    if (rawX2 - rawX1 < 3 && rawY2 - rawY1 < 3) return;

    // Snap to cell boundaries for visual feedback
    const result = IDResolver.resolveRect(
      rawX1, rawY1, rawX2, rawY2,
      this._rowResolver, this._colResolver
    );

    if (result.snapped) {
      this._svgOverlay.showSelection(
        result.snapped.x, result.snapped.y,
        result.snapped.width, result.snapped.height
      );
    } else {
      // Show raw rectangle if outside grid
      this._svgOverlay.showSelection(rawX1, rawY1, rawX2 - rawX1, rawY2 - rawY1);
    }
  }

  _onUp(e) {
    if (!this._isDragging || !this._dragStart ||
        !this._rowResolver || !this._colResolver) {
      this._isDragging = false;
      this._hoverHandler.resume();
      return;
    }

    const pos = this._getLocalCoords(e);
    const rawX1 = Math.min(this._dragStart.x, pos.x);
    const rawY1 = Math.min(this._dragStart.y, pos.y);
    const rawX2 = Math.max(this._dragStart.x, pos.x);
    const rawY2 = Math.max(this._dragStart.y, pos.y);

    if (rawX2 - rawX1 > 3 || rawY2 - rawY1 > 3) {
      // Resolve the selection with snapping
      const result = IDResolver.resolveRect(
        rawX1, rawY1, rawX2, rawY2,
        this._rowResolver, this._colResolver
      );

      this._modelSync.setSelection({
        row_ids: result.row_ids,
        col_ids: result.col_ids,
      });

      // Show the final snapped rectangle
      if (result.snapped) {
        this._svgOverlay.showSelection(
          result.snapped.x, result.snapped.y,
          result.snapped.width, result.snapped.height
        );
      }

      // Notify zoom handler of selection bounds (visual indices)
      if (this._zoomHandler && result.rowRange && result.colRange) {
        this._zoomHandler.setLastSelectionBounds({
          rowStart: result.rowRange.start,
          rowEnd: result.rowRange.end,
          colStart: result.colRange.start,
          colEnd: result.colRange.end,
        });
      }
    } else {
      // Click without meaningful drag — clear selection
      this._modelSync.setSelection({ row_ids: [], col_ids: [] });
      this._svgOverlay.hideSelection();
    }

    this._isDragging = false;
    this._dragStart = null;
    this._hoverHandler.resume();
  }
}
