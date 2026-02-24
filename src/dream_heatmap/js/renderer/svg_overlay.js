/**
 * SVGOverlay: manages the SVG layer for annotations, dendrograms,
 * labels, selection rectangle, and hover highlight.
 */

class SVGOverlay {
  /**
   * @param {SVGElement} svg - root SVG element
   */
  constructor(svg) {
    this.svg = svg;
    this.selectionRect = null;
    this.hoverRect = null;
    this.hoverRectInner = null;
    this.dendrogramGroups = {};  // {side: SVGGElement}
    this._crosshairGroup = null;
    this._tooltip = null;  // set via setTooltip()
  }

  /** Set a tooltip DOM element for annotation hover. */
  setTooltip(tooltip) { this._tooltip = tooltip; }

  /**
   * Size the SVG to match the layout.
   * @param {object} layout
   */
  resize(layout) {
    this.svg.setAttribute("width", layout.totalWidth);
    this.svg.setAttribute("height", layout.totalHeight);
    this.svg.style.position = "absolute";
    this.svg.style.top = "0";
    this.svg.style.left = "0";
    this.svg.style.pointerEvents = "all";
  }

  // --- Hover highlight ---

  showHoverHighlight(x, y, width, height) {
    // Outer rect (white) for visibility on dark cells
    if (!this.hoverRect) {
      this.hoverRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      this.hoverRect.setAttribute("fill", "none");
      this.hoverRect.setAttribute("stroke", "rgba(255,255,255,0.95)");
      this.hoverRect.setAttribute("stroke-width", "2");
      this.hoverRect.style.pointerEvents = "none";
      this.svg.appendChild(this.hoverRect);
    }
    // Inner rect (dark) for visibility on light cells
    if (!this.hoverRectInner) {
      this.hoverRectInner = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      this.hoverRectInner.setAttribute("fill", "none");
      this.hoverRectInner.setAttribute("stroke", "rgba(15,23,42,0.5)");
      this.hoverRectInner.setAttribute("stroke-width", "1");
      this.hoverRectInner.style.pointerEvents = "none";
      this.svg.appendChild(this.hoverRectInner);
    }
    for (const r of [this.hoverRect, this.hoverRectInner]) {
      r.setAttribute("x", x);
      r.setAttribute("y", y);
      r.setAttribute("width", width);
      r.setAttribute("height", height);
      r.style.display = "";
    }
  }

  hideHoverHighlight() {
    if (this.hoverRect) this.hoverRect.style.display = "none";
    if (this.hoverRectInner) this.hoverRectInner.style.display = "none";
  }

  // --- Crosshair ---

  showCrosshair(cellX, cellY, cellW, cellH, layout, rowId, colId) {
    const hm = layout.heatmap;
    if (!this._crosshairGroup) {
      const ns = "http://www.w3.org/2000/svg";
      this._crosshairGroup = document.createElementNS(ns, "g");
      this._crosshairGroup.style.pointerEvents = "none";
      // Row highlight band
      this._chRowBand = document.createElementNS(ns, "rect");
      this._chRowBand.setAttribute("fill", "rgba(13,148,136,0.05)");
      this._crosshairGroup.appendChild(this._chRowBand);
      // Col highlight band
      this._chColBand = document.createElementNS(ns, "rect");
      this._chColBand.setAttribute("fill", "rgba(13,148,136,0.05)");
      this._crosshairGroup.appendChild(this._chColBand);
      // Horizontal dashed line
      this._chHLine = document.createElementNS(ns, "line");
      this._chHLine.setAttribute("stroke", "rgba(13,148,136,0.3)");
      this._chHLine.setAttribute("stroke-width", "1");
      this._chHLine.setAttribute("stroke-dasharray", "4,3");
      this._crosshairGroup.appendChild(this._chHLine);
      // Vertical dashed line
      this._chVLine = document.createElementNS(ns, "line");
      this._chVLine.setAttribute("stroke", "rgba(13,148,136,0.3)");
      this._chVLine.setAttribute("stroke-width", "1");
      this._chVLine.setAttribute("stroke-dasharray", "4,3");
      this._crosshairGroup.appendChild(this._chVLine);

      // Floating row spike label (left edge of heatmap)
      this._chRowLabel = document.createElementNS(ns, "g");
      this._chRowLabelBg = document.createElementNS(ns, "rect");
      this._chRowLabelBg.setAttribute("fill", "#fff");
      this._chRowLabelBg.setAttribute("stroke", "rgba(13,148,136,0.4)");
      this._chRowLabelBg.setAttribute("stroke-width", "0.5");
      this._chRowLabelBg.setAttribute("rx", "2");
      this._chRowLabel.appendChild(this._chRowLabelBg);
      this._chRowLabelText = document.createElementNS(ns, "text");
      this._chRowLabelText.setAttribute("font-size", "9");
      this._chRowLabelText.setAttribute("font-family", '"Outfit", system-ui, -apple-system, sans-serif');
      this._chRowLabelText.setAttribute("fill", "#0d9488");
      this._chRowLabelText.setAttribute("text-anchor", "end");
      this._chRowLabelText.setAttribute("dominant-baseline", "central");
      this._chRowLabel.appendChild(this._chRowLabelText);
      this._crosshairGroup.appendChild(this._chRowLabel);

      // Floating col spike label (bottom edge of heatmap)
      this._chColLabel = document.createElementNS(ns, "g");
      this._chColLabelBg = document.createElementNS(ns, "rect");
      this._chColLabelBg.setAttribute("fill", "#fff");
      this._chColLabelBg.setAttribute("stroke", "rgba(13,148,136,0.4)");
      this._chColLabelBg.setAttribute("stroke-width", "0.5");
      this._chColLabelBg.setAttribute("rx", "2");
      this._chColLabel.appendChild(this._chColLabelBg);
      this._chColLabelText = document.createElementNS(ns, "text");
      this._chColLabelText.setAttribute("font-size", "9");
      this._chColLabelText.setAttribute("font-family", '"Outfit", system-ui, -apple-system, sans-serif');
      this._chColLabelText.setAttribute("fill", "#0d9488");
      this._chColLabelText.setAttribute("text-anchor", "middle");
      this._chColLabelText.setAttribute("dominant-baseline", "hanging");
      this._chColLabel.appendChild(this._chColLabelText);
      this._crosshairGroup.appendChild(this._chColLabel);

      // Insert before hover rects but after content
      if (this.hoverRect) {
        this.svg.insertBefore(this._crosshairGroup, this.hoverRect);
      } else {
        this.svg.appendChild(this._crosshairGroup);
      }
    }
    const cy = cellY + cellH / 2;
    const cx = cellX + cellW / 2;
    // Row band
    this._chRowBand.setAttribute("x", hm.x);
    this._chRowBand.setAttribute("y", cellY);
    this._chRowBand.setAttribute("width", hm.width);
    this._chRowBand.setAttribute("height", cellH);
    // Col band
    this._chColBand.setAttribute("x", cellX);
    this._chColBand.setAttribute("y", hm.y);
    this._chColBand.setAttribute("width", cellW);
    this._chColBand.setAttribute("height", hm.height);
    // Horizontal line
    this._chHLine.setAttribute("x1", hm.x);
    this._chHLine.setAttribute("x2", hm.x + hm.width);
    this._chHLine.setAttribute("y1", cy);
    this._chHLine.setAttribute("y2", cy);
    // Vertical line
    this._chVLine.setAttribute("x1", cx);
    this._chVLine.setAttribute("x2", cx);
    this._chVLine.setAttribute("y1", hm.y);
    this._chVLine.setAttribute("y2", hm.y + hm.height);

    // Floating row spike label
    if (rowId != null) {
      const labelText = String(rowId);
      this._chRowLabelText.textContent = labelText;
      const lblX = hm.x - 4;
      this._chRowLabelText.setAttribute("x", lblX);
      this._chRowLabelText.setAttribute("y", cy);
      // Background rect sized to text
      const textLen = labelText.length * 5.5 + 8;
      this._chRowLabelBg.setAttribute("x", lblX - textLen);
      this._chRowLabelBg.setAttribute("y", cy - 7);
      this._chRowLabelBg.setAttribute("width", textLen);
      this._chRowLabelBg.setAttribute("height", 14);
      this._chRowLabel.style.display = "";
    } else {
      this._chRowLabel.style.display = "none";
    }

    // Floating col spike label
    if (colId != null) {
      const labelText = String(colId);
      this._chColLabelText.textContent = labelText;
      const lblY = hm.y + hm.height + 4;
      this._chColLabelText.setAttribute("x", cx);
      this._chColLabelText.setAttribute("y", lblY);
      const textLen = labelText.length * 5.5 + 8;
      this._chColLabelBg.setAttribute("x", cx - textLen / 2);
      this._chColLabelBg.setAttribute("y", lblY - 1);
      this._chColLabelBg.setAttribute("width", textLen);
      this._chColLabelBg.setAttribute("height", 14);
      this._chColLabel.style.display = "";
    } else {
      this._chColLabel.style.display = "none";
    }

    this._crosshairGroup.style.display = "";

    // Show all auto-hidden labels when crosshair is active
    if (this._labelGroup) {
      this._labelGroup.classList.add("dh-show-all-labels");
    }
  }

