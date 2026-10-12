"""Explanation Agent for MergeMind.

When automated merge attempts fail or verification retries are exhausted,
this agent synthesizes an insightful, plain-English explanation for the human developer.
Zero automatic merging occurs here; the goal is strictly actionable human guidance.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.llm.client import LLMClient
from app.pipeline.state import MergeAttemptRecord

logger = logging.getLogger(__name__)

EXPLANATION_SYSTEM_PROMPT = """You are MergeMind's Explanation Agent.

Your job is to assist a human software engineer by explaining why an automated Git merge conflict resolution attempt failed, and what decisions need to be made manually.

GUIDELINES:
1. Speak clearly, concisely, and technically accurate to a software developer.
2. Analyze the conflict: summarize what the Base version had, what the Local branch (target) changed, and what the Remote branch (PR) changed.
3. Review the failed attempts: clearly explain which tests failed, what syntax errors occurred, or what security rules were triggered.
4. Give concrete, actionable recommendations for how the human reviewer should resolve the conflicting logic.
5. NEVER hallucinate files or functions that do not exist in the provided context.
6. OUTPUT ONLY VALID JSON matching this exact schema:
{
    "summary": "<high-level 1-2 sentence overview of why the automated merge was aborted and escalated>",
    "conflict_overview": "<explanation of the semantic clash between Local and Remote branches>",
    "attempts_summary": [
        "<bullet point for each attempt explaining what failed (e.g. Attempt 1: pytest test_auth failed with AssertionError)>"
    ],
    "recommendations": [
        "<concrete actionable suggestions for the human reviewer in the diff editor>"
    ]
}
Do not wrap your output in conversational markdown or introductory prose. Output pure JSON only.
"""


class ExplanationReport(BaseModel):
    """Structured report produced by the Explanation Agent."""

    summary: str = Field(
        ...,
        description="High-level overview of why the conflict could not be automatically resolved.",
    )
    conflict_overview: str = Field(
        default="",
        description="Detailed analysis of the conflicting intents between Local and Remote branches.",
    )
    attempts_summary: List[str] = Field(
        default_factory=list,
        description="Chronological summary of what each automated attempt tried and where verification failed.",
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Specific, actionable suggestions for the human reviewer.",
    )
    model: Optional[str] = Field(
        default=None,
        description="LLM model identifier that synthesized this explanation.",
    )


class ExplanationAgent:
    """Agent that generates human-friendly explanations when merge retries fail."""

    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or LLMClient()

    async def explain_failure(
        self,
        file_path: str,
        language: str,
        conflicted_file: Dict[str, Any],
        history: List[MergeAttemptRecord],
        ast_analysis: Optional[Dict[str, Any]] = None,
    ) -> ExplanationReport:
        """
        Synthesize an ExplanationReport from conflict context and attempt failure records.
        """
        logger.info("ExplanationAgent synthesizing report for '%s' (%d attempts)", file_path, len(history))

        user_prompt = self._build_prompt(
            file_path=file_path,
            language=language,
            conflicted_file=conflicted_file,
            history=history,
            ast_analysis=ast_analysis,
        )

        try:
            parsed = await self.client.complete_structured_json(
                system_prompt=EXPLANATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            report = ExplanationReport(
                summary=parsed.get("summary", "Automated merge attempts failed verification and require human review."),
                conflict_overview=parsed.get("conflict_overview", ""),
                attempts_summary=parsed.get("attempts_summary", []),
                recommendations=parsed.get("recommendations", []),
                model=self.client.model,
            )
        except Exception as exc:
            logger.warning("ExplanationAgent LLM call failed, falling back to deterministic explanation: %s", exc)
            report = self._fallback_explanation(file_path, history)

        return report

    def _build_prompt(
        self,
        file_path: str,
        language: str,
        conflicted_file: Dict[str, Any],
        history: List[MergeAttemptRecord],
        ast_analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Construct user prompt detailing the conflict and each attempt's failure."""
        base_code = conflicted_file.get("base", "")
        local_code = conflicted_file.get("local", "")
        remote_code = conflicted_file.get("remote", "")

        ast_cat = ""
        ast_reason = ""
        if ast_analysis:
            clf = ast_analysis.get("classification") or {}
            ast_cat = clf.get("category", "")
            ast_reason = clf.get("reason", "")

        attempts_text = []
        for i, att in enumerate(history, 1):
            att_num = att.get("attempt_number", i)
            v = att.get("verification") or {}
            v_status = v.get("overall_status", "unknown")
            stages = v.get("stages") or {}
            failed_stage_details = []
            for sname, sdata in stages.items():
                if sdata.get("status") == "failed":
                    s_err = sdata.get("error_message") or sdata.get("output", "")
                    failed_stage_details.append(f"Stage '{sname}': {s_err[:300]}")
            failed_str = "; ".join(failed_stage_details) if failed_stage_details else "Verification failed"
            attempts_text.append(f"Attempt #{att_num} (Overall Result: {v_status}):\n- Failures: {failed_str}")

        attempts_block = "\n\n".join(attempts_text) if attempts_text else "No detailed attempt logs available."

        return f"""The automated merge agent exhausted its retry limit for the following file:
FILE: {file_path}
LANGUAGE: {language}
AST CLASSIFICATION: {ast_cat} ({ast_reason})

=== BASE CODE (Common Ancestor) ===
```{language}
{base_code[:3000]}
```

=== LOCAL CODE (Target Branch / Ours) ===
```{language}
{local_code[:3000]}
```

=== REMOTE CODE (Source Branch / Theirs) ===
```{language}
{remote_code[:3000]}
```

=== ATTEMPT & VERIFICATION HISTORY ===
{attempts_block}

TASK:
Provide an ExplanationReport in pure JSON summarizing:
1. "summary": Brief explanation of the conflict and escalation.
2. "conflict_overview": The incompatible semantic changes.
3. "attempts_summary": Bullet points for each attempt explaining why it failed.
4. "recommendations": Concrete recommendations for the human reviewer.
"""

    def _fallback_explanation(self, file_path: str, history: List[MergeAttemptRecord]) -> ExplanationReport:
        """Deterministic fallback explanation when LLM is unreachable."""
        attempts_summaries = []
        for i, att in enumerate(history, 1):
            v = att.get("verification") or {}
            stages = v.get("stages") or {}
            fails = [s for s, data in stages.items() if data.get("status") == "failed"]
            attempts_summaries.append(
                f"Attempt #{i}: Failed in verification stages: {', '.join(fails) if fails else 'Unknown failure'}"
            )

        return ExplanationReport(
            summary=f"Automated merge attempts for '{file_path}' could not pass deterministic verification after {len(history)} attempts.",
            conflict_overview="Conflicting logic between branches could not be resolved cleanly without breaking tests or syntax.",
            attempts_summary=attempts_summaries,
            recommendations=[
                "Inspect the conflicting hunks using the 4-way diff editor.",
                "Verify whether both changes should be unified or one branch takes precedence.",
                "Run test suite locally after manual resolution to confirm correctness.",
            ],
            model="deterministic-fallback",
        )
