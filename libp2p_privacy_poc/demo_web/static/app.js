const runBtn = document.getElementById("run-btn");
const bannerEl = document.getElementById("banner");
const runJsonEl = document.getElementById("run-json");
const statementCardsEl = document.getElementById("statement-cards");
const trafficPanelEl = document.getElementById("traffic-panel");
const proofSummaryEl = document.getElementById("proof-summary");
const pinPanelEl = document.getElementById("pin-panel");
const artifactLinksEl = document.getElementById("artifact-links");
const logControlsEl = document.getElementById("log-controls");
const logViewerEl = document.getElementById("log-viewer");
const timingChartEl = document.getElementById("timing-chart");
const riskPanelEl = document.getElementById("risk-panel");
const ovVerifiedEl = document.getElementById("ov-verified");
const ovPeersEl = document.getElementById("ov-peers");
const ovConnectionsEl = document.getElementById("ov-connections");

let currentRunId = null;
let pollTimer = null;
let activeLogBtn = null;

/* ─── Helpers ─── */

function setBanner(status, message) {
  bannerEl.textContent = message || status;
  bannerEl.className = `card banner banner-${status}`;
}

function formatMs(value) {
  if (!Number.isFinite(value)) return "n/a";
  return `${Number(value).toFixed(3)} ms`;
}

function rawMs(value) {
  if (!Number.isFinite(value)) return null;
  return Number(value);
}

function shortHash(hashText) {
  if (typeof hashText !== "string" || hashText.length < 12) return "n/a";
  return `${hashText.slice(0, 12)}\u2026`;
}

/* ─── Statement data extraction ─── */

function statementMapFrom(payload) {
  const empty = {
    membership_v2: { verified: false, mode: "n/a", verifyTime: "n/a", exchangeTime: "n/a", verifyRaw: null, exchangeRaw: null },
    continuity_v2: { verified: false, mode: "n/a", verifyTime: "n/a", exchangeTime: "n/a", verifyRaw: null, exchangeRaw: null },
    unlinkability_v2: { verified: false, mode: "n/a", verifyTime: "n/a", exchangeTime: "n/a", verifyRaw: null, exchangeRaw: null },
  };

  const report = payload.report || {};
  const rows = Array.isArray(report.snark_phase2b_proofs)
    ? report.snark_phase2b_proofs
    : [];
  for (const row of rows) {
    if (!row || !row.statement || !(row.statement in empty)) continue;
    const meta = row.meta || {};
    const verifyMs = row.verify_ms ?? meta.verify_ms ?? meta.elapsed_ms;
    const exchangeMs = row.exchange_ms ?? meta.exchange_ms ?? meta.round_trip_ms;
    empty[row.statement] = {
      verified: row.verified === true,
      mode: row.prove_mode || meta.prove_mode || row.mode || "n/a",
      verifyTime: formatMs(verifyMs),
      exchangeTime: formatMs(exchangeMs),
      verifyRaw: rawMs(verifyMs),
      exchangeRaw: rawMs(exchangeMs),
    };
  }

  return empty;
}

/* ─── Renderers ─── */

function renderStatements(payload) {
  const map = statementMapFrom(payload);
  statementCardsEl.innerHTML = "";
  for (const [name, row] of Object.entries(map)) {
    const div = document.createElement("div");
    div.className = `statement ${row.verified ? "verified" : "not-verified"}`;
    div.innerHTML =
      `<div class="statement-header">` +
        `<div class="statement-title">${name}</div>` +
        `<span class="statement-badge ${row.verified ? "badge-ok" : "badge-bad"}">` +
          `${row.verified ? "\u2713 Verified" : "\u2717 Failed"}` +
        `</span>` +
      `</div>` +
      `<div class="statement-meta-grid">` +
        `<div class="meta-item"><span class="meta-key">Mode</span><span class="meta-val">${row.mode}</span></div>` +
        `<div class="meta-item"><span class="meta-key">Verify</span><span class="meta-val">${row.verifyTime}</span></div>` +
        `<div class="meta-item"><span class="meta-key">Exchange</span><span class="meta-val">${row.exchangeTime}</span></div>` +
        `<div class="meta-item"><span class="meta-key">Status</span><span class="meta-val">${row.verified ? "Pass" : "Fail"}</span></div>` +
      `</div>`;
    statementCardsEl.appendChild(div);
  }
}

function renderOverviewStats(payload) {
  const map = statementMapFrom(payload);
  const verified = Object.values(map).filter((r) => r.verified).length;

  ovVerifiedEl.textContent = `${verified}/3`;
  ovVerifiedEl.className = `stat-value ${verified === 3 ? "stat-ok" : verified > 0 ? "stat-warn" : "stat-bad"}`;

  const report = payload.report || {};
  const stats = (report.privacy_report || {}).statistics || {};
  ovPeersEl.textContent = stats.unique_peers ?? "—";
  ovConnectionsEl.textContent = stats.total_connections ?? "—";
}

