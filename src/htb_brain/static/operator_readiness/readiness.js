/* ================================================================
   TRIBE v2 — Operator Readiness Profile UI
   ================================================================ */

const DIM_ORDER = [
    "procedural_automaticity",
    "threat_detection",
    "situational_awareness",
    "strategic_decision",
    "analytical_synthesis",
    "stress_resilience",
];

const DIM_LABELS = {
    procedural_automaticity: "Procedural\nAutomaticity",
    threat_detection: "Threat\nDetection",
    situational_awareness: "Situational\nAwareness",
    strategic_decision: "Strategic\nDecision",
    analytical_synthesis: "Analytical\nSynthesis",
    stress_resilience: "Stress\nResilience",
};

const DIM_FULL_NAMES = {
    procedural_automaticity: "Procedural Automaticity",
    threat_detection: "Threat Detection & Calibration",
    situational_awareness: "Situational Awareness",
    strategic_decision: "Strategic Decision & Reflection",
    analytical_synthesis: "Analytical Synthesis & Pattern Matching",
    stress_resilience: "Stress Resilience",
};

const SRK_LABELS = {
    "skill-based": "SKILL",
    "cross-mode": "CROSS",
    "rule-based": "RULE",
    "knowledge-based": "KNOW",
    "all-modes-degraded": "ALL",
};

const COLORS = {
    neonGreen: "#9FEF00",
    cyan: "#2EE7B6",
    danger: "#FF6B6B",
    warning: "#FFB86C",
    gridLine: "rgba(30, 42, 58, 0.8)",
    gridLabel: "#4a5568",
    fillGreen: "rgba(159, 239, 0, 0.15)",
    strokeGreen: "rgba(159, 239, 0, 0.7)",
    fillDanger: "rgba(255, 107, 107, 0.08)",
};

// ── Dependency graph layout ──────────────────────────────────────

const DEPS = {
    stress_resilience: ["procedural_automaticity", "threat_detection"],
    analytical_synthesis: ["situational_awareness"],
    strategic_decision: ["analytical_synthesis"],
};

// ── API calls ────────────────────────────────────────────────────

async function fetchProfile(operatorId) {
    const res = await fetch(`/api/v1/profile/${encodeURIComponent(operatorId)}`);
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    return res.json();
}

async function fetchGaps(operatorId) {
    const res = await fetch(`/api/v1/profile/${encodeURIComponent(operatorId)}/gaps`);
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    return res.json();
}

// ── Radar chart ──────────────────────────────────────────────────

