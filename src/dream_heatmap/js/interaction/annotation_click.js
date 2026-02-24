/**
 * AnnotationClickHandler: click a category in an annotation track → select
 * all rows/columns with that category value.
 *
 * Follows the same pattern as DendrogramClickHandler.
 */

class AnnotationClickHandler {
  /**
   * @param {SVGOverlay} svgOverlay - for showing selection rect
   * @param {object} modelSync - for sending selection to Python
   */
  constructor(svgOverlay, modelSync) {
    this._svgOverlay = svgOverlay;
    this._modelSync = modelSync;

    // Set via setContext
    this._rowResolver = null;
    this._colResolver = null;
    this._layout = null;
    this._zoomHandler = null;
  }

  /**
   * Set zoom handler reference for enabling zoom-to-selection after click.
   * @param {ZoomHandler} zoomHandler
   */
  setZoomHandler(zoomHandler) {
    this._zoomHandler = zoomHandler;
  }

  /**
   * Update context after each render.
   */
  setContext(layout, rowResolver, colResolver) {
    this._layout = layout;
    this._rowResolver = rowResolver;
    this._colResolver = colResolver;
  }

  /**
   * Handle a category click in an annotation track.
   *
   * @param {string} categoryName - the clicked category value
   * @param {string} edge - "left", "right", "top", or "bottom"
   * @param {Array<string>} cellLabels - per-cell category labels for the track
   */
  onCategoryClick(categoryName, edge, cellLabels) {
    if (!categoryName || !cellLabels || cellLabels.length === 0) return;

    const isRow = (edge === "left" || edge === "right");
    const axis = isRow ? "row" : "col";
    const resolver = isRow ? this._rowResolver : this._colResolver;
    const otherResolver = isRow ? this._colResolver : this._rowResolver;

    if (!resolver || !otherResolver) return;

    // Find visual indices where the category matches
    const matchedIndices = [];
    for (let i = 0; i < cellLabels.length; i++) {
      if (cellLabels[i] === categoryName) {
        matchedIndices.push(i);
      }
    }
    if (matchedIndices.length === 0) return;

    // Map visual indices to original IDs
    const memberIds = matchedIndices.map(i => resolver.visualOrder[i]);
    const allOtherIds = otherResolver.visualRangeToIds(0, otherResolver.size);

    // Set selection (include category label)
    if (isRow) {
      this._modelSync.setSelection({ row_ids: memberIds, col_ids: allOtherIds, label: categoryName });
    } else {
      this._modelSync.setSelection({ row_ids: allOtherIds, col_ids: memberIds, label: categoryName });
    }

    // Highlight: draw one rect per contiguous run of matched indices
    this._highlightRuns(matchedIndices, resolver, axis, memberIds, allOtherIds);
  }

  /**
   * Find contiguous runs in a sorted array of indices.
   * e.g. [2,3,4, 9,10, 15] → [{start:2, end:4}, {start:9, end:10}, {start:15, end:15}]
   * @returns {Array<{start: number, end: number}>} inclusive ranges
   */
  _findRuns(sortedIndices) {
    const runs = [];
    let runStart = sortedIndices[0];
    let runEnd = sortedIndices[0];
    for (let i = 1; i < sortedIndices.length; i++) {
      if (sortedIndices[i] === runEnd + 1) {
        runEnd = sortedIndices[i];
      } else {
        runs.push({ start: runStart, end: runEnd });
        runStart = sortedIndices[i];
        runEnd = sortedIndices[i];
      }
    }
    runs.push({ start: runStart, end: runEnd });
    return runs;
  }

  /**
   * Highlight selected members by showing one selection rectangle
   * per contiguous run of matched visual indices.
   */
  _highlightRuns(matchedIndices, resolver, axis, memberIds, allOtherIds) {
    if (!this._layout) return;

    const runs = this._findRuns(matchedIndices);
    const heatmap = this._layout.heatmap;
    const rects = [];

    for (const run of runs) {
      if (axis === "row") {
        const yStart = resolver.cellPositions[run.start];
        const yEnd = resolver.cellPositions[run.end] + resolver.cellSize;
        rects.push({ x: heatmap.x, y: yStart, width: heatmap.width, height: yEnd - yStart });
      } else {
        const xStart = resolver.cellPositions[run.start];
        const xEnd = resolver.cellPositions[run.end] + resolver.cellSize;
        rects.push({ x: xStart, y: heatmap.y, width: xEnd - xStart, height: heatmap.height });
      }
    }

    this._svgOverlay.showSelectionRects(rects);

    // Store IDs for ID-based zoom (not range-based)
    if (this._zoomHandler) {
      if (axis === "row") {
        this._zoomHandler.setLastSelectionIds({ row_ids: memberIds, col_ids: allOtherIds });
      } else {
        this._zoomHandler.setLastSelectionIds({ row_ids: allOtherIds, col_ids: memberIds });
      }
    }
  }
}
