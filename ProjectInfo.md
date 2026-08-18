# MergeMind — Project Brief

> AI-powered semantic merge conflict resolver for Git.
> Final-year project, Dept. of Information Technology, St. Francis Institute of Technology.

Use this document as context to scaffold the project. Keep the structure simple and readable — this is a student project with a working demo as the goal, not a production monorepo.

---

## 1. What this project is

Git resolves merge conflicts as plain text diffs — it has no idea what the code *means*. MergeMind is a Git merge driver that understands conflicts semantically: it parses both sides into ASTs, uses a local LLM to propose a resolution, verifies that resolution actually compiles and passes tests inside a sandbox, scans it for security regressions, and only then shows it to the developer. If the LLM can't produce a resolution that passes verification after a few retries, it hands off to a human with a clear explanation of what was tried and why it failed — instead of silently producing a plausible-looking but wrong merge.

**Core principle:** reason with an LLM only where reasoning is actually needed; verify everything deterministically.

---

## 2. Problem it solves

- **Semantic blindness** — Git can't tell a rename from a logic change; both look identical as a text diff
- **Unverified AI output** — existing AI merge/coding tools (Copilot, SWE-agent, Devin) never verify their output before handing it back
- **Security regression** — a large share of real-world breaches trace back to auth/validation logic silently overwritten during merges

---

## 3. How it works — pipeline

1. **Trigger** — Git itself invokes MergeMind automatically via a registered merge driver (`.gitattributes` + `git config merge.mergemind.driver`) whenever it hits a real conflict. No manual step, no polling.
2. **AST classify** *(deterministic)* — Tree-sitter parses both sides; distinguishes trivial changes (renames, formatting) from real semantic conflicts.
3. **Context extraction** *(deterministic)* — pulls the conflicting hunk, a little surrounding code, and relevant call sites/signatures — not the whole file.
4. **Merge agent** *(LLM, local)* — proposes a resolution as a structured JSON patch with its reasoning attached.
5. **Verify** *(deterministic)* — runs the proposed merge in a Docker sandbox against the project's own test suite, then a Semgrep security scan.
6. **Retry loop** — on failure, the merge agent gets the specific failure (failing test + assertion, or flagged security line) and revises. Capped at 2–3 retries.
7. **Explanation agent** *(LLM, local)* — only runs once retries are exhausted; summarizes what was tried and why it failed, in plain language, for a human.
8. **Human review UI** — 4-way diff (base / local / remote / AI-proposed) with rationale, shown in a browser page the CLI serves locally. Developer accepts, edits, or rejects.
9. **Finish** — on accept, MergeMind writes the file, runs `git add`, completes the merge commit. From there it's a normal `git push` — no GitHub API needed for this path.

**Optional (stretch) path:** resolving conflicts on a **remote PR branch** not yet checked out locally — `git fetch origin pull/<PR#>/head:pr-<PR#>` first, then the exact same pipeline runs unchanged. Needs GitHub auth (token or `gh` CLI) and a decision on how the fix gets back (own branch/PR rather than pushing directly to someone else's branch).

---

## 4. Agents — keep this to two

Only two pipeline stages need LLM judgment. Everything else is a deterministic tool call.

| Node | Type | Job |
|---|---|---|
| AST classifier | deterministic | trivial vs. semantic conflict |
| **Merge agent** | **LLM** | generate JSON patch; revise using retry feedback in the same conversation |
| Verify (Docker + Semgrep) | deterministic | pass/fail + specific structured failure reason |
| **Explanation agent** | **LLM** | summarize failure for a human, once retries are exhausted |
| Human review UI | UI | final accept/edit/reject |

Both agents can share one local model instance (different system prompts) — no need to run multiple models concurrently on student hardware.

Coordination is via a shared state object passed through a LangGraph state graph (not agent-to-agent messages). State carries: conflict info, AST diff summary, context, patch attempt history, retry count, test/security results.

**Merge agent output schema** (enforced via Instructor + Pydantic):
```json
{
  "resolved_code": "string",
  "reasoning": "string",
  "confidence": "float"
}
```

---

## 5. Tech stack

- **Core:** Python 3.11+, Node.js 18+
- **Parsing:** Tree-sitter
- **LLM:** Ollama + Qwen 2.5 Coder (7B & 3B), fully local
- **Agent orchestration:** LangGraph
- **Structured output:** Instructor, Pydantic
- **Backend:** FastAPI, Uvicorn, GitPython, Docker SDK
- **Sandbox:** Docker
- **Security scan:** Semgrep
- **Frontend:** React 18, Monaco Editor, Tailwind CSS
- **Realtime progress:** WebSocket (local server → browser tab)
- **DB (if needed for run history):** PostgreSQL, Redis

---

## 6. Proposed project structure

Keep it flat and obvious — one top-level folder per concern, no unnecessary nesting.

```
mergemind/
├── cli/                    # entry point, git merge-driver hook, spawns local server
│   └── main.py
├── pipeline/                # the deterministic + agent pipeline
│   ├── ast_classifier.py
│   ├── context_extractor.py
│   ├── merge_agent.py
│   ├── explanation_agent.py
│   ├── verify_docker.py
│   ├── verify_security.py
│   └── graph.py             # LangGraph state graph wiring it all together
├── git_integration/          # reading repo state, conflict detection, PR fetch
│   ├── repo_reader.py
│   └── pr_fetch.py           # stretch: remote PR branch handling
├── server/                  # local FastAPI + WebSocket server for progress UI
│   ├── app.py
│   └── events.py
├── ui/                      # React + Monaco 4-way diff frontend
│   ├── src/
│   └── package.json
├── tests/
├── docs/
├── .gitattributes.example
└── README.md
```

---

## 7. Non-goals (keep scope tight)

- No cloud LLM calls, no API keys required — everything runs locally
- No custom GitHub bot/Action for automatic PR resolution in the core scope — that's future work, not this year's deliverable
- No support for languages beyond Python / JavaScript / Java in v1
- No attempt to auto-merge without verification — an unverified merge is treated as a failure, not a success, even if it "looks right"

---

## 8. Team

Aarushi Arora, Dhvani Mistry, Prishita Mali, Swayam Kandarkar — St. Francis Institute of Technology, Dept. of Information Technology.