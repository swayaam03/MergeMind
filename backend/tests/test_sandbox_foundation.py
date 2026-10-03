"""Unit tests for Phase 5 Tasks 1 & 2: Sandbox Foundation & Merge Proposal Application."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.sandbox.docker_runner import (
    DockerSandboxRunner,
    DockerUnavailableError,
    sanitize_container_env,
    truncate_output,
)
from app.sandbox.language_configs import (
    detect_file_language,
    detect_workspace_test_framework,
    get_language_config,
)
from app.sandbox.merge_workspace import (
    apply_merge_to_workspace,
    normalize_code_content,
    prepare_proposed_workspace,
)
from app.sandbox.workspace import (
    IsolatedWorkspace,
    WorkspaceSecurityError,
    is_forbidden_file,
    is_path_safe,
    temporary_workspace,
)
from app.schemas.verification import DockerContainerConfig


# ============================================================================
# Task 1 Tests: Isolated Workspace & Boundary Security
# ============================================================================


def test_isolated_workspace_lifecycle():
    """Test creation, file writing, reading, listing, and cleanup of an isolated workspace."""
    workspace = IsolatedWorkspace(prefix="test_mm_ws_")
    ws_path = workspace.create()

    assert ws_path.exists()
    assert ws_path.is_dir()

    # Write file
    file_path = workspace.write_file("sub/dir/test.py", "print('hello world')\n")
    assert file_path.exists()
    assert workspace.read_file("sub/dir/test.py") == "print('hello world')\n"

    # List files
    files = workspace.list_files()
    assert "sub/dir/test.py" in files

    # Cleanup
    workspace.cleanup()
    assert not ws_path.exists()


def test_isolated_workspace_context_manager():
    """Test that context manager guarantees cleanup even on error."""
    recorded_path = None
    try:
        with temporary_workspace() as ws:
            recorded_path = ws.path
            assert recorded_path is not None
            assert recorded_path.exists()
            ws.write_file("test.txt", "data")
            assert ws.read_file("test.txt") == "data"
            raise ValueError("Intentional error inside workspace block")
    except ValueError:
        pass

    assert recorded_path is not None
    assert not recorded_path.exists()


def test_path_traversal_prevention():
    """Verify that writing or reading outside workspace boundaries raises WorkspaceSecurityError."""
    with temporary_workspace() as ws:
        with pytest.raises(WorkspaceSecurityError):
            ws.write_file("../escape.txt", "malicious payload")

        with pytest.raises(WorkspaceSecurityError):
            ws.write_file("foo/../../escape.txt", "malicious payload")

        with pytest.raises(WorkspaceSecurityError):
            ws.read_file("../escape.txt")


def test_is_path_safe():
    """Test boundary validation utility function."""
    base = Path("/safe/workspace")
    assert is_path_safe(base, Path("/safe/workspace/sub/file.py"))
    assert is_path_safe(base, Path("/safe/workspace/file.py"))
    assert not is_path_safe(base, Path("/safe/other_dir/file.py"))
    assert not is_path_safe(base, Path("/etc/passwd"))


def test_is_forbidden_file():
    """Test sensitive file identification filters."""
    assert is_forbidden_file(".env")
    assert is_forbidden_file(".env.local")
    assert is_forbidden_file(".env.production")
    assert is_forbidden_file("id_rsa")
    assert is_forbidden_file("server.key")
    assert is_forbidden_file("certificate.pem")
    assert is_forbidden_file(".git")
    assert is_forbidden_file("credentials.json")

    # Safe files
    assert not is_forbidden_file("main.py")
    assert not is_forbidden_file("package.json")
    assert not is_forbidden_file("README.md")
    assert not is_forbidden_file("test_calc.py")


# ============================================================================
# Task 1 Tests: Docker Sandbox Runner & Security Constraints
# ============================================================================


def test_sanitize_container_env():
    """Ensure host secrets and credentials are completely stripped from container environment."""
    raw_env = {
        "OPENROUTER_API_KEY": "sk-or-v1-secret12345",
        "GITHUB_TOKEN": "ghp_superSecretToken999",
        "AWS_SECRET_ACCESS_KEY": "secret_aws_key",
        "APP_PASSWORD": "my_password",
        "SAFE_PARAM": "12345",
        "FEATURE_FLAG": "enabled",
    }

    clean_env = sanitize_container_env(raw_env)

    # Forbidden keys must be absent
    assert "OPENROUTER_API_KEY" not in clean_env
    assert "GITHUB_TOKEN" not in clean_env
    assert "AWS_SECRET_ACCESS_KEY" not in clean_env
    assert "APP_PASSWORD" not in clean_env

    # Safe parameters must be retained
    assert clean_env["SAFE_PARAM"] == "12345"
    assert clean_env["FEATURE_FLAG"] == "enabled"

    # Default isolation variables must be present
    assert clean_env["CI"] == "true"
    assert clean_env["PYTHONUNBUFFERED"] == "1"


def test_truncate_output():
    """Test truncation of massive container outputs to prevent memory overflow."""
    short_text = "Standard test output"
    assert truncate_output(short_text, max_bytes=100) == short_text

    long_text = "x" * 500
    truncated = truncate_output(long_text, max_bytes=50)
    assert len(truncated.encode("utf-8")) < 200
    assert "Truncated by MergeMind sandbox" in truncated


def test_docker_runner_get_status():
    """Test DockerSandboxRunner status reporting."""
    runner = DockerSandboxRunner()
    status = runner.get_status()

    assert "available" in status
    assert "network_mode" in status
    assert status["network_mode"] == "none"
    assert "cpu_limit" in status
    assert "memory_limit" in status


def test_docker_runner_raises_when_unavailable():
    """Ensure runner raises DockerUnavailableError if daemon is offline."""
    runner = DockerSandboxRunner()
    with patch.object(runner, "is_available", return_value=False):
        with temporary_workspace() as ws:
            cfg = DockerContainerConfig(
                image="python:3.11-slim",
                command=["python", "--version"],
            )
            with pytest.raises(DockerUnavailableError):
                runner.run_in_sandbox(ws.path, cfg)


def test_docker_runner_sdk_execution_lifecycle_mocked():
    """Test container creation, execution, log collection, and cleanup lifecycle via SDK."""
    runner = DockerSandboxRunner()

    mock_container = MagicMock()
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.return_value = b"Test passed\n"

    mock_client = MagicMock()
    mock_client.containers.create.return_value = mock_container
    mock_docker = MagicMock()
    mock_docker.from_env.return_value = mock_client

    with patch.object(runner, "is_available", return_value=True):
        with patch.dict("sys.modules", {"docker": mock_docker}):
            with temporary_workspace() as ws:
                cfg = DockerContainerConfig(
                    image="python:3.11-slim",
                    command=["pytest"],
                    timeout_seconds=30,
                    cpu_limit=1.0,
                    memory_limit="512m",
                    pids_limit=100,
                    network_mode="none",
                )

                result = runner.run_in_sandbox(ws.path, cfg)

                # Verify container creation parameters
                mock_client.containers.create.assert_called_once()
                call_kwargs = mock_client.containers.create.call_args[1]
                assert call_kwargs["image"] == "python:3.11-slim"
                assert call_kwargs["network_mode"] == "none"
                assert call_kwargs["mem_limit"] == "512m"
                assert call_kwargs["pids_limit"] == 100
                assert call_kwargs["nano_cpus"] == 1_000_000_000

                # Verify container start and cleanup
                mock_container.start.assert_called_once()
                mock_container.remove.assert_called_once_with(force=True)

                assert result.exit_code == 0
                assert result.stdout == "Test passed\n"
                assert not result.timed_out
                assert result.is_success


def test_docker_runner_timeout_handling_mocked():
    """Test timeout handling and SIGKILL invocation."""
    runner = DockerSandboxRunner()

    mock_container = MagicMock()
    mock_container.wait.side_effect = Exception("Operation timed out")
    mock_container.logs.side_effect = [b"Partial output before timeout", b"Process stalled"]

    mock_client = MagicMock()
    mock_client.containers.create.return_value = mock_container

    mock_docker = MagicMock()
    mock_docker.from_env.return_value = mock_client

    with patch.object(runner, "is_available", return_value=True):
        with patch.dict("sys.modules", {"docker": mock_docker}):
            with temporary_workspace() as ws:
                cfg = DockerContainerConfig(
                    image="python:3.11-slim",
                    command=["pytest"],
                    timeout_seconds=5,
                )

                result = runner.run_in_sandbox(ws.path, cfg)

                # Container should be killed on timeout
                mock_container.kill.assert_called_once()
                # Container must be removed
                mock_container.remove.assert_called_once_with(force=True)

                assert result.timed_out is True
                assert result.exit_code == 124
                assert "Partial output" in result.stdout


# ============================================================================
# Task 2 Tests: Merge Proposal Application & Workspace Preparation
# ============================================================================


def test_normalize_code_content():
    """Test line-ending normalization and trailing newline."""
    assert normalize_code_content("line1\r\nline2\r\n") == "line1\nline2\n"
    assert normalize_code_content("line1\rline2") == "line1\nline2\n"
    assert normalize_code_content("") == ""


def test_apply_merge_to_workspace_in_memory():
    """Test applying a proposed merge on an in-memory repository structure."""
    source_files = {
        "src/calculator.py": "def add(a, b): return a - b  # buggy old version\n",
        "tests/test_calculator.py": "from src.calculator import add\ndef test_add(): assert add(1, 2) == 3\n",
        "README.md": "# Calculator Project\n",
        ".env": "SECRET_KEY=leak_me\n",  # Must be filtered out
    }

    proposed_code = "def add(a, b):\n    return a + b\n"

    with prepare_proposed_workspace(
        target_file="src/calculator.py",
        merged_code=proposed_code,
        source_files=source_files,
    ) as prop_ws:
        # Check that target file was replaced with proposed code
        applied_content = prop_ws.workspace.read_file("src/calculator.py")
        assert applied_content == "def add(a, b):\n    return a + b\n"

        # Check that other repository files were preserved
        assert prop_ws.workspace.read_file("tests/test_calculator.py") == source_files["tests/test_calculator.py"]
        assert prop_ws.workspace.read_file("README.md") == source_files["README.md"]

        # Check that secret files were excluded
        assert ".env" not in prop_ws.workspace.list_files()

        # Check metadata
        info = prop_ws.info()
        assert info.target_file == "src/calculator.py"
        assert info.language == "python"
        assert info.has_test_suite is True
        assert info.test_framework == "pytest"
        assert info.file_count == 3  # calculator.py, test_calculator.py, README.md


def test_apply_merge_to_workspace_from_local_dir(tmp_path):
    """Test applying a proposed merge copying from a local directory on disk."""
    # Set up source repo on disk
    src_repo = tmp_path / "my_project"
    src_repo.mkdir()
    (src_repo / "src").mkdir()
    (src_repo / "tests").mkdir()
    (src_repo / ".git").mkdir()

    (src_repo / "src" / "service.py").write_text("old code\n")
    (src_repo / "tests" / "test_service.py").write_text("import pytest\n")
    (src_repo / ".env").write_text("API_KEY=top_secret\n")
    (src_repo / ".git" / "config").write_text("[core]\n")

    proposed_code = "new merged code\n"

    with prepare_proposed_workspace(
        target_file="src/service.py",
        merged_code=proposed_code,
        source_repo_path=src_repo,
    ) as prop_ws:
        # Check target replacement
        assert prop_ws.workspace.read_file("src/service.py") == proposed_code

        # Check preserved structure
        assert prop_ws.workspace.read_file("tests/test_service.py") == "import pytest\n"

        # Check secret / VCS exclusions
        files = prop_ws.workspace.list_files()
        assert not any(".env" in f for f in files)
        assert not any(".git" in f for f in files)


def test_apply_merge_invalid_target_path():
    """Ensure path traversal in target_file is rejected."""
    with pytest.raises(WorkspaceSecurityError):
        apply_merge_to_workspace(
            target_file="../escape.py",
            merged_code="print('escape')",
            source_files={"test.py": "1"},
        )


def test_language_detection():
    """Test language detection for various file extensions."""
    assert detect_file_language("main.py") == "python"
    assert detect_file_language("src/component.jsx") == "javascript"
    assert detect_file_language("src/index.ts") == "typescript"
    assert detect_file_language("App.java") == "java"
    assert detect_file_language("data.csv") == "unknown"


def test_get_language_config():
    """Test language config retrieval."""
    py_cfg = get_language_config("python")
    assert py_cfg is not None
    assert py_cfg.name == "python"
    assert "py_compile" in " ".join(py_cfg.syntax_command)

    js_cfg = get_language_config("javascript")
    assert js_cfg is not None
    assert js_cfg.name == "javascript"

    java_cfg = get_language_config("java")
    assert java_cfg is not None
    assert java_cfg.name == "java"
    assert "javac" in " ".join(java_cfg.syntax_command)

    assert get_language_config("unknown_lang") is None