  hideCrosshair() {
    if (this._crosshairGroup) this._crosshairGroup.style.display = "none";
    if (this._labelGroup) this._labelGroup.classList.remove("dh-show-all-labels");
  }

  // --- Selection rectangle ---

  showSelection(x, y, width, height) {
    this.showSelectionRects([{ x, y, width, height }]);
  }

  /**
   * Show multiple disjoint selection rectangles (one per contiguous run).
   * @param {Array<{x: number, y: number, width: number, height: number}>} rects
   */
  showSelectionRects(rects) {
    // Clear previous multi-rect group
    this._clearSelectionGroup();

    if (!this._selectionGroup) {
      this._selectionGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
      this._selectionGroup.style.pointerEvents = "none";
      this.svg.appendChild(this._selectionGroup);
    }
    this._selectionGroup.style.display = "";

    for (const { x, y, width, height } of rects) {
      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", x);
      rect.setAttribute("y", y);
      rect.setAttribute("width", Math.max(0, width));
      rect.setAttribute("height", Math.max(0, height));
      rect.setAttribute("fill", "rgba(13,148,136,0.08)");
      rect.setAttribute("stroke", "rgba(13,148,136,0.6)");
      rect.setAttribute("stroke-width", "1.5");
      rect.setAttribute("stroke-dasharray", "5,4");
      this._selectionGroup.appendChild(rect);
    }

    // Keep legacy selectionRect hidden when using multi-rect
    if (this.selectionRect) this.selectionRect.style.display = "none";
  }

  hideSelection() {
    if (this.selectionRect) {
      this.selectionRect.style.display = "none";
    }
    this._clearSelectionGroup();
  }

  _clearSelectionGroup() {
    if (this._selectionGroup) {
      while (this._selectionGroup.firstChild) {
        this._selectionGroup.removeChild(this._selectionGroup.firstChild);
      }
      this._selectionGroup.style.display = "none";
    }
  }

  // --- Dendrograms ---

  /**
   * Render dendrograms from the layout dendrogram specs.
   * @param {object} dendrograms - {row: dendroSpec|null, col: dendroSpec|null}
   * @param {object} layout - full layout spec
   * @param {function} onBranchClick - callback(memberIds) when branch is clicked
   */
  renderDendrograms(dendrograms, layout, onBranchClick) {
    // Clear previous dendrograms
    for (const side in this.dendrogramGroups) {
      const g = this.dendrogramGroups[side];
      if (g && g.parentNode) g.parentNode.removeChild(g);
    }
    this.dendrogramGroups = {};

    if (!dendrograms) return;

    if (dendrograms.row) {
      this._renderDendrogram(dendrograms.row, layout, "row", onBranchClick);
    }
    if (dendrograms.col) {
      this._renderDendrogram(dendrograms.col, layout, "col", onBranchClick);
    }
  }

