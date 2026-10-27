# MergeMind

AI-powered semantic Git merge conflict resolver.

> Final-year project — Dept. of Information Technology, St. Francis Institute of Technology.

MergeMind parses both sides of a merge conflict into ASTs, uses an LLM to propose a resolution, verifies it inside a Docker sandbox, scans it with Semgrep for security regressions, and presents a 4-way diff for human review. If the LLM can't produce a passing resolution after retries, it hands off to the developer with a clear explanation of what was tried and why.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.11+ | Backend (FastAPI) |
| **Node.js** | 18+ | Frontend (Vite + React) |
| **Docker Desktop** | Latest | Sandbox verification |
| **Git** | 2.30+ | Conflict simulation |

---

## 1. Clone & Configure Environment

```bash
git clone https://github.com/swayaam03/MergeMind.git
cd MergeMind
```

Copy the environment template and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with these required values:

```env
# GitHub App (get from github.com/settings/apps)
GITHUB_APP_ID=<your-app-id>
GITHUB_CLIENT_ID=<your-client-id>
GITHUB_CLIENT_SECRET=<your-client-secret>
GITHUB_PRIVATE_KEY_PATH=./secrets/github-app.pem
GITHUB_WEBHOOK_SECRET=<your-webhook-secret>
GITHUB_APP_SLUG=<your-app-slug>

# Application URLs
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000

# LLM Merge Agent (OpenRouter)
LLM_PROVIDER=openrouter
LLM_MODEL=google/gemini-2.5-flash
OPENROUTER_API_KEY=<your-openrouter-api-key>
LLM_TEMPERATURE=0.1
LLM_TIMEOUT_SECONDS=60
```

Get an OpenRouter API key from [openrouter.ai/keys](https://openrouter.ai/keys).

---

## 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Backend runs at **http://localhost:8000**. API docs available at `/docs`.

---

## 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**.

---

## 4. Docker Sandbox Setup

Docker Desktop must be running for the verification pipeline to execute inside isolated containers instead of in-process on the host.

### Step 1 — Start Docker Desktop

Launch **Docker Desktop** from the Start Menu. Wait for the whale icon in the system tray to turn **green** (steady, not animating).

### Step 2 — Pre-pull Sandbox Images

Pull the container images MergeMind uses for verification. Do this ahead of time to avoid slow first-run delays:

```powershell
docker pull python:3.11-slim
docker pull node:20-slim
docker pull openjdk:17-slim
```

### Step 3 — Verify Docker is Accessible

```powershell
docker info --format "{{.ServerVersion}}"
```

This should print a version number (e.g., `27.5.1`). This is the exact check the backend's `DockerSandboxRunner.is_available()` runs.

### Step 4 — Restart the Backend

After starting Docker, restart uvicorn so the sandbox runner detects it:

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### What Docker Enables

When Docker is running, the verification pipeline executes each stage inside a **locked-down ephemeral container** with:

- `--network none` — prevents all external traffic (no data exfiltration)
- CPU, memory, and PID limits — prevents resource exhaustion
- No host credentials forwarded — secrets are stripped from the container environment
- Dropped Linux capabilities — minimal privilege execution
- Auto-removal — containers are destroyed after execution

| Badge in UI | Meaning |
|---|---|
| **Docker: Isolated** | Verification ran inside Docker containers ✅ |
| **Docker: In-Process** | Docker was offline; ran on host directly ⚠️ |

Both modes run the **same checks** (syntax, build, tests, Semgrep) — Docker adds isolation guarantees.

---

## 5. GitHub App Installation

MergeMind integrates directly with GitHub using a dedicated **GitHub App**.

- **App Integration Flow**: On the `/connect` page, clicking **"Continue with GitHub"** initiates the integration flow by calling the backend endpoint `GET /api/github/install`.
- **Installation Redirect**: The backend constructs the secure installation URL:
  ```
  https://github.com/apps/<GITHUB_APP_SLUG>/installations/new
  ```
  and returns an HTTP redirect to GitHub, allowing users to choose whether to install MergeMind across all repositories or select specific repositories.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        MergeMind Pipeline                       │
├─────────────┬───────────────┬───────────────┬───────────────────┤
│ 1. Trigger  │ 2. AST Parse  │ 3. Context    │ 4. Merge Agent   │
│ (Git/GitHub)│ (Tree-sitter) │ (Deterministic│ (LLM via LiteLLM)│
│             │               │  Extraction)  │                  │
├─────────────┼───────────────┼───────────────┼───────────────────┤
│ 5. Verify   │ 6. Retry Loop │ 7. Explain    │ 8. Human Review  │
│ (Docker     │ (Max 2-3      │ (LLM summary  │ (4-way diff +    │
│  Sandbox)   │  attempts)    │  of failures) │  Accept/Edit/    │
│             │               │               │  Reject)         │
└─────────────┴───────────────┴───────────────┴───────────────────┘
```

**Core principle:** Use an LLM only where reasoning is needed; verify everything else deterministically.

### Verification Pipeline (Zero-LLM)

| Stage | What it checks | Tool |
|-------|---------------|------|
| 1. Syntax Validation | AST parse correctness | `ast.parse` / `node --check` / Tree-sitter |
| 2. Build Check | Compilation (Java) / skip (interpreted) | `javac` / N/A |
| 3. Test Execution | Existing test suite | `pytest` / `npm test` / `mvn test` |
| 4. Security Audit | Vulnerability and regression scan | Semgrep + AST static analysis |

---

### Quick Smoke Test

```powershell
# Verify Docker is reachable by the backend
curl http://localhost:8000/api/health

# Verify OpenRouter key works
python -c "import requests; r = requests.get('https://openrouter.ai/api/v1/auth/key', headers={'Authorization': 'Bearer <YOUR_KEY>'}); print(r.json())"
```

---

## License

See [LICENSE](./LICENSE).
