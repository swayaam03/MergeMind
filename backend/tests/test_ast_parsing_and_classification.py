"""Unit and integration tests for Tree-sitter AST parsing and deterministic conflict classification."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.ast import (
    analyze_conflicted_file,
    classify_conflict,
    compare_ast,
    detect_language,
    parse_code,
)
from app.ast.models import FileAST
from app.main import app


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=False)


# ---------------------------------------------------------------------------
# 1. Language Detection Tests
# ---------------------------------------------------------------------------

def test_language_detection_standard():
    """Verify supported extensions are mapped accurately."""
    assert detect_language("app/main.py") == "python"
    assert detect_language("src/index.js") == "javascript"
    assert detect_language("components/Button.jsx") == "javascript"
    assert detect_language("backend/Server.java") == "java"


def test_language_detection_uppercase():
    """Verify case-insensitive extension matching."""
    assert detect_language("APP/MAIN.PY") == "python"
    assert detect_language("SRC/INDEX.JS") == "javascript"
    assert detect_language("COMPONENTS/APP.JSX") == "javascript"
    assert detect_language("MAIN.JAVA") == "java"


def test_language_detection_unsupported():
    """Verify unsupported extensions return 'unsupported'."""
    assert detect_language("README.md") == "unsupported"
    assert detect_language("config.json") == "unsupported"
    assert detect_language("script.sh") == "unsupported"
    assert detect_language("main.cpp") == "unsupported"
    assert detect_language("style.css") == "unsupported"


# ---------------------------------------------------------------------------
# 2. Parser Tests
# ---------------------------------------------------------------------------

def test_parse_valid_python():
    """Verify valid Python parsing produces root type 'module' and success."""
    code = "def hello():\n    return 'world'\n"
    ast = parse_code("hello.py", code)
    assert ast.parse_success is True
    assert ast.language == "python"
    assert ast.root_type == "module"
    assert ast.has_error is False
    assert len(ast.nodes) >= 1


def test_parse_valid_javascript():
    """Verify valid JavaScript parsing produces root type 'program' and success."""
    code = "function add(a, b) {\n    return a + b;\n}\n"
    ast = parse_code("add.js", code)
    assert ast.parse_success is True
    assert ast.language == "javascript"
    assert ast.root_type == "program"
    assert ast.has_error is False
    assert len(ast.nodes) >= 1


def test_parse_valid_java():
    """Verify valid Java parsing produces root type 'program' and success."""
    code = "public class Calc {\n    public int add(int a, int b) {\n        return a + b;\n    }\n}\n"
    ast = parse_code("Calc.java", code)
    assert ast.parse_success is True
    assert ast.language == "java"
    assert ast.root_type == "program"
    assert ast.has_error is False
    assert len(ast.nodes) >= 1


def test_parse_syntax_error_input():
    """Verify parser handles syntax errors gracefully without crashing."""
    code = "def broken(:\n    return\n"
    ast = parse_code("broken.py", code)
    assert ast.parse_success is True
    assert ast.has_error is True
    assert len(ast.errors) > 0


def test_parse_empty_file():
    """Verify parser handles empty files cleanly."""
    ast = parse_code("empty.py", "")
    assert ast.parse_success is True
    assert ast.has_error is False
    assert len(ast.nodes) == 0


def test_parse_unsupported_language():
    """Verify unsupported language returns parse_success=False and clean error."""
    ast = parse_code("notes.txt", "some text")
    assert ast.parse_success is False
    assert ast.language == "unsupported"
    assert "Unsupported language" in ast.errors[0]


# ---------------------------------------------------------------------------
# 3. AST Extraction Tests (Node types)
# ---------------------------------------------------------------------------

def test_ast_extraction_python_nodes():
    """Verify extraction of function, class, import, assignment, return, call in Python."""
    code = (
        "import os\n"
        "from math import sqrt\n"
        "\n"
        "class Geometry:\n"
        "    pass\n"
        "\n"
        "def distance(x, y):\n"
        "    val = x * y\n"
        "    res = sqrt(val)\n"
        "    return res\n"
    )
    ast = parse_code("geom.py", code)
    node_types = {n.type for n in ast.nodes}
    assert "function_definition" in node_types
    assert "class_definition" in node_types
    assert "import_statement" in node_types or "import_from_statement" in node_types
    assert "assignment" in node_types
    assert "return_statement" in node_types
    assert "call" in node_types

    # Verify extracted names
    names = [n.name for n in ast.nodes if n.name]
    assert "Geometry" in names
    assert "distance" in names


def test_ast_extraction_javascript_nodes():
    """Verify extraction of function, arrow function, class, import, variable, return, call in JS."""
    code = (
        "import React from 'react';\n"
        "class App {}\n"
        "const multiply = (a, b) => a * b;\n"
        "function compute(x) {\n"
        "    const res = multiply(x, 2);\n"
        "    return res;\n"
        "}\n"
    )
    ast = parse_code("app.js", code)
    node_types = {n.type for n in ast.nodes}
    assert "function_declaration" in node_types
    assert "class_declaration" in node_types
    assert "import_statement" in node_types
    assert "variable_declarator" in node_types
    assert "return_statement" in node_types
    assert "call_expression" in node_types


def test_ast_extraction_java_nodes():
    """Verify extraction of class, method, import, variable, return, call in Java."""
    code = (
        "import java.util.List;\n"
        "public class Service {\n"
        "    public int process(int val) {\n"
        "        int result = calculate(val);\n"
        "        return result;\n"
        "    }\n"
        "    private int calculate(int x) { return x * 2; }\n"
        "}\n"
    )
    ast = parse_code("Service.java", code)
    node_types = {n.type for n in ast.nodes}
    assert "class_declaration" in node_types
    assert "method_declaration" in node_types
    assert "import_declaration" in node_types
    assert "return_statement" in node_types
    assert "method_invocation" in node_types


# ---------------------------------------------------------------------------
# 4. Comparison Tests
# ---------------------------------------------------------------------------

def test_compare_function_added():
    """Verify compare_ast identifies newly added function."""
    base = parse_code("f.py", "def a(): pass\n")
    side = parse_code("f.py", "def a(): pass\ndef b(): pass\n")
    changes = compare_ast(base, side)
    change_types = [c.change_type for c in changes]
    assert "added_function" in change_types
    added = next(c for c in changes if c.change_type == "added_function")
    assert added.node_name == "b"


def test_compare_function_removed():
    """Verify compare_ast identifies removed function."""
    base = parse_code("f.py", "def a(): pass\ndef b(): pass\n")
    side = parse_code("f.py", "def a(): pass\n")
    changes = compare_ast(base, side)
    change_types = [c.change_type for c in changes]
    assert "removed_function" in change_types
    removed = next(c for c in changes if c.change_type == "removed_function")
    assert removed.node_name == "b"


def test_compare_function_modified():
    """Verify compare_ast identifies modified function body."""
    base = parse_code("f.py", "def add(x, y):\n    return x + y\n")
    side = parse_code("f.py", "def add(x, y):\n    return x + y + 1\n")
    changes = compare_ast(base, side)
    assert any(c.change_type == "modified_function" and c.node_name == "add" for c in changes)


def test_compare_class_added_and_modified():
    """Verify compare_ast identifies added and modified classes."""
    base = parse_code("f.py", "class User:\n    pass\n")
    side = parse_code("f.py", "class User:\n    name = 'Alice'\nclass Account:\n    pass\n")
    changes = compare_ast(base, side)
    change_types = [c.change_type for c in changes]
    assert "modified_class" in change_types
    assert "added_class" in change_types


def test_compare_import_changes():
    """Verify compare_ast identifies added and removed imports."""
    base = parse_code("f.py", "import math\n")
    side = parse_code("f.py", "import os\n")
    changes = compare_ast(base, side)
    change_types = [c.change_type for c in changes]
    assert "added_import" in change_types
    assert "removed_import" in change_types


# ---------------------------------------------------------------------------
# 5. Classification Tests (All 7 Categories)
# ---------------------------------------------------------------------------

def test_classify_modify_modify():
    """Both sides modify the same function -> MODIFY_MODIFY."""
    base = "def calc(x):\n    return x\n"
    local = "def calc(x):\n    return x + 1\n"
    remote = "def calc(x):\n    return x + 2\n"

    analysis = analyze_conflicted_file("calc.py", base, local, remote)
    assert analysis.classification.category == "MODIFY_MODIFY"
    assert "calc" in analysis.classification.reason


def test_classify_add_add():
    """Both sides add a new function with the same name -> ADD_ADD."""
    base = "def existing(): pass\n"
    local = "def existing(): pass\ndef helper(): return 1\n"
    remote = "def existing(): pass\ndef helper(): return 2\n"

    analysis = analyze_conflicted_file("calc.py", base, local, remote)
    assert analysis.classification.category == "ADD_ADD"
    assert "helper" in analysis.classification.reason


def test_classify_delete_modify():
    """One side deletes a function that the other side modified -> DELETE_MODIFY."""
    base = "def old_func():\n    return 1\n\ndef keep(): pass\n"
    local = "def keep(): pass\n"  # deleted old_func
    remote = "def old_func():\n    return 2\n\ndef keep(): pass\n"  # modified old_func

    analysis = analyze_conflicted_file("calc.py", base, local, remote)
    assert analysis.classification.category == "DELETE_MODIFY"
    assert "old_func" in analysis.classification.reason


def test_classify_import_import():
    """Both sides modify only imports -> IMPORT_IMPORT."""
    base = "import math\n\ndef run(): pass\n"
    local = "import math\nimport os\n\ndef run(): pass\n"
    remote = "import math\nimport sys\n\ndef run(): pass\n"

    analysis = analyze_conflicted_file("calc.py", base, local, remote)
    assert analysis.classification.category == "IMPORT_IMPORT"


def test_classify_different_region():
    """Local modifies func_a, remote modifies func_b -> DIFFERENT_REGION."""
    base = "def func_a():\n    return 1\n\ndef func_b():\n    return 2\n"
    local = "def func_a():\n    return 10\n\ndef func_b():\n    return 2\n"
    remote = "def func_a():\n    return 1\n\ndef func_b():\n    return 20\n"

    analysis = analyze_conflicted_file("calc.py", base, local, remote)
    assert analysis.classification.category == "DIFFERENT_REGION"


def test_classify_same_region():
    """Both sides modify statements in the same top-level region -> SAME_REGION."""
    base = "x = 1\ny = 2\n"
    local = "x = 10\ny = 2\n"
    remote = "x = 20\ny = 2\n"

    analysis = analyze_conflicted_file("calc.py", base, local, remote)
    assert analysis.classification.category in ("SAME_REGION", "MODIFY_MODIFY")


def test_classify_unknown():
    """Unsupported language or non-classifiable code -> UNKNOWN."""
    analysis = analyze_conflicted_file("unsupported.xyz", "a", "b", "c")
    assert analysis.classification.category == "UNKNOWN"
    assert "unsupported" in analysis.classification.reason.lower()


# ---------------------------------------------------------------------------
# 6. Security Tests
# ---------------------------------------------------------------------------

def test_security_never_executes_source_code():
    """
    Verify that parsing malicious code does not execute side effects.
    """
    import os
    canary_file = "CANARY_TEST_FILE_MUST_NOT_EXIST.tmp"
    if os.path.exists(canary_file):
        os.remove(canary_file)

    malicious_code = f"import os\nos.system('echo CANARY > {canary_file}')\n"
    ast = parse_code("malicious.py", malicious_code)

    assert ast.parse_success is True
    assert not os.path.exists(canary_file)


def test_security_no_subprocess_during_ast_parsing():
    """Verify that parse_code makes no subprocess or system calls."""
    with patch("subprocess.run") as mock_subproc:
        code = "def add(a, b): return a + b\n"
        parse_code("add.py", code)
        mock_subproc.assert_not_called()


# ---------------------------------------------------------------------------
# 7. Integration Test with PR #8 (calculator.py)
# ---------------------------------------------------------------------------

def test_integration_calculator_pr8():
    """
    Verify AST analysis on the exact three-way conflict from real PR #8
    produces the expected deterministic MODIFY_MODIFY classification.
    """
    base = (
        "def calculate_total(price, tax):\n"
        "    tax_amount = price * tax\n"
        "    discount = price * 0.20\n"
        "    total = price + tax_amount - discount\n"
        "    return total\n"
    )
    local = (
        "def calculate_total(price, tax):\n"
        "    tax_amount = price * tax\n"
        "    discount = price * 0.20\n"
        "    total = price + tax_amount - discount\n"
        "    return total-10\n"
    )
    remote = (
        "def calculate_total(price, tax):\n"
        "    tax_amount = price * tax\n"
        "    discount = price * 0.20\n"
        "    total = price + tax_amount - discount\n"
        "    return total+10\n"
    )

    analysis = analyze_conflicted_file("calculator.py", base, local, remote)

    assert analysis.path == "calculator.py"
    assert analysis.language == "python"
    assert analysis.base["parse_success"] is True
    assert analysis.local["parse_success"] is True
    assert analysis.remote["parse_success"] is True
    assert analysis.classification.category == "MODIFY_MODIFY"
    assert analysis.classification.confidence == "deterministic"
    assert "calculate_total" in analysis.classification.reason


# ---------------------------------------------------------------------------
# 8. API Endpoint Test: GET /conflicts/ast
# ---------------------------------------------------------------------------

@patch("app.api.routes.conflicts.get_installation_access_token")
@patch("app.api.routes.conflicts.get_installation_repositories")
@patch("app.api.routes.conflicts.get_pull_request_detail")
@patch("app.api.routes.conflicts.simulate_merge_and_extract_conflicts")
def test_api_conflicts_ast_endpoint(
    mock_simulate,
    mock_get_pr,
    mock_get_repos,
    mock_get_token,
    client,
):
    """Verify GET /api/github/repositories/{owner}/{repo}/pulls/{pull_number}/conflicts/ast returns AST analysis."""
    mock_get_token.return_value = "ghs_test_token"
    mock_get_repos.return_value = [{"full_name": "test-owner/test-repo"}]
    mock_get_pr.return_value = {
        "number": 8,
        "mergeable": False,
        "mergeable_state": "dirty",
        "base": {"ref": "main", "sha": "b_sha"},
        "head": {"ref": "test", "sha": "h_sha"},
    }
    mock_simulate.return_value = {
        "merge_base_sha": "mb_sha",
        "changed_files": ["calculator.py"],
        "conflicting_files": ["calculator.py"],
        "conflicts": [
            {
                "path": "calculator.py",
                "language": "python",
                "base_sha": "b1",
                "local_sha": "l1",
                "remote_sha": "r1",
                "base": "def add(x): return x\n",
                "local": "def add(x): return x + 1\n",
                "remote": "def add(x): return x + 2\n",
                "conflict_markers": {"ours": "x + 1", "theirs": "x + 2"},
                "conflict_type": "textual",
            }
        ],
    }

    client.cookies.set("installation_id", "123456")
    response = client.get("/api/github/repositories/test-owner/test-repo/pulls/8/conflicts/ast")

    assert response.status_code == 200
    data = response.json()
    assert "conflicts_ast" in data
    assert len(data["conflicts_ast"]) == 1
    ast_item = data["conflicts_ast"][0]
    assert ast_item["path"] == "calculator.py"
    assert ast_item["language"] == "python"
    assert ast_item["classification"]["category"] == "MODIFY_MODIFY"
    assert ast_item["classification"]["confidence"] == "deterministic"