  /**
   * Render a single dendrogram (row or col).
   */
  _renderDendrogram(spec, layout, axis, onBranchClick) {
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("class", `dendrogram-${spec.side}`);
    this.dendrogramGroups[spec.side] = g;

    const heatmap = layout.heatmap;

    for (const link of spec.links) {
      let path;
      if (axis === "row") {
        // Row dendrogram: drawn to the left of the heatmap
        // leaf axis = vertical (y), height axis = horizontal (x, growing left)
        const dendroRight = heatmap.x;  // right edge of dendro area
        const y1 = link.leafLeft;
        const y2 = link.leafRight;
        const xMerge = dendroRight - link.heightMerge;
        const xLeft = dendroRight - link.heightLeftChild;
        const xRight = dendroRight - link.heightRightChild;

        path = this._createUPath(xLeft, y1, xMerge, xRight, y2, "horizontal");
      } else {
        // Col dendrogram: drawn above the heatmap
        // leaf axis = horizontal (x), height axis = vertical (y, growing up)
        const dendroBottom = heatmap.y;  // bottom edge of dendro area
        const x1 = link.leafLeft;
        const x2 = link.leafRight;
        const yMerge = dendroBottom - link.heightMerge;
        const yLeft = dendroBottom - link.heightLeftChild;
        const yRight = dendroBottom - link.heightRightChild;

        path = this._createUPath(x1, yLeft, yMerge, x2, yRight, "vertical");
      }

      // Style
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", "#cbd5e1");
      path.setAttribute("stroke-width", "1");
      path.style.cursor = "pointer";

      // Click to select subtree
      const memberIds = link.memberIds;
      path.addEventListener("click", (e) => {
        e.stopPropagation();
        if (onBranchClick) onBranchClick(memberIds, axis);
      });

      // Hover highlight
      path.addEventListener("mouseenter", () => {
        path.setAttribute("stroke", "#e11d48");
        path.setAttribute("stroke-width", "1.5");
      });
      path.addEventListener("mouseleave", () => {
        path.setAttribute("stroke", "#cbd5e1");
        path.setAttribute("stroke-width", "1");
      });

      g.appendChild(path);
    }

    // Insert dendrograms before selection/hover rects
    if (this.svg.firstChild) {
      this.svg.insertBefore(g, this.svg.firstChild);
    } else {
      this.svg.appendChild(g);
    }
  }

  /**
   * Create a U-shaped SVG path for a dendrogram link.
   *
   * For horizontal U (row dendro): three segments connecting two leaf positions
   *   via a merge point to the left.
   * For vertical U (col dendro): three segments connecting two leaf positions
   *   via a merge point above.
   */
  _createUPath(pos1, childHeight1, mergeHeight, pos2, childHeight2, orientation) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    let d;

    if (orientation === "horizontal") {
      // Row dendrogram: U opens leftward
      // pos1, pos2 = y positions of children
      // childHeight1/2 = x positions of children, mergeHeight = x merge point
      // (xChild1, y1) → (xMerge, y1) → (xMerge, y2) → (xChild2, y2)
      d = `M ${pos1} ${childHeight1} L ${mergeHeight} ${childHeight1} L ${mergeHeight} ${childHeight2} L ${pos2} ${childHeight2}`;
    } else {
      // vertical U (col dendro)
      // pos1, pos2 = x positions of children
      // horizontal from (pos1, childHeight1) up to (pos1, mergeHeight)
      // then across to (pos2, mergeHeight)
      // then down to (pos2, childHeight2)
      d = `M ${pos1} ${childHeight1} L ${pos1} ${mergeHeight} L ${pos2} ${mergeHeight} L ${pos2} ${childHeight2}`;
    }

