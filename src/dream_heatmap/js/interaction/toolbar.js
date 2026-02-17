/**
 * Toolbar: floating modebar with action buttons (Plotly-style).
 * Fades in on container hover via CSS (.dh-toolbar).
 */

const TOOLBAR_ICONS = {
  zoomToSelection: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
    <rect x="2" y="2" width="7" height="7" stroke-dasharray="2,1"/>
    <circle cx="10" cy="10" r="3.5"/>
    <line x1="12.5" y1="12.5" x2="15" y2="15"/>
  </svg>`,
  resetZoom: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
    <rect x="1" y="1" width="14" height="14" rx="1"/>
    <line x1="4" y1="8" x2="12" y2="8"/>
    <line x1="8" y1="4" x2="8" y2="12"/>
  </svg>`,
  downloadPng: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
    <path d="M8 2v8M8 10l-3-3M8 10l3-3"/>
    <path d="M2 12v2h12v-2"/>
  </svg>`,
  crosshairToggle: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
    <line x1="8" y1="1" x2="8" y2="15"/>
    <line x1="1" y1="8" x2="15" y2="8"/>
    <circle cx="8" cy="8" r="3"/>
  </svg>`,
};

class Toolbar {
  /**
   * @param {HTMLElement} container - the .dh-container div
   */
  constructor(container) {
    this._container = container;
    this._el = document.createElement("div");
    this._el.className = "dh-toolbar";
    this._buttons = {};
    container.appendChild(this._el);
  }

  /**
   * Add a button to the toolbar.
   * @param {string} name - unique key
   * @param {string} svgIcon - inline SVG markup
   * @param {string} title - tooltip text
   * @param {function} onClick - click handler
   */
  addButton(name, svgIcon, title, onClick) {
    const btn = document.createElement("button");
    btn.innerHTML = svgIcon;
    btn.title = title;
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      onClick();
    });
    this._buttons[name] = btn;
    this._el.appendChild(btn);
  }

  /**
   * Toggle active highlight on a button.
   */
  setActive(name, active) {
    const btn = this._buttons[name];
    if (btn) {
      if (active) btn.classList.add("active");
      else btn.classList.remove("active");
    }
  }
}
