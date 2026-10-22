"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const viewNames = {
  overview: "Overview",
  explore: "Explore codebase",
  impact: "Impact analysis",
  risk: "Risk investigation",
  graph: "Knowledge graph",
};

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function prettyJSON(value) {
  return escapeHTML(JSON.stringify(value, null, 2));
}

function show(view, options = {}) {
  const requested = viewNames[view] ? view : "overview";

  $$(".view").forEach((section) => {
    section.classList.toggle("hidden", section.id !== `view-${requested}`);
  });

  $$(".nav-item").forEach((button) => {
    const active = button.dataset.view === requested;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });

  const breadcrumb = $("#breadcrumb-current");
  if (breadcrumb) breadcrumb.textContent = viewNames[requested];

  if (options.updateHistory !== false) {
    history.replaceState(null, "", `#${requested}`);
  }

  if (options.scroll !== false) {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  if (requested === "graph") loadGraph();
}

$$("[data-view]").forEach((button) => {
  button.addEventListener("click", () => show(button.dataset.view));
});

$$("[data-go]").forEach((button) => {
  button.addEventListener("click", () => show(button.dataset.go));
});

window.addEventListener("hashchange", () => {
  show(location.hash.replace(/^#/, ""), {
    updateHistory: false,
    scroll: false,
  });
});

function setOutput(element, html) {
  if (element) element.innerHTML = html;
}

function showError(element, error) {
  setOutput(
    element,
    `<div class="error-message"><strong>Something went wrong.</strong><br>${escapeHTML(error.message || error)}</div>`
  );
}

function setBusy(button, busy, label = "Working…") {
  if (!button) return;

  if (busy) {
    button.dataset.originalContent = button.innerHTML;
    button.disabled = true;
    button.textContent = label;
  } else {
    button.disabled = false;
    if (button.dataset.originalContent) {
      button.innerHTML = button.dataset.originalContent;
      delete button.dataset.originalContent;
    }
  }
}

async function postJSON(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const raw = await response.text();
  let data;

  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    throw new Error(`The server returned an unreadable response (HTTP ${response.status}).`);
  }

  if (!response.ok) {
    throw new Error(data.error || data.message || `Request failed (HTTP ${response.status}).`);
  }

  if (data.error) throw new Error(data.error);
  return data;
}

function loadingMarkup(message) {
  return `<div class="loading-message">${escapeHTML(message)}</div>`;
}

function sectionTitle(title) {
  return `<div class="result-section-title">${escapeHTML(title)}</div>`;
}

function renderText(value) {
  if (value === null || value === undefined || value === "") return "Not provided";
  if (typeof value === "object") return `<pre>${prettyJSON(value)}</pre>`;
  return escapeHTML(value).replace(/\n/g, "<br>");
}

function renderList(items, emptyMessage = "No items returned.") {
  if (!Array.isArray(items) || items.length === 0) {
    return `<p>${escapeHTML(emptyMessage)}</p>`;
  }

  return `<div class="result-list">${items.map((item) => {
    if (typeof item === "string") {
      return `<div class="result-item"><p>${escapeHTML(item)}</p></div>`;
    }

    const title = item.name || item.path || item.file || item.title || item.id || "Finding";
    const description = item.description || item.reason || item.detail || item.message || "";
    return `<div class="result-item">
      <strong>${escapeHTML(title)}</strong>
      ${description ? `<p>${renderText(description)}</p>` : ""}
      ${item.evidence ? `<p>${renderText(item.evidence)}</p>` : ""}
    </div>`;
  }).join("")}</div>`;
}

function renderGeneric(data) {
  if (typeof data === "string") return `<div class="finding-card">${renderText(data)}</div>`;

  const preferred = ["answer", "response", "summary", "result", "message", "explanation"];
  let html = "";

  preferred.forEach((key) => {
    if (data[key] !== undefined && data[key] !== null && data[key] !== "") {
      html += `<div class="finding-card"><h3>${escapeHTML(key.replace(/_/g, " "))}</h3><p>${renderText(data[key])}</p></div>`;
    }
  });

  Object.entries(data).forEach(([key, value]) => {
    if (preferred.includes(key) || value === null || value === undefined) return;

    if (Array.isArray(value)) {
      html += sectionTitle(key.replace(/_/g, " "));
      html += renderList(value);
    } else if (typeof value === "object") {
      html += `<div class="finding-card"><h3>${escapeHTML(key.replace(/_/g, " "))}</h3>${renderGeneric(value)}</div>`;
    } else {
      html += `<div class="finding-card"><h3>${escapeHTML(key.replace(/_/g, " "))}</h3><p>${renderText(value)}</p></div>`;
    }
  });

  return html || `<pre>${prettyJSON(data)}</pre>`;
}

/* Explore the repository */

const exploreForm = $("#explore-form");
const exploreOutput = $("#explore-out");
const exploreButton = $("#explore-btn");

if (exploreForm) {
  exploreForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const question = $("#question")?.value.trim();
    if (!question) return;

    setBusy(exploreButton, true, "Exploring…");
    setOutput(exploreOutput, loadingMarkup("Looking for relevant code and evidence…"));

    try {
      const data = await postJSON("/api/query", { question });
      setOutput(exploreOutput, renderGeneric(data));
    } catch (error) {
      showError(exploreOutput, error);
    } finally {
      setBusy(exploreButton, false);
    }
  });
}

