/**
 * DendrogramClickHandler: click a dendrogram branch → select subtree members.
 *
 * When a user clicks a branch in the dendrogram, all row or column IDs
 * in that subtree are selected and sent to Python.
 */

class DendrogramClickHandler {
  /**
   * @param {SVGOverlay} svgOverlay - for showing selection rect
   * @param {ModelSync} modelSync - for sending selection to Python
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
   * Set zoom handler reference for enabling zoom-to-selection after branch click.
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
   * Handle a dendrogram branch click.
   * Called from SVGOverlay's dendrogram rendering.
   *
   * @param {Array} memberIds - IDs in the clicked subtree
   * @param {string} axis - "row" or "col"
   */
  onBranchClick(memberIds, axis) {
    if (!memberIds || memberIds.length === 0) return;

    const memberSet = new Set(memberIds);

    if (axis === "row" && this._rowResolver && this._colResolver) {
      // Select all rows in the subtree, all columns
      const allColIds = this._colResolver.visualRangeToIds(0, this._colResolver.size);
      this._modelSync.setSelection({
        row_ids: memberIds,
        col_ids: allColIds,
      });
      this._highlightMembers(memberSet, this._rowResolver, "row");
    } else if (axis === "col" && this._rowResolver && this._colResolver) {
      // Select all columns in the subtree, all rows
      const allRowIds = this._rowResolver.visualRangeToIds(0, this._rowResolver.size);
      this._modelSync.setSelection({
        row_ids: allRowIds,
        col_ids: memberIds,
      });
      this._highlightMembers(memberSet, this._colResolver, "col");
    }
  }

  /**
   * Highlight selected members by showing a selection rectangle
   * spanning the selected rows or columns.
   */
  _highlightMembers(memberSet, resolver, axis) {
    if (!this._layout) return;

    // Find min and max visual indices of members
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
