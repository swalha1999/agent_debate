# Guidelines for Writing Professional Software at the Highest Level of Excellence

Dr. Yoram Segal
All rights reserved © — Dr. Yoram Segal
2026-03-26
Version 3.00

---

## Table of Contents

1. Introduction — The Professional Programmer in the Age of AI
2. Mandatory Project Structure and Documentation
3. Code Documentation and Project Structure
4. SDK Architecture and Object-Oriented Design
5. API Gatekeeper and Rate Limiting
6. Test-Driven Development and Quality Assurance
7. Code Review, Configuration Management, and Information Security
8. Version Control and the `uv` Package Manager
9. Research and Results Analysis
10. User Interface and User Experience
11. Costs and Pricing
12. Extensibility and Maintainability
13. International Quality Standards
14. Project Organization as a Package
15. Parallel Processing and Performance
16. Modular Design and Building Blocks
17. Final Checklist
18. Additional Sources and Standards
19. Important Note
20. Appendix: Detailed Submission Guidelines

---

## 1. Introduction — The Professional Programmer in the Age of AI

### 1.1 What is a Professional Programmer?

A **Professional Software Engineer** is not just someone who knows how to write code, but someone who understands the full software lifecycle: planning, documentation, testing, and maintaining complex systems. A professional programmer adheres to high code-quality standards, follows proven best practices, and works in a team while maintaining consistency, clear communication, and accountability.

Key characteristics of a professional programmer:

- **Systems thinking** — the ability to see the big picture and understand how each component fits into the system as a whole
- **Plan before doing** — writing requirements, architecture, and design documents before the first line of code
- **Quality without compromise** — emphasis on clean, documented, well-tested, and secure code
- **Continuous learning** — keeping up with new technologies, tools, and methodologies
- **Effective communication** — the ability to describe technical solutions to varied audiences

### 1.2 Teamwork in Software Development

Professional software development is almost always done in a team. Effective teamwork is based on several key principles:

**Roles and responsibilities** — A typical development team includes a Software Architect responsible for system design, Developers who implement the code, a QA Engineer who validates product quality, a Product Manager who defines requirements, and often a DevOps engineer responsible for infrastructure and deployment pipelines.

**Workflows** — Professional teams use methodologies such as Scrum, Kanban, or SAFe, which include daily standups, sprint reviews, retrospectives, and code reviews via Pull Requests.

**Shared standards** — The team defines and enforces coding standards, a unified project structure, and automated CI/CD test/deploy pipelines.

### 1.3 Software Project Lifecycle

Every professional software project follows a defined Software Development Life Cycle (SDLC):

1. **Requirements** — write a detailed Product Requirements Document (PRD)
2. **Planning and Architecture** — system design, planning documents (PLAN), and milestones (TODO)
3. **Development** — write code per the plan, using TDD (Test-Driven Development)
4. **Testing** — unit, integration, and system tests
5. **Release** — deploy the software to production
6. **Maintenance and Improvement** — bug fixes, new features, and upgrades

### 1.4 The Revolution: AI and Guided Coding

In the current era, AI and AI agents are fundamentally changing how software is developed. **Vibe Coding** — where a programmer guides AI agents to create, test, and improve code — enables a single developer to act as a Senior Software Architect orchestrating multiple AI agents in parallel.

**Multiplying productivity:** A programmer working with AI agents using guided coding can produce, in a given time, up to 16× more high-quality lines of code compared to writing manually without AI. The implication is that any programmer, regardless of seniority or prior experience, can become a high-level professional — provided they follow the rules and processes defined in this document.

**The first and most important rule:** To unlock the full potential of AI agents, you must define clear and detailed requirements. Without requirements, planning, and architecture documents, AI agents will produce code that may work but will not meet professional standards. Therefore, **the first rule of professional coding with AI is to define and require full documentation before a single line of code**.

This document defines all the requirements, standards, and processes you must meet to produce software at the highest professional level. Follow these guidelines and you will be able to harness the full power of AI agents and become an architect orchestrating a team of agents — producing professional-grade results that were not previously possible.

---

## 2. Mandatory Project Structure and Documentation

Every professional software project **must** include a minimal directory structure and documentation. Without these documents, the project does not meet minimum requirements.

### 2.1 README.md at the Project Root

Every project **must** include a `README.md` file at the root directory. This file serves as a full user manual [1], [2] and includes:

- **Installation Instructions** — system requirements, step-by-step install, environment setup, common troubleshooting
- **Usage Instructions** — running in different modes, flags and options, CLI/GUI, and a typical workflow
- **Examples and Demos** — code examples, screenshots, common use-case scenarios
- **Configuration Guide** — explanation of config files, parameters, and their effects
- **Contribution Guidelines** — code and style standards
- **License & Credits** — usage license and attribution to third-party libraries

