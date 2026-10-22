const $ = (s) => document.querySelector(s); const $$ = (s) => Array.from(document.querySelectorAll(s));

function h(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined && text !== null) e.textContent = text;
  return e;
}

async function post(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  let data = {};
  try { data = await res.json(); } catch (e) { /* non-JSON error page */ }
  if (!res.ok || data.error) throw new Error(data.error || "Request failed (" + res.status + ")");
  return data;
}

function busy(btn, on, label) {
  if (!btn.dataset.label) btn.dataset.label = btn.textContent;
  btn.disabled = on;
  btn.textContent = on ? label : btn.dataset.label;
}
function loading(out, msg) {
  const w = h("div", "loading");
  w.append(h("div", "spinner"), h("span", "", msg));
  out.replaceChildren(w);
}
function fail(out, err) { out.replaceChildren(h("div", "error", err.message || String(err))); }

function badge(text) {
  const t = text.toUpperCase();
  let k = "mute";
  if (t.includes("NOT VERIFIED") || t.includes("INSUFFICIENT")) k = "bad";
  else if (t.includes("INFERRED")) k = "warn";
  else if (t.includes("VERIFIED")) k = "ok";
  return h("span", "badge " + k, text);
}
function block(title, ...kids) {
  const b = h("section", "block");
  b.append(h("h3", "", title));
  kids.forEach((k) => b.append(k));
  return b;
}

/* ---------- navigation ---------- */
const VIEWS = {
  overview: ["CODEBASE INTELLIGENCE", "Understand your code."],
  explore: ["EXPLORE", "Explore the connections."],
  impact: ["IMPACT ANALYSIS", "Trace what could change."],
  risk: ["RISK INVESTIGATION", "Investigate what might break."],
  graph: ["KNOWLEDGE GRAPH", "See the whole weave."],
};
function show(view) {
  if (!VIEWS[view]) view = "overview";
  $$(".view").forEach((v) => v.classList.toggle("hidden", v.id !== "view-" + view)); $$
(".nav").forEach((n) => n.classList.toggle("active", n.dataset.view === view));
  $("#eyebrow").textContent = VIEWS[view][0];
  $("#page-title").textContent = VIEWS[view][1];
  if (view === "graph") {
    const f = $("#graph-frame");
    if (!f.getAttribute("src")) f.setAttribute("src", f.dataset.src);
  }
  history.replaceState(null, "", "#" + view);
  window.scrollTo(0, 0);
}
$$(".nav").forEach((b) => b.addEventListener("click", () => show(b.dataset.view))); $$
("[data-go]").forEach((b) => b.addEventListener("click", () => show(b.dataset.go)));

/* ---------- explore ---------- */
async function explore(q) {
  const out = $("#explore-out"), btn = $("#explore-btn");
  if (!q) return fail(out, new Error("Please enter a question first."));
  $("#question").value = q;
  loading(out, "Tracing connections in the graph...");
  busy(btn, true, "Searching...");
  try {
    const d = await post("/api/query", { question: q });
    const pre = h("pre", "plain", d.answer || "No results returned.");
    out.replaceChildren(pre);
  } catch (e) { fail(out, e); } finally { busy(btn, false); }
}
$("#explore-form").addEventListener("submit", (e) => { e.preventDefault(); explore($("#question").value.trim()); }); $$("[data-ask]").forEach((b) => b.addEventListener("click", () => explore(b.dataset.ask)));

