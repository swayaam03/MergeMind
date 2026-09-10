# MergeMind --- Development Roadmap & Phase Tracker

> **Project:** MergeMind\
> **Description:** AI-powered semantic Git merge conflict resolver\
> **Team:** Aarushi Arora, Dhvani Mistry, Prishita Mali, Swayam
> Kandarkar\
> **Institution:** St. Francis Institute of Technology --- Department of
> Information Technology

------------------------------------------------------------------------

## IDE INSTRUCTION

This file is the **source of truth for MergeMind development progress**.

When working on this project:

1.  Identify the **CURRENT PHASE** below before making changes.
2.  Work only on tasks belonging to the current phase unless explicitly
    instructed otherwise.
3.  Do not implement future-phase functionality prematurely.
4.  Mark individual tasks `[x]` only when they are actually implemented
    and working.
5.  When all required tasks in a phase are complete, change that phase
    to `COMPLETED`.
6.  Then update `CURRENT PHASE` to the next phase.
7.  Always preserve the overall architecture and keep the project simple
    and readable.
8.  Do not introduce unnecessary microservices, agents, queues, or
    infrastructure.
9.  Never mark functionality as complete if it is only a placeholder,
    mock, TODO, or partially working implementation.

------------------------------------------------------------------------

# CURRENT PROJECT STATUS

**Current Phase:** Phase 1 --- Project Foundation & Configuration

**Current Phase Number:** 1 / 10

**Completed Phases:** 0

**Remaining Phases:** 9

**Overall Status:** 🟡 IN PROGRESS

------------------------------------------------------------------------

# Phase Overview

  Phase   Name                                           Status
  ------- ---------------------------------------------- ----------------
  1       Project Foundation & Configuration             🟡 IN PROGRESS
  2       Git & Repository Integration                   ⚪ NOT STARTED
  3       AST Parsing & Conflict Classification          ⚪ NOT STARTED
  4       LLM / OpenRouter Integration                   ⚪ NOT STARTED
  5       MergeMind Verification Pipeline                ⚪ NOT STARTED
  6       LangGraph Retry & Explanation Workflow         ⚪ NOT STARTED
  7       GitHub Web Application & Repository Tracking   ⚪ NOT STARTED
  8       Human-in-the-Loop Review UI                    ⚪ NOT STARTED
  9       End-to-End Integration & Testing               ⚪ NOT STARTED
  10      Evaluation, Documentation & Final Demo         ⚪ NOT STARTED

------------------------------------------------------------------------

# PHASE 1 --- Project Foundation & Configuration

**Status:** 🟡 IN PROGRESS

### Goal

Create a clean, runnable foundation for the backend and frontend without
implementing the actual merge-resolution logic.

### Tasks

-   [ ] Verify the complete MergeMind folder structure.
-   [ ] Initialize the Python backend environment.
-   [ ] Initialize the React frontend.
-   [ ] Create the FastAPI application entry point.
-   [ ] Create the initial React application.
-   [ ] Add environment configuration support.
-   [ ] Create `.env.example`.
-   [ ] Add `.gitignore`.
-   [ ] Add basic backend/frontend README setup instructions.
-   [ ] Verify backend starts successfully.
-   [ ] Verify frontend starts successfully.
-   [ ] Verify frontend can communicate with backend.
-   [ ] Add a basic `/health` backend endpoint.
-   [ ] Add basic project-level configuration.

### Phase Completion Condition

Phase 1 is complete only when:

-   Backend starts successfully.
-   Frontend starts successfully.
-   Frontend can reach the backend.
-   Environment variables are loaded correctly.
-   The repository has the intended folder structure.
-   No core MergeMind functionality is falsely represented as
    implemented.

------------------------------------------------------------------------

# PHASE 2 --- Git & Repository Integration

**Status:** ⚪ NOT STARTED

### Goal

Make MergeMind understand local Git repositories and detect real merge
conflicts.

### Tasks

-   [ ] Implement Git repository discovery.
-   [ ] Implement repository status reading.
-   [ ] Implement branch information retrieval.
-   [ ] Detect conflicted files.
-   [ ] Extract Git conflict markers/hunks.
-   [ ] Retrieve base version.
-   [ ] Retrieve local/ours version.
-   [ ] Retrieve remote/theirs version.
-   [ ] Create structured conflict data.
-   [ ] Implement initial Git merge-driver interface.
-   [ ] Create `.gitattributes` integration example.
-   [ ] Test against deliberately conflicting sample repositories.