$$("[data-ask]").forEach((button) => {
  button.addEventListener("click", () => {
    const input = $("#question");
    if (input) {
      input.value = button.dataset.ask || "";
      input.focus();
    }
  });
});

/* Trace impact */

const impactForm = $("#impact-form");
const impactOutput = $("#impact-out");
const impactButton = $("#impact-btn");

if (impactForm) {
  impactForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const target = $("#impact-target")?.value.trim();
    if (!target) return;

    setBusy(impactButton, true, "Tracing…");
    setOutput(impactOutput, loadingMarkup("Tracing available relationships…"));

    try {
      const data = await postJSON("/api/impact", { target });
      setOutput(impactOutput, renderGeneric(data));
    } catch (error) {
      showError(impactOutput, error);
    } finally {
      setBusy(impactButton, false);
    }
  });
}

/* Investigate change risk */

const riskForm = $("#risk-form");
const riskOutput = $("#risk-out");
const riskButton = $("#risk-btn");
const modeInputs = $$('input[name="mode"]');
const commitFields = $("#commit-fields");

function updateMode() {
  const selected = $('input[name="mode"]:checked');
  const isCommitMode = selected?.value === "commits";
  if (commitFields) commitFields.classList.toggle("hidden", !isCommitMode);
}

modeInputs.forEach((input) => input.addEventListener("change", updateMode));
updateMode();

function getInvestigationSummary(data) {
  const candidates = [
    data.summary,
    data.overview,
    data.assessment,
    data.conclusion,
    data.report,
  ];

  return candidates.find((value) => typeof value === "string" && value.trim()) || "";
}

function renderInvestigation(data) {
  let html = "";
  const summary = getInvestigationSummary(data);

  if (summary) {
    html += `<div class="finding-card"><div class="eyebrow">SUMMARY</div><p>${renderText(summary)}</p></div>`;
  }

  const scalarKeys = [
    "risk_level",
    "risk_score",
    "confidence",
    "changed_files",
    "files_changed",
    "mode",
    "base",
    "head",
  ];

  const scalarItems = scalarKeys
    .filter((key) => data[key] !== undefined && data[key] !== null)
    .map((key) => `<div class="result-item"><strong>${escapeHTML(key.replace(/_/g, " "))}</strong><p>${renderText(data[key])}</p></div>`);

  if (scalarItems.length) {
    html += sectionTitle("Investigation details");
    html += `<div class="result-list">${scalarItems.join("")}</div>`;
  }

  const listKeys = [
    "findings",
    "risks",
    "warnings",
    "changed_paths",
    "changed_files_list",
    "affected_files",
    "tests",
    "evidence",
    "recommendations",
    "unknowns",
  ];

  listKeys.forEach((key) => {
    if (Array.isArray(data[key]) && data[key].length) {
      html += sectionTitle(key.replace(/_/g, " "));
      html += renderList(data[key]);
    }
  });

  const ai = data.ai_commentary || data.ai_analysis || data.model_analysis;
  if (ai) {
    html += sectionTitle("AI commentary");
    html += `<div class="finding-card">${renderText(ai)}</div>`;
  }

  if (!html) html = renderGeneric(data);

  html += `<div class="finding-card"><p><strong>Evidence boundary</strong></p>
    <p>This report reflects the data returned by the investigation. It does not establish that the change is safe, and it does not claim tests passed unless the backend explicitly reports that result.</p></div>`;

  html += `<div class="report-actions"><button class="button button-secondary" id="download-report" type="button">Download report ↓</button></div>`;
  return html;
}

function downloadReport(data) {
  const text = [
    "# loom investigation report",
    "",
    `Generated: ${new Date().toLocaleString()}`,
    "",
    "## Results",
    "",
    JSON.stringify(data, null, 2),
    "",
    "## Evidence boundary",
    "",
    "This report reflects the data returned by the investigation. It does not establish that the change is safe, and it does not claim tests passed unless the backend explicitly reports that result.",
  ].join("\n");

  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `loom-investigation-${new Date().toISOString().slice(0, 10)}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

if (riskForm) {
  riskForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const mode = $('input[name="mode"]:checked')?.value || "working";
    const body = {
      mode,
      run_model: Boolean($("#run-model")?.checked),
    };

    if (mode === "commits") {
      body.base = $("#base")?.value.trim();
      body.head = $("#head")?.value.trim();

      if (!body.base || !body.head) {
        showError(riskOutput, new Error("Enter both the base and head revisions."));
        return;
      }
    }

    setBusy(riskButton, true, "Investigating…");
    setOutput(riskOutput, loadingMarkup("Following changed code through the available graph and evidence…"));

    try {
      const data = await postJSON("/api/investigate", body);
      setOutput(riskOutput, renderInvestigation(data));

      const downloadButton = $("#download-report", riskOutput);
      if (downloadButton) {
        downloadButton.addEventListener("click", () => downloadReport(data));
      }
    } catch (error) {
      showError(riskOutput, error);
    } finally {
      setBusy(riskButton, false);
    }
  });
}

/* Load the graph only when the graph page is opened. */

let graphLoaded = false;

function loadGraph() {
  const frame = $("#graph-frame");
  if (!frame || graphLoaded) return;

  frame.src = "/graph";
  graphLoaded = true;

  frame.addEventListener("error", () => {
    graphLoaded = false;
  }, { once: true });
}

/* Initial page */

const initialView = location.hash.replace(/^#/, "") || "overview";

show(initialView, {
  updateHistory: false,
  scroll: false,
});