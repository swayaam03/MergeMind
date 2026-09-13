"""Language detection and Tree-sitter grammar mappings for MergeMind.

Supports:
- Python (.py)
- JavaScript (.js, .jsx)
- Java (.java)

All other extensions return "unsupported".
"""

from pathlib import Path
from typing import Any

from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_java

SUPPORTED_LANGUAGES = {"python", "javascript", "java"}

_LANGUAGE_CACHE: dict[str, Language] = {}
_PARSER_CACHE: dict[str, Parser] = {}


def detect_language(path: str) -> str:
    """
    Detect programming language from file path extension.
    Case-insensitive matching.
    Returns: 'python', 'javascript', 'java', or 'unsupported'.
    """
    ext = Path(path).suffix.lower()
    if ext == ".py":
        return "python"
    if ext in (".js", ".jsx"):
        return "javascript"
    if ext == ".java":
        return "java"
    return "unsupported"


def get_language(lang_name: str) -> Language | None:
    """Retrieve or initialize the Tree-sitter Language instance for a supported language."""
    if lang_name not in SUPPORTED_LANGUAGES:
        return None

    if lang_name not in _LANGUAGE_CACHE:
        if lang_name == "python":
            _LANGUAGE_CACHE[lang_name] = Language(tree_sitter_python.language())
        elif lang_name == "javascript":
            _LANGUAGE_CACHE[lang_name] = Language(tree_sitter_javascript.language())
        elif lang_name == "java":
            _LANGUAGE_CACHE[lang_name] = Language(tree_sitter_java.language())

    return _LANGUAGE_CACHE.get(lang_name)


def get_parser_for_language(lang_name: str) -> Parser | None:
    """Retrieve or initialize a cached Parser instance for the given language."""
    if lang_name not in SUPPORTED_LANGUAGES:
        return None

    if lang_name not in _PARSER_CACHE:
        language = get_language(lang_name)
        if language is None:
            return None
        _PARSER_CACHE[lang_name] = Parser(language)

    return _PARSER_CACHE.get(lang_name)
