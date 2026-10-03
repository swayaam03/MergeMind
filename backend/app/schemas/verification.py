"""Pydantic schemas for sandbox execution and verification pipeline."""

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

LanguageType = Literal["python", "javascript", "typescript", "java", "unknown"]
VerificationStageStatus = Literal["PASS", "FAIL", "SKIPPED", "ERROR"]
OverallVerificationStatus = Literal["PASSED", "FAILED", "ERROR"]


class DockerContainerConfig(BaseModel):
    """Configuration for running a command in a locked-down Docker sandbox."""

    image: str = Field(..., description="Docker image name, e.g. python:3.11-slim")
    command: List[str] = Field(..., description="Command and arguments to execute")
    working_dir: str = Field(default="/workspace", description="Working directory inside container")
    timeout_seconds: int = Field(default=45, ge=1, le=300, description="Execution timeout in seconds")
    cpu_limit: float = Field(default=1.0, ge=0.1, le=8.0, description="Max CPU limit (fractional cores)")
    memory_limit: str = Field(default="512m", description="Max memory limit (e.g. 512m, 1g)")
    pids_limit: int = Field(default=100, ge=10, le=1000, description="Max process limit to prevent fork bombs")
    network_mode: str = Field(default="none", description="Network isolation mode ('none' prevents all external traffic)")
    environment: Dict[str, str] = Field(default_factory=dict, description="Allowed container environment variables")
    read_only: bool = Field(default=False, description="Whether root filesystem is mounted read-only")
    cap_drop: List[str] = Field(default_factory=lambda: ["ALL"], description="Linux capabilities to drop")
    user: Optional[str] = Field(default=None, description="Non-root user to run as inside container")


class ContainerExecutionResult(BaseModel):
    """Output from a container or sandbox execution."""

    exit_code: int = Field(..., description="Process exit code (0 = success)")
    stdout: str = Field(default="", description="Captured standard output (truncated if excessive)")
    stderr: str = Field(default="", description="Captured standard error (truncated if excessive)")
    duration_seconds: float = Field(default=0.0, description="Elapsed execution time in seconds")
    timed_out: bool = Field(default=False, description="Whether execution was terminated due to timeout")
    error_message: Optional[str] = Field(default=None, description="Internal error or exception details if runner failed")

    @property
    def is_success(self) -> bool:
        """Returns True if process exited cleanly with code 0 and did not time out."""
        return self.exit_code == 0 and not self.timed_out and not self.error_message


class ProposedWorkspaceInfo(BaseModel):
    """Metadata describing an isolated workspace prepared with proposed merged code."""

    workspace_id: str = Field(..., description="Unique identifier for this temporary workspace")
    workspace_path: str = Field(..., description="Absolute path to isolated workspace directory on host")
    target_file: str = Field(..., description="Relative path of the modified/resolved file")
    language: LanguageType = Field(default="unknown", description="Detected language of target file")
    file_count: int = Field(default=0, description="Total number of files in the isolated workspace")
    has_test_suite: bool = Field(default=False, description="Whether tests were detected in the workspace")
    test_framework: Optional[str] = Field(default=None, description="Detected test framework (e.g. pytest, npm, maven)")
    replaced_file_size: int = Field(default=0, description="Size in bytes of the applied merged code")


class StageResult(BaseModel):
    """Verification result for an individual deterministic stage."""

    stage: Literal["syntax", "build", "tests", "security"]
    status: VerificationStageStatus = Field(..., description="PASS, FAIL, SKIPPED, or ERROR")
    exit_code: Optional[int] = Field(default=None, description="Process exit code if applicable")
    duration_seconds: float = Field(default=0.0, description="Stage duration in seconds")
    summary: str = Field(..., description="Concise human-readable summary of stage outcome")
    details: Optional[str] = Field(default=None, description="Detailed error log, traceback, or compiler output")
    failing_items: List[str] = Field(default_factory=list, description="Specific failing tests, syntax errors, or rule IDs")


class VerificationReport(BaseModel):
    """Consolidated verification result for a merge proposal."""

    overall_status: OverallVerificationStatus = Field(..., description="Overall verification outcome")
    language: LanguageType = Field(default="unknown", description="Programming language verified")
    target_file: str = Field(..., description="Target conflicted file verified")
    syntax: StageResult = Field(..., description="Syntax checking stage result")
    build: StageResult = Field(..., description="Build / compilation stage result")
    tests: StageResult = Field(..., description="Test execution stage result")
    security: StageResult = Field(..., description="Security scanning stage result")
    total_duration_seconds: float = Field(default=0.0, description="Total pipeline execution duration")
    docker_used: bool = Field(default=True, description="Whether Docker sandbox was utilized for verification")
    sandbox_details: Dict[str, Any] = Field(default_factory=dict, description="Sandbox diagnostics and container metrics")
