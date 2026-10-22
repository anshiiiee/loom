# loom

**See the connections. Know what might break.**

loom investigates code changes by connecting Git diffs to a codebase knowledge graph. It traces relationships, applies deterministic rules, and helps developers understand what a change might affect.

## Features

- **Explore:** Ask questions about the codebase and trace relationships.
- **Impact analysis:** Identify components connected to a selected symbol.
- **Risk investigation:** Map changed symbols and identify potential risks.
- **Evidence-based findings:** Distinguish verified findings from inferred relationships and unverified AI commentary.
- **Downloadable reports:** Export investigation results as Markdown.

## Principles

- A dependency does not prove that something will break.
- AI output is commentary, not verified evidence.
- Test candidates are not treated as executed tests.
- No findings does not mean a change is safe.

## Requirements

- Python 3
- Git
- A target repository to analyze
- Graphify-generated knowledge graph data for graph-based analysis

Optional AI explanations require a compatible local Ollama installation and configured model.

## Setup

1. Clone the Loom repository from GitHub.
2. Create a virtual environment: `python3 -m venv venv`.
3. Activate it: `source venv/bin/activate`.
4. Install dependencies: `pip install -r requirements.txt`.
5. Start the application: `python app.py`.

## Usage

1. Explore the codebase or select a symbol for impact analysis.
2. Run a risk investigation against the selected Git changes.
3. Review findings, dependencies, and test candidates.
4. Download the Markdown investigation report.

## Limitations

- Results depend on knowledge graph coverage.
- Graph relationships do not prove runtime behavior or breakage.
- Some routes and indirect dependencies may be missing.
- Tests are not claimed to pass unless actually executed.

## Project status

Loom is under active development.

## License

No license has been selected yet.
