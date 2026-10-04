from __future__ import annotations

import ast
from pathlib import Path

CONTEXTS = {
    "academy",
    "curriculum",
    "identity",
    "journey",
    "platform",
    "read_models",
}
FORBIDDEN_SEGMENTS = {"infrastructure", "repository", "repositories"}


def test_contexts_do_not_import_other_context_infrastructure() -> None:
    app_root = Path(__file__).resolve().parents[1] / "app"
    violations: list[str] = []

    for context in CONTEXTS:
        context_root = app_root / context
        if not context_root.exists():
            continue
        for path in context_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or not node.module:
                    continue
                parts = node.module.split(".")
                if len(parts) < 3 or parts[0] != "app":
                    continue
                imported_context = parts[1]
                if imported_context == context:
                    continue
                if imported_context in CONTEXTS and FORBIDDEN_SEGMENTS.intersection(parts[2:]):
                    violations.append(f"{path.relative_to(app_root)} -> {node.module}")

    assert not violations, "\n".join(violations)
