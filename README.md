loom 🐳

See the connections. Know what might break.

loom is a codebase intelligence tool that connects code relationships to change-impact analysis and risk investigation.

A small code change can have consequences far beyond the file being edited. Finding those connections manually takes time, and overlooking a dependency can lead to unexpected failures.

loom helps developers investigate those connections. It maps a repository into a knowledge graph, traces dependencies, examines code changes, and surfaces potential risks using available evidence.

The goal isn’t to claim that a change is safe. It’s to help developers understand what could be affected, why it matters, and what still needs to be verified.

⸻

Why loom?

Understanding a codebase is difficult when its relationships are scattered across files, modules, functions, and tests.

Traditional code review often requires developers to piece together these relationships manually. loom brings them into one investigation workflow.

Instead of asking only what changed, loom helps you ask what that change could affect.

Features

🔎 Explore your codebase

Ask questions about your repository and investigate the code relationships and evidence available to the system.

↗ Impact analysis

Start with a file or code entity and trace its known relationships to understand which connected parts of the codebase may be affected.

◎ Risk investigation

Investigate local working-tree changes or compare Git revisions to identify potential risks associated with changed code.

⌘ Knowledge graph

Explore a graph representation of the repository to understand how code entities connect.

📋 Evidence-based findings

Connect investigation results to available repository evidence. Distinguish known relationships from potential risks and unresolved questions.

📝 Downloadable reports

Export investigation results as Markdown for sharing, reviewing, or documenting findings.

🤖 Optional AI commentary

Use optional model-generated commentary to help interpret investigation results. AI commentary supplements the available evidence; it does not replace verification.

⸻

How it works

        YOUR CODEBASE
              |
              v
     Build a knowledge graph
              |
              v
       Identify relationships
              |
              v
       Investigate changes
              |
              v
    Trace potential downstream impact
              |
              v
     Review findings and evidence

loom brings together repository structure, code relationships, Git changes, and available evidence to help developers investigate potential consequences.

The quality of the results depends on the repository information and relationships available to the system.

⸻

What makes loom different?

Evidence before confidence.

loom is designed to help developers investigate risk without pretending that uncertainty has disappeared.

* Relationships matter: A changed file is only the starting point. Its connections can reveal where further investigation is needed.
* Findings need context: Potential risks are more useful when accompanied by supporting evidence.
* Unknowns stay unknown: A risk investigation is not proof that a change will fail—or that it is safe.
* AI is optional: Model-generated commentary can assist interpretation without replacing evidence-based analysis.

The objective is to make change investigation more understandable, traceable, and useful.

⸻

Tech stack

Technology	Purpose
Python	Backend logic and investigation workflows
Flask	Web application and API
HTML	Application structure
CSS	Interface styling
JavaScript	Interactive frontend and API requests
Git	Change tracking and revision comparison
Knowledge graph	Representing code entities and their relationships
Ollama	Optional local model integration, when configured

⸻

Getting started

Prerequisites

Before running loom, make sure you have:

* Python 3 installed.
* Git installed.
* The loom repository cloned locally.
* A target repository available for analysis.
* The knowledge graph and repository data required by your current configuration.

If you want to use AI commentary, you may also need a compatible local model and a configured Ollama installation.

1. Clone the repository

git clone https://github.com/anshiiiee/loom.git
cd loom

2. Create a virtual environment

python3 -m venv venv

Activate it on macOS or Linux:

source venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

4. Configure the target repository

Configure the repository you want loom to investigate according to the project’s existing configuration and knowledge-graph setup.

Make sure the required graph data is available before running an investigation.

Note: The exact repository path and graph-generation steps depend on your local setup. Follow the project’s configured paths and graph-generation workflow rather than assuming that cloning loom automatically prepares another repository for analysis.

5. Start the application

python app.py

Open the local address in your browser:

http://127.0.0.1:5001

⸻

Using loom

Explore codebase

Ask a question about your repository and inspect the returned findings.

Analyze impact

Enter a file or code entity to investigate its known relationships and potential downstream impact.

Investigate changes

Choose one of the available investigation modes:

* Working tree: Investigate local changes.
* Git revisions: Compare a base revision with a head revision.

Review the findings and supporting evidence. If configured, enable optional AI commentary for additional interpretation.

Explore the graph

Open the knowledge graph to inspect the repository relationships represented by loom.

⸻

Design principles

loom is built around three principles:

1. Trace the connection.
Understand how a change relates to the rest of the system.

2. Show the evidence.
Make investigation results useful by connecting them to information available in the repository.

3. Be honest about uncertainty.
Potential risks are not guaranteed failures. Missing evidence is not proof of safety, and tests should not be reported as passing unless their execution and results have actually been verified.

⸻

Current limitations

loom’s findings depend on the repository data, graph relationships, and Git information available to it.

* Incomplete graph data can limit impact analysis.
* A dependency relationship does not automatically mean a change will cause a failure.
* Risk findings indicate areas that may need attention, not guaranteed defects.
* AI-generated commentary can be incorrect and should be checked against the underlying evidence.
* An investigation does not replace running the relevant tests and validating the application.

⸻

Roadmap

Potential areas for future development include:

* More precise dependency and change-impact tracing.
* Better evidence linking between changed code and downstream dependencies.
* Clearer risk prioritization and explanations.
* Improved investigation reports.
* More comprehensive validation and test integration.

⸻

Contributing

Contributions, feedback, and suggestions are welcome.

If you find a bug or have an idea for improving loom, open an issue in the repository. For code changes, submit a pull request describing the problem, the proposed solution, and how the change was tested.

⸻

License

A license has not yet been specified.

Until a license is added, don’t assume that the repository grants permission to reuse, modify, or redistribute its code.

⸻

Author

Anshi Limbani

GitHub: @anshiiiee

⸻

<p align="center">
  <strong>loom.</strong><br>
  <em>See the connections. Know what might break.</em>
</p>