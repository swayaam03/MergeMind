"""API routes for LLM merge proposal generation."""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, Body, Cookie, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.api.routes.pull_requests import resolve_installation_id
from app.ast import analyze_conflicted_file
from app.context.extractor import extract_repository_context
from app.git.conflicts import (
    GitConflictError,
    checkout_pr_baseline,
    simulate_merge_and_extract_conflicts,
)
from app.git.github import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubConfigError,
    get_installation_access_token,
    get_installation_repositories,
    get_pull_request_detail,
)
from app.llm.client import (
    LLMConfigurationError,
    LLMError,
    LLMProviderError,
    LLMResponseParsingError,
    LLMTimeoutError,
)
from app.llm.merge_agent import MergeAgent
from app.llm.schemas import MergeProposal, MergeProposalRequest
from app.pipeline.verifier import verify_merge_proposal
from app.schemas.verification import LanguageType, VerificationReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["merges"])


@router.post(
    "/repositories/{owner}/{repo}/pulls/{pull_number}/merge-proposal",
    response_model=MergeProposal,
)
async def generate_merge_proposal(
    owner: str,
    repo: str,
    pull_number: int,
    request: Request,
    body: Optional[MergeProposalRequest] = Body(default=None),
    file_path: Optional[str] = Query(
        default=None,
        description="Optional conflicting file path to resolve. Overrides body.file_path if provided.",
    ),
    installation_id_cookie: Optional[str] = Cookie(
        default=None,
        alias="installation_id",
        description="GitHub App installation ID stored in HttpOnly cookie",
    ),
    installation_id_query: Optional[int] = Query(
        default=None,
        alias="installation_id",
        description="Optional installation ID override for testing or direct API clients",
    ),
    installation_id_header: Optional[str] = Header(
        default=None,
        alias="x-installation-id",
        description="Optional installation ID provided via HTTP header",
    ),
) -> Dict[str, Any]:
    """
    Generate an AI semantic merge conflict resolution proposal for a conflicted pull request.

    Deterministic pipeline flow:
    1. Authenticate via installation context.
    2. Verify repository accessibility.
    3. Retrieve PR metadata and confirm mergeable == False.
    4. Simulate Git merge in isolated environment to extract Base, Local, Remote and conflict markers.
    5. Parse and classify AST structure using Tree-sitter.
    6. Extract repository context (manifests, compact tree, docs, neighbor files).
    7. Invoke MergeAgent via LiteLLM to synthesize resolution.
    8. Validate structured MergeProposal.

    Security guarantees:
    - NEVER modifies GitHub.
    - NEVER commits or pushes code.
    - NEVER executes generated code.
    - NEVER sends credentials or secrets to LLM.
    """
    target_installation_id = resolve_installation_id(
        request=request,
        installation_id_cookie=installation_id_cookie,
        installation_id_header=installation_id_header,
        installation_id_query=installation_id_query,
        endpoint_name=f"POST /repositories/{owner}/{repo}/pulls/{pull_number}/merge-proposal",
    )

    # Determine requested target file path (Query param takes precedence)
    target_file_path = file_path or (body.file_path if body else None)

    try:
        installation_token = get_installation_access_token(target_installation_id)

        # 1. Verify repository accessibility
        accessible_repos = get_installation_repositories(installation_token)
        target_full_name = f"{owner}/{repo}".lower()
        is_accessible = any(
            str(r.get("full_name", "")).lower() == target_full_name
            for r in accessible_repos
        )
        if not is_accessible:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Repository '{owner}/{repo}' is not accessible to this installation.",
            )

        # 2. Retrieve PR detail to check mergeability and branch names
        pr_data = get_pull_request_detail(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            installation_token=installation_token,
        )

        base_obj = pr_data.get("base") or {}
        head_obj = pr_data.get("head") or {}
        base_branch = base_obj.get("ref", "main")
        head_branch = head_obj.get("ref", "")
        base_sha = base_obj.get("sha", "")
        head_sha = head_obj.get("sha", "")
        mergeable = pr_data.get("mergeable")

        if mergeable is True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pull request has no merge conflicts (mergeable = true). No proposal required.",
            )

        if mergeable is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub is still calculating mergeability for this pull request.",
            )

        # 3. Simulate Git merge to extract Base, Local, and Remote code
        extraction_result = simulate_merge_and_extract_conflicts(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            base_branch=base_branch,
            head_branch=head_branch,
            base_sha=base_sha,
            head_sha=head_sha,
            installation_token=installation_token,
        )

        conflicts = extraction_result.get("conflicts", [])
        if not conflicts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No conflicting files detected for this pull request.",
            )

        # 4. Tree-sitter AST analysis
        for c in conflicts:
            ast_res = analyze_conflicted_file(
                path=c["path"],
                base_code=c.get("base", ""),
                local_code=c.get("local", ""),
                remote_code=c.get("remote", ""),
            )
            c["ast_analysis"] = ast_res.model_dump()

        # 5. Select target conflict
        selected_conflict: Optional[Dict[str, Any]] = None
        if target_file_path:
            for c in conflicts:
                if c["path"] == target_file_path:
                    selected_conflict = c
                    break
            if not selected_conflict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File '{target_file_path}' is not among the conflicting files in PR #{pull_number}.",
                )
        else:
            selected_conflict = conflicts[0]

        # 6. Extract deterministic repository context
        ast_analyses = {c["path"]: c["ast_analysis"] for c in conflicts if "ast_analysis" in c}
        conflict_sources = {c["path"]: c.get("local", "") or c.get("base", "") for c in conflicts}

        repo_context = extract_repository_context(
            owner=owner,
            repo=repo,
            token=installation_token,
            base_ref=base_branch,
            head_ref=head_branch,
            conflicting_files=[c["path"] for c in conflicts],
            ast_analyses=ast_analyses,
            conflict_sources=conflict_sources,
        )

        # 7. Execute LLM Merge Agent
        agent = MergeAgent()
        proposal = await agent.propose_merge(
            conflicted_file=selected_conflict,
            repository_context=repo_context,
        )

        return proposal.model_dump()

    except HTTPException:
        raise
    except LLMConfigurationError as exc:
        logger.error("LLM configuration error for %s/%s PR #%d: %s", owner, repo, pull_number, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except LLMTimeoutError as exc:
        logger.error("LLM timeout for %s/%s PR #%d: %s", owner, repo, pull_number, exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    except (LLMProviderError, LLMResponseParsingError) as exc:
        logger.error("LLM provider/parsing error for %s/%s PR #%d: %s", owner, repo, pull_number, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except GitHubConfigError as exc:
        logger.error("GitHub App configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub App configuration is missing or invalid.",
        ) from exc
    except GitHubAuthError as exc:
        logger.error("GitHub App authentication failed for installation %d: %s", target_installation_id, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub App authentication failed.",
        ) from exc
    except GitHubAPIError as exc:
        logger.error("GitHub API error for %s/%s PR #%d: %s (status=%d)", owner, repo, pull_number, exc, exc.status_code)
        if exc.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pull request #{pull_number} or repository '{owner}/{repo}' not found on GitHub.",
            ) from exc
        if exc.status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Repository '{owner}/{repo}' is not accessible to this installation.",
            ) from exc
        raise HTTPException(
            status_code=exc.status_code if 400 <= exc.status_code < 600 else status.HTTP_502_BAD_GATEWAY,
            detail="GitHub API error while retrieving pull request.",
        ) from exc
    except GitConflictError as exc:
        logger.error("Git conflict simulation failed for %s/%s PR #%d: %s", owner, repo, pull_number, exc)
        raise HTTPException(
            status_code=exc.status_code,
            detail=f"Git conflict extraction failed: {str(exc)}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error generating merge proposal for %s/%s PR #%d", owner, repo, pull_number)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while generating merge proposal.",
        ) from exc


