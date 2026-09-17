"""Deterministic technology, framework, and build tool detection.

Scans repository directory trees and manifest/dependency files (package.json,
requirements.txt, pyproject.toml, Pipfile, pom.xml, etc.) to identify languages,
runtimes, frameworks, and testing tools without invoking any LLM or external process.
"""

import json
import re
from typing import Dict, List, Optional, Set, Tuple

from app.context.models import ProjectInfo, TechnologyInfo

# Known Python libraries and frameworks
PYTHON_LIBRARIES: Dict[str, Tuple[str, str]] = {
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
    "scipy": ("SciPy", "framework"),
    "scikit-learn": ("scikit-learn", "framework"),
}

# Known JavaScript/TypeScript packages
JS_PACKAGES: Dict[str, Tuple[str, str]] = {
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

# Known Java packages / dependencies
JAVA_PACKAGES: Dict[str, Tuple[str, str]] = {
    "spring-boot": ("Spring Boot", "framework"),
    "spring-core": ("Spring", "framework"),
    "junit": ("JUnit", "testing"),
    "testng": ("TestNG", "testing"),
    "hibernate": ("Hibernate", "framework"),
    "lombok": ("Lombok", "framework"),
    "quarkus": ("Quarkus", "framework"),
    "micronaut": ("Micronaut", "framework"),
}

# Signatures for build manifests found in directory tree
MANIFEST_SIGNATURES: Dict[str, Tuple[str, str, str, str, str]] = {
    # filename: (display_name, category, language, package_manager, source_file)
    "package.json": ("Node.js / npm", "package_manager", "javascript", "npm", "package.json"),
    "package-lock.json": ("npm", "package_manager", "javascript", "npm", "package-lock.json"),
    "yarn.lock": ("Yarn", "package_manager", "javascript", "yarn", "yarn.lock"),
    "pnpm-lock.yaml": ("pnpm", "package_manager", "javascript", "pnpm", "pnpm-lock.yaml"),
    "requirements.txt": ("Python (pip)", "package_manager", "python", "pip", "requirements.txt"),
    "pyproject.toml": ("Python (pyproject)", "package_manager", "python", "pip", "pyproject.toml"),
    "pipfile": ("Pipenv", "package_manager", "python", "pipenv", "Pipfile"),
    "poetry.lock": ("Poetry", "package_manager", "python", "poetry", "poetry.lock"),
    "pom.xml": ("Maven", "build", "java", "maven", "pom.xml"),
    "build.gradle": ("Gradle", "build", "java", "gradle", "build.gradle"),
    "build.gradle.kts": ("Gradle (Kotlin)", "build", "java", "gradle", "build.gradle.kts"),
    "cargo.toml": ("Cargo / Rust", "package_manager", "rust", "cargo", "Cargo.toml"),
    "go.mod": ("Go Modules", "package_manager", "go", "go modules", "go.mod"),
    "gemfile": ("Bundler / Ruby", "package_manager", "ruby", "bundler", "Gemfile"),
    "composer.json": ("Composer / PHP", "package_manager", "php", "composer", "composer.json"),
    "dockerfile": ("Docker", "runtime", "", "", "Dockerfile"),
    "docker-compose.yml": ("Docker Compose", "runtime", "", "", "docker-compose.yml"),
    "docker-compose.yaml": ("Docker Compose", "runtime", "", "", "docker-compose.yaml"),
    "tsconfig.json": ("TypeScript", "language", "typescript", "", "tsconfig.json"),
}


def parse_requirements_txt(content: str, filename: str = "requirements.txt") -> List[TechnologyInfo]:
    """Parse python requirements.txt file contents for known libraries and versions."""
    technologies: List[TechnologyInfo] = []
    seen: set[str] = set()

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue

        match = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)$", line)
        if not match:
            continue

        pkg_raw, version_raw = match.groups()
        pkg_key = pkg_raw.lower().replace("_", "-")
        version = version_raw.strip() if version_raw.strip() else None

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


