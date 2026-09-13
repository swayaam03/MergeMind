"""Deterministic technology, framework, and build tool detection.

Scans repository directory trees and manifest/dependency files (package.json,
requirements.txt, pyproject.toml, pom.xml, etc.) to identify languages,
runtimes, frameworks, and testing tools without invoking any LLM.
"""

import json
import re
from typing import Dict, List, Optional

from app.context.models import TechnologyInfo

# Known Python libraries and frameworks
PYTHON_LIBRARIES: Dict[str, tuple[str, str]] = {
    "fastapi": ("FastAPI", "framework"),
    "flask": ("Flask", "framework"),
    "django": ("Django", "framework"),
    "pytest": ("pytest", "testing"),
    "unittest": ("unittest", "testing"),
    "pydantic": ("Pydantic", "framework"),
    "sqlalchemy": ("SQLAlchemy", "framework"),
    "celery": ("Celery", "framework"),
    "torch": ("PyTorch", "framework"),
    "tensorflow": ("TensorFlow", "framework"),
    "pandas": ("Pandas", "framework"),
    "numpy": ("NumPy", "framework"),
    "httpx": ("HTTPX", "framework"),
    "requests": ("Requests", "framework"),
    "uvicorn": ("Uvicorn", "runtime"),
    "gunicorn": ("Gunicorn", "runtime"),
}

# Known JavaScript/TypeScript packages
JS_PACKAGES: Dict[str, tuple[str, str]] = {
    "react": ("React", "framework"),
    "react-dom": ("React DOM", "framework"),
    "react-native": ("React Native", "framework"),
    "vue": ("Vue.js", "framework"),
    "@angular/core": ("Angular", "framework"),
    "next": ("Next.js", "framework"),
    "nuxt": ("Nuxt.js", "framework"),
    "svelte": ("Svelte", "framework"),
    "express": ("Express", "framework"),
    "koa": ("Koa", "framework"),
    "nest": ("NestJS", "framework"),
    "@nestjs/core": ("NestJS", "framework"),
    "vite": ("Vite", "build"),
    "webpack": ("Webpack", "build"),
    "esbuild": ("esbuild", "build"),
    "rollup": ("Rollup", "build"),
    "jest": ("Jest", "testing"),
    "mocha": ("Mocha", "testing"),
    "vitest": ("Vitest", "testing"),
    "cypress": ("Cypress", "testing"),
    "tailwindcss": ("Tailwind CSS", "framework"),
    "typescript": ("TypeScript", "language"),
}

# Signatures for build manifests found in directory tree
MANIFEST_SIGNATURES: Dict[str, tuple[str, str, str]] = {
    "package.json": ("Node.js / npm", "package_manager", "package.json"),
    "package-lock.json": ("npm", "package_manager", "package-lock.json"),
    "yarn.lock": ("Yarn", "package_manager", "yarn.lock"),
    "pnpm-lock.yaml": ("pnpm", "package_manager", "pnpm-lock.yaml"),
    "requirements.txt": ("Python (pip)", "package_manager", "requirements.txt"),
    "pyproject.toml": ("Python (pyproject)", "package_manager", "pyproject.toml"),
    "pipfile": ("Pipenv", "package_manager", "Pipfile"),
    "poetry.lock": ("Poetry", "package_manager", "poetry.lock"),
    "pom.xml": ("Maven", "build", "pom.xml"),
    "build.gradle": ("Gradle", "build", "build.gradle"),
    "build.gradle.kts": ("Gradle (Kotlin)", "build", "build.gradle.kts"),
    "cargo.toml": ("Cargo / Rust", "package_manager", "Cargo.toml"),
    "go.mod": ("Go Modules", "package_manager", "go.mod"),
    "gemfile": ("Bundler / Ruby", "package_manager", "Gemfile"),
    "composer.json": ("Composer / PHP", "package_manager", "composer.json"),
    "dockerfile": ("Docker", "runtime", "Dockerfile"),
    "docker-compose.yml": ("Docker Compose", "runtime", "docker-compose.yml"),
    "docker-compose.yaml": ("Docker Compose", "runtime", "docker-compose.yaml"),
    "tsconfig.json": ("TypeScript", "language", "tsconfig.json"),
}


