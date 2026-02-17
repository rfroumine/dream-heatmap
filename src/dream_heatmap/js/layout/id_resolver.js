/**
 * IDResolver: JS mirror of Python's IDMapper.
 * Maps pixel coordinates → visual indices → original IDs.
 */

class IDResolver {
  /**
   * @param {object} mapperData - {visual_order: [...], gap_positions: [...], size: N}
   * @param {number[]} cellPositions - pixel start positions for each cell
   * @param {number} cellSize - pixel size of each cell
   */
  constructor(mapperData, cellPositions, cellSize) {
    this.visualOrder = mapperData.visual_order;
    this.gapPositions = new Set(mapperData.gap_positions || []);
    this.cellPositions = cellPositions;
    this.cellSize = cellSize;
    this.size = mapperData.size;
  }

  /**
   * Map a pixel coordinate to a visual index via binary search.
   * @param {number} pixel
   * @returns {number|null} visual index or null if in gap/outside
   */
  pixelToVisualIndex(pixel) {
    if (this.size === 0) return null;

    const first = this.cellPositions[0];
    const last = this.cellPositions[this.size - 1];
    if (pixel < first || pixel >= last + this.cellSize) {
      return null;
    }

    // Binary search: find largest index where cellPositions[index] <= pixel
    let lo = 0;
    let hi = this.size - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >>> 1;
      if (this.cellPositions[mid] <= pixel) {
        lo = mid + 1;
      } else {
        hi = mid - 1;
      }
    }

    const index = hi;
    if (index < 0 || index >= this.size) return null;

    // Check pixel is within this cell (not in a trailing gap)
    if (pixel < this.cellPositions[index] + this.cellSize) {
      return index;
    }
    return null; // in a gap
  }

  /**
   * Map a visual index range [start, end) to original IDs.
   * @param {number} start
   * @param {number} end
   * @returns {Array} original IDs
   */
  visualRangeToIds(start, end) {
    start = Math.max(0, start);
    end = Math.min(this.size, end);
    if (start >= end) return [];
    return this.visualOrder.slice(start, end);
  }

  /**
   * Find the first cell index whose cell region overlaps pixel.
   * Uses binary search. Returns null if pixel is past all cells.
   * @param {number} pixel
   * @returns {number|null}
   */
  findFirstOverlapping(pixel) {
    if (this.size === 0) return null;
    // We want the first i where cellPositions[i] + cellSize > pixel
    // i.e. the cell hasn't ended before pixel
    let lo = 0;
    let hi = this.size;
    while (lo < hi) {
      const mid = (lo + hi) >>> 1;
      if (this.cellPositions[mid] + this.cellSize <= pixel) {
        lo = mid + 1;
      } else {
        hi = mid;
      }
    }
    return lo < this.size ? lo : null;
  }

  /**
   * Find the last cell index whose cell region overlaps pixel.
   * Uses binary search. Returns null if pixel is before all cells.
   * @param {number} pixel
   * @returns {number|null}
   */
  findLastOverlapping(pixel) {
    if (this.size === 0) return null;
    // We want the last i where cellPositions[i] < pixel
    // (the cell starts before the pixel)
    let lo = 0;
    let hi = this.size - 1;
    if (this.cellPositions[0] >= pixel) return null;

    while (lo <= hi) {
      const mid = (lo + hi) >>> 1;
      if (this.cellPositions[mid] < pixel) {
        lo = mid + 1;
      } else {
        hi = mid - 1;
      }
    }
    return hi >= 0 ? hi : null;
  }

  /**
   * Get pixel bounds [start, end) for a cell at visual index.
   * @param {number} index
   * @returns {{start: number, end: number}|null}
   */
  getCellBounds(index) {
    if (index < 0 || index >= this.size) return null;
    return {
      start: this.cellPositions[index],
      end: this.cellPositions[index] + this.cellSize,
    };
  }

  /**
   * Snap a pixel range to cell boundaries.
   * Returns the visual index range [startIdx, endIdx] (inclusive)
   * and the corresponding snapped pixel range.
   * @param {number} pixelStart
   * @param {number} pixelEnd
   * @returns {{startIdx: number, endIdx: number, pixelStart: number, pixelEnd: number}|null}
   */
  snapRange(pixelStart, pixelEnd) {
    const startIdx = this.findFirstOverlapping(pixelStart);
    const endIdx = this.findLastOverlapping(pixelEnd);
    if (startIdx === null || endIdx === null || startIdx > endIdx) return null;

    return {
      startIdx,
      endIdx,
      pixelStart: this.cellPositions[startIdx],
      pixelEnd: this.cellPositions[endIdx] + this.cellSize,
    };
  }

  /**
   * Resolve a pixel rectangle to original IDs, with snapped bounds.
   * @param {number} x1 - left pixel
   * @param {number} y1 - top pixel
   * @param {number} x2 - right pixel
   * @param {number} y2 - bottom pixel
   * @param {IDResolver} rowResolver
   * @param {IDResolver} colResolver
   * @returns {{row_ids: Array, col_ids: Array, snapped: {x: number, y: number, width: number, height: number}|null}}
   */
  static resolveRect(x1, y1, x2, y2, rowResolver, colResolver) {
    const rowSnap = rowResolver.snapRange(y1, y2);
    const colSnap = colResolver.snapRange(x1, x2);

    if (!rowSnap || !colSnap) {
      return { row_ids: [], col_ids: [], snapped: null };
    }

    return {
      row_ids: rowResolver.visualRangeToIds(rowSnap.startIdx, rowSnap.endIdx + 1),
      col_ids: colResolver.visualRangeToIds(colSnap.startIdx, colSnap.endIdx + 1),
      rowRange: { start: rowSnap.startIdx, end: rowSnap.endIdx + 1 },
      colRange: { start: colSnap.startIdx, end: colSnap.endIdx + 1 },
      snapped: {
        x: colSnap.pixelStart,
        y: rowSnap.pixelStart,
        width: colSnap.pixelEnd - colSnap.pixelStart,
        height: rowSnap.pixelEnd - rowSnap.pixelStart,
      },
    };
  }
}