### Phase Completion Condition

MergeMind can identify a real Git conflict and return structured
information about the base, local, remote, and conflicting sections.

------------------------------------------------------------------------

# PHASE 3 --- AST Parsing & Conflict Classification

**Status:** ⚪ NOT STARTED

### Goal

Use Tree-sitter to understand whether a conflict is trivial or genuinely
semantic.

### Supported Languages

-   Python
-   JavaScript
-   Java

### Tasks

-   [ ] Integrate Tree-sitter.
-   [ ] Add language parser configuration.
-   [ ] Parse Python code.
-   [ ] Parse JavaScript code.
-   [ ] Parse Java code.
-   [ ] Build AST comparison utilities.
-   [ ] Create conflict classification model.
-   [ ] Implement `TRIVIAL` classification.
-   [ ] Implement `SEMANTIC` classification.
-   [ ] Implement `UNKNOWN` / unsupported handling.
-   [ ] Create AST diff summary.
-   [ ] Create sample trivial conflicts.
-   [ ] Create sample semantic conflicts.
-   [ ] Test classification accuracy.

### Important Principle

Do not use an LLM for deterministic AST parsing or basic conflict
classification.

### Phase Completion Condition

MergeMind can parse supported code and produce a structured
classification and AST summary for a conflict.

------------------------------------------------------------------------

# PHASE 4 --- LLM / OpenRouter Integration

**Status:** ⚪ NOT STARTED

### Goal

Connect the MergeMind Merge Agent to an LLM through LiteLLM, using
OpenRouter as the current development provider.

### Architecture

``` text
Merge Agent
     |
     v
LiteLLM
     |
     v
OpenRouter
     |
     v
Configured Model
```

The model provider must remain configurable so Ollama/local inference
can be supported later.

### Tasks

-   [ ] Implement the generic LLM client.
-   [ ] Configure LiteLLM.
-   [ ] Configure OpenRouter environment variables.
-   [ ] Add model configuration.
-   [ ] Create merge-agent prompt.
-   [ ] Create Pydantic merge output schema.
-   [ ] Integrate Instructor where appropriate.
-   [ ] Enforce structured merge output.
-   [ ] Validate `resolved_code`.
-   [ ] Validate `reasoning`.
-   [ ] Validate `confidence`.
-   [ ] Add error handling for LLM failures.
-   [ ] Test with controlled sample conflicts.

### Merge Agent Output

``` json
{
  "resolved_code": "string",
  "reasoning": "string",
  "confidence": 0.0
}
```

### Phase Completion Condition

The Merge Agent can receive structured conflict context and reliably
return a validated structured resolution through LiteLLM/OpenRouter.

------------------------------------------------------------------------

# PHASE 5 --- MergeMind Verification Pipeline

**Status:** ⚪ NOT STARTED

### Goal

Never trust an AI-generated merge without deterministic verification.

### Pipeline

``` text
AI Resolution
      |
      v
Docker Sandbox
      |
      v
Compile / Run Tests
      |
      v
Semgrep Security Scan
      |
      v
Structured Result
```

### Tasks

-   [ ] Implement Docker sandbox runner.
-   [ ] Create Python sandbox configuration.
-   [ ] Create JavaScript sandbox configuration.
-   [ ] Create Java sandbox configuration.
-   [ ] Apply proposed resolution inside sandbox.
-   [ ] Install project dependencies safely.
-   [ ] Compile/run project code where applicable.
-   [ ] Execute project tests.
-   [ ] Capture stdout/stderr.
-   [ ] Create structured test result.
-   [ ] Integrate Semgrep.
-   [ ] Create structured security result.
-   [ ] Detect security findings.
-   [ ] Connect verification results to pipeline state.

### Phase Completion Condition

A proposed merge is accepted by the system only after passing the
required compilation/tests and security checks.

------------------------------------------------------------------------

# PHASE 6 --- LangGraph Retry & Explanation Workflow

**Status:** ⚪ NOT STARTED

### Goal

Create the complete intelligent workflow with limited self-correction
and human escalation.

### Core LLM Components

Only two LLM-based agents:

1.  **Merge Agent**
2.  **Explanation Agent**

All other components should remain deterministic or orchestration logic.

### Workflow

``` text
Conflict
   |
   v
AST Classification
   |
   v
Context Extraction
   |
   v
Merge Agent
   |
   v
Verification
   |
   +---- PASS ----> Security Scan
   |
   +---- FAIL ----> Retry Merge Agent
                         |
                         v
                    Verification
                         |
                    max retries
                         |
                         v
                 Explanation Agent
                         |
                         v
                   Human Review
```

