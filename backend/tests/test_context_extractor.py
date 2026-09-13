"""Unit and integration tests for repository context extraction."""

import base64
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.context.github_content import (
    fetch_directory_tree,
    fetch_file_content,
    fetch_languages,
    fetch_readme,
)
from app.context.models import FilePreview, RepositoryContext, TechnologyInfo
from app.context.relevance import find_relevant_paths, is_ignored_path
from app.context.technology import (
    detect_technologies,
    parse_package_json,
    parse_requirements_txt,
)
from app.context.extractor import extract_repository_context
from app.main import app


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


# ---------------------------------------------------------------------------
# 1. Pydantic Models Validation Tests
# ---------------------------------------------------------------------------

def test_file_preview_model():
    """Verify FilePreview serializes and enforces structure."""
    preview = FilePreview(
        path="src/utils.py",
        content="def helper(): pass",
        size=18,
        truncated=False,
        reason="same_directory",
    )
    assert preview.path == "src/utils.py"
    assert preview.content == "def helper(): pass"
    assert preview.size == 18
    assert preview.truncated is False
    assert preview.reason == "same_directory"


def test_technology_info_model():
    """Verify TechnologyInfo stores categorized technology details."""
    tech = TechnologyInfo(
        name="FastAPI",
        category="framework",
        detected_from="requirements.txt",
        version=">=0.115.0",
    )
    assert tech.name == "FastAPI"
    assert tech.category == "framework"
    assert tech.detected_from == "requirements.txt"
    assert tech.version == ">=0.115.0"


def test_repository_context_model():
    """Verify RepositoryContext holds all elements with defaults."""
    ctx = RepositoryContext(
        repository="owner/repo",
        base_ref="main",
        head_ref="feature",
        readme_preview="# Project Title",
        directory_structure=["main.py", "README.md"],
        tree_truncated=False,
        detected_technologies=[
            TechnologyInfo(name="Python", category="language", detected_from="GitHub Language API")
        ],
        languages={"Python": 4200},
        relevant_files=[
            FilePreview(path="utils.py", content="...", size=3, truncated=False)
        ],
        total_files_examined=2,
    )
    data = ctx.model_dump()
    assert data["repository"] == "owner/repo"
    assert data["base_ref"] == "main"
    assert data["head_ref"] == "feature"
    assert len(data["directory_structure"]) == 2
    assert data["total_files_examined"] == 2


# ---------------------------------------------------------------------------
# 2. Technology Detection Tests
# ---------------------------------------------------------------------------

def test_parse_requirements_txt():
    """Verify python requirements.txt parsing for frameworks, libraries, and versions."""
    content = """
    # Dependencies
    fastapi>=0.115.0
    uvicorn==0.23.0
    pydantic~=2.0
    pytest>=8.0.0
    requests
    unknown-custom-package==1.0
    """
    techs = parse_requirements_txt(content, "requirements.txt")
    names = {t.name: t for t in techs}

    assert "FastAPI" in names
    assert names["FastAPI"].category == "framework"
    assert names["FastAPI"].version == ">=0.115.0"

    assert "Uvicorn" in names
    assert names["Uvicorn"].category == "runtime"

    assert "Pydantic" in names
    assert names["Pydantic"].category == "framework"

    assert "pytest" in names
    assert names["pytest"].category == "testing"

    assert "Requests" in names
    assert names["Requests"].category == "framework"


def test_parse_package_json():
    """Verify package.json parsing for JS/TS frameworks, tools, and testing packages."""
    content = """{
        "name": "my-frontend",
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "tailwindcss": "^3.3.0"
        },
        "devDependencies": {
            "vite": "^4.4.5",
            "jest": "^29.0.0",
            "typescript": "^5.0.0"
        }
    }"""
    techs = parse_package_json(content, "package.json")
    names = {t.name: t for t in techs}

    assert "React" in names
    assert names["React"].category == "framework"
    assert names["React"].version == "^18.2.0"

    assert "Tailwind CSS" in names
    assert names["Tailwind CSS"].category == "framework"

    assert "Vite" in names
    assert names["Vite"].category == "build"

    assert "Jest" in names
    assert names["Jest"].category == "testing"

    assert "TypeScript" in names
    assert names["TypeScript"].category == "language"