class VerifyProposalRequest(BaseModel):
    """Payload for deterministic verification of a proposed merge."""

    target_file: str = Field(..., description="Path of conflicted file being verified")
    merged_code: str = Field(..., description="Proposed resolved merged code")
    language: Optional[LanguageType] = Field(default=None, description="Optional language hint")


@router.post(
    "/repositories/{owner}/{repo}/pulls/{pull_number}/verify-proposal",
    response_model=VerificationReport,
)
def verify_proposal(
    owner: str,
    repo: str,
    pull_number: int,
    request: Request,
    body: VerifyProposalRequest = Body(...),
    installation_id_cookie: Optional[str] = Cookie(
        default=None,
        alias="installation_id",
        description="GitHub App installation ID stored in HttpOnly cookie",
    ),
    installation_id_query: Optional[int] = Query(
        default=None,
        alias="installation_id",
        description="Optional installation ID override for testing or direct API clients",
    ),
    installation_id_header: Optional[str] = Header(
        default=None,
        alias="x-installation-id",
        description="Optional installation ID provided via HTTP header",
    ),
) -> VerificationReport:
    """
    Execute 4-stage deterministic verification on a proposed merge resolution.

    Verification Stages:
    1. Syntax Validation: AST / compiler check on target file
    2. Build / Compilation: Language-specific build check
    3. Test Execution: Existing test suite run inside locked-down sandbox
    4. Security Audit: Semgrep and AST static analysis for sinks and secrets

    ZERO LLMs are called during verification.
    """
    target_installation_id = resolve_installation_id(
        request=request,
        installation_id_cookie=installation_id_cookie,
        installation_id_header=installation_id_header,
        installation_id_query=installation_id_query,
        endpoint_name=f"POST /repositories/{owner}/{repo}/pulls/{pull_number}/verify-proposal",
    )

    try:
        installation_token = get_installation_access_token(target_installation_id)
        pr_detail = get_pull_request_detail(owner, repo, pull_number, installation_token)

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)
            try:
                checkout_pr_baseline(
                    owner=owner,
                    repo=repo,
                    base_branch=pr_detail.get("base_ref", "main"),
                    base_sha=pr_detail.get("base_sha", ""),
                    installation_token=installation_token,
                    target_dir=temp_path,
                )
            except Exception as clone_err:
                logger.warning(
                    "Baseline checkout failed, proceeding with isolated target file workspace: %s",
                    clone_err,
                )
                # Create directory structure for target file if baseline clone is unreachable
                target_p = temp_path / body.target_file
                target_p.parent.mkdir(parents=True, exist_ok=True)
                target_p.write_text(body.merged_code, encoding="utf-8")

            report = verify_merge_proposal(
                source_dir=temp_path,
                target_file=body.target_file,
                merged_code=body.merged_code,
                language=body.language,
            )
            return report

    except HTTPException:
        raise
    except GitHubAuthError as exc:
        logger.error("GitHub App authentication failed for installation %d: %s", target_installation_id, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub App authentication failed.",
        ) from exc
    except GitHubAPIError as exc:
        logger.error("GitHub API error for %s/%s PR #%d: %s", owner, repo, pull_number, exc)
        raise HTTPException(
            status_code=exc.status_code if 400 <= exc.status_code < 600 else status.HTTP_502_BAD_GATEWAY,
            detail="GitHub API error while verifying pull request.",
        ) from exc
    except Exception as exc:
        logger.exception("Verification pipeline error for %s/%s PR #%d", owner, repo, pull_number)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification pipeline failed: {str(exc)}",
        ) from exc