### Tasks

-   [ ] Implement shared `MergeState`.
-   [ ] Add conflict information to state.
-   [ ] Add AST information to state.
-   [ ] Add context to state.
-   [ ] Add merge attempt history.
-   [ ] Add retry counter.
-   [ ] Add verification results.
-   [ ] Add security results.
-   [ ] Implement LangGraph workflow.
-   [ ] Implement conditional retry routing.
-   [ ] Set a retry limit of approximately 2--3 attempts.
-   [ ] Feed specific test failures back to the Merge Agent.
-   [ ] Feed specific security findings back when appropriate.
-   [ ] Implement Explanation Agent.
-   [ ] Generate human-readable failure explanation.
-   [ ] Add pipeline status events.

### Phase Completion Condition

MergeMind can perform a complete automated attempt, retry when
verification fails, and escalate to human review after the retry limit.

------------------------------------------------------------------------

# PHASE 7 --- GitHub Web Application & Repository Tracking

**Status:** ⚪ NOT STARTED

### Goal

Allow users to connect GitHub through the web application and monitor
repositories and pull requests.

### Intended Flow

``` text
User
 |
 v
MergeMind Web App
 |
 v
Connect GitHub
 |
 v
GitHub Authorization
 |
 v
Repository List
 |
 v
Pull Requests
 |
 v
Conflict Detection
 |
 v
MergeMind Pipeline
```

### Tasks

-   [ ] Implement GitHub authentication flow.
-   [ ] Securely handle GitHub credentials/tokens.
-   [ ] Store connected user information.
-   [ ] Retrieve user's repositories.
-   [ ] Store repository metadata.
-   [ ] Display repositories in dashboard.
-   [ ] Retrieve pull requests.
-   [ ] Detect conflicted pull requests where supported.
-   [ ] Retrieve PR metadata.
-   [ ] Retrieve changed files.
-   [ ] Add webhook endpoint.
-   [ ] Verify GitHub webhook signatures.
-   [ ] Track repository/PR events.
-   [ ] Create repository history view.
-   [ ] Create conflict history records.

### Database Entities

At minimum:

``` text
User
Repository
PullRequest
Conflict
MergeRun
MergeAttempt
```

### Phase Completion Condition

A user can connect GitHub, view repositories, view pull requests, and
see MergeMind-tracked conflict information through the web application.

------------------------------------------------------------------------

# PHASE 8 --- Human-in-the-Loop Review UI

**Status:** ⚪ NOT STARTED

### Goal

Provide the developer with a clear interface to inspect and control
every AI-generated resolution.

### Review Layout

``` text
-----------------------------------------------------
| Base | Local | Remote | AI-Merged                 |
-----------------------------------------------------
|                                                   |
|               4-Way Code Diff                     |
|                                                   |
-----------------------------------------------------
| AI Reasoning                                      |
| Confidence                                        |
| Verification                                     |
| Test Results                                      |
| Security Results                                  |
-----------------------------------------------------
|        ACCEPT     EDIT     REJECT                 |
-----------------------------------------------------
```

### Tasks

-   [ ] Create dashboard.
-   [ ] Create repository page.
-   [ ] Create pull request page.
-   [ ] Create conflict list.
-   [ ] Create conflict details page.
-   [ ] Integrate Monaco Editor.
-   [ ] Implement 4-way diff.
-   [ ] Display Base code.
-   [ ] Display Local code.
-   [ ] Display Remote code.
-   [ ] Display AI-Merged code.
-   [ ] Display AI reasoning.
-   [ ] Display confidence.
-   [ ] Display verification results.
-   [ ] Display security findings.
-   [ ] Display retry history.
-   [ ] Implement Accept action.
-   [ ] Implement Edit action.
-   [ ] Implement Reject action.
-   [ ] Add live pipeline progress using WebSocket.

### Important Principle

The human developer has final approval authority.

MergeMind must not silently push an AI-generated resolution.

### Phase Completion Condition

A developer can inspect a proposed merge, understand why it was
generated, see verification/security results, and Accept/Edit/Reject it.

------------------------------------------------------------------------

# PHASE 9 --- End-to-End Integration & Testing

**Status:** ⚪ NOT STARTED

### Goal

Connect every major component and verify the complete MergeMind
workflow.

### Complete Flow