function drawRadar(canvas, dimensions) {
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const W = 460, H = 460;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    ctx.scale(dpr, dpr);

    const cx = W / 2, cy = H / 2;
    const R = 170;
    const n = DIM_ORDER.length;
    const angleStep = (2 * Math.PI) / n;
    const startAngle = -Math.PI / 2;

    ctx.clearRect(0, 0, W, H);

    // Grid rings (0.25, 0.5, 0.75, 1.0)
    for (let ring = 1; ring <= 4; ring++) {
        const r = (ring / 4) * R;
        ctx.beginPath();
        for (let i = 0; i <= n; i++) {
            const a = startAngle + i * angleStep;
            const x = cx + r * Math.cos(a);
            const y = cy + r * Math.sin(a);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.strokeStyle = COLORS.gridLine;
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    // Spokes + labels
    ctx.font = "11px 'JetBrains Mono', monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (let i = 0; i < n; i++) {
        const a = startAngle + i * angleStep;
        const x1 = cx + R * Math.cos(a);
        const y1 = cy + R * Math.sin(a);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(x1, y1);
        ctx.strokeStyle = COLORS.gridLine;
        ctx.lineWidth = 1;
        ctx.stroke();

        // Label
        const labelR = R + 36;
        const lx = cx + labelR * Math.cos(a);
        const ly = cy + labelR * Math.sin(a);
        ctx.fillStyle = COLORS.gridLabel;
        const lines = DIM_LABELS[DIM_ORDER[i]].split("\n");
        lines.forEach((line, li) => {
            ctx.fillText(line, lx, ly + (li - (lines.length - 1) / 2) * 13);
        });
    }

    // Coverage polygon
    const readinessValues = DIM_ORDER.map(k => {
        const d = dimensions[k];
        return d ? d.readiness : 0;
    });

    ctx.beginPath();
    for (let i = 0; i <= n; i++) {
        const idx = i % n;
        const a = startAngle + idx * angleStep;
        const v = Math.min(readinessValues[idx], 1.0);
        const r = v * R;
        const x = cx + r * Math.cos(a);
        const y = cy + r * Math.sin(a);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.fillStyle = COLORS.fillGreen;
    ctx.fill();
    ctx.strokeStyle = COLORS.strokeGreen;
    ctx.lineWidth = 2;
    ctx.stroke();

    // Dots at vertices
    for (let i = 0; i < n; i++) {
        const a = startAngle + i * angleStep;
        const v = Math.min(readinessValues[i], 1.0);
        const r = v * R;
        const x = cx + r * Math.cos(a);
        const y = cy + r * Math.sin(a);
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fillStyle = v >= 0.15 ? COLORS.neonGreen : COLORS.danger;
        ctx.fill();
    }

    // Coverage percentage labels on dots
    ctx.font = "bold 11px 'JetBrains Mono', monospace";
    for (let i = 0; i < n; i++) {
        const a = startAngle + i * angleStep;
        const v = Math.min(readinessValues[i], 1.0);
        const r = v * R + 16;
        const x = cx + r * Math.cos(a);
        const y = cy + r * Math.sin(a);
        ctx.fillStyle = v >= 0.15 ? COLORS.neonGreen : COLORS.danger;
        ctx.fillText(Math.round(v * 100) + "%", x, y);
    }
}

// ── Dimension summary list ───────────────────────────────────────

const LEVEL_COLORS = {
    "ready": COLORS.neonGreen,
    "proficient": COLORS.cyan,
    "developing": COLORS.warning,
    "untrained": COLORS.danger,
};

function renderDimensions(container, dimensions) {
    container.innerHTML = "";
    DIM_ORDER.forEach(key => {
        const d = dimensions[key];
        if (!d) return;
        const pct = Math.round(d.readiness * 100);
        const level = d.level || "untrained";
        const color = LEVEL_COLORS[level] || COLORS.danger;
        const isGap = d.readiness < 0.15;

        const el = document.createElement("div");
        el.className = `dim-item ${isGap ? "not-covered" : "covered"}`;
        el.innerHTML = `
            <div class="dim-header">
                <span class="dim-name">${DIM_FULL_NAMES[key]}</span>
                <span class="dim-badge ${isGap ? "not-covered" : "covered"}" style="background:${color}22;color:${color}">${level.toUpperCase()}</span>
            </div>
            <div class="dim-meta">
                <span>Readiness: ${pct}%</span>
                <span>Signal: ${d.raw_signal.toFixed(2)}</span>
                <span>Avg: ${d.mean_strength.toFixed(2)}</span>
            </div>
            <div class="dim-bar-track">
                <div class="dim-bar-fill" style="width:${pct}%; background:${color}"></div>
            </div>
        `;
        container.appendChild(el);
    });
}

// ── Gap analysis ─────────────────────────────────────────────────

function renderGaps(container, gapsData) {
    container.innerHTML = "";

    if (gapsData.all_clear) {
        container.innerHTML = '<div class="gaps-clear">All 6 dimensions covered. Operator is readiness-complete.</div>';
        return;
    }

    gapsData.gaps.forEach(gap => {
        const el = document.createElement("div");
        el.className = `gap-item ${gap.severity}`;

        let blockedHtml = "";
        if (gap.blocked_by.length > 0) {
            const names = gap.blocked_by.map(k => DIM_FULL_NAMES[k] || k).join(", ");
            blockedHtml = `<div class="gap-blocked">BLOCKED BY: ${names}</div>`;
        }

        const recsHtml = gap.recommended_content
            .map(r => `<span class="gap-rec-tag">${r}</span>`)
            .join("");

        el.innerHTML = `
            <div class="gap-header">
                <span class="gap-severity ${gap.severity}">${gap.severity}</span>
                <span class="gap-dim-name">${DIM_FULL_NAMES[gap.dimension] || gap.dimension}</span>
                <span style="margin-left:auto; font-family:var(--mono); font-size:11px; color:var(--text-muted)">
                    ${Math.round(gap.readiness * 100)}% readiness
                </span>
            </div>
            <div class="gap-error-risk">SRK Risk: ${gap.srk_error_risk}</div>
            <div class="gap-message">${gap.message}</div>
            ${blockedHtml}
            <div class="gap-recs">${recsHtml}</div>
        `;
        container.appendChild(el);
    });
}

// ── Dependency graph ─────────────────────────────────────────────

function drawDependencies(canvas, dimensions) {
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const W = 700, H = 280;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, W, H);

    // Layout: 3 columns
    // Col 1 (no prereqs): dims 1, 2, 3
    // Col 2 (depends on col 1): dim 5
    // Col 3 (depends on col 2): dim 4
    // Dim 6 depends on 1+2, placed in col 2
    const nodeW = 140, nodeH = 50;
    const positions = {
        procedural_automaticity: { x: 40, y: 30 },
        threat_detection:        { x: 40, y: 115 },
        situational_awareness:   { x: 40, y: 200 },
        analytical_synthesis:    { x: 280, y: 200 },
        strategic_decision:      { x: 520, y: 200 },
        stress_resilience:       { x: 280, y: 72 },
    };

    // Draw arrows first (behind nodes)
    ctx.lineWidth = 2;
    const arrowSize = 8;
    for (const [target, sources] of Object.entries(DEPS)) {
        const tp = positions[target];
        if (!tp) continue;
        for (const src of sources) {
            const sp = positions[src];
            if (!sp) continue;

            const sx = sp.x + nodeW;
            const sy = sp.y + nodeH / 2;
            const tx = tp.x;
            const ty = tp.y + nodeH / 2;

            // Arrow line
            ctx.beginPath();
            ctx.moveTo(sx, sy);
            ctx.lineTo(tx, ty);

            const dim = dimensions[target];
            const covered = dim && dim.readiness >= 0.15;
            ctx.strokeStyle = covered ? "rgba(159,239,0,0.3)" : "rgba(255,107,107,0.3)";
            ctx.stroke();

            // Arrowhead
            const angle = Math.atan2(ty - sy, tx - sx);
            ctx.beginPath();
            ctx.moveTo(tx, ty);
            ctx.lineTo(tx - arrowSize * Math.cos(angle - 0.4), ty - arrowSize * Math.sin(angle - 0.4));
            ctx.lineTo(tx - arrowSize * Math.cos(angle + 0.4), ty - arrowSize * Math.sin(angle + 0.4));
            ctx.closePath();
            ctx.fillStyle = ctx.strokeStyle;
            ctx.fill();
        }
    }

    // Draw nodes
    ctx.font = "bold 11px 'JetBrains Mono', monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (const [key, pos] of Object.entries(positions)) {
        const dim = dimensions[key];
        const readiness = dim ? dim.readiness : 0;
        const covered = readiness >= 0.15;

        // Node box
        ctx.fillStyle = covered ? "rgba(159,239,0,0.08)" : "rgba(255,107,107,0.06)";
        ctx.strokeStyle = covered ? "rgba(159,239,0,0.4)" : "rgba(255,107,107,0.3)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.roundRect(pos.x, pos.y, nodeW, nodeH, 6);
        ctx.fill();
        ctx.stroke();

        // Label
        ctx.fillStyle = covered ? COLORS.neonGreen : COLORS.danger;
        const shortName = DIM_LABELS[key].replace("\n", " ");
        ctx.fillText(shortName, pos.x + nodeW / 2, pos.y + nodeH / 2 - 8);

        // Coverage
        ctx.font = "10px 'JetBrains Mono', monospace";
        ctx.fillStyle = COLORS.gridLabel;
        ctx.fillText(Math.round(readiness * 100) + "% readiness", pos.x + nodeW / 2, pos.y + nodeH / 2 + 10);
        ctx.font = "bold 11px 'JetBrains Mono', monospace";
    }
}

