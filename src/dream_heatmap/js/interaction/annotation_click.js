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

    // Set selection
    if (isRow) {
      this._modelSync.setSelection({ row_ids: memberIds, col_ids: allOtherIds });
    } else {
      this._modelSync.setSelection({ row_ids: allOtherIds, col_ids: memberIds });
    }

    // Highlight: find bounding visual range of matched indices
    this._highlightMembers(new Set(memberIds), resolver, axis);
  }

  /**
   * Highlight selected members by showing a selection rectangle
   * spanning the selected rows or columns.
   */
  _highlightMembers(memberSet, resolver, axis) {
    if (!this._layout) return;

    let minIdx = Infinity;
    let maxIdx = -Infinity;
    for (let i = 0; i < resolver.size; i++) {
      if (memberSet.has(resolver.visualOrder[i])) {
        minIdx = Math.min(minIdx, i);
        maxIdx = Math.max(maxIdx, i);
      }
    }
    if (minIdx === Infinity) return;

    const heatmap = this._layout.heatmap;
    if (axis === "row") {
      const yStart = resolver.cellPositions[minIdx];
      const yEnd = resolver.cellPositions[maxIdx] + resolver.cellSize;
      this._svgOverlay.showSelection(
        heatmap.x, yStart, heatmap.width, yEnd - yStart
      );
      if (this._zoomHandler) {
        this._zoomHandler.setLastSelectionBounds({
          rowStart: minIdx, rowEnd: maxIdx + 1,
          colStart: 0, colEnd: this._colResolver.size,
        });
      }
    } else {
      const xStart = resolver.cellPositions[minIdx];
      const xEnd = resolver.cellPositions[maxIdx] + resolver.cellSize;
      this._svgOverlay.showSelection(
        xStart, heatmap.y, xEnd - xStart, heatmap.height
      );
      if (this._zoomHandler) {
        this._zoomHandler.setLastSelectionBounds({
          rowStart: 0, rowEnd: this._rowResolver.size,
          colStart: minIdx, colEnd: maxIdx + 1,
        });
      }
    }
  }
}
