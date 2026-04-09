/* ================================================================
   TRIBE v2 — Skill Mastery & ORI Dashboard
   ================================================================ */

const GROUP_NAMES = {
    1: "G1 Strategic Thinking",
    2: "G2 Procedural Fluency",
    3: "G3 Language Processing",
    4: "G4 Visual Processing",
    5: "G5 Situational Awareness",
    6: "G6 Motivation & Drive",
    7: "G7 Memory Encoding",
    8: "G8 Knowledge Synthesis",
    9: "G9 Threat Awareness",
    10: "G10 Deep Internalization",
};

const TYPE_COLORS = {
    procedural: "var(--procedural)",
    analytical: "var(--analytical)",
    operational: "var(--operational)",
};

const TYPE_POINTS = { procedural: 33, analytical: 33, operational: 34 };

const CLEARANCE_CLASSES = {
    full: "clearance-full",
    limited: "clearance-limited",
    restricted: "clearance-restricted",
    grounded: "clearance-grounded",
};

const HEALTH_ICONS = { fresh: "\u2713", at_risk: "\u26A0", needs_refresh: "\uD83D\uDD34" };

let lastPrediction = null;

// ── Helpers ──────────────────────────────────────────────────────────

function operatorId() {
    return document.getElementById("operatorId").value.trim() || "demo-operator";
}

async function api(path, opts) {
    const res = await fetch(path, opts);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
}

// ── Load profile ────────────────────────────────────────────────────

async function loadProfile() {
    const oid = operatorId();
    try {
        const [skills, ori, completions] = await Promise.all([
            api(`/api/v1/mastery/${oid}/skills`),
            api(`/api/v1/mastery/${oid}/ori`),
            api(`/api/v1/mastery/${oid}/completions`),
        ]);
        renderORI(ori);
        renderSkills(skills);
        renderHistory(completions);
    } catch (e) {
        renderORI(null);
        renderSkills(null);
        renderHistory([]);
    }
}

// ── ORI Rendering ───────────────────────────────────────────────────

function renderORI(data) {
    const scoreEl = document.getElementById("oriScore");
    const clearEl = document.getElementById("oriClearance");
    const gradeEl = document.getElementById("oriGrade");
    const factorsEl = document.getElementById("oriFactors");

    if (!data || data.total_skills === 0) {
        scoreEl.textContent = "--";
        scoreEl.style.color = "var(--text-muted)";
        clearEl.textContent = "No data";
        clearEl.className = "ori-clearance clearance-grounded";
        gradeEl.textContent = "";
        factorsEl.innerHTML = "";
        return;
    }

    const ori = data.ori;
    scoreEl.textContent = ori.toFixed(1);

    // Color by clearance
    const cls = CLEARANCE_CLASSES[data.clearance] || "clearance-grounded";
    scoreEl.style.color = "";
    scoreEl.className = "ori-score " + cls;
    clearEl.textContent = data.clearance.toUpperCase() + " CLEARANCE";
    clearEl.className = "ori-clearance " + cls;
    gradeEl.textContent = `Grade ${data.grade} — ${data.grade_description}`;

    // Factor bars
    const factors = data.factors || {};
    const weighted = data.weighted_factors || {};
    factorsEl.innerHTML = ["mastery", "currency", "repetition", "certification"]
        .map(f => {
            const val = factors[f] || 0;
            const w = weighted[f] || 0;
            const colors = {
                mastery: "var(--neon-green)",
                currency: "var(--cyan)",
                repetition: "var(--purple)",
                certification: "var(--warning)",
            };
            return `<div class="ori-factor">
                <div class="ori-factor-label">${f}</div>
                <div class="ori-factor-bar">
                    <div class="ori-factor-fill" style="width:${val}%;background:${colors[f]}"></div>
                </div>
                <div class="ori-factor-val">${val.toFixed(0)}% (\u00d7${({mastery:.25,currency:.30,repetition:.25,certification:.20})[f]} = ${w.toFixed(1)})</div>
            </div>`;
        }).join("");
}

// ── Skills Rendering ────────────────────────────────────────────────

function renderSkills(data) {
    const el = document.getElementById("skillsList");
    if (!data || !data.skills || data.skills.length === 0) {
        el.innerHTML = '<div class="empty-sub">No skills recorded yet. Classify and record content above.</div>';
        return;
    }

    el.innerHTML = data.skills.map(s => {
        const p = s.completed_types.includes("procedural") ? 1 : 0;
        const a = s.completed_types.includes("analytical") ? 1 : 0;
        const o = s.completed_types.includes("operational") ? 1 : 0;
        const health = HEALTH_ICONS[s.health] || "";
        return `<div class="skill-row">
            <div class="skill-name">${s.skill_id}</div>
            <div class="skill-bars">
                <div class="skill-bar-row">
                    <div class="skill-bar-label">P</div>
                    <div class="skill-bar-track"><div class="skill-bar-fill procedural" style="width:${p*100}%"></div></div>
                </div>
                <div class="skill-bar-row">
                    <div class="skill-bar-label">A</div>
                    <div class="skill-bar-track"><div class="skill-bar-fill analytical" style="width:${a*100}%"></div></div>
                </div>
                <div class="skill-bar-row">
                    <div class="skill-bar-label">O</div>
                    <div class="skill-bar-track"><div class="skill-bar-fill operational" style="width:${o*100}%"></div></div>
                </div>
            </div>
            <div class="skill-score">${s.current}<span style="font-size:11px;color:var(--text-muted)">/${s.peak}</span></div>
            <div class="skill-stage stage-${s.stage}">${s.stage.replace("_"," ")}</div>
            <div class="skill-health" title="${s.health || ''}">${health}</div>
        </div>`;
    }).join("");
}

