import json
import sys
import urllib.request

from loom_graph import LoomGraph
from diff_mapper import (
    git_diff, parse_changed_lines, py_def_ranges,
    node_line, innermost_overlaps, heuristic_tests,
)
from evidence import get_diff_text, snippet_for_node
from rules import detect_rule_findings

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5-coder:3b"
MAX_IMPACT_ITEMS = 8


def collect_changes(g, rev_args):
    """Map a git diff to graph seed nodes. Returns (changed_symbols, seed_ids, changed_paths)."""
    changed = parse_changed_lines(git_diff(rev_args))
    symbols = []
    seeds = []
    for path, ranges in changed.items():
        ids = g.nodes_in_file(path)
        nodes = [g.nodes[i] for i in ids]
        sym_nodes = [n for n in nodes if not path.endswith(n["label"])]
        defs = py_def_ranges(path) if path.endswith(".py") else None
        for s, e in ranges:
            if defs is not None:
                for d in innermost_overlaps(defs, s, e):
                    for n in sym_nodes:
                        if node_line(n) == d[0] and n["id"] not in seeds:
                            seeds.append(n["id"])
                            symbols.append((path, n["label"], n["source_location"]))
    return symbols, seeds, list(changed.keys())


def is_comment_only(diff_text):
    changed = [
        l[1:].strip() for l in diff_text.splitlines()
        if (l.startswith("+") or l.startswith("-"))
        and not l.startswith("+++") and not l.startswith("---")
    ]
    if not changed:
        return False
    return all(c == "" or c.startswith(("#", "//", "/*", "*", "*/")) for c in changed)


def build_prompt(diff_text, symbols, impact, tests, heuristic,
                 snippets=None, rule_findings=None):
    lines = []
    lines.append("You are a code reviewer. Use ONLY the evidence below.")
    lines.append("Do not invent files, functions, or test results.")
    lines.append("")
    lines.append("== GIT DIFF ==")
    lines.append(diff_text)
    lines.append("")
    lines.append("== CHANGED SYMBOLS (from graph) ==")
    for path, label, loc in symbols:
        lines.append(f"- {label} in {path} at {loc}")
    lines.append("")
    lines.append("== CURRENT SOURCE OF CHANGED SYMBOLS ==")
    for s in snippets or ["(not available)"]:
        lines.append(s)
    lines.append("")
    lines.append("== GRAPH DEPENDENTS (who depends on the change) ==")
    if not impact:
        lines.append("- none found in graph")
    for r in impact[:MAX_IMPACT_ITEMS]:
        lines.append(f"- [{r['status']}] {r['label']} in {r['file']} {r['line']} "
                     f"via {r['relation']} ({r['confidence']})")
    lines.append("")
    lines.append("== TESTS FOUND IN GRAPH ==")
    if not tests:
        lines.append("- none")
    for r in tests[:MAX_IMPACT_ITEMS]:
        lines.append(f"- {r['label']} in {r['file']} {r['line']}")
    lines.append("")
    lines.append("== HEURISTIC TEST CANDIDATES (not verified) ==")
    for c in heuristic or ["none"]:
        lines.append(f"- {c}")
    lines.append("")
    lines.append("== TASK ==")
    if rule_findings:
        lines.append("CONFIRMED FINDINGS (do not dispute):")
        for f in rule_findings:
            lines.append(f"- {f['title']}: {f['detail']}")
        lines.append("In 3 sentences or fewer, explain what callers or tests of the changed")
        lines.append("function could break because of the confirmed finding. Refer to the")
        lines.append("changed lines in the diff. Do not list any other risks.")
    else:
        lines.append("List at most 2 possible risks. Each must quote a CHANGED line")
        lines.append("(starting with + or -) and explain how that exact change could fail.")
        lines.append("Do not criticise unchanged code. If you cannot, answer INSUFFICIENT EVIDENCE.")
    return "\n".join(lines)


