# MergeMind — Known Issues & Troubleshooting Log

---

## Issue #1: Missing Installation Context (401 Unauthorized) After Server Restart or Fresh Browser Session

**Date:** September 13, 2026  
**Status:** Documented / Workaround Available / Configuration Fix Identified  
**Severity:** Low (Developer Experience / Local Environment)  
**Affected Endpoints:**
- `GET /api/github/repositories`
- `GET /api/github/repositories/{owner}/{repo}/pulls`
- `GET /api/github/repositories/{owner}/{repo}/pulls/{pull_number}`
- `GET /api/github/repositories/{owner}/{repo}/pulls/{pull_number}/conflicts`

---

### 1. Symptoms & Observed Logs

During local execution (`uvicorn app.main:app --host 127.0.0.1 --port 8000` + Vite frontend on `localhost:5173`), requests to `/api/github/repositories` fail repeatedly with `401 Unauthorized`:

```text
INFO:     127.0.0.1:59583 - "GET /api/github/repositories HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:59583 - "GET /api/github/repositories HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:59583 - "GET /api/github/install HTTP/1.1" 307 Temporary Redirect
INFO:     127.0.0.1:49930 - "GET /api/github/repositories HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:49930 - "GET /api/github/repositories HTTP/1.1" 401 Unauthorized
```

Clicking the **"Connect GitHub App"** button redirects to GitHub, but navigating back to the frontend keeps showing:
> *"Missing installation context. Please connect your GitHub account."*

---

### 2. Root Cause Analysis

#### A. HttpOnly Session Cookie Lifecycle
MergeMind does not store sensitive tokens or permanent user credentials in a database. Instead, it relies on a secure `installation_id` HttpOnly cookie stored in the browser.

The **only** endpoint that writes this cookie is:
```http
GET /api/github/setup?installation_id=<ID>
```
Upon execution, it verifies the installation with GitHub, sends the response header:
```http
Set-Cookie: installation_id=<ID>; Path=/; HttpOnly; SameSite=Lax
```
and issues a `307 Temporary Redirect` to `http://localhost:5173/repositories`.

#### B. GitHub App "Already Installed" Behavior
When a user clicks "Connect with GitHub", the frontend hits `/api/github/install`, which redirects to:
```
https://github.com/apps/<GITHUB_APP_SLUG>/installations/new
```
- **First-time installation**: GitHub displays the green **"Install"** button. After clicking it, GitHub automatically redirects to the App's configured **Setup URL**: `http://localhost:8000/api/github/setup?installation_id=...`.
- **Already-installed state**: If the app is **already installed** on the GitHub account (`swayaam03` with installation ID `160653761`), GitHub treats the user as an existing installer. Instead of a fresh installation and redirect, GitHub shows:
  > *"Already installed on swayaam03 (Configure)"*
- Because no new installation action occurred, GitHub **never fires the redirect back to `/api/github/setup`**.
- As a result, the browser never receives the `Set-Cookie` header, leaving subsequent API calls without authentication.

---

### 3. Immediate Workaround (Quick Fix)

Whenever cookies are lost (e.g. browser cache cleared, incognito mode, or new browser session), navigate directly to the setup route in your browser once:

```
http://localhost:8000/api/github/setup?installation_id=160653761
```

**What this does:**
1. Validates installation ID `160653761` using the GitHub App's private key and JWT.
2. Writes the `installation_id` HttpOnly cookie to your browser.
3. Automatically redirects back to `http://localhost:5173/repositories` with all repositories accessible.

---

### 4. Permanent GitHub App Settings Fix

To make GitHub trigger the redirect even when reconfiguring an already-installed app:

1. Open **[GitHub App Developer Settings](https://github.com/settings/apps/mergemindd)**.
2. Navigate to **General** → **Identifying and authorizing users**.
3. Set **Setup URL (optional)** to:
   ```text
   http://localhost:8000/api/github/setup
   ```
4. Enable the checkbox:
   - **☑ Redirect on update**  
     *(Enables GitHub to redirect back to the Setup URL whenever an installation's repository permissions are saved or updated).*
5. Click **Save changes**.

---

### 5. Recommended Future Enhancements

- **Local Dev Fallback Mode**: If running in `DEBUG=True` or `ENVIRONMENT=development` and `.env` specifies a default `DEV_INSTALLATION_ID`, allow `/api/github/repositories` to fall back to this ID when no cookie is present.
- **Frontend Connect Dialog**: On the `/connect` screen, provide an "Already installed? Quick connect" option for developers that directly routes through `/api/github/setup?installation_id=<id>`.