/* ---------- shared rendering ---------- */
function depRow(r) {
  const row = h("div", "row");
  const top = h("div", "row-top");
  top.append(badge(r.status), h("strong", "", r.label));
  if (r.is_test) top.append(h("span", "tag", "test"));
  row.append(top,
    h("code", "path", r.file + " " + r.line),
    h("span", "meta", "depth " + r.depth + " · " + r.relation + " (" + r.confidence + ") · evidence at " + r.edge_file + " " + r.edge_line));
  return row;
}
function depGroups(rows) {
  const order = ["VERIFIED DEPENDENCY", "INFERRED DEPENDENCY", "POTENTIAL (indirect)"];
  const by = {};
  rows.forEach((r) => { (by[r.status] = by[r.status] || []).push(r); });
  const wrap = h("div");
  order.concat(Object.keys(by).filter((k) => !order.includes(k))).forEach((k, i) => {
    if (!by[k]) return;
    const d = document.createElement("details");
    d.open = i === 0;
    d.append(h("summary", "", k + " (" + by[k].length + ")"));
    by[k].forEach((r) => d.append(depRow(r)));
    wrap.append(d);
  });
  return wrap;
}
function codeList(items) {
  const l = h("div");
  items.forEach((t) => { const r = h("div", "row"); r.append(h("code", "path", t)); l.append(r); });
  return l;
}

/* ---------- impact ---------- */
function renderImpact(d) {
  const out = h("div");
  out.append(h("p", "lead", d.production_total + " production and " + d.test_total + " test components depend on this target."));
  const chips = h("div", "chips");
  d.seeds.forEach((s) => chips.append(h("span", "chip", s.label + " · " + s.file + " " + s.line)));
  out.append(block("Target", chips));
  if (d.production.length) {
    const shown = d.production.length < d.production_total ? " (showing " + d.production.length + " of " + d.production_total + ")" : "";
    out.append(block("Production components" + shown, depGroups(d.production)));
  }
  if (d.tests.length) out.append(block("Tests linked in the graph", depGroups(d.tests)));
  out.append(block("How to read this",
    h("p", "meta", "VERIFIED means the relationship appears directly in the code. It does not prove a change will break the dependent. INFERRED edges are weaker, and POTENTIAL results are two or more hops away. " + d.note)));
  return out;
}
$("#impact-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const out = $("#impact-out"), btn = $("#impact-btn");
  loading(out, "Tracing dependents...");
  busy(btn, true, "Tracing...");
  try { out.replaceChildren(renderImpact(await post("/api/impact", { target: $("#impact-target").value.trim() }))); } catch (err) { fail(out, err); } finally { busy(btn, false); } }); $$("[data-target]").forEach((b) => b.addEventListener("click", () => { $("#impact-target").value = b.dataset.target; $("#impact-form").requestSubmit(); }));

