"""Docker sandbox execution runner for MergeMind verification.

Enforces zero-trust isolation:
- Network disabled (--network none) to prevent data exfiltration and external calls
- Resource constraints (CPU quota, memory limit, process/pid limits)
- No host credentials or sensitive secrets forwarded
- Dropped Linux capabilities
- Guaranteed container stop and removal lifecycle
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.schemas.verification import ContainerExecutionResult, DockerContainerConfig

logger = logging.getLogger(__name__)

# Baseline safe environment variables allowed in containers
SAFE_ENV_DEFAULTS: Dict[str, str] = {
    "CI": "true",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONUNBUFFERED": "1",
    "DEBIAN_FRONTEND": "noninteractive",
}

# Substrings that identify forbidden secret environment variable keys
FORBIDDEN_ENV_SUBSTRINGS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "AUTH",
    "CREDENTIAL",
    "PRIVATE",
    "OPENROUTER",
    "GITHUB",
)


class DockerSandboxError(Exception):
    """Base exception for Docker sandbox operations."""
    pass


class DockerUnavailableError(DockerSandboxError):
    """Raised when the Docker daemon or CLI is not accessible on the host."""
    pass


class DockerTimeoutError(DockerSandboxError):
    """Raised when container execution exceeds the configured timeout."""
    pass


def sanitize_container_env(custom_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Construct a clean environment dictionary for the container.
    Strictly forbids and removes any tokens, keys, passwords, or host secrets.
    """
    clean_env = dict(SAFE_ENV_DEFAULTS)
    if custom_env:
        for k, v in custom_env.items():
            k_upper = k.upper()
            if any(forbidden in k_upper for forbidden in FORBIDDEN_ENV_SUBSTRINGS):
                logger.warning("Redacted forbidden environment variable from container: %s", k)
                continue
            clean_env[k] = str(v)
    return clean_env


def truncate_output(text: str, max_bytes: int = 500_000) -> str:
    """Truncate container output to prevent memory exhaustion from runaway logging."""
    if not text:
        return ""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[:max_bytes].decode("utf-8", errors="replace")
    return f"{truncated}\n\n[... Truncated by MergeMind sandbox after {max_bytes} bytes ...]"


