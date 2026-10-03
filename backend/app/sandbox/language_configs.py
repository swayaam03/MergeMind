"""Language-specific sandbox configurations and command templates for verification.

Supports Python, JavaScript/TypeScript, and Java.
Configures safe Docker images, syntax verification commands, compilation steps,
and test execution runners.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings
from app.schemas.verification import LanguageType


@dataclass(frozen=True)
class LanguageConfig:
    """Configuration definition for a programming language environment."""

    name: LanguageType
    docker_image: str
    extensions: List[str]
    syntax_command: List[str]
    compile_command: Optional[List[str]] = None
    default_test_command: Optional[List[str]] = None
    test_file_patterns: List[str] = field(default_factory=list)
    manifest_files: List[str] = field(default_factory=list)


# Language configurations for supported targets
LANGUAGE_CONFIGS: Dict[str, LanguageConfig] = {
    "python": LanguageConfig(
        name="python",
        docker_image=settings.SANDBOX_IMAGE_PYTHON,
        extensions=[".py", ".pyw"],
        syntax_command=["python", "-m", "py_compile"],
        compile_command=None,
        default_test_command=["python", "-m", "pytest", "-v"],
        test_file_patterns=["test_*.py", "*_test.py", "tests/"],
        manifest_files=["pyproject.toml", "requirements.txt", "setup.py", "setup.cfg"],
    ),
    "javascript": LanguageConfig(
        name="javascript",
        docker_image=settings.SANDBOX_IMAGE_JAVASCRIPT,
        extensions=[".js", ".mjs", ".cjs", ".jsx"],
        syntax_command=["node", "--check"],
        compile_command=None,
        default_test_command=["npm", "test", "--", "--passWithNoTests"],
        test_file_patterns=["*.test.js", "*.spec.js", "test/", "__tests__/"],
        manifest_files=["package.json"],
    ),
    "typescript": LanguageConfig(
        name="typescript",
        docker_image=settings.SANDBOX_IMAGE_JAVASCRIPT,
        extensions=[".ts", ".tsx"],
        syntax_command=["node", "--check"],  # Or tsc --noEmit when installed
        compile_command=None,
        default_test_command=["npm", "test"],
        test_file_patterns=["*.test.ts", "*.spec.ts", "*.test.tsx", "*.spec.tsx", "test/", "__tests__/"],
        manifest_files=["package.json", "tsconfig.json"],
    ),
    "java": LanguageConfig(
        name="java",
        docker_image=settings.SANDBOX_IMAGE_JAVA,
        extensions=[".java"],
        syntax_command=["javac"],
        compile_command=["javac"],
        default_test_command=["mvn", "test", "-B"],
        test_file_patterns=["*Test.java", "*Tests.java", "src/test/"],
        manifest_files=["pom.xml", "build.gradle", "build.gradle.kts"],
    ),
}


def get_language_config(language: str) -> Optional[LanguageConfig]:
    """Retrieve language configuration by name or alias."""
    norm = (language or "").strip().lower()
    return LANGUAGE_CONFIGS.get(norm)


def detect_file_language(file_path: str) -> LanguageType:
    """Detect language of a file based on file extension."""
    ext = Path(file_path).suffix.lower()
    for lang, cfg in LANGUAGE_CONFIGS.items():
        if ext in cfg.extensions:
            return cfg.name
    return "unknown"


def detect_workspace_test_framework(workspace_dir: Path, language: LanguageType) -> Optional[str]:
    """
    Inspect an isolated workspace to detect existing test suites and frameworks.
    """
    if not workspace_dir.exists():
        return None

    if language == "python":
        if (workspace_dir / "pytest.ini").exists() or (workspace_dir / "conftest.py").exists():
            return "pytest"
        if (workspace_dir / "setup.cfg").exists() or (workspace_dir / "pyproject.toml").exists():
            return "pytest"
        # Check if tests directory exists or any test files exist
        if (workspace_dir / "tests").is_dir() or (workspace_dir / "test").is_dir():
            return "pytest"
        for _ in workspace_dir.glob("**/test_*.py"):
            return "pytest"

    elif language in ("javascript", "typescript"):
        pkg_json = workspace_dir / "package.json"
        if pkg_json.exists():
            try:
                import json
                content = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
                scripts = content.get("scripts", {})
                if "test" in scripts:
                    test_cmd = scripts["test"]
                    if "jest" in test_cmd:
                        return "jest"
                    if "mocha" in test_cmd:
                        return "mocha"
                    if "vitest" in test_cmd:
                        return "vitest"
                    return "npm-test"
            except Exception:
                pass
        for _ in workspace_dir.glob("**/*.test.js"):
            return "jest"
        for _ in workspace_dir.glob("**/*.spec.js"):
            return "jest"

    elif language == "java":
        if (workspace_dir / "pom.xml").exists():
            return "maven"
        if (workspace_dir / "build.gradle").exists() or (workspace_dir / "build.gradle.kts").exists():
            return "gradle"

    return None