// ── History Rendering ───────────────────────────────────────────────

function renderHistory(data) {
    const el = document.getElementById("historyList");
    if (!data || data.length === 0) {
        el.innerHTML = '<div class="empty-sub">No completions yet.</div>';
        return;
    }

    el.innerHTML = data.map(c => {
        const d = new Date(c.completed_at);
        const dateStr = d.toLocaleDateString() + " " + d.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"});
        return `<div class="history-row">
            <div class="history-type type-${c.completion_type}">${c.completion_type}</div>
            <div class="history-course">${c.course_id}</div>
            <div class="history-skills">${c.skill_tags.join(", ")}</div>
            <div class="history-date">${dateStr}</div>
        </div>`;
    }).join("");
}

// ── Classify ────────────────────────────────────────────────────────

async function classifyContent() {
    const text = document.getElementById("contentText").value.trim();
    if (!text) return;

    const btn = document.getElementById("classifyBtn");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Predicting...';

    try {
        const pred = await api("/api/v1/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, content_type: "module" }),
        });

        lastPrediction = pred;
        showClassifyResult(pred);
    } catch (e) {
        document.getElementById("classifyResult").style.display = "block";
        document.getElementById("classifyType").textContent = "Error";
        document.getElementById("classifyType").className = "classify-type";
        document.getElementById("classifyRegions").textContent = e.message;
        document.getElementById("recordBtn").style.display = "none";
    } finally {
        btn.disabled = false;
        btn.textContent = "Predict & Classify";
    }
}

function showClassifyResult(pred) {
    const result = document.getElementById("classifyResult");
    result.style.display = "block";

    const type = pred.completion_type;
    const typeEl = document.getElementById("classifyType");
    typeEl.textContent = type;
    typeEl.className = "classify-type type-" + type;

    document.getElementById("classifyPoints").textContent = `+${TYPE_POINTS[type]} points`;

    // Show top 3 groups
    const groups = (pred.group_scores || [])
        .slice()
        .sort((a, b) => b.z_score - a.z_score)
        .slice(0, 5);

    const regionsHtml = groups.map((g, i) => {
        const isTop3 = i < 3;
        const marker = isTop3 ? "\u2B24" : "\u25CB";
        const isClassifier = [1,2,5,8,9].includes(g.id);
        const label = GROUP_NAMES[g.id] || `G${g.id}`;
        const zs = g.z_score.toFixed(2);
        let tag = "";
        if (isTop3 && g.id === 2) tag = ' <span style="color:var(--procedural)">[PROCEDURAL marker]</span>';
        if (isTop3 && [1,5,8].includes(g.id)) tag = ' <span style="color:var(--analytical)">[ANALYTICAL marker]</span>';
        if (isTop3 && g.id === 9) tag = ' <span style="color:var(--operational)">[OPERATIONAL marker]</span>';
        return `<div style="opacity:${isTop3?1:0.5}">${marker} <strong>${label}</strong> z=${zs}${tag}</div>`;
    }).join("");

    document.getElementById("classifyRegions").innerHTML =
        `<div style="font-family:var(--mono);font-size:12px;margin-bottom:4px;color:var(--text-muted)">TOP BRAIN REGIONS:</div>${regionsHtml}`;

    // Show record button if we have skill tags
    const skills = document.getElementById("skillTags").value.trim();
    const course = document.getElementById("courseId").value.trim();
    const recordBtn = document.getElementById("recordBtn");
    recordBtn.style.display = (skills && course) ? "inline-block" : "none";
    document.getElementById("recordStatus").textContent = "";
}

// ── Record completion ───────────────────────────────────────────────

async function recordCompletion() {
    if (!lastPrediction) return;

    const oid = operatorId();
    const courseId = document.getElementById("courseId").value.trim();
    const skillTags = document.getElementById("skillTags").value.trim().split(",").map(s => s.trim()).filter(Boolean);
    const type = lastPrediction.completion_type;

    const groupZ = {};
    (lastPrediction.group_scores || []).forEach(g => { groupZ[g.id] = g.z_score; });

    const btn = document.getElementById("recordBtn");
    btn.disabled = true;

    try {
        await api(`/api/v1/mastery/${oid}/completions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                course_id: courseId,
                completion_type: type,
                skill_tags: skillTags,
                group_z_scores: groupZ,
            }),
        });
        document.getElementById("recordStatus").textContent = "\u2713 Recorded!";
        btn.style.display = "none";
        loadProfile();
    } catch (e) {
        document.getElementById("recordStatus").textContent = "Error: " + e.message;
    } finally {
        btn.disabled = false;
    }
}

// ── Init ────────────────────────────────────────────────────────────

document.getElementById("loadBtn").addEventListener("click", loadProfile);
document.getElementById("classifyBtn").addEventListener("click", classifyContent);
document.getElementById("recordBtn").addEventListener("click", recordCompletion);

document.getElementById("operatorId").addEventListener("keydown", e => {
    if (e.key === "Enter") loadProfile();
});

// Load on start
loadProfile();