function downloadInvestigationReport(d, mode) {
  const lines = [];
  const facts = d.rule_findings || [];
  const symbols = d.symbols || [];
  const paths = d.paths || [];
  const impact = d.impact || [];
  const tests = d.tests || [];
  const heuristicTests = d.heuristic_tests || [];
  const add = (...items) => lines.push(...items);
  const status = d.investigation_status || (
    paths.length || symbols.length
      ? "CHANGES_DETECTED_STATUS_UNKNOWN"
      : "STATUS_UNKNOWN"
  );
  const statusDescriptions = {
    NO_CHANGES_DETECTED:
      "No changes were detected in the selected Git diff. This is not a safety assessment.",
    CHANGES_UNMAPPED:
      "Changes were detected, but no changed symbols could be mapped to the knowledge graph.",
    CHANGES_MAPPED:
      "Changes were detected and at least one changed symbol was mapped to the knowledge graph.",
    CHANGES_DETECTED_STATUS_UNKNOWN:
      "Change information was returned, but the backend did not provide an explicit investigation status.",
    STATUS_UNKNOWN:
      "The investigation status could not be established from the available response."
  };
  add(
    "# Loom — Risk Investigation Report",
    "",
    `Generated: ${new Date().toLocaleString()}`,
    `Investigation mode: ${mode}`,
    "",
    "## Investigation status",
    "",
    `**${status}**`,
    "",
    statusDescriptions[status] || "Unrecognized investigation status; interpret the results cautiously.",
    ""
  );
  if (status === "NO_CHANGES_DETECTED") {
    add(
      "## Assessment",
      "",
      "There was no diff to investigate. No conclusion about code safety can be drawn.",
      "",
      "---",
      "Generated by loom — See the connections. Know what might break."
    );
  } else {
    add("## Summary", "");
    if (facts.length) {
      add(`${facts.length} deterministic finding(s) require human review.`);
    } else {
      add("No deterministic rule findings were reported. This does not establish that the change is safe.");
    }

    add("", "## Changed files", "");

    if (paths.length) {
      paths.forEach((p) => add(`- \`${p}\``));
    } else {
      add("- No changed-file paths were returned.");
    }

    add("", "## Changed symbols", "");

    if (symbols.length) {
      symbols.forEach((s) => {
        add(`- **${s[1]}** — \`${s[0]} ${s[2]}\``);
      });
    } else {
      add("- No changed symbols were mapped.");
    }

    add("", "## Verified findings", "");

    if (facts.length) {
      facts.forEach((f) => {
        add(
          `### ${f.status || "VERIFIED FACT"}: ${f.title}`,
          "",
          `- **Detail:** ${f.detail}`,
          `- **Why it matters:** ${f.why_it_matters}`,
          `- **Suggested verification:** ${f.verify}`,
          ""
        );
      });
    } else {
      add("No deterministic rule findings were returned.", "");
    }

    add("## Affected components", "");

    if (impact.length) {
      impact.forEach((item) => {
        add(
          `- **${item.label || item.id || "Component"}**`,
          `  - File: \`${item.file || "Not supplied"}\``,
          `  - Relationship/evidence: ${item.status || "Not supplied"}`
        );
      });
    } else {
      add("No affected components were returned by the graph trace.");
    }

    add("", "## Test status", "");

    if (tests.length) {
      tests.forEach((t) => {
        add(`- Graph-linked test candidate: \`${t.label || t.file || t.id || "Unnamed"}\` — NOT VERIFIED`);
      });
    } else {
      add("- No graph-linked test candidates were returned.");
    }

    heuristicTests.forEach((t) => {
      add(`- Heuristic test candidate: \`${t}\` — NOT VERIFIED`);
    });

    add(
      "- **Execution:** Tests were not executed as part of this investigation.",
      "",
      "## AI commentary",
      ""
    );

    if (d.ai_text) {
      add(
        "**UNVERIFIED — local model output. This is commentary, not a confirmed finding.**",
        "",
        d.ai_text.trim()
      );
    } else {
      add("No AI commentary was included.");
    }

    add(
      "",
      "## Remaining uncertainties",
      "",
      "- Graph relationships describe extracted structure; they do not prove runtime behaviour or breakage.",
      "- URL routing and test-client relationships may be missing from the graph.",
      "- The deterministic rules cover only a limited set of change types.",
      "- A lack of findings is not proof that a change is safe.",
      "",
      "## Overall assessment",
      "",
      facts.length
        ? "Loom detected one or more rule-based findings. Review the evidence and verify affected behaviour before merging."
        : "Loom did not report a deterministic rule finding. Available evidence is insufficient to conclude that the change is safe.",
      "",
      "---",
      "Generated by loom — See the connections. Know what might break."
    );
  }
  const blob = new Blob(
    [lines.join("\n") + "\n"],
    { type: "text/markdown;charset=utf-8" }
  );
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `loom-investigation-${new Date().toISOString().slice(0, 10)}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/* ---------- risk investigation report ---------- */
function renderRisk(d, aiRequested) {
  const out = h("div", "report");
  const facts = d.rule_findings || [];
  const syms = d.symbols || [];
  let kind = "mute", text;
  if (d.comment_only) { kind = "ok"; text = "Comment-only change. No functional change detected."; }
  else if (facts.length) { kind = "warn"; text = facts.length + " verified finding" + (facts.length > 1 ? "s" : "") + " need a human check."; }
  else if (!syms.length) { text = d.message || "No changes were mapped to graph symbols."; }
  else { text = "No rule matched. That is not a clean bill of health: no tests were run."; }
  const v = h("div", "verdict " + kind);
  v.append(h("strong", "", text));
  if (d.message && d.message !== text) v.append(h("span", "meta", d.message));
  out.append(v);

  if (syms.length) {
    const l = h("div");
    syms.forEach((s) => { const r = h("div", "row"); r.append(h("strong", "", s[1]), h("code", "path", s[0] + " " + s[2])); l.append(r); });
    out.append(block("Changed symbols", l));
  } else if ((d.paths || []).length) {
    out.append(block("Changed files", codeList(d.paths)));
  }

  if (facts.length) {
    const l = h("div");
    facts.forEach((f) => {
      const c = h("div", "finding");
      const top = h("div", "row-top");
      top.append(badge(f.status), h("strong", "", f.title));
      c.append(top, h("code", "path", f.detail),
        h("span", "meta", "Why it matters: " + f.why_it_matters),
        h("span", "meta", "Verify: " + f.verify));
      l.append(c);
    });
    out.append(block("Verified findings (from code, not AI)", l));
  }

  const dep = (d.impact || []);
  if (dep.length) {
    const note = d.impact_scope === "file"
      ? "The changed symbol has no dependents in the graph, so these are dependents of the whole file."
      : "Dependents of the changed symbols.";
    out.append(block("Affected components · " + d.impact_total + " found", h("p", "meta", note), depGroups(dep)));
  } else if (syms.length && !d.comment_only) {
    out.append(block("Affected components",
      h("p", "meta", "None found in the graph. The graph does not capture URL routing or test-client calls, so this is not proof of safety.")));
  }

  if (!d.comment_only && syms.length) {
    const tl = h("div");
    if ((d.tests || []).length) tl.append(depGroups(d.tests));
    (d.heuristic_tests || []).forEach((t) => {
      const r = h("div", "row");
      const top = h("div", "row-top");
      top.append(badge("NOT VERIFIED"), h("code", "path", t), h("span", "tag", "naming heuristic"));
      r.append(top);
      tl.append(r);
    });
    const ran = h("div", "row");
    const rt = h("div", "row-top");
    rt.append(badge("NOT VERIFIED"), h("strong", "", "Tests were not executed"));
    ran.append(rt, h("span", "meta", "This project needs PostgreSQL and its pinned dependencies to run tests, which are not set up here. No pass or fail is claimed."));
    tl.append(ran);
    out.append(block("Tests", tl));
  }

  if (d.ai_text) {
    const a = h("div", "ai");
    a.append(h("p", "meta", "UNVERIFIED AI explanation from a small local model. Treat it as a lead, not a finding."), h("pre", "plain", d.ai_text.trim()));
    out.append(block("AI commentary", a));
  } else if (!aiRequested && !d.comment_only && facts.length) {
    out.append(block("AI commentary", h("p", "meta", "Off. Tick the AI option above to add a local-model explanation of the verified findings.")));
  }

  const un = h("ul", "plain");
  ["Graph edges show structure, not behaviour. A dependent is not proven to break.",
   "Routing and test-client calls are not captured, so views can look isolated.",
   "Rule checks cover only a few change types, such as status codes and permissions."].forEach((t) => un.append(h("li", "", t)));
  out.append(block("Remaining uncertainties", un));
  return out;
}

$$("input[name=mode]").forEach((r) => r.addEventListener("change", () => {
  $("#commit-fields").classList.toggle("hidden", $("input[name=mode]:checked").value !== "commits");
}));

$("#risk-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const out = $("#risk-out"), btn = $("#risk-btn");
  const mode = $("input[name=mode]:checked").value;
  const ai = $("#run-model").checked;
  loading(out, ai ? "Analysing the change and asking the local model..." : "Analysing the change...");
  busy(btn, true, "Investigating...");
  try {
    const d = await post("/api/investigate", {
      mode,
      base: $("#base").value.trim(),
      head: $("#head").value.trim(),
      run_model: ai
    });
    out.replaceChildren(renderRisk(d, ai));
  
    const downloadBtn = h("button", "btn", "Download Report");
    downloadBtn.type = "button";
    downloadBtn.addEventListener("click", () => downloadInvestigationReport(d, mode));
  
    out.prepend(downloadBtn);
  } catch (err) {
    fail(out, err);
  } finally {
    busy(btn, false);
  }
});

show(location.hash.slice(1));