def test_detect_technologies_composite():
    """Verify combination of directory signatures, manifest contents, and language stats."""
    tree = [
        "Dockerfile",
        "package.json",
        "src/index.js",
        "backend/Cargo.toml",
    ]
    manifests = {
        "package.json": '{"dependencies": {"express": "^4.18.2"}}',
    }
    github_langs = {"JavaScript": 25000, "Rust": 15000}

    techs = detect_technologies(tree, manifest_contents=manifests, github_languages=github_langs)
    names = {t.name for t in techs}

    assert "Docker" in names
    assert "Node.js / npm" in names
    assert "Cargo / Rust" in names
    assert "Express" in names
    assert "JavaScript" in names
    assert "Rust" in names


# ---------------------------------------------------------------------------
# 3. Relevance & Neighbor Discovery Tests
# ---------------------------------------------------------------------------

def test_ignored_path_detection():
    """Verify ignored directories are rejected."""
    assert is_ignored_path(".git/HEAD") is True
    assert is_ignored_path("node_modules/react/index.js") is True
    assert is_ignored_path("backend/__pycache__/app.pyc") is True
    assert is_ignored_path(".venv/bin/activate") is True
    assert is_ignored_path("src/components/Button.jsx") is False


def test_find_relevant_paths_prioritizes_tests_and_siblings():
    """Verify relevant files discover unit tests, siblings, and init files without conflicting files."""
    tree = [
        "calculator.py",
        "test_calculator.py",
        "utils.py",
        "__init__.py",
        "node_modules/bad.js",
        "other/file.py",
    ]
    conflicts = ["calculator.py"]

    relevant = find_relevant_paths(conflicts, tree, max_files=5)
    paths = [p[0] for p in relevant]

    # Matching test should be found first
    assert "test_calculator.py" in paths
    # Siblings and package init should be found
    assert "__init__.py" in paths
    assert "utils.py" in paths
    # Conflicting file itself must NEVER be included
    assert "calculator.py" not in paths
    # Ignored directories must NEVER be included
    assert "node_modules/bad.js" not in paths


# ---------------------------------------------------------------------------
# 4. GitHub Content Fetching Tests
# ---------------------------------------------------------------------------

def test_fetch_readme_success():
    """Verify README is fetched and base64-decoded properly."""
    raw_text = "# Test Project\n\nThis is a sample readme."
    b64_content = base64.b64encode(raw_text.encode("utf-8")).decode("ascii")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": b64_content,
        "encoding": "base64",
    }

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    readme = fetch_readme("owner", "repo", "token123", client=mock_client)
    assert readme == raw_text


def test_fetch_readme_not_found():
    """Verify 404 returns None without raising an exception."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    readme = fetch_readme("owner", "repo", "token123", client=mock_client)
    assert readme is None


def test_fetch_directory_tree_success():
    """Verify directory tree returns paths and truncation flag."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "truncated": False,
        "tree": [
            {"path": "app/main.py", "type": "blob"},
            {"path": "README.md", "type": "blob"},
            {"path": "app", "type": "tree"},
        ],
    }
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    paths, is_trunc = fetch_directory_tree("owner", "repo", "main", "token123", client=mock_client)
    assert len(paths) == 3
    assert "app/main.py" in paths
    assert is_trunc is False


def test_fetch_file_content_capping():
    """Verify large file content is capped to max_bytes with truncated=True."""
    long_text = "A" * 100
    b64 = base64.b64encode(long_text.encode("utf-8")).decode("ascii")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "type": "file",
        "size": 100,
        "encoding": "base64",
        "content": b64,
    }
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    content, size, truncated = fetch_file_content(
        "owner", "repo", "big.txt", "token123", max_bytes=20, client=mock_client
    )
    assert len(content) == 20
    assert size == 100
    assert truncated is True


# ---------------------------------------------------------------------------
# 5. Extraction Orchestrator Test
# ---------------------------------------------------------------------------

