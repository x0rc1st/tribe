// tooltip.js — Floating tooltip / detail card system for the brain viewer

export class TooltipSystem {
    /**
     * @param {ShadowRoot|HTMLElement} container — the shadow root or element to append the tooltip to
     */
    constructor(container) {
        this._container = container;

        // Main tooltip element
        this._el = document.createElement('div');
        this._el.classList.add('bv-tooltip');
        this._el.setAttribute('role', 'tooltip');
        this._el.setAttribute('aria-hidden', 'true');
        this._container.appendChild(this._el);

        // Detail card (expanded view on click)
        this._detail = document.createElement('div');
        this._detail.classList.add('bv-detail-card');
        this._detail.setAttribute('aria-hidden', 'true');
        this._container.appendChild(this._detail);

        this._visible = false;
        this._detailVisible = false;
    }

    /**
     * Show the small hover tooltip at screen coordinates.
     * @param {number} x — client X
     * @param {number} y — client Y
     * @param {{name: string, score: number, operator_frame?: string}} data
     */
    show(x, y, data) {
        if (!data) { this.hide(); return; }

        const scorePercent = (data.score * 100).toFixed(1);
        const bar = this._buildBar(data.score);

        this._el.innerHTML = `
            <div class="bv-tooltip-header">${this._esc(data.name)}</div>
            <div class="bv-tooltip-score">
                <span class="bv-tooltip-label">Activation</span>
                <span class="bv-tooltip-value">${scorePercent}%</span>
            </div>
            <div class="bv-tooltip-bar-track">${bar}</div>
            ${data.operator_frame ? `<div class="bv-tooltip-frame">${this._esc(data.operator_frame)}</div>` : ''}
        `;

        // Position with offset and clamping
        const rect = this._container.host
            ? this._container.host.getBoundingClientRect()
            : this._container.getBoundingClientRect();

        let left = x - rect.left + 16;
        let top = y - rect.top - 10;

        // Clamp so tooltip doesn't overflow right/bottom
        const tw = 260; // approx width
        const th = 120; // approx height
        if (left + tw > rect.width) left = left - tw - 32;
        if (top + th > rect.height) top = rect.height - th - 8;
        if (top < 4) top = 4;

        this._el.style.left = `${left}px`;
        this._el.style.top = `${top}px`;
        this._el.style.opacity = '1';
        this._el.style.pointerEvents = 'none';
        this._el.setAttribute('aria-hidden', 'false');
        this._visible = true;
    }

    /** Hide the small tooltip. */
    hide() {
        this._el.style.opacity = '0';
        this._el.setAttribute('aria-hidden', 'true');
        this._visible = false;
    }

    /**
     * Show an expanded detail card (on click).
     * @param {{name: string, score: number, operator_frame?: string, id?: number|string, vertex_count?: number}} data
     */
    showDetail(data) {
        if (!data) { this.hideDetail(); return; }

        const scorePercent = (data.score * 100).toFixed(1);
        const bar = this._buildBar(data.score);

        this._detail.innerHTML = `
            <button class="bv-detail-close" aria-label="Close detail card">&times;</button>
            <h3 class="bv-detail-title">${this._esc(data.name)}</h3>
            <div class="bv-detail-row">
                <span class="bv-detail-label">Activation Score</span>
                <span class="bv-detail-value">${scorePercent}%</span>
            </div>
            <div class="bv-tooltip-bar-track bv-detail-bar">${bar}</div>
            ${data.operator_frame
                ? `<div class="bv-detail-section">
                       <span class="bv-detail-label">Operator Frame</span>
                       <p class="bv-detail-text">${this._esc(data.operator_frame)}</p>
                   </div>`
                : ''}
            ${data.id !== undefined
                ? `<div class="bv-detail-meta">Group ID: ${this._esc(String(data.id))}</div>`
                : ''}
        `;

        this._detail.style.opacity = '1';
        this._detail.style.pointerEvents = 'auto';
        this._detail.setAttribute('aria-hidden', 'false');
        this._detailVisible = true;

        // Close button handler
        this._detail.querySelector('.bv-detail-close').addEventListener('click', () => {
            this.hideDetail();
        }, { once: true });
    }

    /** Hide the detail card. */
    hideDetail() {
        this._detail.style.opacity = '0';
        this._detail.style.pointerEvents = 'none';
        this._detail.setAttribute('aria-hidden', 'true');
        this._detailVisible = false;
    }

    get isDetailVisible() { return this._detailVisible; }

    // ---- private helpers ----

    _buildBar(score) {
        const pct = Math.max(0, Math.min(100, score * 100));
        return `<div class="bv-tooltip-bar" style="width:${pct}%"></div>`;
    }

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }
}