// ── Module list with dimension badges ────────────────────────────

const DIM_SHORT = {
    procedural_automaticity: "PROC",
    threat_detection: "THRT",
    situational_awareness: "SA",
    strategic_decision: "STRT",
    analytical_synthesis: "SYNTH",
    stress_resilience: "STRESS",
};

function renderModules(container, modules) {
    container.innerHTML = "";
    if (modules.length === 0) {
        container.innerHTML = '<div style="color:var(--text-muted); font-size:13px">No modules recorded.</div>';
        return;
    }

    // Show most recent first
    const sorted = [...modules].reverse();
    sorted.forEach(mod => {
        const el = document.createElement("div");
        el.className = "module-item";

        const badgesHtml = DIM_ORDER.map(key => {
            const d = mod.dimensions[key];
            const str = d ? d.strength : 0;
            const engaged = str > 0;
            return `<span class="module-badge ${engaged ? "covered" : "not-covered"}" title="str=${str.toFixed(2)}">${DIM_SHORT[key]}</span>`;
        }).join("");

        el.innerHTML = `
            <div class="module-name">${mod.module_name || mod.module_id}</div>
            <div class="module-id">${mod.module_id}</div>
            <div class="module-badges">${badgesHtml}</div>
        `;
        container.appendChild(el);
    });
}

// ── Main ─────────────────────────────────────────────────────────

async function loadProfile() {
    const operatorId = document.getElementById("operatorId").value.trim();
    if (!operatorId) return;

    const emptyState = document.getElementById("emptyState");
    const mainContent = document.getElementById("mainContent");

    try {
        const [profile, gapsData] = await Promise.all([
            fetchProfile(operatorId),
            fetchGaps(operatorId),
        ]);

        emptyState.style.display = "none";
        mainContent.style.display = "block";

        // Radar
        drawRadar(document.getElementById("radarCanvas"), profile.dimensions);

        // Dimension summary
        renderDimensions(document.getElementById("dimensionList"), profile.dimensions);

        // Gaps
        renderGaps(document.getElementById("gapsContainer"), gapsData);

        // Dependencies
        drawDependencies(document.getElementById("depsCanvas"), profile.dimensions);

        // Modules
        renderModules(document.getElementById("modulesList"), profile.completed_modules);

    } catch (err) {
        emptyState.style.display = "flex";
        mainContent.style.display = "none";
        alert("Error: " + err.message);
    }
}

// Event listeners
document.getElementById("loadBtn").addEventListener("click", loadProfile);
document.getElementById("operatorId").addEventListener("keydown", e => {
    if (e.key === "Enter") loadProfile();
});