@patch("app.context.extractor.fetch_file_content")
@patch("app.context.extractor.fetch_directory_tree")
@patch("app.context.extractor.fetch_languages")
@patch("app.context.extractor.fetch_readme")
def test_extract_repository_context(
    mock_readme,
    mock_languages,
    mock_tree,
    mock_content,
):
    """Verify orchestrator ties together all components into a RepositoryContext."""
    mock_readme.return_value = "# My Project"
    mock_languages.return_value = {"Python": 1000}
    mock_tree.return_value = (
        ["calculator.py", "test_calculator.py", "requirements.txt"],
        False,
    )

    def fake_file_content(owner, repo, path, token, ref=None, max_bytes=None, client=None):
        if path == "requirements.txt":
            return ("fastapi>=0.115.0\npytest\n", 25, False)
        if path == "test_calculator.py":
            return ("def test_add(): assert 1 + 1 == 2\n", 35, False)
        return (None, 0, False)

    mock_content.side_effect = fake_file_content

    ctx = extract_repository_context(
        owner="test-owner",
        repo="test-repo",
        token="token123",
        base_ref="main",
        head_ref="feature",
        conflicting_files=["calculator.py"],
    )

    assert ctx.repository == "test-owner/test-repo"
    assert ctx.base_ref == "main"
    assert ctx.head_ref == "feature"
    assert ctx.readme_preview == "# My Project"
    assert ctx.tree_truncated is False
    assert len(ctx.directory_structure) == 3

    # Check detected technologies
    tech_names = {t.name for t in ctx.detected_technologies}
    assert "FastAPI" in tech_names
    assert "pytest" in tech_names

    # Check relevant files
    relevant_paths = [f.path for f in ctx.relevant_files]
    assert "test_calculator.py" in relevant_paths
    assert any("test_add" in f.content for f in ctx.relevant_files)


# ---------------------------------------------------------------------------
# 6. API Route Integration Tests
# ---------------------------------------------------------------------------

def test_context_endpoint_unauthorized(client):
    """Verify 401 when installation_id is missing from cookie, header, and query."""
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/1/context")
    assert response.status_code == 401
    assert "missing installation context" in response.json()["detail"].lower()


@patch("app.api.routes.context.extract_repository_context")
@patch("app.api.routes.context.get_pull_request_detail")
@patch("app.api.routes.context.get_installation_repositories")
@patch("app.api.routes.context.get_installation_access_token")
def test_context_endpoint_success(
    mock_token,
    mock_repos,
    mock_pr,
    mock_extract,
    client,
):
    """Verify successful context retrieval for an authorized installation."""
    mock_token.return_value = "ghs_test_token"
    mock_repos.return_value = [{"full_name": "test-owner/test-repo"}]
    mock_pr.return_value = {
        "number": 8,
        "base": {"ref": "main", "sha": "base123"},
        "head": {"ref": "test", "sha": "head123"},
    }
    mock_extract.return_value = RepositoryContext(
        repository="test-owner/test-repo",
        base_ref="main",
        head_ref="test",
        readme_preview="# Project Docs",
        directory_structure=["calculator.py", "test_calculator.py"],
        tree_truncated=False,
        detected_technologies=[
            TechnologyInfo(name="Python", category="language", detected_from="GitHub Language API")
        ],
        languages={"Python": 1200},
        relevant_files=[
            FilePreview(
                path="test_calculator.py",
                content="def test_calc(): pass",
                size=22,
                truncated=False,
                reason="matching_test_for_calculator.py",
            )
        ],
        total_files_examined=2,
    )

    client.cookies.set("installation_id", "160653761")
    response = client.get(
        "/api/github/repositories/test-owner/test-repo/pulls/8/context?conflicting_files=calculator.py"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["repository"] == "test-owner/test-repo"
    assert data["base_ref"] == "main"
    assert data["head_ref"] == "test"
    assert data["readme_preview"] == "# Project Docs"
    assert len(data["directory_structure"]) == 2
    assert len(data["detected_technologies"]) == 1
    assert data["detected_technologies"][0]["name"] == "Python"
    assert len(data["relevant_files"]) == 1
    assert data["relevant_files"][0]["path"] == "test_calculator.py"
