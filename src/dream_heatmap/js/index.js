/**
 * dream-heatmap: anywidget ESM entry point.
 *
 * Exports render() for the anywidget protocol.
 * All dependent classes (CanvasRenderer, ColorMapper, SVGOverlay,
 * IDResolver, ModelSync, HoverHandler, SelectionHandler,
 * DendrogramClickHandler, binary decoders) are defined above
 * in the concatenated bundle.
 */

function render({ model, el }) {
  // Create container
  const container = document.createElement("div");
  container.className = "dh-container";
  el.appendChild(container);

  // Create canvas for heatmap cells
  const canvas = document.createElement("canvas");
  container.appendChild(canvas);

  // Create SVG overlay for interactivity
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.style.position = "absolute";
  svg.style.top = "0";
  svg.style.left = "0";
  container.appendChild(svg);

  // Tooltip element
  const tooltip = document.createElement("div");
  tooltip.className = "dh-tooltip";
  container.appendChild(tooltip);

  // Initialize components
  const sync = new ModelSync(model);
  const canvasRenderer = new CanvasRenderer(canvas);
  const svgOverlay = new SVGOverlay(svg);
  svgOverlay.setTooltip(tooltip);
  const colorBarRenderer = new ColorBarRenderer(svg);
  const legendRenderer = new LegendRenderer(svg);
  const hoverHandler = new HoverHandler(svg, tooltip, svgOverlay, container);
  const selectionHandler = new SelectionHandler(svg, svgOverlay, sync, hoverHandler);
  const dendroClickHandler = new DendrogramClickHandler(svgOverlay, sync);
  const annotationClickHandler = new AnnotationClickHandler(svgOverlay, sync);
  const viewport = new Viewport();
  const zoomHandler = new ZoomHandler(svg, sync, viewport, svgOverlay);
  selectionHandler.setZoomHandler(zoomHandler);
  dendroClickHandler.setZoomHandler(zoomHandler);
  annotationClickHandler.setZoomHandler(zoomHandler);

  // Toolbar
  const toolbar = new Toolbar(container);
  toolbar.addButton("zoomToSelection", TOOLBAR_ICONS.zoomToSelection, "Zoom to selection", () => {
    zoomHandler.zoomToSelection();
  });
  toolbar.addButton("resetZoom", TOOLBAR_ICONS.resetZoom, "Reset zoom", () => {
    zoomHandler.resetZoom();
  });
  toolbar.addButton("downloadPng", TOOLBAR_ICONS.downloadPng, "Download as PNG", () => {
    downloadAsPng(canvas);
  });
  toolbar.addButton("crosshairToggle", TOOLBAR_ICONS.crosshairToggle, "Toggle crosshair", () => {
    const enabled = !hoverHandler.getCrosshairEnabled();
    hoverHandler.setCrosshairEnabled(enabled);
    toolbar.setActive("crosshairToggle", enabled);
  });
  toolbar.setActive("crosshairToggle", true);

  function downloadAsPng(cvs) {
    try {
      const link = document.createElement("a");
      link.download = "heatmap.png";
      link.href = cvs.toDataURL("image/png");
      link.click();
    } catch (e) {
      console.warn("Download failed:", e);
    }
  }

  function fullRender() {
    // Clear stale selection rect and zoom bounds from previous render
    svgOverlay.hideSelection();
    zoomHandler.setLastSelectionBounds(null);

    // Decode data from model
    const matrixBytes = sync.getMatrixBytes();
    const lutBytes = sync.getColorLUT();
    const layout = sync.getLayout();
    const idMappers = sync.getIDMappers();
    const config = sync.getConfig();

    if (!layout || !layout.nRows || !layout.nCols) return;

    const matrix = decodeMatrixBytes(matrixBytes);
    const lut = decodeColorLUT(lutBytes);
    const colorMapper = new ColorMapper(lut, config.vmin, config.vmax, config.nanColor);

    // Create ID resolvers
    const rowResolver = idMappers.row
      ? new IDResolver(idMappers.row, layout.rowPositions, layout.rowCellSize)
      : null;
    const colResolver = idMappers.col
      ? new IDResolver(idMappers.col, layout.colPositions, layout.colCellSize)
      : null;

    // Render heatmap cells
    canvasRenderer.render(matrix, layout, colorMapper);
    svgOverlay.resize(layout);

    // Render dendrograms
    const dendrograms = config.dendrograms || null;
    dendroClickHandler.setContext(layout, rowResolver, colResolver);
    svgOverlay.renderDendrograms(dendrograms, layout, (memberIds, axis) => {
      dendroClickHandler.onBranchClick(memberIds, axis);
    });

    // Render annotations
    const annotations = config.annotations || null;
    annotationClickHandler.setContext(layout, rowResolver, colResolver);
    svgOverlay.renderAnnotations(annotations, layout, (categoryName, edge, cellLabels) => {
      annotationClickHandler.onCategoryClick(categoryName, edge, cellLabels);
    });

    // Render color bar + categorical legends (unified in legend panel)
    const legends = config.legends || null;
    const colorBarTitle = config.colorBarTitle || null;
    const colorBarSubtitle = config.colorBarSubtitle || null;
    if (layout.legendPanel || layout.hasColorBar) {
      legendRenderer.render(
        legends, layout.legendPanel,
        colorBarRenderer, lut, config.vmin, config.vmax, colorBarTitle, colorBarSubtitle
      );
    } else {
      legendRenderer.clear();
      colorBarRenderer.clear();
    }

    // Render axis labels
    const labels = config.labels || null;
    svgOverlay.renderLabels(labels, layout);

    // Render title
    const titleText = config.title || null;
    svgOverlay.renderTitle(titleText, layout);

    // Update handler contexts
    hoverHandler.setContext(layout, matrix, rowResolver, colResolver, colorMapper);
    selectionHandler.setContext(layout, rowResolver, colResolver);
    zoomHandler.setContext(layout, rowResolver, colResolver);

    // Size container
    container.style.width = layout.totalWidth + "px";
    container.style.height = layout.totalHeight + "px";
  }

  // Initial render
  fullRender();

  // Re-render on data changes
  sync.onChange(fullRender);

  return () => {
    el.innerHTML = "";
  };
}

export default { render };