### 2.2 The `/docs` Folder — Mandatory Documentation

Every project **must** include a `/docs` folder at the project root, containing at minimum:

1. **Product Requirements Document** — `docs/PRD.md` (PRD)

   The PRD is the central document that defines the project's purpose and requirements [3], [4], [5]. It includes:

   - Project overview and context, user-problem description, market analysis, and target-audience identification
   - Measurable goals, KPIs, and acceptance criteria
   - Functional and non-functional requirements, user stories, and use-case scenarios
   - Assumptions, dependencies, constraints, and out-of-scope items
   - Timeline and milestones with expected deliverables

2. **Planning Document** — `docs/PLAN.md`

   The planning document describes the project's architecture and technical design and includes:

   - C4 Model diagrams (Context, Container, Component, Code)
   - UML diagrams for complex processes and deployment diagrams
   - Architecture Decision Records (ADRs) with rationale, trade-offs, and alternatives
   - API and interface documentation, data schemas, and contracts

3. **Tasks Document** — `docs/TODO.md`

   The tasks document details all required tasks for project implementation:

   - Detailed task list with priorities and status (not started / in progress / done)
   - Phased breakdown with milestones
   - Ownership for each task
   - Definition of done for each task

### 2.3 Dedicated PRDs for Algorithms and Mechanisms

**Important requirement:** For every specific algorithm, central mechanism, or complex technical component in the project, you must create a dedicated, separate PRD document. For example:

- `docs/PRD_ml_algorithm.md` — machine learning algorithm
- `docs/PRD_authentication.md` — user authentication mechanism
- `docs/PRD_search_engine.md` — search engine
- `docs/PRD_caching.md` — caching system

Each dedicated PRD includes:

- A detailed description of the algorithm or mechanism, including theoretical background
- Specific requirements, expected I/O, and performance metrics
- Constraints and limitations, alternatives considered, and rationale for the choice
- Specific success criteria and test scenarios

### 2.4 Recommended Project Structure

```
project-root/
├── src/                       # Source code
│   ├── <package>/
│   │   ├── __init__.py
│   │   ├── sdk/               # SDK layer
│   │   │   └── sdk.py
│   │   ├── services/          # Business logic
│   │   ├── shared/            # Shared utilities
│   │   │   ├── gatekeeper.py  # API gatekeeper
│   │   │   ├── config.py      # Configuration manager
│   │   │   └── version.py     # Version tracking
│   │   └── constants.py
│   └── main.py
├── tests/                     # Unit and integration tests
│   ├── unit/
│   └── integration/
├── docs/                      # Documentation (MANDATORY)
│   ├── PRD.md
│   ├── PLAN.md
│   ├── TODO.md
│   └── PRD_<mechanism>.md     # Per-algorithm PRDs
├── config/                    # Configuration files
│   ├── setup.json
│   └── rate_limits.json
├── data/                      # Input data
├── results/                   # Experiment results
├── assets/                    # Images, graphs, resources
├── notebooks/                 # Analysis notebooks
├── README.md                  # MANDATORY
├── pyproject.toml             # Build & dependencies
├── uv.lock                    # Locked dependencies
├── .env-example               # Secret placeholders
└── .gitignore
```

### 2.5 Mandatory Workflow

The required workflow is:

1. Create `docs/PRD.md` and get it approved before continuing
2. Create `docs/PLAN.md` — architectural planning
3. Create `docs/TODO.md` — task list
4. Create dedicated PRDs for every central algorithm/mechanism
5. Approve all documents before development begins
6. Begin development — update `TODO.md` as you progress
7. Save results, create visualizations, and update `README.md`

---

## 3. Code Documentation and Project Structure

Correct code documentation and an organized project structure are essential foundations for professional software development. Good documentation lets other developers quickly understand the code, use it correctly, and contribute effectively.

### 3.1 Modular Project Structure

Proper organization is the key to efficient maintenance and future development. Principles include logical division of the project into folders by role — source code, tests, documentation, data, results, configuration, and resources. The organization can be feature-based or layered, with clear separation between code, data, results, and documentation.

### 3.2 File Size Rule — Maximum 150 Lines

**Every code file must be at most 150 lines of code** (blank lines and comment lines are not counted). When a file exceeds the limit, **split it into multiple files** — never compress code to fit the limit.

Splitting strategies:

