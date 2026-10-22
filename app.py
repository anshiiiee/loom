import json
import os
import re
import subprocess
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

from loom_graph import LoomGraph  # noqa: E402
from loom_ai import investigate  # noqa: E402

app = Flask(__name__)

REPO_DIR = BASE_DIR / "opensource-job-portal"
GRAPH_DIR = REPO_DIR / "graphify-out"
GRAPH_FILE = GRAPH_DIR / "graph.json"
GRAPHIFY_PATH = Path.home() / ".local" / "bin" / "graphify"

REV_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/~^-]{0,99}$")
MAX_IMPACT_ROWS = 60

_graph_cache = {}


def get_graph():
    if "g" not in _graph_cache:
        _graph_cache["g"] = LoomGraph()
    return _graph_cache["g"]


@app.route("/")
def index():
    node_count = 0
    edge_count = 0
    if GRAPH_FILE.exists():
        try:
            with GRAPH_FILE.open("r", encoding="utf-8") as graph_file:
                graph = json.load(graph_file)
            if isinstance(graph, dict):
                node_count = len(graph.get("nodes", []))
                edge_count = len(graph.get("links", graph.get("edges", [])))
        except (OSError, json.JSONDecodeError):
            pass
    return render_template(
        "index.html",
        node_count=node_count,
        edge_count=edge_count,
        repo_name="opensource-job-portal",
    )


@app.route("/graph")
def graph_view():
    return send_from_directory(str(GRAPH_DIR), "graph.html")


@app.route("/api/query", methods=["POST"])
def query_graph():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    if not question:
        return jsonify({"error": "Please enter a question."}), 400
    if not REPO_DIR.is_dir():
        return jsonify({"error": "Repository folder not found."}), 500
    if not GRAPHIFY_PATH.exists():
        return jsonify({"error": "Graphify executable not found."}), 500
    try:
        result = subprocess.run(
            [str(GRAPHIFY_PATH), "query", question, "--budget", "3000"],
            cwd=str(REPO_DIR),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        output = result.stdout.strip() or result.stderr.strip()
        if result.returncode != 0:
            return jsonify({"error": output or "Graphify query failed."}), 500
        return jsonify({"answer": output or "No results returned.", "success": True})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Query timed out. Try a shorter question."}), 504


@app.route("/api/impact", methods=["POST"])
def impact():
    data = request.get_json(silent=True) or {}
    target = str(data.get("target", "")).strip()
    if not target:
        return jsonify({"error": "Enter a file path or symbol name."}), 400

    g = get_graph()
    if "::" in target:
        path_hint, label = target.split("::", 1)
        seeds = g.find_symbols(label, path_hint)
    elif "/" in target or target.endswith((".py", ".ts", ".svelte", ".js")):
        seeds = g.nodes_in_file(target)
    else:
        seeds = g.find_symbols(target)

    if not seeds:
        return jsonify({"error": "No matching project nodes found in the graph."}), 404

    results = [r for r in g.trace_impact(seeds) if r["node_id"] not in seeds]
    prod = [r for r in results if not r["is_test"]]
    tests = [r for r in results if r["is_test"]]
    return jsonify({
        "seeds": [
            {"label": g.nodes[s]["label"], "file": g.nodes[s]["source_file"],
             "line": g.nodes[s]["source_location"]}
            for s in seeds[:20]
        ],
        "production_total": len(prod),
        "test_total": len(tests),
        "production": prod[:MAX_IMPACT_ROWS],
        "tests": tests[:MAX_IMPACT_ROWS],
        "note": "Dependency impact from imports and uses edges, not a full call graph. "
                "INFERRED edges are not proof of breakage.",
    })


def build_rev_args(data):
    mode = data.get("mode", "working")
    if mode == "working":
        return ["HEAD"], None
    if mode == "commits":
        base = str(data.get("base", "")).strip()
        head = str(data.get("head", "")).strip()
        if not (REV_RE.match(base) and REV_RE.match(head)):
            return None, "Base and head must be plain commit or branch names."
        return [base, head], None
    return None, "Unknown mode."


@app.route("/api/investigate", methods=["POST"])
def investigate_change():
    data = request.get_json(silent=True) or {}
    rev_args, err = build_rev_args(data)
    if err:
        return jsonify({"error": err}), 400
    run_model = bool(data.get("run_model", False))
    try:
        result = investigate(rev_args, on_token=None, run_model=run_model)
    except Exception as exc:
        return jsonify({"error": f"Investigation failed: {exc}"}), 500

    result["impact_total"] = len(result["impact"])
    result["test_total"] = len(result["tests"])
    result["impact"] = result["impact"][:MAX_IMPACT_ROWS]
    result["tests"] = result["tests"][:MAX_IMPACT_ROWS]
    result["prompt"] = None
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
