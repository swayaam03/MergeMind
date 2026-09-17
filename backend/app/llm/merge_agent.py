"""MergeAgent orchestrates prompt construction, LLM client invocation, and proposal validation."""

import logging
from typing import Any, Dict, Optional

from app.context.models import RepositoryContext
from app.llm.client import LLMClient
from app.llm.prompts import MERGEMIND_SYSTEM_PROMPT, build_merge_prompt
from app.llm.schemas import MergeProposal

logger = logging.getLogger(__name__)


class MergeAgent:
    """Semantic Git merge agent for resolving code conflicts."""

    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or LLMClient()

    async def propose_merge(
        self,
        conflicted_file: Dict[str, Any],
        repository_context: Optional[RepositoryContext] = None,
    ) -> MergeProposal:
        """
        Synthesize a semantic merge proposal for a single conflicted file.

        Steps:
        1. Construct structured prompt using Repository Context, AST analysis, and Base/Local/Remote code.
        2. Invoke LLM Client with strict system prompt and timeout.
        3. Validate and enforce status semantics on returned MergeProposal.
        """
        path = conflicted_file.get("path", "")
        logger.info("MergeAgent proposing resolution for file: '%s'", path)

        user_prompt = build_merge_prompt(
            conflicted_file=conflicted_file,
            repository_context=repository_context,
        )

        proposal = await self.client.complete_merge_proposal(
            system_prompt=MERGEMIND_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        # Attach target file path
        if not proposal.file_path and path:
            proposal.file_path = path

        # Enforce status semantics
        if proposal.status == "resolved" and not proposal.merged_code.strip():
            logger.warning("LLM marked proposal as 'resolved' but returned empty merged_code. Demoting to 'unresolved'.")
            proposal.status = "unresolved"
            if not proposal.explanation:
                proposal.explanation = "Model returned empty code; marked as unresolved."
            proposal.risks.append("Proposed merged code was empty.")

        logger.info(
            "Merge proposal generated for '%s': status=%s, preserved=%d, risks=%d",
            path,
            proposal.status,
            len(proposal.preserved_changes),
            len(proposal.risks),
        )

        return proposal
