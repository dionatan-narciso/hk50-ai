"""Conservative dead-code and dependency audit for the backend.

The audit is intentionally report-only. It identifies symbols that may be
unused, but never deletes code or fails CI merely because a candidate exists.
Python's dynamic features make static dead-code detection imperfect, so every
candidate must be reviewed before removal.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
TEST_ROOT = BACKEND_ROOT / "tests"

# Framework and convention-based entry points may not have normal call sites.
PUBLIC_NAME_PREFIXES = ("run_", "get_", "load_", "save_", "update_", "build_", "calculate_", "generate_")
PUBLIC_DECORATORS = {"get", "post", "put", "patch", "delete", "websocket"}


@dataclass(frozen=True)
class Symbol:
    module: str
    name: str
    path: str
    line: int
    kind: str


@dataclass(frozen=True)
class Candidate:
    module: str
    name: str
    path: str
    line: int
    reason: str
    confidence: str


def iter_python_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def module_name(path: Path) -> str:
    relative = path.relative_to(BACKEND_ROOT).with_suffix("")
    return ".".join(relative.parts)


def decorator_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    return None


def is_framework_entry_point(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        decorator_name(decorator) in PUBLIC_DECORATORS
        for decorator in node.decorator_list
    )


def collect_definitions(files: Iterable[Path]) -> list[Symbol]:
    definitions: list[Symbol] = []

    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module = module_name(path)

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.append(Symbol(module, node.name, str(path), node.lineno, "function"))
            elif isinstance(node, ast.ClassDef):
                definitions.append(Symbol(module, node.name, str(path), node.lineno, "class"))

    return definitions


def collect_references(files: Iterable[Path]) -> tuple[set[str], set[tuple[str, str]]]:
    """Collect name references and explicit ``from module import symbol`` links."""

    referenced_names: set[str] = set()
    imported_symbols: set[tuple[str, str]] = set()

    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                referenced_names.add(node.id)
            elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                referenced_names.add(node.attr)
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    imported_symbols.add((node.module, alias.name))
                    referenced_names.add(alias.asname or alias.name)

    return referenced_names, imported_symbols


def collect_unused_imports(files: Iterable[Path]) -> list[Candidate]:
    candidates: list[Candidate] = []

    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        loaded_names = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    bound_name = alias.asname or alias.name.split(".")[0]
                    if bound_name not in loaded_names:
                        candidates.append(Candidate(
                            module_name(path),
                            bound_name,
                            str(path),
                            node.lineno,
                            "import is not referenced in this module",
                            "high",
                        ))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    bound_name = alias.asname or alias.name
                    if bound_name not in loaded_names:
                        candidates.append(Candidate(
                            module_name(path),
                            bound_name,
                            str(path),
                            node.lineno,
                            "imported symbol is not referenced in this module",
                            "high",
                        ))

    return candidates


def collect_dead_code_candidates(app_files: list[Path], all_files: list[Path]) -> list[Candidate]:
    definitions = collect_definitions(app_files)
    referenced_names, imported_symbols = collect_references(all_files)
    candidates: list[Candidate] = []

    for symbol in definitions:
        if symbol.name.startswith("_"):
            # Private helpers are legitimate candidates when no static reference exists.
            confidence = "medium"
        else:
            confidence = "low"

        if symbol.name in referenced_names:
            continue
        if (symbol.module.removeprefix("app."), symbol.name) in imported_symbols:
            continue
        if (symbol.module, symbol.name) in imported_symbols:
            continue
        if symbol.name.startswith(PUBLIC_NAME_PREFIXES):
            # These often form API/service surfaces and need explicit human review.
            confidence = "low"

        path = Path(symbol.path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        matching = next(
            (
                node for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.name == symbol.name
                and node.lineno == symbol.line
            ),
            None,
        )
        if isinstance(matching, (ast.FunctionDef, ast.AsyncFunctionDef)) and is_framework_entry_point(matching):
            continue

        candidates.append(Candidate(
            symbol.module,
            symbol.name,
            symbol.path,
            symbol.line,
            "no static references found in backend application or tests",
            confidence,
        ))

    return candidates


def run_audit(backend_root: Path = BACKEND_ROOT) -> dict:
    app_root = backend_root / "app"
    test_root = backend_root / "tests"
    script_root = backend_root / "scripts"

    app_files = list(iter_python_files(app_root))
    all_files = sorted({
        *app_files,
        *iter_python_files(test_root),
        *iter_python_files(script_root),
    })

    parse_errors: list[dict] = []
    valid_files: list[Path] = []
    for path in all_files:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            valid_files.append(path)
        except (SyntaxError, UnicodeDecodeError) as exc:
            parse_errors.append({"path": str(path), "error": str(exc)})

    valid_app_files = [path for path in app_files if path in valid_files]
    dead_code = collect_dead_code_candidates(valid_app_files, valid_files)
    unused_imports = collect_unused_imports(valid_app_files)

    return {
        "status": "failed" if parse_errors else "completed",
        "files_scanned": len(valid_files),
        "parse_errors": parse_errors,
        "dead_code_candidates": [asdict(item) for item in dead_code],
        "unused_import_candidates": [asdict(item) for item in unused_imports],
        "note": (
            "Candidates are advisory. Review dynamic imports, framework routing, "
            "callbacks and public API compatibility before removal."
        ),
    }


def print_human_report(report: dict) -> None:
    print("Dead-code and dependency audit")
    print(f"Files scanned: {report['files_scanned']}")
    print(f"Parse errors: {len(report['parse_errors'])}")
    print(f"Dead-code candidates: {len(report['dead_code_candidates'])}")
    print(f"Unused-import candidates: {len(report['unused_import_candidates'])}")

    for heading, key in (
        ("Dead-code candidates", "dead_code_candidates"),
        ("Unused-import candidates", "unused_import_candidates"),
    ):
        items = report[key]
        if not items:
            continue
        print(f"\n{heading}:")
        for item in items:
            print(
                f"- [{item['confidence']}] {item['path']}:{item['line']} "
                f"{item['name']} — {item['reason']}"
            )

    print(f"\n{report['note']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args()

    report = run_audit()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_human_report(report)

    return 1 if report["parse_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