    path.setAttribute("d", d);
    return path;
  }

  // --- Annotations ---

  /**
   * Render annotation tracks.
   * @param {object} annotations - {left: [...], right: [...], top: [...], bottom: [...]}
   * @param {object} layout - layout spec
   */
  renderAnnotations(annotations, layout, onCategoryClick) {
    // Remove previous annotation group
    if (this._annotationGroup) {
      this._annotationGroup.remove();
    }
    this._annotationGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this._annotationGroup.setAttribute("class", "annotations");

    if (!annotations) {
      this.svg.appendChild(this._annotationGroup);
      return;
    }

    for (const edge of ["left", "right", "top", "bottom"]) {
      const tracks = annotations[edge];
      if (!tracks || tracks.length === 0) continue;

      for (const track of tracks) {
        this._renderAnnotationTrack(track, edge, layout, onCategoryClick);
      }
    }

    // Insert before interactive elements
    if (this.svg.firstChild) {
      this.svg.insertBefore(this._annotationGroup, this.svg.firstChild);
    } else {
      this.svg.appendChild(this._annotationGroup);
    }
  }

  _renderAnnotationTrack(track, edge, layout, onCategoryClick) {
    const heatmap = layout.heatmap;
    const isRow = (edge === "left" || edge === "right");
    const positions = isRow ? layout.rowPositions : layout.colPositions;
    const cellSize = isRow ? layout.rowCellSize : layout.colCellSize;

    // Merge renderData properties into track object for backward compatibility
    // renderData contains the actual annotation data (type, labels, values, etc.)
    const renderData = track.renderData || {};
    const mergedTrack = {
      ...track,
      ...renderData,
      // Ensure offset and trackWidth are available (from track, not renderData)
      offset: track.offset,
      trackWidth: track.trackWidth,
    };
    const trackType = mergedTrack.type;

    // Secondary gaps: positions where annotation rects should bridge the gap
    const secondaryGaps = new Set(
      isRow ? (layout.rowSecondaryGaps || []) : (layout.colSecondaryGaps || [])
    );

    if (trackType === "categorical") {
      this._renderCategorical(mergedTrack, edge, positions, cellSize, heatmap, secondaryGaps, onCategoryClick);
    } else if (trackType === "bar") {
      this._renderBar(mergedTrack, edge, positions, cellSize, heatmap, secondaryGaps);
    } else if (trackType === "sparkline") {
      this._renderSparkline(mergedTrack, edge, positions, cellSize, heatmap, secondaryGaps);
    } else if (trackType === "boxplot") {
      this._renderBoxPlot(mergedTrack, edge, positions, cellSize, heatmap, secondaryGaps);
    } else if (trackType === "violin") {
      this._renderViolin(mergedTrack, edge, positions, cellSize, heatmap, secondaryGaps);
    } else if (trackType === "label") {
      this._renderLabelTrack(mergedTrack, edge, positions, cellSize, heatmap, secondaryGaps);
    }
  }

  _getTrackRect(edge, offset, trackWidth, heatmap) {
    if (edge === "left")  return { x: heatmap.x - offset - trackWidth, y: heatmap.y, w: trackWidth, h: heatmap.height };
    if (edge === "right") return { x: heatmap.x + heatmap.width + offset, y: heatmap.y, w: trackWidth, h: heatmap.height };
    if (edge === "top")   return { x: heatmap.x, y: heatmap.y - offset - trackWidth, w: heatmap.width, h: trackWidth };
    if (edge === "bottom")return { x: heatmap.x, y: heatmap.y + heatmap.height + offset, w: heatmap.width, h: trackWidth };
  }

  _renderCategorical(track, edge, positions, cellSize, heatmap, secondaryGaps, onCategoryClick) {
    const isRow = (edge === "left" || edge === "right");
    const area = this._getTrackRect(edge, track.offset, track.trackWidth, heatmap);
    const catLabels = track.cellLabels || [];

    for (let i = 0; i < track.cellColors.length; i++) {
      const color = track.cellColors[i];
      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      let rx, ry, rw, rh;
      // Bridge secondary gaps: extend rect to cover the gap to the next cell
      let extraSize = 0;
      if (secondaryGaps && secondaryGaps.has(i + 1) && i + 1 < positions.length) {
        extraSize = positions[i + 1] - (positions[i] + cellSize);
      }
      if (isRow) {
        rx = area.x; ry = positions[i]; rw = area.w; rh = cellSize + extraSize;
      } else {
        rx = positions[i]; ry = area.y; rw = cellSize + extraSize; rh = area.h;
      }
      rect.setAttribute("x", rx);
      rect.setAttribute("y", ry);
      rect.setAttribute("width", rw);
      rect.setAttribute("height", rh);
      rect.setAttribute("fill", color);
      // Hover tooltip for categorical cells
      const catName = catLabels[i] || "";
      if (catName && this._tooltip) {
        const tipHtml = `<span class="dh-tip-label">${track.name || "Category"}</span> ` +
          `<span class="dh-tip-swatch" style="background:${color}"></span>` +
          `<span class="dh-tip-value">${catName}</span>`;
        this._addAnnotationHover(rect, tipHtml);
      } else {
        rect.style.pointerEvents = "none";
      }
      // Click-to-select: click a colored cell to select all rows/cols with this category
      if (catName && onCategoryClick) {
        rect.style.cursor = "pointer";
        rect.addEventListener("click", (e) => {
          e.stopPropagation();
          onCategoryClick(catName, edge, catLabels);
        });
      }
      this._annotationGroup.appendChild(rect);
    }

    // Contiguous-run spanning labels (ComplexHeatmap style)
    if (track.showLabels === false) return;
    // Detect runs of the same category and render one centered label per run
    const runs = [];
    let runStart = 0;
    for (let i = 1; i <= catLabels.length; i++) {
      if (i === catLabels.length || catLabels[i] !== catLabels[runStart]) {
        if (catLabels[runStart]) {
          runs.push({ label: catLabels[runStart], start: runStart, end: i - 1,
            color: track.cellColors[runStart] });
        }
        runStart = i;
      }
    }

    const ns = "http://www.w3.org/2000/svg";
    for (const run of runs) {
      let spanStart, spanEnd, spanSize;
      if (isRow) {
        spanStart = positions[run.start];
        spanEnd = positions[run.end] + cellSize;
      } else {
        spanStart = positions[run.start];
        spanEnd = positions[run.end] + cellSize;
      }
      spanSize = spanEnd - spanStart;
      if (spanSize < 20) continue;  // too small to label

      const text = document.createElementNS(ns, "text");
      text.textContent = run.label;
      const fontSize = spanSize < 30 ? "8" : "9";
      text.setAttribute("font-size", fontSize);
      text.setAttribute("font-family", '"Outfit", system-ui, -apple-system, sans-serif');
      text.setAttribute("fill", this._contrastColor(run.color));
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("dominant-baseline", "central");

      // Click-to-select on run text labels
      if (onCategoryClick) {
        text.style.pointerEvents = "all";
        text.style.cursor = "pointer";
        text.addEventListener("click", (e) => {
          e.stopPropagation();
          onCategoryClick(run.label, edge, catLabels);
        });
      } else {
        text.style.pointerEvents = "none";
      }

      if (isRow) {
        // Vertical text centered on the run span
        const cx = area.x + area.w / 2;
        const cy = spanStart + spanSize / 2;
        text.setAttribute("x", cx);
        text.setAttribute("y", cy);
        text.setAttribute("transform", `rotate(-90, ${cx}, ${cy})`);
      } else {
        // Horizontal text centered on the run span
        text.setAttribute("x", spanStart + spanSize / 2);
        text.setAttribute("y", area.y + area.h / 2);
      }
      this._annotationGroup.appendChild(text);
    }
  }

  /**
   * Return white or black text color for best contrast against a background.
   */
  _contrastColor(bgColor) {
    // Parse hex or rgb color
    let r = 128, g = 128, b = 128;
    if (bgColor.startsWith("#")) {
      const hex = bgColor.replace("#", "");
      if (hex.length === 3) {
        r = parseInt(hex[0] + hex[0], 16);
        g = parseInt(hex[1] + hex[1], 16);
        b = parseInt(hex[2] + hex[2], 16);
      } else if (hex.length === 6) {
        r = parseInt(hex.substring(0, 2), 16);
        g = parseInt(hex.substring(2, 4), 16);
        b = parseInt(hex.substring(4, 6), 16);
      }
    } else {
      const m = bgColor.match(/(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
      if (m) { r = +m[1]; g = +m[2]; b = +m[3]; }
    }
    // Relative luminance (sRGB)
    const lum = 0.299 * r + 0.587 * g + 0.114 * b;
    return lum > 150 ? "#1e293b" : "#f8fafc";
  }

  _renderBar(track, edge, positions, cellSize, heatmap, secondaryGaps) {
    const isRow = (edge === "left" || edge === "right");
    const area = this._getTrackRect(edge, track.offset, track.trackWidth, heatmap);
    const range = track.vmax - track.vmin || 1;
    const ns = "http://www.w3.org/2000/svg";

    for (let i = 0; i < track.values.length; i++) {
      const val = track.values[i];
      const norm = Math.max(0, Math.min(1, (val - track.vmin) / range));
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("rx", "1");

      // Bridge secondary gaps
      let extraSize = 0;
      if (secondaryGaps && secondaryGaps.has(i + 1) && i + 1 < positions.length) {
        extraSize = positions[i + 1] - (positions[i] + cellSize);
      }

      if (isRow) {
        const barW = norm * area.w;
        rect.setAttribute("x", edge === "left" ? area.x + area.w - barW : area.x);
        rect.setAttribute("y", positions[i]);
        rect.setAttribute("width", barW);
        rect.setAttribute("height", cellSize + extraSize);
      } else {
        const barH = norm * area.h;
        rect.setAttribute("x", positions[i]);
        rect.setAttribute("y", edge === "top" ? area.y + area.h - barH : area.y);
        rect.setAttribute("width", cellSize + extraSize);
        rect.setAttribute("height", barH);
      }
      rect.setAttribute("fill", track.color);
      rect.style.pointerEvents = "none";
      this._annotationGroup.appendChild(rect);
    }

    // Full-cell transparent overlay rects for reliable hover
    if (this._tooltip) {
      for (let i = 0; i < track.values.length; i++) {
        const val = track.values[i];
        const hoverRect = document.createElementNS(ns, "rect");
        // Bridge secondary gaps for hover rects too
        let hoverExtra = 0;
        if (secondaryGaps && secondaryGaps.has(i + 1) && i + 1 < positions.length) {
          hoverExtra = positions[i + 1] - (positions[i] + cellSize);
        }
        if (isRow) {
          hoverRect.setAttribute("x", area.x);
          hoverRect.setAttribute("y", positions[i]);
          hoverRect.setAttribute("width", area.w);
          hoverRect.setAttribute("height", cellSize + hoverExtra);
        } else {
          hoverRect.setAttribute("x", positions[i]);
          hoverRect.setAttribute("y", area.y);
          hoverRect.setAttribute("width", cellSize + hoverExtra);
          hoverRect.setAttribute("height", area.h);
        }
        hoverRect.setAttribute("fill", "transparent");
        const displayVal = isFinite(val) ? parseFloat(val.toPrecision(4)) : "NaN";
        const tipHtml = `<span class="dh-tip-label">${track.name || "Bar"}</span> ` +
          `<span class="dh-tip-value">${displayVal}</span>`;
        this._addAnnotationHover(hoverRect, tipHtml);
        this._annotationGroup.appendChild(hoverRect);
      }
    }

    // Baseline axis line
    const axisLine = document.createElementNS(ns, "line");
    axisLine.setAttribute("stroke", "#cbd5e1");
    axisLine.setAttribute("stroke-width", "1");
    axisLine.style.pointerEvents = "none";

    const font = '"Outfit", system-ui, -apple-system, sans-serif';
    const minLabel = document.createElementNS(ns, "text");
    const maxLabel = document.createElementNS(ns, "text");
    for (const lbl of [minLabel, maxLabel]) {
      lbl.setAttribute("font-size", "8");
      lbl.setAttribute("font-family", font);
      lbl.setAttribute("fill", "#64748b");
      lbl.style.pointerEvents = "none";
    }
    const minText = isFinite(track.vmin) ? parseFloat(track.vmin.toPrecision(3)) : "";
    const maxText = isFinite(track.vmax) ? parseFloat(track.vmax.toPrecision(3)) : "";
    minLabel.textContent = minText;
    maxLabel.textContent = maxText;

    if (isRow) {
      // Baseline along the left/right edge where bars start
      const baseX = edge === "left" ? area.x + area.w : area.x;
      axisLine.setAttribute("x1", baseX);
      axisLine.setAttribute("x2", baseX);
      axisLine.setAttribute("y1", area.y);
      axisLine.setAttribute("y2", area.y + area.h);
      // Min at bottom, max at top (or vice versa based on bar direction)
      const tipX = edge === "left" ? area.x : area.x + area.w;
      minLabel.setAttribute("x", baseX);
      minLabel.setAttribute("y", area.y + area.h + 9);
      minLabel.setAttribute("text-anchor", "middle");
      maxLabel.setAttribute("x", tipX);
      maxLabel.setAttribute("y", area.y + area.h + 9);
      maxLabel.setAttribute("text-anchor", "middle");
    } else {
      // Baseline along the bottom/top edge where bars start
      const baseY = edge === "top" ? area.y + area.h : area.y;
      axisLine.setAttribute("x1", area.x);
      axisLine.setAttribute("x2", area.x + area.w);
      axisLine.setAttribute("y1", baseY);
      axisLine.setAttribute("y2", baseY);
      // Min at left, max at right
      const tipY = edge === "top" ? area.y : area.y + area.h;
      minLabel.setAttribute("x", area.x - 2);
      minLabel.setAttribute("y", baseY);
      minLabel.setAttribute("text-anchor", "end");
      minLabel.setAttribute("dominant-baseline", "central");
      maxLabel.setAttribute("x", area.x - 2);
      maxLabel.setAttribute("y", tipY);
      maxLabel.setAttribute("text-anchor", "end");
      maxLabel.setAttribute("dominant-baseline", "central");
    }

    this._annotationGroup.appendChild(axisLine);
    this._annotationGroup.appendChild(minLabel);
    this._annotationGroup.appendChild(maxLabel);
  }

  _renderSparkline(track, edge, positions, cellSize, heatmap, secondaryGaps) {
    const isRow = (edge === "left" || edge === "right");
    const area = this._getTrackRect(edge, track.offset, track.trackWidth, heatmap);
    const range = track.vmax - track.vmin || 1;

    for (let i = 0; i < track.series.length; i++) {
      const series = track.series[i];
      if (!series || series.length < 2) continue;

      const n = series.length;
      let points = [];
      if (isRow) {
        const xStep = area.w / (n - 1);
        for (let j = 0; j < n; j++) {
          if (series[j] === null) continue;
          const x = area.x + j * xStep;
          const norm = (series[j] - track.vmin) / range;
          const y = positions[i] + cellSize - norm * cellSize;
          points.push(`${x},${y}`);
        }
      } else {
        const yStep = area.h / (n - 1);
        for (let j = 0; j < n; j++) {
          if (series[j] === null) continue;
          const y = area.y + j * yStep;
          const norm = (series[j] - track.vmin) / range;
          const x = positions[i] + norm * cellSize;
          points.push(`${x},${y}`);
        }
      }

      if (points.length >= 2) {
        const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
        line.setAttribute("points", points.join(" "));
        line.setAttribute("fill", "none");
        line.setAttribute("stroke", track.color);
        line.setAttribute("stroke-width", "1");
        line.style.pointerEvents = "none";
        this._annotationGroup.appendChild(line);
      }

      // Hover tooltip
      if (this._tooltip) {
        const hoverRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        if (isRow) {
          hoverRect.setAttribute("x", area.x);
          hoverRect.setAttribute("y", positions[i]);
          hoverRect.setAttribute("width", area.w);
          hoverRect.setAttribute("height", cellSize);
        } else {
          hoverRect.setAttribute("x", positions[i]);
          hoverRect.setAttribute("y", area.y);
          hoverRect.setAttribute("width", cellSize);
          hoverRect.setAttribute("height", area.h);
        }
        hoverRect.setAttribute("fill", "transparent");
        const vals = series.filter(v => v !== null);
        const summary = vals.length <= 5
          ? vals.map(v => parseFloat(v.toPrecision(3))).join(", ")
          : `n=${vals.length}, range=[${parseFloat(Math.min(...vals).toPrecision(3))}, ${parseFloat(Math.max(...vals).toPrecision(3))}]`;
        const tipHtml = `<span class="dh-tip-label">${track.name || "Sparkline"}</span> ` +
          `<span class="dh-tip-value">${summary}</span>`;
        this._addAnnotationHover(hoverRect, tipHtml);
        this._annotationGroup.appendChild(hoverRect);
      }
    }
  }

  _renderBoxPlot(track, edge, positions, cellSize, heatmap, secondaryGaps) {
    const isRow = (edge === "left" || edge === "right");
    const area = this._getTrackRect(edge, track.offset, track.trackWidth, heatmap);
    const range = track.vmax - track.vmin || 1;

    for (let i = 0; i < track.stats.length; i++) {
      const s = track.stats[i];
      if (!s) continue;

      const norm = (v) => Math.max(0, Math.min(1, (v - track.vmin) / range));

      if (isRow) {
        const mapX = (v) => area.x + norm(v) * area.w;
        const cy = positions[i] + cellSize / 2;
        const boxH = cellSize * 0.6;

        // Whisker line
        const whisker = document.createElementNS("http://www.w3.org/2000/svg", "line");
        whisker.setAttribute("x1", mapX(s.min)); whisker.setAttribute("x2", mapX(s.max));
        whisker.setAttribute("y1", cy); whisker.setAttribute("y2", cy);
        whisker.setAttribute("stroke", track.color); whisker.setAttribute("stroke-width", "1");
        whisker.style.pointerEvents = "none";
        this._annotationGroup.appendChild(whisker);

        // Box
        const box = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        box.setAttribute("x", mapX(s.q1)); box.setAttribute("width", mapX(s.q3) - mapX(s.q1));
        box.setAttribute("y", cy - boxH / 2); box.setAttribute("height", boxH);
        box.setAttribute("fill", track.color); box.setAttribute("fill-opacity", "0.3");
        box.setAttribute("stroke", track.color); box.setAttribute("stroke-width", "1");
        box.style.pointerEvents = "none";
        this._annotationGroup.appendChild(box);

        // Median line
        const med = document.createElementNS("http://www.w3.org/2000/svg", "line");
        med.setAttribute("x1", mapX(s.median)); med.setAttribute("x2", mapX(s.median));
        med.setAttribute("y1", cy - boxH / 2); med.setAttribute("y2", cy + boxH / 2);
        med.setAttribute("stroke", track.color); med.setAttribute("stroke-width", "2");
        med.style.pointerEvents = "none";
        this._annotationGroup.appendChild(med);
      } else {
        const mapY = (v) => area.y + area.h - norm(v) * area.h;
        const cx = positions[i] + cellSize / 2;
        const boxW = cellSize * 0.6;

        const whisker = document.createElementNS("http://www.w3.org/2000/svg", "line");
        whisker.setAttribute("y1", mapY(s.min)); whisker.setAttribute("y2", mapY(s.max));
        whisker.setAttribute("x1", cx); whisker.setAttribute("x2", cx);
        whisker.setAttribute("stroke", track.color); whisker.setAttribute("stroke-width", "1");
        whisker.style.pointerEvents = "none";
        this._annotationGroup.appendChild(whisker);

        const box = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        box.setAttribute("y", mapY(s.q3)); box.setAttribute("height", mapY(s.q1) - mapY(s.q3));
        box.setAttribute("x", cx - boxW / 2); box.setAttribute("width", boxW);
        box.setAttribute("fill", track.color); box.setAttribute("fill-opacity", "0.3");
        box.setAttribute("stroke", track.color); box.setAttribute("stroke-width", "1");
        box.style.pointerEvents = "none";
        this._annotationGroup.appendChild(box);

        const med = document.createElementNS("http://www.w3.org/2000/svg", "line");
        med.setAttribute("y1", mapY(s.median)); med.setAttribute("y2", mapY(s.median));
        med.setAttribute("x1", cx - boxW / 2); med.setAttribute("x2", cx + boxW / 2);
        med.setAttribute("stroke", track.color); med.setAttribute("stroke-width", "2");
        med.style.pointerEvents = "none";
        this._annotationGroup.appendChild(med);
      }

      // Hover tooltip for box plot
      if (this._tooltip) {
        const hoverRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        if (isRow) {
          hoverRect.setAttribute("x", area.x);
          hoverRect.setAttribute("y", positions[i]);
          hoverRect.setAttribute("width", area.w);
          hoverRect.setAttribute("height", cellSize);
        } else {
          hoverRect.setAttribute("x", positions[i]);
          hoverRect.setAttribute("y", area.y);
          hoverRect.setAttribute("width", cellSize);
          hoverRect.setAttribute("height", area.h);
        }
        hoverRect.setAttribute("fill", "transparent");
        const fmt = (v) => parseFloat(v.toPrecision(3));
        const tipHtml = `<span class="dh-tip-label">${track.name || "BoxPlot"}</span> ` +
          `<span class="dh-tip-value">min=${fmt(s.min)} Q1=${fmt(s.q1)} med=${fmt(s.median)} Q3=${fmt(s.q3)} max=${fmt(s.max)}</span>`;
        this._addAnnotationHover(hoverRect, tipHtml);
        this._annotationGroup.appendChild(hoverRect);
      }
    }
  }

  _renderViolin(track, edge, positions, cellSize, heatmap, secondaryGaps) {
    const isRow = (edge === "left" || edge === "right");
    const area = this._getTrackRect(edge, track.offset, track.trackWidth, heatmap);

    for (let i = 0; i < track.densities.length; i++) {
      const d = track.densities[i];
      if (!d) continue;

      const { counts, centers } = d;
      const range = track.vmax - track.vmin || 1;

      if (isRow) {
        const cy = positions[i] + cellSize / 2;
        const halfH = cellSize * 0.4;
        let points = [];
        // Top half
        for (let j = 0; j < counts.length; j++) {
          const x = area.x + ((centers[j] - track.vmin) / range) * area.w;
          const y = cy - counts[j] * halfH;
          points.push(`${x},${y}`);
        }
        // Bottom half (reversed)
        for (let j = counts.length - 1; j >= 0; j--) {
          const x = area.x + ((centers[j] - track.vmin) / range) * area.w;
          const y = cy + counts[j] * halfH;
          points.push(`${x},${y}`);
        }
        const poly = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
        poly.setAttribute("points", points.join(" "));
        poly.setAttribute("fill", track.color);
        poly.setAttribute("fill-opacity", "0.4");
        poly.setAttribute("stroke", track.color);
        poly.setAttribute("stroke-width", "0.5");
        poly.style.pointerEvents = "none";
        this._annotationGroup.appendChild(poly);
      } else {
        const cx = positions[i] + cellSize / 2;
        const halfW = cellSize * 0.4;
        let points = [];
        for (let j = 0; j < counts.length; j++) {
          const y = area.y + area.h - ((centers[j] - track.vmin) / range) * area.h;
          const x = cx - counts[j] * halfW;
          points.push(`${x},${y}`);
        }
        for (let j = counts.length - 1; j >= 0; j--) {
          const y = area.y + area.h - ((centers[j] - track.vmin) / range) * area.h;
          const x = cx + counts[j] * halfW;
          points.push(`${x},${y}`);
        }
        const poly = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
        poly.setAttribute("points", points.join(" "));
        poly.setAttribute("fill", track.color);
        poly.setAttribute("fill-opacity", "0.4");
        poly.setAttribute("stroke", track.color);
        poly.setAttribute("stroke-width", "0.5");
        poly.style.pointerEvents = "none";
        this._annotationGroup.appendChild(poly);
      }

      // Hover tooltip for violin
      if (this._tooltip) {
        const hoverRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        if (isRow) {
          hoverRect.setAttribute("x", area.x);
          hoverRect.setAttribute("y", positions[i]);
          hoverRect.setAttribute("width", area.w);
          hoverRect.setAttribute("height", cellSize);
        } else {
          hoverRect.setAttribute("x", positions[i]);
          hoverRect.setAttribute("y", area.y);
          hoverRect.setAttribute("width", cellSize);
          hoverRect.setAttribute("height", area.h);
        }
        hoverRect.setAttribute("fill", "transparent");
        // Find peak density center
        let peakIdx = 0;
        for (let j = 1; j < counts.length; j++) {
          if (counts[j] > counts[peakIdx]) peakIdx = j;
        }
        const peakCenter = parseFloat(centers[peakIdx].toPrecision(3));
        const tipHtml = `<span class="dh-tip-label">${track.name || "Violin"}</span> ` +
          `<span class="dh-tip-value">peak at ${peakCenter}</span>`;
        this._addAnnotationHover(hoverRect, tipHtml);
        this._annotationGroup.appendChild(hoverRect);
      }
    }
  }

  _renderLabelTrack(track, edge, positions, cellSize, heatmap, secondaryGaps) {
    const isRow = (edge === "left" || edge === "right");
    const area = this._getTrackRect(edge, track.offset, track.trackWidth, heatmap);
    const fontSize = track.fontSize || 10;

    // Labels is an array of strings (from LabelAnnotation.get_render_data)
    const labels = track.labels || [];

    for (let i = 0; i < labels.length; i++) {
      // Handle both string labels and object labels (for backward compatibility)
      const labelText = typeof labels[i] === "string" ? labels[i] : (labels[i].text || labels[i]);
      const labelVisible = typeof labels[i] === "object" && labels[i].visible === false ? false : true;
      
      if (!labelVisible) continue;

      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.textContent = labelText;
      text.setAttribute("font-size", fontSize);
      text.setAttribute("font-family", '"Outfit", system-ui, -apple-system, sans-serif');
      text.setAttribute("fill", "#334155");
      text.style.pointerEvents = "none";

      if (isRow) {
        const cy = positions[i] + cellSize / 2;
        if (edge === "left") {
          text.setAttribute("x", area.x + area.w - 2);
          text.setAttribute("text-anchor", "end");
        } else {
          text.setAttribute("x", area.x + 2);
          text.setAttribute("text-anchor", "start");
        }
        text.setAttribute("y", cy);
        text.setAttribute("dominant-baseline", "central");
      } else {
        const cx = positions[i] + cellSize / 2;
        if (edge === "top") {
          text.setAttribute("x", cx);
          text.setAttribute("y", area.y + area.h - 2);
          text.setAttribute("text-anchor", "end");
          text.setAttribute("transform", `rotate(-90, ${cx}, ${area.y + area.h - 2})`);
        } else {
          text.setAttribute("x", cx);
          text.setAttribute("y", area.y + 2);
          text.setAttribute("text-anchor", "start");
          text.setAttribute("dominant-baseline", "hanging");
          text.setAttribute("transform", `rotate(-90, ${cx}, ${area.y + 2})`);
        }
      }

      this._annotationGroup.appendChild(text);
    }
  }

  // --- Annotation track titles ---

  _renderTrackTitle(track, edge, layout) {
    const heatmap = layout.heatmap;
    const isRow = (edge === "left" || edge === "right");
    const area = this._getTrackRect(edge, track.offset, track.trackWidth, heatmap);
    const font = '"Outfit", system-ui, -apple-system, sans-serif';
    const ns = "http://www.w3.org/2000/svg";
    const text = document.createElementNS(ns, "text");
    text.textContent = track.name || "";
    text.setAttribute("font-size", "9");
    text.setAttribute("font-family", font);
    text.setAttribute("fill", "#64748b");
    text.setAttribute("font-weight", "500");
    text.style.pointerEvents = "none";

    if (isRow) {
      // Title above the track (vertical / rotated)
      const cy = area.y + area.h / 2;
      const cx = area.x + area.w / 2;
      text.setAttribute("x", cx);
      text.setAttribute("y", cy);
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("transform", `rotate(-90, ${cx}, ${cy})`);
    } else {
      // Title above the track (horizontal)
      const cx = area.x + area.w / 2;
      text.setAttribute("x", cx);
      text.setAttribute("y", area.y - 4);
      text.setAttribute("text-anchor", "middle");
    }

    this._annotationGroup.appendChild(text);
  }

  // --- Annotation hover tooltip ---

  _addAnnotationHover(el, tooltipText) {
    if (!this._tooltip) return;
    const tip = this._tooltip;
    el.style.pointerEvents = "all";
    el.style.cursor = "default";
    el.addEventListener("mouseenter", (e) => {
      tip.innerHTML = tooltipText;
      tip.style.display = "block";
    });
    el.addEventListener("mousemove", (e) => {
      const cr = tip.parentElement.getBoundingClientRect();
      tip.style.left = (e.clientX - cr.left + 14) + "px";
      tip.style.top = (e.clientY - cr.top - 10) + "px";
    });
    el.addEventListener("mouseleave", () => {
      tip.style.display = "none";
    });
  }

  // --- Row/Col Labels (axis labels) ---

  /**
   * Render row/col axis labels alongside the heatmap.
   * @param {object} labels - {row: {labels: [...], side: "right"}, col: {labels: [...], side: "bottom"}}
   * @param {object} layout
   */
  renderLabels(labels, layout) {
    if (this._labelGroup) this._labelGroup.remove();
    this._labelGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this._labelGroup.setAttribute("class", "axis-labels");

    if (!labels) { this.svg.appendChild(this._labelGroup); return; }

    const heatmap = layout.heatmap;
    const font = '"Outfit", system-ui, -apple-system, sans-serif';
    // Offset past annotations so labels don't overlap
    const leftAnnotW = layout.leftAnnotationWidth || 0;
    const rightAnnotW = layout.rightAnnotationWidth || 0;
    const topAnnotH = layout.topAnnotationHeight || 0;
    const bottomAnnotH = layout.bottomAnnotationHeight || 0;

    if (labels.row && labels.row.labels) {
      const side = labels.row.side || "right";
      const labelX = side === "right"
        ? heatmap.x + heatmap.width + rightAnnotW + 6
        : heatmap.x - leftAnnotW - 6;
      const anchor = side === "right" ? "start" : "end";

      for (const lbl of labels.row.labels) {
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.textContent = lbl.text;
        text.setAttribute("x", labelX);
        text.setAttribute("y", lbl.position);
        text.setAttribute("font-size", lbl.fontSize || 10);
        text.setAttribute("font-family", font);
        text.setAttribute("fill", "#334155");
        text.setAttribute("text-anchor", anchor);
        text.setAttribute("dominant-baseline", "central");
        text.style.pointerEvents = "none";
        if (!lbl.visible) {
          text.classList.add("dh-label-auto-hidden");
          text.style.display = "none";
        }
        this._labelGroup.appendChild(text);
      }
    }

    if (labels.col && labels.col.labels) {
      const side = labels.col.side || "bottom";
      if (side === "bottom") {
        const labelY = heatmap.y + heatmap.height + bottomAnnotH + 6;
        for (const lbl of labels.col.labels) {
          const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
          text.textContent = lbl.text;
          text.setAttribute("x", lbl.position);
          text.setAttribute("y", labelY);
          text.setAttribute("font-size", lbl.fontSize || 10);
          text.setAttribute("font-family", font);
          text.setAttribute("fill", "#334155");
          text.setAttribute("text-anchor", "start");
          text.setAttribute("dominant-baseline", "hanging");
          text.setAttribute("transform", `rotate(45, ${lbl.position}, ${labelY})`);
          text.style.pointerEvents = "none";
          if (!lbl.visible) {
            text.classList.add("dh-label-auto-hidden");
            text.style.display = "none";
          }
          this._labelGroup.appendChild(text);
        }
      } else {
        // Top labels: rotated above the heatmap
        const labelY = heatmap.y - topAnnotH - 6;
        for (const lbl of labels.col.labels) {
          const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
          text.textContent = lbl.text;
          text.setAttribute("x", lbl.position);
          text.setAttribute("y", labelY);
          text.setAttribute("font-size", lbl.fontSize || 10);
          text.setAttribute("font-family", font);
          text.setAttribute("fill", "#334155");
          text.setAttribute("text-anchor", "end");
          text.setAttribute("dominant-baseline", "auto");
          text.setAttribute("transform", `rotate(-45, ${lbl.position}, ${labelY})`);
          text.style.pointerEvents = "none";
          if (!lbl.visible) {
            text.classList.add("dh-label-auto-hidden");
            text.style.display = "none";
          }
          this._labelGroup.appendChild(text);
        }
      }
    }

    this.svg.appendChild(this._labelGroup);
  }

  /**
   * Remove all overlay content.
   */
  clear() {
    while (this.svg.firstChild) {
      this.svg.removeChild(this.svg.firstChild);
    }
    this.selectionRect = null;
    this.hoverRect = null;
    this.hoverRectInner = null;
    this.dendrogramGroups = {};
    this._annotationGroup = null;
    this._labelGroup = null;
    this._crosshairGroup = null;
    this._titleGroup = null;
  }

  /**
   * Render a centered title above the heatmap.
   * @param {string|null} title - Title text (null to hide)
   * @param {object} layout - Layout spec with heatmap rect and titleY
   */
  renderTitle(title, layout) {
    // Remove old title group
    if (this._titleGroup && this._titleGroup.parentNode) {
      this._titleGroup.parentNode.removeChild(this._titleGroup);
    }
    this._titleGroup = null;

    if (!title || !layout || !layout.titleY) return;

    var ns = "http://www.w3.org/2000/svg";
    this._titleGroup = document.createElementNS(ns, "g");
    this._titleGroup.setAttribute("class", "dh-title");
    this._titleGroup.style.pointerEvents = "none";

    var text = document.createElementNS(ns, "text");
    text.textContent = title;
    var cx = layout.heatmap.x + layout.heatmap.width / 2;
    text.setAttribute("x", cx);
    text.setAttribute("y", layout.titleY);
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("font-size", "16");
    text.setAttribute("font-weight", "600");
    text.setAttribute("font-family", '"Outfit", system-ui, -apple-system, sans-serif');
    text.setAttribute("fill", "#1e293b");
    this._titleGroup.appendChild(text);

    this.svg.appendChild(this._titleGroup);
  }
}