def ask_ollama(prompt, on_token=None):
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": True,
                       "options": {"temperature": 0.2, "num_ctx": 4096}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    parts = []
    with urllib.request.urlopen(req, timeout=600) as resp:
        for raw in resp:
            if not raw.strip():
                continue
            chunk = json.loads(raw)
            piece = chunk.get("response", "")
            parts.append(piece)
            if on_token:
                on_token(piece)
            if chunk.get("done"):
                break
    return "".join(parts)


def investigate(rev_args, on_token=None, run_model=True):
    """Investigate real Git changes and keep evidence separate from AI commentary."""
    g = LoomGraph()
    full_diff = git_diff(rev_args)
    symbols, seeds, paths = collect_changes(g, rev_args)
    out = {
        "symbols": symbols,
        "paths": paths,
        "rule_findings": [],
        "impact": [],
        "tests": [],
        "heuristic_tests": heuristic_tests(paths),
        "comment_only": False,
        "prompt": None,
        "ai_text": None,
        "message": None,
        "investigation_status": None,
    }

    # Distinguish an empty diff from changes that could not be mapped.
    changed_lines = [
        line for line in full_diff.splitlines()
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    ]

    if not changed_lines:
        out["investigation_status"] = "NO_CHANGES_DETECTED"
        out["message"] = (
            "No changes detected in the selected Git diff. "
            "This is not a safety assessment."
        )
        return out

    if not seeds:
        out["investigation_status"] = "CHANGES_UNMAPPED"
        out["message"] = (
            "Changes were detected, but no changed symbols could be mapped "
            "to the knowledge graph. File-level impact may be incomplete."
        )
        out["rule_findings"] = detect_rule_findings(full_diff)
        return out

    out["investigation_status"] = "CHANGES_MAPPED"

    results = [r for r in g.trace_impact(seeds) if r["node_id"] not in seeds]
    out["impact_scope"] = "symbol"

    if not results:
        file_seeds = []
        for p in paths:
            file_seeds.extend(
                i for i in g.nodes_in_file(p)
                if p.endswith(g.nodes[i]["label"])
            )
        results = [
            r for r in g.trace_impact(file_seeds)
            if r["node_id"] not in file_seeds
        ]
        out["impact_scope"] = "file"

    out["impact"] = [r for r in results if not r["is_test"]]
    out["tests"] = [r for r in results if r["is_test"]]

    if is_comment_only(full_diff):
        out["comment_only"] = True
        out["message"] = (
            "VERIFIED FACT: every changed line is a comment or blank line, "
            "so no functional change was detected. AI risk analysis skipped."
        )
        return out

    out["rule_findings"] = detect_rule_findings(full_diff)

    snippets = [
        s for s in (
            snippet_for_node(p, loc) for p, _, loc in symbols
        ) if s
    ]

    out["prompt"] = build_prompt(
        get_diff_text(rev_args),
        symbols,
        out["impact"],
        out["tests"],
        out["heuristic_tests"],
        snippets,
        out["rule_findings"],
    )

    if run_model:
        out["ai_text"] = ask_ollama(out["prompt"], on_token=on_token)

    return out

if __name__ == "__main__":
    args = sys.argv[1:] or ["HEAD"]
    print("Analysing... (verified findings print first, then the AI explanation streams)\n",
          flush=True)
    result = investigate(args, on_token=lambda t: print(t, end="", flush=True),
                         run_model=True)
    # Note: with streaming, the model text has already printed above.
    print("\n\n" + "=" * 60)
    print("SUMMARY (from code, not AI)")
    print("Changed symbols:",
          ", ".join(f"{l} ({p})" for p, l, _ in result["symbols"]) or "none")
    if result["message"]:
        print(result["message"])
    for f in result["rule_findings"]:
        print(f"[{f['status']}] {f['title']}")
        print(f"    {f['detail']}")
        print(f"    Why it matters: {f['why_it_matters']}")
        print(f"    Verify: {f['verify']}")
    print(f"Graph dependents: {len(result['impact'])} production, {len(result['tests'])} test")
    print("Heuristic test candidates (not verified):",
          ", ".join(result["heuristic_tests"]) or "none")
    if result["ai_text"]:
        print("\nThe text streamed above is an UNVERIFIED AI explanation from a small local model.")