def parse_requirements_txt(content: str, filename: str = "requirements.txt") -> List[TechnologyInfo]:
    """Parse python requirements.txt file contents for known libraries and versions."""
    technologies: List[TechnologyInfo] = []
    seen: set[str] = set()

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue

        # Match package name and optional version constraint (e.g. package>=1.0.0, package==2.0)
        match = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)$", line)
        if not match:
            continue

        pkg_raw, version_raw = match.groups()
        pkg_key = pkg_raw.lower().replace("_", "-")
        version = version_raw.strip() if version_raw.strip() else None

        # Check in known libraries (normalize key)
        normalized_key = pkg_key.replace("-", "")
        for key, (display_name, category) in PYTHON_LIBRARIES.items():
            if key == normalized_key or key == pkg_key:
                if display_name not in seen:
                    seen.add(display_name)
                    technologies.append(
                        TechnologyInfo(
                            name=display_name,
                            category=category,
                            detected_from=filename,
                            version=version,
                        )
                    )
                break

    return technologies


def parse_package_json(content: str, filename: str = "package.json") -> List[TechnologyInfo]:
    """Parse Node.js package.json file contents for known dependencies and devDependencies."""
    technologies: List[TechnologyInfo] = []
    seen: set[str] = set()

    try:
        data = json.loads(content)
    except Exception:
        return technologies

    if not isinstance(data, dict):
        return technologies

    deps = {}
    if isinstance(data.get("dependencies"), dict):
        deps.update(data["dependencies"])
    if isinstance(data.get("devDependencies"), dict):
        deps.update(data["devDependencies"])

    for pkg_name, ver in deps.items():
        pkg_lower = pkg_name.lower()
        if pkg_lower in JS_PACKAGES:
            display_name, category = JS_PACKAGES[pkg_lower]
            if display_name not in seen:
                seen.add(display_name)
                technologies.append(
                    TechnologyInfo(
                        name=display_name,
                        category=category,
                        detected_from=filename,
                        version=str(ver) if ver else None,
                    )
                )

    return technologies


def detect_technologies(
    directory_paths: List[str],
    manifest_contents: Optional[Dict[str, str]] = None,
    github_languages: Optional[Dict[str, int]] = None,
) -> List[TechnologyInfo]:
    """
    Deterministically detect technologies from repository tree and manifest contents.

    1. Checks repository file names against MANIFEST_SIGNATURES.
    2. Parses dependency file contents (package.json, requirements.txt).
    3. Incorporates GitHub language breakdown.
    4. De-duplicates and sorts findings.
    """
    detected: List[TechnologyInfo] = []
    seen_names: set[str] = set()
    manifest_contents = manifest_contents or {}

    # 1. Inspect directory structure for manifest files
    for path in directory_paths:
        filename = path.split("/")[-1].lower()
        if filename in MANIFEST_SIGNATURES:
            name, category, source_file = MANIFEST_SIGNATURES[filename]
            if name not in seen_names:
                seen_names.add(name)
                detected.append(
                    TechnologyInfo(
                        name=name,
                        category=category,
                        detected_from=path,
                        version=None,
                    )
                )

    # 2. Inspect manifest file contents for frameworks/libraries
    for manifest_path, content in manifest_contents.items():
        fname = manifest_path.split("/")[-1].lower()
        if fname in ("package.json",):
            pkg_techs = parse_package_json(content, filename=manifest_path)
            for t in pkg_techs:
                if t.name not in seen_names:
                    seen_names.add(t.name)
                    detected.append(t)
        elif fname in ("requirements.txt", "requirements-dev.txt", "requirements-test.txt"):
            req_techs = parse_requirements_txt(content, filename=manifest_path)
            for t in req_techs:
                if t.name not in seen_names:
                    seen_names.add(t.name)
                    detected.append(t)

    # 3. Add GitHub languages if present
    if github_languages:
        for lang_name in sorted(github_languages.keys(), key=lambda l: github_languages[l], reverse=True):
            if lang_name not in seen_names:
                seen_names.add(lang_name)
                detected.append(
                    TechnologyInfo(
                        name=lang_name,
                        category="language",
                        detected_from="GitHub Language API",
                        version=None,
                    )
                )

    return detected