class DockerSandboxRunner:
    """
    Executes commands inside locked-down, ephemeral Docker containers.
    Handles container lifecycles, timeouts, and resource limitations.
    """

    def __init__(
        self,
        default_timeout: int = settings.SANDBOX_TIMEOUT_SECONDS,
        default_cpu: float = settings.SANDBOX_CPU_LIMIT,
        default_memory: str = settings.SANDBOX_MEMORY_LIMIT,
        default_pids_limit: int = settings.SANDBOX_PIDS_LIMIT,
        network_mode: str = settings.SANDBOX_NETWORK_MODE,
    ) -> None:
        self.default_timeout = default_timeout
        self.default_cpu = default_cpu
        self.default_memory = default_memory
        self.default_pids_limit = default_pids_limit
        self.network_mode = network_mode
        self._docker_cli_path: Optional[str] = shutil.which("docker")

    def is_available(self) -> bool:
        """
        Check if Docker is installed and the Docker daemon is responding.
        Checks both Python docker SDK and Docker CLI.
        """
        # Try docker CLI first
        if self._docker_cli_path:
            try:
                res = subprocess.run(
                    [self._docker_cli_path, "info", "--format", "{{.ServerVersion}}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=4,
                )
                if res.returncode == 0 and res.stdout.strip():
                    return True
            except Exception:
                pass

        # Try Python docker SDK
        try:
            import docker  # type: ignore
            if hasattr(docker, "from_env"):
                client = docker.from_env()
                client.ping()
                return True
        except Exception:
            return False

        return False

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status of Docker availability and settings."""
        available = self.is_available()
        return {
            "available": available,
            "cli_found": bool(self._docker_cli_path),
            "cli_path": self._docker_cli_path,
            "network_mode": self.network_mode,
            "cpu_limit": self.default_cpu,
            "memory_limit": self.default_memory,
            "timeout_seconds": self.default_timeout,
        }

    def run_in_sandbox(
        self,
        workspace_dir: str | Path,
        config: DockerContainerConfig,
    ) -> ContainerExecutionResult:
        """
        Run a containerized command on the given workspace directory.

        Guarantees:
        - Network disabled
        - Host secrets stripped
        - Resource quotas enforced
        - Hard timeout enforced
        - Container destroyed on completion or error
        """
        resolved_workspace = Path(workspace_dir).resolve()
        if not resolved_workspace.exists():
            raise FileNotFoundError(f"Workspace directory does not exist: {resolved_workspace}")

        if not self.is_available():
            raise DockerUnavailableError(
                "Docker daemon is not running or docker CLI is not installed on this host."
            )

        # Merge environment with strict sanitization
        container_env = sanitize_container_env(config.environment)

        # Try running via Python Docker SDK if available and valid
        try:
            import docker  # type: ignore
            if hasattr(docker, "from_env"):
                return self._run_via_docker_sdk(resolved_workspace, config, container_env)
        except Exception as sdk_err:
            logger.debug("Docker SDK execution not available: %s", sdk_err)

        return self._run_via_docker_cli(resolved_workspace, config, container_env)

    def _run_via_docker_sdk(
        self,
        workspace_dir: Path,
        config: DockerContainerConfig,
        environment: Dict[str, str],
    ) -> ContainerExecutionResult:
        """Execute container using the docker Python SDK."""
        import docker  # type: ignore

        client = docker.from_env()
        container = None
        start_time = time.monotonic()
        timed_out = False

        # Convert CPU float to nano_cpus
        nano_cpus = int(config.cpu_limit * 1_000_000_000)

        # Volume mount: /workspace inside container
        volumes = {
            str(workspace_dir): {
                "bind": config.working_dir,
                "mode": "ro" if config.read_only else "rw",
            }
        }

        try:
            # Create container without starting immediately
            container = client.containers.create(
                image=config.image,
                command=config.command,
                working_dir=config.working_dir,
                volumes=volumes,
                environment=environment,
                network_mode=config.network_mode,
                nano_cpus=nano_cpus,
                mem_limit=config.memory_limit,
                pids_limit=config.pids_limit,
                cap_drop=config.cap_drop,
                user=config.user,
                detach=True,
            )

            container.start()

            # Wait with hard timeout
            try:
                wait_res = container.wait(timeout=config.timeout_seconds)
                exit_code = wait_res.get("StatusCode", 1)
            except Exception as wait_exc:
                # Timeout occurred
                timed_out = True
                exit_code = 124
                logger.warning("Container timed out after %ds: %s", config.timeout_seconds, wait_exc)
                try:
                    container.kill()
                except Exception:
                    pass

            duration = round(time.monotonic() - start_time, 3)

            # Retrieve stdout & stderr logs
            raw_stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            raw_stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            return ContainerExecutionResult(
                exit_code=exit_code,
                stdout=truncate_output(raw_stdout),
                stderr=truncate_output(raw_stderr),
                duration_seconds=duration,
                timed_out=timed_out,
            )

        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception as rem_exc:
                    logger.debug("Failed to remove container: %s", rem_exc)

    def _run_via_docker_cli(
        self,
        workspace_dir: Path,
        config: DockerContainerConfig,
        environment: Dict[str, str],
    ) -> ContainerExecutionResult:
        """Execute container using the docker CLI binary as fallback."""
        if not self._docker_cli_path:
            raise DockerUnavailableError("Docker CLI binary not found on PATH.")

        cli_cmd: List[str] = [
            self._docker_cli_path,
            "run",
            "--rm",
            f"--network={config.network_mode}",
            f"--cpus={config.cpu_limit}",
            f"--memory={config.memory_limit}",
            f"--pids-limit={config.pids_limit}",
            f"-w={config.working_dir}",
            f"-v={str(workspace_dir)}:{config.working_dir}:{'ro' if config.read_only else 'rw'}",
        ]

        for cap in config.cap_drop:
            cli_cmd.append(f"--cap-drop={cap}")

        if config.user:
            cli_cmd.append(f"--user={config.user}")

        for k, v in environment.items():
            cli_cmd.extend(["-e", f"{k}={v}"])

        cli_cmd.append(config.image)
        cli_cmd.extend(config.command)

        start_time = time.monotonic()
        timed_out = False

        try:
            proc = subprocess.run(
                cli_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=config.timeout_seconds,
            )
            duration = round(time.monotonic() - start_time, 3)
            return ContainerExecutionResult(
                exit_code=proc.returncode,
                stdout=truncate_output(proc.stdout),
                stderr=truncate_output(proc.stderr),
                duration_seconds=duration,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration = round(time.monotonic() - start_time, 3)
            stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return ContainerExecutionResult(
                exit_code=124,
                stdout=truncate_output(stdout),
                stderr=truncate_output(stderr) + "\nExecution timed out.",
                duration_seconds=duration,
                timed_out=True,
            )
        except Exception as exc:
            duration = round(time.monotonic() - start_time, 3)
            return ContainerExecutionResult(
                exit_code=1,
                stdout="",
                stderr=str(exc),
                duration_seconds=duration,
                timed_out=False,
                error_message=str(exc),
            )
