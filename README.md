# MergeMind

AI-powered semantic Git merge conflict resolver.

---

## GitHub App Installation

MergeMind integrates directly with GitHub using a dedicated **GitHub App**.

- **App Integration Flow**: On the `/connect` page, clicking **"Continue with GitHub"** initiates the integration flow by calling the backend endpoint `GET /api/github/install`.
- **Installation Redirect**: The backend constructs the secure installation URL:
  ```text
  https://github.com/apps/<GITHUB_APP_SLUG>/installations/new
  ```
  and returns an HTTP redirect to GitHub, allowing users to choose whether to install MergeMind across all repositories or select specific repositories.
- **Next Phases**: Repository synchronization, webhook event ingestion, and conflict resolution will be connected in subsequent phases.