function renderRiskPanel(payload) {
  const report = payload.report || {};
  const privacyReport = report.privacy_report || {};
  const scoreRaw = privacyReport.overall_risk_score;
  const levelRaw = privacyReport.risk_level;
  const score = Number.isFinite(Number(scoreRaw)) ? Number(scoreRaw) : null;

  const map = statementMapFrom(payload);
  const verified = Object.values(map).filter((r) => r.verified).length;

  let riskLevel;
  if (typeof levelRaw === "string" && levelRaw.trim()) {
    riskLevel = levelRaw.toUpperCase();
  } else if (score !== null) {
    if (score >= 0.75) riskLevel = "CRITICAL";
    else if (score >= 0.5) riskLevel = "HIGH";
    else if (score >= 0.25) riskLevel = "MEDIUM";
    else riskLevel = "LOW";
  } else {
    // Fallback only when report score is unavailable.
    if (verified === 3) riskLevel = "LOW";
    else if (verified === 2) riskLevel = "MEDIUM";
    else if (verified === 1) riskLevel = "HIGH";
    else riskLevel = "CRITICAL";
  }

  let riskColor = "var(--warn)";
  let riskPct = 50;
  if (riskLevel === "LOW") {
    riskColor = "var(--ok)";
    riskPct = 15;
  } else if (riskLevel === "MEDIUM") {
    riskColor = "var(--warn)";
    riskPct = 55;
  } else if (riskLevel === "HIGH") {
    riskColor = "var(--warn)";
    riskPct = 75;
  } else if (riskLevel === "CRITICAL") {
    riskColor = "var(--bad)";
    riskPct = 95;
  }

  // SVG arc gauge for risk
  const circumference = Math.PI * 32;
  const halfCirc = circumference;
  const dashOffset = halfCirc - (halfCirc * riskPct) / 100;

  riskPanelEl.innerHTML =
    `<div class="risk-meter">` +
      `<div class="risk-arc">` +
        `<svg viewBox="0 0 80 80">` +
          `<circle class="risk-arc-bg" cx="40" cy="40" r="32" stroke-dasharray="${halfCirc}" stroke-dashoffset="0" />` +
          `<circle class="risk-arc-fill" cx="40" cy="40" r="32" stroke="${riskColor}" ` +
            `stroke-dasharray="${halfCirc}" stroke-dashoffset="${dashOffset}" />` +
        `</svg>` +
      `</div>` +
      `<div>` +
        `<div class="risk-label" style="color:${riskColor};font-size:1.15rem">${riskLevel}</div>` +
        `<div style="color:var(--text-muted);font-size:0.78rem;margin-top:2px">` +
          `Risk from network analysis${score !== null ? ` (${score.toFixed(2)}/1.00)` : ""}` +
        `</div>` +
      `</div>` +
    `</div>` +
    `<div class="mini-bar-group" style="margin-top:16px">` +
      Object.entries(map).map(([name, row]) => {
        const color = row.verified ? "var(--ok)" : "var(--bad)";
        return `<div class="mini-bar-row">` +
          `<span class="mini-bar-label">${name.replace("_v2", "")}</span>` +
          `<div class="mini-bar-track"><div class="mini-bar-fill" style="width:${row.verified ? "100" : "0"}%;background:${color}"></div></div>` +
          `<span class="mini-bar-value" style="color:${color}">${row.verified ? "Pass" : "Fail"}</span>` +
        `</div>`;
      }).join("") +
    `</div>`;
}

function renderTimingChart(payload) {
  const map = statementMapFrom(payload);
  const allTimes = [];
  for (const row of Object.values(map)) {
    if (row.verifyRaw !== null) allTimes.push(row.verifyRaw);
    if (row.exchangeRaw !== null) allTimes.push(row.exchangeRaw);
  }

  if (allTimes.length === 0) {
    timingChartEl.innerHTML = `<div class="empty-state">No timing data available yet.</div>`;
    return;
  }

  const maxTime = Math.max(...allTimes, 1);

  let html = "";
  for (const [name, row] of Object.entries(map)) {
    const vPct = row.verifyRaw !== null ? Math.max((row.verifyRaw / maxTime) * 100, 2) : 0;
    const ePct = row.exchangeRaw !== null ? Math.max((row.exchangeRaw / maxTime) * 100, 2) : 0;

    html +=
      `<div class="timing-row">` +
        `<div class="timing-label">${name}</div>` +
        `<div class="timing-bars">` +
          `<div class="timing-bar-wrapper">` +
            `<div class="timing-bar-track"><div class="timing-bar verify-bar" style="width:${vPct}%"></div></div>` +
            `<span class="timing-bar-ms">${row.verifyTime}</span>` +
          `</div>` +
          `<div class="timing-bar-wrapper">` +
            `<div class="timing-bar-track"><div class="timing-bar exchange-bar" style="width:${ePct}%"></div></div>` +
            `<span class="timing-bar-ms">${row.exchangeTime}</span>` +
          `</div>` +
        `</div>` +
      `</div>`;
  }

  html +=
    `<div class="timing-legend">` +
      `<div class="timing-legend-item"><span class="timing-legend-swatch swatch-verify"></span>Verify</div>` +
      `<div class="timing-legend-item"><span class="timing-legend-swatch swatch-exchange"></span>Exchange</div>` +
    `</div>`;

  timingChartEl.innerHTML = html;
}

