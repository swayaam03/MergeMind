"""GitHub Webhook receiver with HMAC-SHA256 signature verification and event tracking."""

import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.core.config import settings
from app.db.database import (
    upsert_pull_request,
    upsert_repository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github/webhooks", tags=["webhooks"])


def verify_github_signature(payload_bytes: bytes, signature_header: Optional[str]) -> bool:
    """Verify GitHub HMAC-SHA256 webhook signature using constant-time comparison."""
    secret = settings.GITHUB_WEBHOOK_SECRET
    if not secret or not secret.strip():
        logger.warning("GITHUB_WEBHOOK_SECRET is not configured. Webhooks signature verification is disabled in dev mode.")
        return True

    if not signature_header:
        logger.error("Missing X-Hub-Signature-256 header")
        return False

    if not signature_header.startswith("sha256="):
        logger.error("Invalid signature format (must start with 'sha256=')")
        return False

    expected_sig = signature_header[len("sha256=") :].strip()
    computed_sig = hmac.new(
        key=secret.strip().encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed_sig, expected_sig)


@router.post("", status_code=status.HTTP_200_OK)
async def handle_github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
) -> Dict[str, Any]:
    """
    Receive, verify, and process incoming GitHub webhook notifications.

    Supported events:
    - ping: Webhook setup validation
    - pull_request: Synchronizes PR status, branches, and conflict readiness
    - installation / installation_repositories: Updates tracked repository memberships
    """
    body_bytes = await request.body()

    # 1. Cryptographic HMAC-SHA256 signature validation
    if not verify_github_signature(body_bytes, x_hub_signature_256):
        logger.warning("Rejected webhook delivery %s due to invalid signature", x_github_delivery)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub webhook signature.",
        )

    # 2. Parse JSON payload
    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse webhook JSON body: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        ) from exc

    event = (x_github_event or "unknown").lower()
    action = payload.get("action", "")
    logger.info("Processing webhook event: '%s' (action='%s', delivery='%s')", event, action, x_github_delivery)

    # 3. Handle 'ping' event
    if event == "ping":
        zen = payload.get("zen", "MergeMind connection verified.")
        return {"status": "success", "event": "ping", "zen": zen}

    # 4. Handle 'pull_request' events
    if event == "pull_request":
        pr_data = payload.get("pull_request") or {}
        repo_data = payload.get("repository") or {}

        repo_full_name = repo_data.get("full_name") or ""
        pr_number = pr_data.get("number") or payload.get("number")

        if repo_full_name and pr_number:
            # Sync repository metadata
            upsert_repository(
                owner=repo_data.get("owner", {}).get("login", ""),
                name=repo_data.get("name", ""),
                full_name=repo_full_name,
                default_branch=repo_data.get("default_branch", "main"),
                is_private=repo_data.get("private", False),
                installation_id=payload.get("installation", {}).get("id"),
            )

            # Sync PR metadata
            base_ref = pr_data.get("base", {}).get("ref", "main")
            head_ref = pr_data.get("head", {}).get("ref", "")
            mergeable_state = pr_data.get("mergeable_state")
            has_conflicts = mergeable_state in ("dirty", "conflict")

            upsert_pull_request(
                repository_full_name=repo_full_name,
                number=int(pr_number),
                title=pr_data.get("title", f"PR #{pr_number}"),
                state=pr_data.get("state", "open"),
                base_branch=base_ref,
                head_branch=head_ref,
                mergeable_state=mergeable_state,
                has_conflicts=has_conflicts,
            )

            logger.info("Synchronized PR #%d for %s (conflicted=%s)", pr_number, repo_full_name, has_conflicts)

        return {
            "status": "processed",
            "event": "pull_request",
            "action": action,
            "pr_number": pr_number,
            "repository": repo_full_name,
        }

    # 5. Handle repository installation updates
    if event in ("installation", "installation_repositories"):
        installation_id = payload.get("installation", {}).get("id")
        repos_added = payload.get("repositories_added") or payload.get("repositories") or []

        for r in repos_added:
            full_name = r.get("full_name", "")
            if full_name:
                parts = full_name.split("/")
                owner = parts[0] if len(parts) > 1 else ""
                name = parts[1] if len(parts) > 1 else full_name
                upsert_repository(
                    owner=owner,
                    name=name,
                    full_name=full_name,
                    is_private=r.get("private", False),
                    installation_id=installation_id,
                )

        return {
            "status": "processed",
            "event": event,
            "action": action,
            "installation_id": installation_id,
        }

    return {"status": "ignored", "event": event, "action": action}