def parse_pyproject_toml(content: str, filename: str = "pyproject.toml") -> List[TechnologyInfo]:
    """Parse Python pyproject.toml contents for known dependencies without external parser."""
    technologies: List[TechnologyInfo] = []
    seen: set[str] = set()

    # Match lines like "fastapi>=0.100.0" or fastapi = "^0.100.0"
    for line in content.splitlines():
        line = line.strip().strip(",").strip('"').strip("'")
        if not line or line.startswith("#") or line.startswith("["):
            continue

        # Look for key in line
        for key, (display_name, category) in PYTHON_LIBRARIES.items():
            if re.search(rf"\b{re.escape(key)}\b", line, re.IGNORECASE):
                if display_name not in seen:
                    seen.add(display_name)
                    technologies.append(
                        TechnologyInfo(
                            name=display_name,
                            category=category,
                            detected_from=filename,
                            version=None,
                        )
                    )

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


def parse_pom_xml(content: str, filename: str = "pom.xml") -> List[TechnologyInfo]:
    """Parse Maven pom.xml contents for known Java frameworks without external XML parser."""
    technologies: List[TechnologyInfo] = []
    seen: set[str] = set()

    for key, (display_name, category) in JAVA_PACKAGES.items():
        if key in content.lower():
            if display_name not in seen:
                seen.add(display_name)
                technologies.append(
                    TechnologyInfo(
                        name=display_name,
                        category=category,
                        detected_from=filename,
                        version=None,
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
    Returns categorized TechnologyInfo items.
    """
    detected: List[TechnologyInfo] = []
    seen_names: Set[str] = set()
    manifest_contents = manifest_contents or {}

    # 1. Inspect directory structure for manifest files
    for path in directory_paths:
        filename = path.split("/")[-1].lower()
        if filename in MANIFEST_SIGNATURES:
            name, category, _, _, source_file = MANIFEST_SIGNATURES[filename]
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
        if fname == "package.json":
            for t in parse_package_json(content, filename=manifest_path):
                if t.name not in seen_names:
                    seen_names.add(t.name)
                    detected.append(t)
        elif fname in ("requirements.txt", "requirements-dev.txt", "requirements-test.txt", "pipfile"):
            for t in parse_requirements_txt(content, filename=manifest_path):
                if t.name not in seen_names:
                    seen_names.add(t.name)
                    detected.append(t)
        elif fname == "pyproject.toml":
            for t in parse_pyproject_toml(content, filename=manifest_path):
                if t.name not in seen_names:
                    seen_names.add(t.name)
                    detected.append(t)
        elif fname == "pom.xml":
            for t in parse_pom_xml(content, filename=manifest_path):
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


def build_project_info(
    directory_paths: List[str],
    manifest_contents: Optional[Dict[str, str]] = None,
    github_languages: Optional[Dict[str, int]] = None,
    description: Optional[str] = None,
) -> ProjectInfo:
    """
    Extract structured ProjectInfo matching Section 7 and 11 requirements:
    {
        "description": "...",
        "languages": ["python"],
        "frameworks": ["FastAPI"],
        "package_managers": ["pip"]
    }
    """
    manifest_contents = manifest_contents or {}
    languages: Set[str] = set()
    frameworks: Set[str] = set()
    package_managers: Set[str] = set()

    # 1. From directory structure signatures
    for path in directory_paths:
        fname = path.split("/")[-1].lower()
        if fname in MANIFEST_SIGNATURES:
            _, _, lang, pm, _ = MANIFEST_SIGNATURES[fname]
            if lang:
                languages.add(lang.lower())
            if pm:
                package_managers.add(pm.lower())

        # Also infer from file extensions
        if fname.endswith(".py"):
            languages.add("python")
        elif fname.endswith((".js", ".jsx", ".mjs")):
            languages.add("javascript")
        elif fname.endswith((".ts", ".tsx")):
            languages.add("typescript")
            languages.add("javascript")
        elif fname.endswith((".java", ".kt")):
            languages.add("java")
        elif fname.endswith(".rs"):
            languages.add("rust")
        elif fname.endswith(".go"):
            languages.add("go")

    # 2. From GitHub Languages
    if github_languages:
        for lang in github_languages:
            languages.add(lang.lower())

    # 3. From detailed technology detection
    techs = detect_technologies(directory_paths, manifest_contents, github_languages)
    for t in techs:
        if t.category in ("framework", "testing", "runtime"):
            frameworks.add(t.name)
        elif t.category == "package_manager":
            package_managers.add(t.name.lower())
        elif t.category == "language":
            languages.add(t.name.lower())

    return ProjectInfo(
        description=description,
        languages=sorted(languages),
        frameworks=sorted(frameworks),
        package_managers=sorted(package_managers),
    )