function renderTraffic(payload) {
  const report = payload.report || {};
  const stats = (report.privacy_report || {}).statistics || {};
  const requested = (payload.config || {}).traffic_nodes ?? "n/a";
  const observed = stats.unique_peers ?? "n/a";
  const connections = stats.total_connections ?? "n/a";

  const maxVal = Math.max(
    Number(requested) || 0,
    Number(observed) || 0,
    Number(connections) || 0,
    1
  );

  trafficPanelEl.innerHTML =
    `<div class="mini-bar-group">` +
      _trafficBarRow("Requested nodes", requested, maxVal, "var(--accent)") +
      _trafficBarRow("Unique peers", observed, maxVal, "var(--ok)") +
      _trafficBarRow("Total connections", connections, maxVal, "#0fbcf9") +
    `</div>`;
}

function _trafficBarRow(label, value, max, color) {
  const numVal = Number(value);
  const pct = Number.isFinite(numVal) && max > 0 ? Math.max((numVal / max) * 100, 2) : 0;
  return `<div class="mini-bar-row">` +
    `<span class="mini-bar-label">${label}</span>` +
    `<div class="mini-bar-track"><div class="mini-bar-fill" style="width:${pct}%;background:${color}"></div></div>` +
    `<span class="mini-bar-value">${value}</span>` +
  `</div>`;
}

function renderProofSummary(payload) {
  const report = payload.report || {};
  const summary = report.proof_exchange_summary || {};
  const statements = Array.isArray(summary.statements) ? summary.statements : [];
  if (!statements.length) {
    proofSummaryEl.innerHTML = `<div class="empty-state">No proof exchange summary available.</div>`;
    return;
  }

  const rows = statements
    .map((row) => {
      const verified = row.verified === true;
      const assetHash = shortHash(((row.asset_source || {}).sha256));
      return `<tr>` +
        `<td>${row.statement || "n/a"}</td>` +
        `<td class="${verified ? "cell-ok" : "cell-bad"}">${verified ? "\u2713" : "\u2717"}</td>` +
        `<td>v${row.schema_v ?? "n/a"}</td>` +
        `<td>${row.depth ?? "n/a"}</td>` +
        `<td>${row.prove_mode || "n/a"}</td>` +
        `<td>${formatMs(row.verify_ms)}</td>` +
        `<td>${formatMs(row.exchange_ms)}</td>` +
        `<td>${assetHash}</td>` +
      `</tr>`;
    })
    .join("");

  proofSummaryEl.innerHTML =
    `<div class="kv-row"><span class="kv-key">Protocol</span><span class="protocol-tag">${summary.protocol_id || "n/a"}</span></div>` +
    `<div class="kv-row"><span class="kv-key">Peer</span><span class="peer-addr">${summary.peer_multiaddr || "n/a"}</span></div>` +
    `<table class="summary-table">` +
      `<thead><tr>` +
        `<th>Statement</th><th>OK</th><th>Schema</th><th>Depth</th>` +
        `<th>Mode</th><th>Verify</th><th>Exchange</th><th>Asset Hash</th>` +
      `</tr></thead>` +
      `<tbody>${rows}</tbody>` +
    `</table>`;
}

function renderPin(payload) {
  const pin = (payload.summary || {}).pin || {};
  const pinResults = Array.isArray(pin.pin_results) ? pin.pin_results : [];
  const cids = pinResults.map((x) => x.cid).filter(Boolean);

  pinPanelEl.innerHTML =
    `<div class="kv-row"><span class="kv-key">Mode requested</span><span class="kv-val">${pin.mode_requested || "n/a"}</span></div>` +
    `<div class="kv-row"><span class="kv-key">Backend used</span><span class="kv-val">${pin.backend_used || "n/a"}</span></div>` +
    `<div class="kv-row"><span class="kv-key">Fallback to mock</span><span class="kv-val">${pin.fell_back_to_mock === true ? "yes" : "no"}</span></div>` +
    `<div class="kv-row"><span class="kv-key">Status</span><span class="kv-val">${pin.error ? "error (" + pin.error + ")" : "ok"}</span></div>` +
    `<div class="kv-row"><span class="kv-key">CIDs</span><span class="kv-val" style="font-size:0.78rem;word-break:break-all">${cids.length ? cids.join(", ") : "n/a"}</span></div>`;
}