- **Extract helper functions** — independent functions to a separate file
- **Extract a mixin** — when a class has multiple responsibilities
- **50/50 split** — when there are two logical halves (read/write)
- **Extract constants** — constants to `constants.py`
- **Extract models** — model definitions to a separate file

### 3.3 Code Quality and Comments

Code quality is measured not only by functionality but also by readability and maintainability. Code Comments Standards [6], [7], [8] require comments to explain the **why**, not just the **what**. Every function, class, and module should have detailed Docstrings. Comments should explain complex design decisions, document assumptions and preconditions, and update alongside code changes.

Quality coding principles include using descriptive and precise variable and function names, writing short, focused, single-responsibility functions, avoiding duplication via DRY (Don't Repeat Yourself), and maintaining consistent style throughout the project.

---

## 4. SDK Architecture and Object-Oriented Design

### 4.1 SDK-based Architecture

Every central business-logic function must be accessible through an SDK layer. The SDK is the single entry point for all consumers: menus, GUI, CLI, third-party integrations, and future services.

```
External Consumers (GUI / CLI / REST / Third Party)
        |
        v
   +---------+
   |   SDK   |  <-- Single entry point for ALL logic
   +----+----+
        |
        v
   +-------------+
   |   Domain    |  <-- Services, models, orchestrators
   |  Services   |
   +----+--------+
        |
        v
   +----------------+
   | Infrastructure |  <-- DB, file I/O, external APIs
   +----------------+
```

Architectural requirements:

- Every business function is exposed via the SDK class
- **No business logic** in GUI, CLI, or controller layers — these layers delegate to the SDK
- External consumers can import the SDK and run all operations without accessing internal modules

### 4.2 Object-Oriented Design (OOP) — No Code Duplication

Code must be written in OOP style. Do not duplicate code. When the same logic appears in two or more files, extract it into a shared module, base class, or mixin.

- Same function body in two or more files — extract to a shared module
- Same `try/except` pattern in three or more files — create a wrapper function
- Same method in three or more classes — create a base class or mixin
- Copied logic with slight variations — use the Template Method pattern

Mixin rules:

- Each mixin handles a single concern
- Mixins do not override each other's methods
- Mixins must be independently testable

---

## 5. API Gatekeeper and Rate Limiting

### 5.1 Centralized API Gatekeeper

All external API calls must pass through a **centralized gatekeeper**. The gatekeeper handles rate limiting, queues, retries, and monitoring.

Gatekeeper requirements:

- **No direct API calls** that bypass the gatekeeper
- Rate limits are enforced before each call
- Overflow is moved to a queue, not dropped
- All API calls are logged for monitoring

```python
# API Gatekeeper Interface

class ApiGatekeeper:
    """Centralized API call manager."""

    def __init__(self, config: RateLimitConfig):
        """Initialize with rate limit config."""
        ...

    def execute(self, api_call, *args, **kwargs):
        """Execute API call through gatekeeper.
        - Check rate limits before execution
        - Queue if limit reached
        - Retry on transient failures
        - Log all calls
        """
        ...

    def get_queue_status(self) -> QueueStatus:
        """Return queue depth and stats."""
        ...
```

### 5.2 Rate Limit Configuration

**All rate limits must be read from a configuration file — never hard-coded.**

```json
// Rate Limit Configuration
{
  "rate_limits": {
    "version": "1.00",
    "services": {
      "default": {
        "requests_per_minute": 30,
        "requests_per_hour": 500,
        "concurrent_max": 5,
        "retry_after_seconds": 30,
        "max_retries": 3
      }
    }
  }
}
```

### 5.3 Overflow Queue Management

When rate limits are reached, the gatekeeper **must** move requests to a queue rather than dropping them or crashing:

- FIFO queue for pending requests
- Maximum queue depth defined in configuration
- Backpressure signal when the queue is full
- A drain mechanism that processes requests as rate windows reset

---

## 6. Test-Driven Development and Quality Assurance

### 6.1 The TDD Process — Red, Green, Refactor

All development must follow Test-Driven Development: **RED → GREEN → REFACTOR**.

- Every module must include a corresponding test file
- Every public function/method must include at least one test
- Tests cover both the happy path and error cases
- Tests are written **before** or alongside implementation, not as an afterthought

Test structure:

```
tests/
  unit/
    test_<module>/         # Mirror src/ structure
      test_<file>.py
  integration/
    test_<feature>.py
  conftest.py              # Shared fixtures
```

Test rules:

1. Every new module must have a corresponding test file
2. Every public function must have at least one test
3. Test the happy path **and** error cases
4. Use fixtures from `conftest.py` for shared test data
5. Mock external dependencies (database, files, API)
6. Test files also obey the 150-line rule
7. No tests that depend on external services

### 6.2 Test Coverage — Minimum 85%

**Global test coverage must be 85% or higher.** The test suite must fail if coverage drops below this threshold.

Configuration in `pyproject.toml`:

```toml
# Coverage Configuration
[tool.coverage.run]
source = ["src"]
omit = ["src/main.py", "*/tests/*", "src/**/gui/*"]

[tool.coverage.report]
fail_under = 85
```

Required coverage types include statement coverage, branch coverage, and path coverage for critical paths.

### 6.3 Edge Cases and Failure Handling

Identifying and documenting edge cases is a critical part of quality software development. Identify boundary conditions, document each case in detail, and include screenshots of failures where relevant. Error-handling mechanisms must include defensive programming, clear error messages, detailed logging, and graceful degradation.

### 6.4 Expected Test Results

Document the expected results for each test, generate automated test reports with pass/fail rates, and keep logs of successful and failed runs.

---

## 7. Code Review, Configuration Management, and Information Security

### 7.1 Linter Compliance — Zero Ruff Violations

**Zero Ruff violations are allowed.** All code must pass `ruff check` without errors.

Configuration in `pyproject.toml`:

```toml
# Ruff Configuration
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E","F","W","I","N","UP","B","C4","SIM"]
ignore = ["E501"]
```

Active rule categories:

- **E** — PEP 8 errors (indentation, whitespace, style)
- **F** — Pyflakes (undefined names, unused imports)
- **W** — PEP 8 warnings
- **I** — isort (import order)
- **N** — pep8-naming (naming conventions)
- **UP** — pyupgrade (Python 3.10+ modernization)
- **B** — flake8-bugbear (common bugs)
- **C4** — comprehensions usage
- **SIM** — simplification

### 7.2 No Hard-coded Values

**All configurable values must come from configuration files, not source code.**

Table 1: Hard-coded vs. configuration

| Category | Wrong | Right |
|---|---|---|
| API URL | `"https://api.example.com"` | `cfg.get("api_url")` |
| Rate limits | `rate_limit = 10` | `cfg.get("rate_limit", 10)` |
| Timeouts | `timeout=60` | `cfg.get("timeout", 60)` |
| Secrets | `api_key = "abc123"` | `os.environ.get("API_KEY")` |

Allowed values in code: physical/mathematical constants, default parameter values, constants in `constants.py`, and `Enum` values.

### 7.3 Configuration Architecture

**All configuration must follow a clear hierarchy with versioned config files.**

```
config/
  setup.json              # Main app config (versioned)
  rate_limits.json        # API rate limits (versioned)
  logging_config.json     # Logging configuration
.env                      # Secrets (git-ignored)
.env-example              # Secret placeholders (committed)
pyproject.toml            # Build, lint, test settings
src/<package>/constants.py # Immutable project constants
```

### 7.4 Information Security and Secrets

**No secret data in the project. When pushing to GitHub, you must include `.env-example` with placeholder values.**

- Never store API keys, passwords, or tokens in source code [9], [10], [11]
- Use environment variables only: `os.environ.get("API_KEY")`
- `.gitignore` must include: `.env`, `*.key`, `*.pem`, `credentials.json`
- `.env-example` must exist with placeholder values
- In production environments — use a secret-management tool
- Rotate keys periodically, monitor usage, and apply least privilege

---

## 8. Version Control and the `uv` Package Manager

### 8.1 Global Version Tracking

Both code and configuration files must include explicit version tracking. Versions start at 1.00 and increment on meaningful changes.

Table 2: Required version locations

| Initial value | Location | Item |
|---|---|---|
| 1.00 | `src/<pkg>/shared/version.py` | Code version |
| 1.00 | `"version"` key in JSON | Config version |
| 1.00 | `"rate_limits.version"` | Rate-limits version |

The application should validate config-version compatibility at startup.

### 8.2 Recommended Git Practices

Recommended practices include keeping a clean commit history with meaningful messages, using separate branches for new features, performing code reviews via Pull Requests, and using tagging to mark major releases.

### 8.3 The Prompt Book

Documenting the AI-driven development process (Prompt Engineering Log) includes a list of all significant prompts used to build the project, descriptions of context and goal, examples of resulting outputs, iterative improvements, and best practices distilled from experience.

### 8.4 The `uv` Package Manager — Mandatory

**All projects must use `uv` as the package manager and task runner. Using `pip`, `pip install`, `python -m`, `venv`, or `virtualenv` directly is forbidden.**

Table 3: Required `uv` commands

| Task | Right (uv) | Forbidden |
|---|---|---|
| Install dependencies | `uv sync` | `pip install` |
| Add a dependency | `uv add <pkg>` | `pip install <pkg>` |
| Run a script | `uv run python script.py` | `python script.py` |
| Run tests | `uv run pytest tests/` | `python -m pytest` |
| Lock dependencies | `uv lock` | `pip freeze` |

Requirements:

- `pyproject.toml` is the single source of truth for dependencies (no `requirements.txt`)
- `uv.lock` exists and is in version control
- No direct calls to `pip` or `python -m` in code, scripts, CI/CD, or documentation
- All tools run via `uv run`

---

## 9. Research and Results Analysis

In-depth research and results analysis are what distinguishes a regular software project from professional, excellence-grade work. The research portion includes systematic experiments, quantitative and qualitative analysis, and visual presentation of results.

### 9.1 Parameter Exploration

**Sensitivity Analysis** is the systematic process of measuring how parameters affect system performance. The process includes systematic experiments with controlled parameter changes, accurate documentation of each parameter's effect, and the use of advanced analysis methods such as partial derivatives, variance-based analysis, or one-at-a-time (OAT).

### 9.2 Results Analysis Notebook

A **Results Analysis Notebook** is a central tool for presenting the research. Depth is achieved using a Jupyter Notebook or similar tools, methodical analysis of experimental results, comparing algorithms / configurations / approaches, and including mathematical proofs or theoretical analyses. Use LaTeX to write professional equations and formulas, and include references to the academic literature.

### 9.3 Visual Presentation of Results

High-quality data visualization is essential for conveying the research message. Visualization types include Bar charts for comparisons, Line charts for trends, Scatter plots for correlations, Heatmaps for parameter sensitivity, Box plots for distributions, and Waterfall charts for change analysis. Chart quality is measured by clear labels, consistent and accessible colors, detailed captions and clear legends, and high resolution.

---

## 10. User Interface and User Experience

A good UI/UX is critical to the success of any software system [12], [13].

### 10.1 Quality Criteria

Usability criteria include: Learnability, Efficiency, Memorability, Error Prevention, and Satisfaction. Nielsen's 10 Heuristics [14]: visibility of system status, match between system and the real world, user control and freedom, consistency and standards, error prevention, recognition rather than recall, flexibility and efficiency of use, aesthetic and minimalist design, help users recover from errors, and help and documentation.

### 10.2 Interface Documentation

Comprehensive interface documentation includes screenshots of every state, a description of a typical user workflow, explanations of interactions and feedback, and accessibility considerations.

---

## 11. Costs and Pricing

Understanding development and operating costs is essential to plan a project correctly.

### 11.1 Cost Analysis

Cost analysis (Cost Breakdown) of API token usage includes accurate counts of tokens in and out, cost per million tokens, and total cost estimates by model and service.

Table 4: API Token Cost Breakdown

| Model | Input Tokens | Output Tokens | Total Cost |
|---|---|---|---|
| GPT-4 | 1,245,000 | 523,000 | $45.67 |
| Claude 3 | 890,000 | 412,000 | $32.11 |
| Total | 2,135,000 | 935,000 | $77.78 |

Optimization strategies include reducing token usage, batch processing, and choosing models by cost/benefit.

### 11.2 Budget Management

Effective budget management includes cost forecasting at scale, real-time usage monitoring, and budget-overage alerts.

---

## 12. Extensibility and Maintainability

### 12.1 Extension Points

Plugins Architecture allows adding new functionality without changing the core code: clear interfaces for extension, lifecycle hooks such as `beforeCreate`, `afterUpdate`, middleware mechanisms, and API-first design.

### 12.2 Maintainability

Maintainable code is characterized by modularity and separation of concerns, reusable components, and analyzability and testability.

---

## 13. International Quality Standards

The ISO/IEC 25010 standard [15] defines a comprehensive software-quality model covering eight main quality attributes.

### 13.1 Product Quality Characteristics

- **Functional Suitability** — completeness, correctness, appropriateness
- **Performance Efficiency** — response times, resource utilization, capacity
- **Compatibility** — interoperability and co-existence
- **Usability** — learnability, operability, accessibility, and protection against errors
- **Reliability** — maturity, availability, fault tolerance, and recoverability
- **Security** — confidentiality, integrity, authenticity, accountability
- **Maintainability** — modularity, reusability, analyzability, modifiability, and testability
- **Portability** — adaptability, installability, replaceability

---

## 14. Project Organization as a Package

Organizing code as a package is a foundational principle in professional software development. A well-organized package enables code reuse, clear dependency management, simple distribution and installation, and built-in testing.

### 14.1 Package Definition File

Every package must include a `pyproject.toml` (preferred) or `setup.py` specifying name, version, description, author, license, and dependencies.

### 14.2 `__init__.py` Files

`__init__.py` files must be present in the root and every subdirectory. It is recommended to use them to expose public interfaces via `__all__` and to set `__version__`.

### 14.3 Relative Paths

All imports must use relative paths or package names, never absolute paths. File reads and writes also happen relative to the package path.

### 14.4 Checklist: Organizing as a Package

1. **Package definition file:** Does `pyproject.toml` exist? Does it include name, version, and dependencies? Are dependencies pinned to versions?
2. **`__init__.py`:** Does it exist at the root? Does it export public interfaces? Is `__version__` defined?
3. **Folder structure:** Is source code in a dedicated folder? Are tests in `tests/`? Is documentation in `docs`?
4. **Relative paths:** Are all imports relative? Are absolute paths avoided?

---

## 15. Parallel Processing and Performance

Use of multiprocessing and multithreading is essential for the optimal performance of modern software.

### 15.1 Multiprocessing vs. Multithreading

**Multiprocessing** suits CPU-bound work: mathematical computation, image processing, model training. Each process runs in its own memory and uses a different CPU core.

**Multithreading** suits I/O-bound work: network calls, database access, file read/write. Threads enable other operations during wait time.

### 15.2 Thread Safety

Thread safety is critical: protect shared variables with locks, use `queue.Queue` for inter-thread messaging, avoid deadlocks, and use context managers.

### 15.3 Checklist: Parallel Processing

1. **Identify operations:** identify CPU-bound/I/O-bound work, choose the right tool, evaluate the benefit
2. **Implementation:** dynamic process/thread count, safe data sharing, prevent memory leaks
3. **Resource management:** correct close/cleanup, exception handling, prevent leaks
4. **Safety:** protect shared variables, prevent race conditions and deadlocks

---

## 16. Modular Design and Building Blocks

Building-blocks design is a modular approach in which each component is a self-contained unit with a well-defined interface.

### 16.1 Building Block Structure

Each building block is defined by:

- **Input Data** — types, valid range, external dependencies, comprehensive validation
- **Output Data** — types, format, edge-case behavior
- **Setup Data** — parameters with defaults, configuration, initialization

### 16.2 Design Principles

**Single Responsibility** — each block is responsible for a single task. **Separation of Concerns** — each block addresses one aspect. **Reusability** — blocks are independent and not tied to specific code. **Testability** — each block is testable via dependency injection.

### 16.3 Building Block Example

```python
# Building Block Example

class DataProcessor:
    """
    Input:  raw_data (List[Dict]),
            filter_criteria (Dict)
    Output: processed_data (List[Dict])
    Setup:  processing_mode ('fast'/'accurate'),
            batch_size (int, default: 100)
    """

    def __init__(self, processing_mode='fast',
                 batch_size=100):
        self.processing_mode = processing_mode
        self.batch_size = batch_size
        self._validate_config()

    def process(self, raw_data, filter_criteria):
        self._validate_input(raw_data,
                             filter_criteria)
        return self._do_processing(
            raw_data, filter_criteria)

    def _validate_config(self):
        if self.processing_mode \
                not in ['fast', 'accurate']:
            raise ValueError("Invalid mode")
        if self.batch_size <= 0:
            raise ValueError("Batch size > 0")

    def _validate_input(self, data, criteria):
        if not isinstance(data, list):
            raise TypeError("data must be list")
        if not isinstance(criteria, dict):
            raise TypeError("criteria must be dict")
```

---

## 17. Final Checklist

Before submitting the project, go through a comprehensive checklist.

### 17.1 Mandatory Structure and Documentation

- Comprehensive `README.md` at the project root, user-manual grade
- `docs/` folder with `PRD.md`, `PLAN.md`, and `TODO.md`
- Dedicated PRDs for every algorithm/central mechanism
- Architecture documentation with clear diagrams
- A documented prompt book

### 17.2 Architecture and Code

- SDK architecture — all business logic via the SDK layer
- OOP design — no code duplication, inheritance and mixins
- API gatekeeper — all external calls via the gatekeeper
- Rate limits from configuration, queue management on overflow
- Files up to 150 lines of code, comments and docstrings
- Consistent code style and descriptive names

### 17.3 Testing and Quality

- TDD — tests written before/with the code
- Test coverage 85% and above
- Zero Ruff violations
- Documented edge cases and error handling
- Automated test reports

### 17.4 Configuration and Security

- Separate config files versioned with the code
- `.env-example` with placeholder values
- No API keys or secrets in code
- `.gitignore` updated
- Use `uv` as the single package manager
- `pyproject.toml` and `uv.lock` exist

### 17.5 Research and Visualization

- Systematic experiments with parameter changes
- Documented sensitivity analysis, analysis notebook with charts
- High-quality charts, screenshots, architecture diagrams
- Token cost analysis and optimization strategies

### 17.6 Extensibility and Standards

- Documented extension points
- Organized as a professional Python package
- Parallel processing with thread safety
- Building-blocks-based design
- Compliance with ISO/IEC 25010
- Clean Git history, license, attribution, deployment instructions

---

## 18. Additional Sources and Standards

To prepare an excellence-grade project, refer to international standards and sources: MIT's software quality assurance plan [16], the ISO/IEC 25010 software quality model [15], Google's engineering practices [17], Microsoft's REST API guidelines [18], and Nielsen's usability heuristics [14].

---

## 19. Important Note

This document presents a particularly high level of excellence. Not every section is fully mandatory, but the more criteria you meet, the higher the quality assessment will be. Focus on depth, professionalism, and demonstrating high-level development capabilities.

It is recommended to use LLM tools and AI agents to help complete the project. Note that AI agents may also be used as part of the evaluation.

### 19.1 Quick Reference Card for Requirements

Table 5: Code Quality Requirements Summary

| Enforcement | Threshold | Rule |
|---|---|---|
| Code review | All logic via SDK | SDK architecture |
| Code review | Extract on 2+ copies | OOP / no duplication |
| Code review + test | All calls through it | API gatekeeper |
| Config check | From config, not code | Rate limits |
| Integration test | Queue, no crash | Overflow handling |
| Version module | Starts at 1.00 | Version control |
| Workflow | Red-Green-Refactor | TDD |
| Automated check | ≤ 150 lines | File size |
| `ruff check` | 0 violations | Linter |
| `pytest --cov` | ≥ 85% | Test coverage |
| Code review | 0 in source | Hard-coded values |
| Automated scan | `.env-example` + 0 | Secrets |
| Automated check | All via `uv` | Package manager |

---

## 20. Appendix: Detailed Submission Guidelines

This appendix gathers all detailed guidelines for submitting a professional software project. The guidelines are organized systematically and cover every required aspect.

### 20.1 Project Documents and Planning

**Product Requirements Document (PRD):**

- Project overview and context — project goal, user problem, market analysis, target audience
- Goals and success metrics — measurable goals, KPIs, acceptance criteria
- Functional and non-functional requirements — feature list, user stories, performance and security
- Assumptions, dependencies, and limitations — external systems, technical constraints, out-of-scope
- Timeline and milestones — detailed schedule with checkpoints and deliverables

**Architecture Document:**

- C4 Model diagrams (Context, Container, Component, Code)
- UML diagrams for complex processes
- Deployment diagrams and operational architecture
- Architecture Decision Records (ADRs) with rationale and trade-offs
- API and interface documentation, data schemas, and contracts

### 20.2 Code Documentation and Project Structure

**Comprehensive README:**

- Installation Instructions — system requirements, step-by-step install, env setup, troubleshooting
- Usage Instructions — running in different modes, flags and options, typical workflow
- Examples and Demos — code examples, screenshots, use-case scenarios, video links
- Configuration Guide — config files, parameters and their effects
- Contribution Guidelines — code and style standards
- License & Credits — usage license, third-party attribution

**Modular Project Structure:**

- Folder split by role: `src/`, `tests/`, `docs/`, `data/`, `results/`, `config/`, `assets/`
- Files up to ~150 lines of code
- Descriptive and consistent folder/file names
- Clear separation of concerns

**Code Quality:**

- Comments that explain the **why**, not just the **what**
- Docstrings for every function, class, and module
- Descriptive variable and function names
- Short, single-responsibility functions
- DRY — no duplication

### 20.3 Configuration Management and Information Security

**Configuration Files:**

- Separate files in `.json`, `.yaml`, or `.env`
- No hard-coded values in code
- Example files (`.env-example`) with default values
- `.gitignore` to prevent committing sensitive files
- Template files for different environments

**Information Security:**

- Absolute prohibition on storing API keys in code
- Use environment variables only
- Hide `.env` via `.gitignore`
- Periodic key rotation and usage monitoring
- Least privilege

### 20.4 Software Testing and Quality

**Unit Tests:**

- 85% minimum coverage on new code
- Increased coverage for critical/business code
- Statement, branch, and critical-path coverage
- Automation in the CI/CD pipeline
- Coverage reports

**Edge-case Handling:**

- Systematic identification of boundary conditions
- Each edge case documented with expected input and response
- Defensive programming with input checks
- Clear error messages and detailed logs
- Graceful degradation in failure modes

### 20.5 Research and Analysis

**Parameter Exploration:**

- Systematic experiments with controlled parameter changes
- Methods: partial derivatives, OAT, variance analysis
- Experiment table, illustrative charts, statistical analysis

**Visualization:**

- Bar, Line, Scatter, Heatmap, Box plots
- Clear labels, consistent and accessible colors, high resolution
- Tools: Matplotlib, Seaborn, Plotly, Tableau, D3.js

### 20.6 User Interface

- Usability criteria: learnability, efficiency, memorability, error prevention, satisfaction
- Nielsen's 10 heuristics
- Screenshots of every screen and state
- User workflow description
- Accessibility considerations

### 20.7 Version Control and Costs

**Version Control:**

- Clear commit history with meaningful messages
- Separate branches for new features
- Pull Requests with code reviews
- Tagging of major releases
- A documented prompt book

**Cost Analysis:**

- Token counts in and out
- Cost per million tokens by model
- Cost forecasting, real-time monitoring, budget alerts
- Optimization strategies

### 20.8 Extensibility and Standards

- Plugins architecture with clear interfaces
- Hooks, middleware, API-first design
- Modularity, reuse, analyzability, and testability
- Compliance with ISO/IEC 25010
- Reference to international standards: MIT SQA, Google Engineering, Microsoft API, Nielsen

### 20.9 Final Checklist

1. **Documentation:** PRD, architecture, README, API docs, prompt book
2. **Code:** modular structure, files ≤ 150 lines, comments and docstrings, consistent style
3. **Configuration:** separate files, `.env-example`, no secrets, `.gitignore`
4. **Tests:** 85%+ coverage, edge cases, error handling, analysis notebook, automated reports
5. **Research:** parameter exploration, sensitivity analysis, analysis notebook, charts
6. **Visualization:** high-quality charts, screenshots, architecture diagrams
7. **Costs:** token table, detailed analysis, optimization
8. **Extensibility:** extension points, plugin examples, interfaces
9. **General:** Git history, license, attribution, deployment

---

## English References

1. Archbee, *Readme files guide*, https://www.archbee.com/blog/readme-files-guide, 2024.
2. GitHub, *About readmes*, https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes, 2024.
3. Monday.com, *PRD template — product requirement document*, https://monday.com/blog/rnd/prd-template-product-requirement-document/, 2024.
4. Miro, *Modular PRD template*, https://miro.com/templates/modular-prd/, 2024.
5. Aha!, *What is a good product requirements document template*, https://www.aha.io/roadmapping/guide/requirements-management, 2024.
6. Daily.dev, *10 code commenting best practices for developers*, https://daily.dev/blog/10-code-commenting-best-practices-for-developers, 2024.
7. Stack Overflow, *Best practices for writing code comments*, https://stackoverflow.blog/2021/12/23/best-practices-for-writing-code-comments/, 2021.
8. Codacy, *Code documentation best practices*, https://blog.codacy.com/code-documentation, 2024.
9. Hoop.dev, *API security best practices: Protecting secrets with environment variables*, https://hoop.dev/blog/api-security-best-practices-protecting-secrets-with-environment-variables/, 2024.
10. Claude Support, *API key best practices: Keeping your keys safe and secure*, https://support.claude.com/en/articles/9767949-api-key-best-practices, 2024.
11. OpenAI, *Best practices for API key safety*, https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety, 2024.
12. UX Design, *Measuring design quality with heuristics*, https://uxdesign.cc/measuring-design-quality-with-heuristics-44857efa514, 2024.
13. J. Nielsen, *10 usability heuristics for user interface design*, https://www.nngroup.com/articles/ten-usability-heuristics/, 1994.
14. J. Nielsen, *10 usability heuristics for user interface design*, https://www.nngroup.com/articles/ten-usability-heuristics/, 1994.
15. ISO, *ISO/IEC 25010:2011 systems and software quality requirements and evaluation*, https://www.iso.org/standard/35733.html, 2011.
16. MIT ACIS, *MIT software quality assurance plan*, https://acisweb.mit.edu/acis/sqap/sqap.r1.html, 2022.
17. Google, *Google engineering practices documentation*, https://google.github.io/eng-practices/, 2023.
18. Microsoft, *Microsoft REST API guidelines*, https://github.com/microsoft/api-guidelines, 2023.
