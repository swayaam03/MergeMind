# MergeMind — Project Info

> AI-powered semantic merge conflict resolver for Git.
> Final-year project, Dept. of Information Technology, St. Francis Institute of Technology.

Use this document as project context when generating or scaffolding code. Keep the structure simple and readable — this is a student project aiming for a working, demonstrable result, not a production monorepo.

---

## 1. What this project is

Git resolves merge conflicts as plain text diffs — it has no idea what the code *means*. MergeMind is a Git merge driver that understands conflicts semantically: it parses both sides into ASTs, uses an LLM to propose a resolution, verifies that resolution actually compiles and passes tests inside a sandbox, scans it for security regressions, and only then shows it to the developer. If the LLM can't produce a resolution that passes verification after a few retries, it hands off to a human with a clear explanation of what was tried and why — instead of silently producing a plausible-looking but wrong merge.

**Core principle:** use an LLM only where reasoning is actually needed; verify everything else deterministically.

---

## 2. Problem it solves

- **Semantic blindness** — Git can't tell a rename from a logic change; both look identical as a text diff
- **Unverified AI output** — existing AI merge/coding tools (Copilot, SWE-agent, Devin) never verify their output before handing it back
- **Security regression** — a large share of real-world breaches trace back to auth/validation logic silently overwritten during merges

---

## 3. Pipeline

1. **Trigger** — Git invokes MergeMind automatically as a registered merge driver (`.gitattributes` + `git config merge.mergemind.driver`) whenever it hits a real conflict. No manual step.
2. **AST classify** *(deterministic)* — Tree-sitter parses both sides; distinguishes trivial changes (renames, formatting) from real semantic conflicts.
3. **Context extraction** *(deterministic)* — pulls the conflicting hunk, surrounding code, and relevant call sites/signatures — not the whole file.
4. **Merge agent** *(LLM)* — proposes a resolution as a structured JSON patch with reasoning attached.
5. **Verify** *(deterministic)* — runs the proposed merge in a Docker sandbox against the project's own tests, then a Semgrep security scan. Produces a *specific* structured failure reason, not just pass/fail.
6. **Retry loop** — on failure, the merge agent gets the specific failure (failing test + assertion, or flagged security line) in the same conversation and revises. Capped at 2–3 retries.
7. **Explanation agent** *(LLM)* — only runs once retries are exhausted; summarizes what was tried and why it failed, in plain language, for a human.
8. **Human review UI** — 4-way diff (base / local / remote / AI-proposed) with rationale, served as a local web page the CLI spawns. Developer accepts, edits, or rejects.
9. **Finish** — on accept, MergeMind writes the file, runs `git add`, completes the merge commit. From there it's a normal `git push` — no GitHub API needed for this path.

**Stretch goal — remote PR branches:** resolving conflicts on a PR not yet checked out locally. `git fetch origin pull/<PR#>/head:pr-<PR#>` first, then the same pipeline runs unchanged. Needs GitHub auth (token or `gh` CLI) and a decision on how the fix gets back (own branch/PR, not pushing directly to someone else's branch).

---

## 4. Agents — two, not more

| Node | Type | Job |
|---|---|---|
| AST classifier | deterministic | trivial vs. semantic conflict |
| **Merge agent** | **LLM** | generate JSON patch; revise using retry feedback in the same conversation |
| Verify (Docker + Semgrep) | deterministic | pass/fail + specific structured failure reason |
| **Explanation agent** | **LLM** | summarize failure for a human, once retries are exhausted |
| Human review UI | UI | final accept/edit/reject |

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

## 5. LLM backend strategy

Local-only inference (Ollama + Qwen 2.5 Coder) is the stated design goal — it's the project's main differentiator from cloud AI coding tools (no source code leaves the machine, no API cost). In practice, running a 7B model locally can be too heavy for a student laptop during active development, so the backend is **pluggable, not hard-coded**:

- LLM calls go through **LiteLLM**, so the model is a config value, not a code change:
  ```python
  # local
  model = "ollama/qwen2.5-coder:7b"
  # cloud, via OpenRouter
  model = "openrouter/nvidia/nemotron-3-nano-30b-a3b"
  ```
- **Local (Ollama)** is the default / what gets demoed to satisfy the "100% local" claim.
- **OpenRouter** is used during day-to-day development so the model doesn't hang the dev machine while iterating on prompts.
- **Different model per agent, sized to the job:**
  - *Merge agent* (needs reliable structured code output) → a paid, stable model — e.g. `nvidia/nemotron-3-nano-30b-a3b` (~$0.05/$0.20 per 1M tokens, tool calling + structured output support) or `qwen/qwen3-coder-next`.
  - *Explanation agent* (summarizing a failure in plain English — lower stakes) → a free-tier model is acceptable here.
- **Don't rely on `:free` OpenRouter endpoints for the merge agent in a live demo** — free tiers get delisted or rate-limited without warning. Use a cheap paid model for anything that has to work reliably on presentation day.
- Before committing to one model, benchmark 2–3 candidates (e.g. Nemotron 3 Nano, Qwen3-Coder-Next, local Qwen 2.5 Coder) against ~15–20 real conflicts from an open-source repo and report merge-success rate, retry count, and cost — this doubles as evaluation methodology for the write-up.

---

## 6. Tech stack

- **Core:** Python 3.11+, Node.js 18+
- **Parsing:** Tree-sitter
- **LLM access:** LiteLLM (backend-agnostic) → Ollama (local) or OpenRouter (cloud: Qwen Coder, NVIDIA Nemotron, etc.)
- **Agent orchestration:** LangGraph
- **Structured output:** Instructor, Pydantic
- **Backend:** FastAPI, Uvicorn, GitPython, Docker SDK
- **Sandbox:** Docker
- **Security scan:** Semgrep
- **Frontend:** React 18, Monaco Editor, Tailwind CSS
- **Realtime progress:** WebSocket (local server → browser tab)
- **DB (if needed for run history):** PostgreSQL, Redis

---

## 7. Proposed project structure

```
mergemind/
├── cli/                      # entry point, git merge-driver hook, spawns local server
│   └── main.py
├── pipeline/                  # deterministic + agent pipeline
│   ├── ast_classifier.py
│   ├── context_extractor.py
│   ├── merge_agent.py
│   ├── explanation_agent.py
│   ├── verify_docker.py
│   ├── verify_security.py
│   └── graph.py               # LangGraph state graph wiring it all together
├── llm/                       # backend-agnostic model access
│   ├── client.py              # LiteLLM wrapper
│   └── models.yaml            # per-agent model config (local / OpenRouter, per-role)
├── git_integration/            # reading repo state, conflict detection, PR fetch
│   ├── repo_reader.py
│   └── pr_fetch.py             # stretch: remote PR branch handling
├── server/                    # local FastAPI + WebSocket server for progress UI
│   ├── app.py
│   └── events.py
├── ui/                        # React + Monaco 4-way diff frontend
│   ├── src/
│   └── package.json
├── tests/
├── docs/
├── .gitattributes.example
└── README.md
```

---

## 8. Non-goals (keep scope tight)

- No attempt to auto-merge without verification — an unverified merge is a failure, even if it "looks right"
- No custom GitHub bot/Action for fully automatic PR resolution in the core scope — future work
- No support for languages beyond Python / JavaScript / Java in v1
- No hard dependency on any single cloud model provider — backend must stay swappable

---

## 9. Team

Aarushi Arora, Dhvani Mistry, Prishita Mali, Swayam Kandarkar — St. Francis Institute of Technology, Dept. of Information Technology.