function renderArtifactLinks(payload) {
  artifactLinksEl.innerHTML = "";
  if (!currentRunId) {
    artifactLinksEl.innerHTML = `<div class="empty-state">No run yet.</div>`;
    return;
  }

  const links = [
    { label: "summary.json", href: `/api/runs/${currentRunId}/artifacts/summary.json` },
    { label: "report.json", href: `/api/runs/${currentRunId}/artifacts/report.json` },
    { label: "zk_serve.log", href: `/api/runs/${currentRunId}/logs/server` },
    { label: "analyze.log", href: `/api/runs/${currentRunId}/logs/analyze` },
    { label: "zk_dial.log", href: `/api/runs/${currentRunId}/logs/dial` },
    { label: "pin.log", href: `/api/runs/${currentRunId}/logs/pin` },
    { label: "fetch.log", href: `/api/runs/${currentRunId}/logs/fetch` },
  ];

  for (const item of links) {
    const a = document.createElement("a");
    a.href = item.href;
    a.textContent = item.label;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    artifactLinksEl.appendChild(a);
  }
}

function renderLogControls(payload) {
  logControlsEl.innerHTML = "";
  activeLogBtn = null;
  if (!currentRunId) {
    logControlsEl.textContent = "No run yet.";
    return;
  }
  if (payload.status === "running" || !payload.summary) {
    logControlsEl.textContent = "Logs become available after run completion.";
    return;
  }

  const names = ["server", "analyze", "dial", "pin", "fetch"];
  for (const name of names) {
    const btn = document.createElement("button");
    btn.textContent = `${name}.log`;
    btn.addEventListener("click", async () => {
      if (activeLogBtn) activeLogBtn.classList.remove("active");
      btn.classList.add("active");
      activeLogBtn = btn;
      try {
        const res = await fetch(`/api/runs/${currentRunId}/logs/${name}`);
        if (!res.ok) {
          let detail = "";
          try {
            const payload = await res.json();
            detail = payload.error ? `: ${payload.error}` : "";
          } catch (_err) {
            detail = "";
          }
          throw new Error(`HTTP ${res.status}${detail}`);
        }
        logViewerEl.textContent = await res.text();
      } catch (err) {
        logViewerEl.textContent = `Failed to load log: ${err}`;
      }
    });
    logControlsEl.appendChild(btn);
  }
}

/* ─── Main render ─── */

function renderRun(payload) {
  runJsonEl.textContent = JSON.stringify(payload, null, 2);
  renderStatements(payload);
  renderOverviewStats(payload);
  renderRiskPanel(payload);
  renderTimingChart(payload);
  renderTraffic(payload);
  renderProofSummary(payload);
  renderPin(payload);
  renderArtifactLinks(payload);
  renderLogControls(payload);

  if (payload.status === "running") {
    setBanner("running", "Run in progress\u2026");
    runBtn.disabled = true;
    return;
  }
  if (payload.status === "success") {
    setBanner("success", payload.message || "Run succeeded.");
  } else if (payload.status === "fallback") {
    setBanner("fallback", payload.message || "Fallback detected.");
  } else {
    setBanner("failed", payload.message || "Run failed.");
  }
  runBtn.disabled = false;
}

/* ─── Polling ─── */

async function pollRun(runId) {
  try {
    const res = await fetch(`/api/runs/${runId}`);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const payload = await res.json();
    renderRun(payload);
    if (payload.status !== "running" && pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  } catch (err) {
    setBanner("failed", `Polling failed: ${err}`);
    runBtn.disabled = false;
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }
}

async function startRun() {
  runBtn.disabled = true;
  setBanner("running", "Starting run\u2026");
  logViewerEl.textContent = "No log selected.";
  try {
    const res = await fetch("/api/runs", { method: "POST" });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const payload = await res.json();
    currentRunId = payload.run_id;
    renderRun(payload);
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => pollRun(currentRunId), 1000);
  } catch (err) {
    setBanner("failed", `Failed to start run: ${err}`);
    runBtn.disabled = false;
  }
}

/* ─── Collapsible metadata toggle ─── */

const metadataToggle = document.getElementById("metadata-toggle");
const metadataBody = document.getElementById("metadata-body");
if (metadataToggle && metadataBody) {
  metadataToggle.addEventListener("click", () => {
    metadataToggle.classList.toggle("open");
    metadataBody.classList.toggle("open");
  });
}

/* ─── Init ─── */

runBtn.addEventListener("click", startRun);
setBanner("ready", 'Ready. Click "Run End-to-End Validation".');
