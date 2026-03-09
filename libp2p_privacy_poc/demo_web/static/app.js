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

let currentRunId = null;
let pollTimer = null;

function setBanner(status, message) {
  bannerEl.textContent = message || status;
  bannerEl.className = `card banner banner-${status}`;
}

function formatMs(value) {
  if (!Number.isFinite(value)) return "n/a";
  return `${Number(value).toFixed(3)} ms`;
}

function shortHash(hashText) {
  if (typeof hashText !== "string" || hashText.length < 12) return "n/a";
  return `${hashText.slice(0, 12)}...`;
}

function statementMapFrom(payload) {
  const empty = {
    membership_v2: { verified: false, mode: "n/a", verifyTime: "n/a", exchangeTime: "n/a" },
    continuity_v2: { verified: false, mode: "n/a", verifyTime: "n/a", exchangeTime: "n/a" },
    unlinkability_v2: { verified: false, mode: "n/a", verifyTime: "n/a", exchangeTime: "n/a" },
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
    };
  }

  return empty;
}

function renderStatements(payload) {
  const map = statementMapFrom(payload);
  statementCardsEl.innerHTML = "";
  for (const [name, row] of Object.entries(map)) {
    const div = document.createElement("div");
    div.className = "statement";
    div.innerHTML = `
      <div class="statement-title">${name}</div>
      <div class="statement-status ${row.verified ? "ok" : "bad"}">
        ${row.verified ? "verified" : "not verified"}
      </div>
      <div class="statement-meta">prove_mode: ${row.mode}</div>
      <div class="statement-meta">verify: ${row.verifyTime}</div>
      <div class="statement-meta">exchange: ${row.exchangeTime}</div>
    `;
    statementCardsEl.appendChild(div);
  }
}

function renderTraffic(payload) {
  const report = payload.report || {};
  const stats = (report.privacy_report || {}).statistics || {};
  const requested = (payload.config || {}).traffic_nodes ?? "n/a";
  const observed = stats.unique_peers ?? "n/a";
  const connections = stats.total_connections ?? "n/a";
  trafficPanelEl.innerHTML = `
    <div><strong>Requested traffic nodes:</strong> ${requested}</div>
    <div><strong>Observed unique peers:</strong> ${observed}</div>
    <div><strong>Total connections:</strong> ${connections}</div>
  `;
}

function renderProofSummary(payload) {
  const report = payload.report || {};
  const summary = report.proof_exchange_summary || {};
  const statements = Array.isArray(summary.statements) ? summary.statements : [];
  if (!statements.length) {
    proofSummaryEl.innerHTML = "<div>No proof exchange summary available.</div>";
    return;
  }

  const rows = statements
    .map((row) => {
      const verified = row.verified === true ? "✓" : "✗";
      const assetHash = shortHash(((row.asset_source || {}).sha256));
      return `
        <tr>
          <td>${row.statement || "n/a"}</td>
          <td>${verified}</td>
          <td>v${row.schema_v ?? "n/a"}</td>
          <td>${row.depth ?? "n/a"}</td>
          <td>${row.prove_mode || "n/a"}</td>
          <td>${formatMs(row.verify_ms)}</td>
          <td>${formatMs(row.exchange_ms)}</td>
          <td>${assetHash}</td>
        </tr>
      `;
    })
    .join("");

  proofSummaryEl.innerHTML = `
    <div><strong>Protocol:</strong> ${summary.protocol_id || "n/a"}</div>
    <div><strong>Peer:</strong> ${summary.peer_multiaddr || "n/a"}</div>
    <table class="summary-table">
      <thead>
        <tr>
          <th>Statement</th>
          <th>OK</th>
          <th>Schema</th>
          <th>Depth</th>
          <th>Mode</th>
          <th>Verify</th>
          <th>Exchange</th>
          <th>Asset Hash</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderPin(payload) {
  const pin = (payload.summary || {}).pin || {};
  const pinResults = Array.isArray(pin.pin_results) ? pin.pin_results : [];
  const cids = pinResults.map((x) => x.cid).filter(Boolean);

  pinPanelEl.innerHTML = `
    <div><strong>Requested mode:</strong> ${pin.mode_requested || "n/a"}</div>
    <div><strong>Backend used:</strong> ${pin.backend_used || "n/a"}</div>
    <div><strong>Fallback to mock:</strong> ${pin.fell_back_to_mock === true ? "yes" : "no"}</div>
    <div><strong>Pin status:</strong> ${pin.error ? `error (${pin.error})` : "ok"}</div>
    <div><strong>CIDs:</strong> ${cids.length ? cids.join(", ") : "n/a"}</div>
  `;
}

function renderArtifactLinks(payload) {
  artifactLinksEl.innerHTML = "";
  if (!currentRunId) {
    artifactLinksEl.textContent = "No run yet.";
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
    btn.textContent = `View ${name}.log`;
    btn.addEventListener("click", async () => {
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

function renderRun(payload) {
  runJsonEl.textContent = JSON.stringify(payload, null, 2);
  renderStatements(payload);
  renderTraffic(payload);
  renderProofSummary(payload);
  renderPin(payload);
  renderArtifactLinks(payload);
  renderLogControls(payload);

  if (payload.status === "running") {
    setBanner("running", "Run in progress...");
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
  setBanner("running", "Starting run...");
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

runBtn.addEventListener("click", startRun);
setBanner("ready", 'Ready. Click "Run Full Demo".');
