# Agent Rules — MergeMind

See /projectinfo.md for full project context, architecture, and pipeline.

- Follow PEP 8 for Python; keep functions small and single-purpose
- LLM calls must go through llm/client.py (LiteLLM) — never call a provider SDK directly, backend must stay swappable
- Deterministic stages (AST classify, Docker verify, Semgrep) must not call any LLM
- Don't add dependencies or folders beyond what's in projectinfo.md §7 without asking first
- Respect the non-goals in projectinfo.md §8 — this is a scoped student project, not a production tool