``` text
GitHub / Local Git
        |
        v
Conflict Detection
        |
        v
AST Classification
        |
        v
Context Extraction
        |
        v
Merge Agent
        |
        v
Docker Verification
        |
        v
Semgrep
        |
   +----+----+
   |         |
 PASS       FAIL
   |         |
   |         v
   |      Retry
   |         |
   |         v
   |    Explanation
   |         |
   +-----> Human Review
                |
          +-----+-----+
          |     |     |
        Accept Edit Reject
```

### Tasks

-   [ ] Connect backend modules.
-   [ ] Connect frontend to backend.
-   [ ] Connect GitHub flow to pipeline.
-   [ ] Connect WebSocket progress updates.
-   [ ] Test successful merge.
-   [ ] Test failed merge.
-   [ ] Test retry flow.
-   [ ] Test exhausted retries.
-   [ ] Test security failure.
-   [ ] Test human acceptance.
-   [ ] Test human rejection.
-   [ ] Test human editing.
-   [ ] Test Python conflicts.
-   [ ] Test JavaScript conflicts.
-   [ ] Test Java conflicts.
-   [ ] Add integration tests.
-   [ ] Add representative conflict fixtures.
-   [ ] Fix major bugs.

### Phase Completion Condition

A complete MergeMind run can start from a real conflict and finish with
either a verified human-approved resolution or a clear manual-resolution
escalation.

------------------------------------------------------------------------

# PHASE 10 --- Evaluation, Documentation & Final Demo

**Status:** ⚪ NOT STARTED

### Goal

Evaluate MergeMind scientifically and prepare the final-year project
demonstration and documentation.

### Evaluation

Benchmark approximately 15--20 real conflicts from open-source
repositories.

Compare 2--3 candidate models where practical.

Track:

-   Merge success rate
-   Verification success rate
-   Retry count
-   Human escalation rate
-   Test failures
-   Security findings
-   Processing time
-   Token usage
-   Estimated cost

### Tasks

-   [ ] Prepare evaluation dataset.
-   [ ] Define evaluation methodology.
-   [ ] Benchmark selected models.
-   [ ] Record results.
-   [ ] Analyze success/failure cases.
-   [ ] Document limitations.
-   [ ] Document architecture.
-   [ ] Document API.
-   [ ] Document algorithms.
-   [ ] Document setup instructions.
-   [ ] Update README.
-   [ ] Prepare final demonstration scenarios.
-   [ ] Prepare final presentation.
-   [ ] Prepare project report material.
-   [ ] Clean code and remove dead code.
-   [ ] Verify reproducible setup.

### Phase Completion Condition

MergeMind has reproducible evaluation results, complete documentation,
and a reliable final demonstration.

------------------------------------------------------------------------

# Architecture Guardrails

These rules apply throughout development.

## Keep

-   FastAPI backend
-   React frontend
-   Tree-sitter
-   LangGraph
-   LiteLLM
-   OpenRouter during development
-   Optional Ollama/local inference
-   Docker sandbox
-   Semgrep
-   GitPython
-   PostgreSQL where persistence is required
-   WebSocket for live progress
-   Monaco Editor for review

## Avoid

-   Microservices
-   Kubernetes
-   Unnecessary message queues
-   Excessive autonomous agents
-   Hard-coding OpenRouter inside pipeline logic
-   Automatic unverified merges
-   Automatic direct pushes to user repositories
-   Fake verification results
-   Fake security results
-   Fake AI responses
-   Supporting additional programming languages before the core scope
    works

------------------------------------------------------------------------

# Definition of Done

A feature is considered **DONE** only when:

-   It is implemented.
-   It is connected to the relevant part of the system.
-   It works with a real test/example.
-   Errors are handled reasonably.
-   It does not break existing functionality.
-   It is reflected in this roadmap.
-   It is not merely a placeholder or TODO.

------------------------------------------------------------------------

# Progress Log

## Phase 1

**Status:** IN PROGRESS

Notes:

-   Initial project structure defined.
-   Backend/frontend architecture defined.
-   OpenRouter + LiteLLM selected as the current development LLM path.
-   GitHub-connected web application included in the overall
    architecture.
-   Core implementation has not started yet.

------------------------------------------------------------------------

## Future Progress Entries

Add short entries here whenever a phase is completed or a major
milestone is reached.

Example:

``` text
[2026-09-XX]
Phase 1 completed.
Backend and frontend start successfully.
Configuration and health endpoint verified.
Moving to Phase 2.
```
