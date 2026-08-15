import ast
from pathlib import Path

DOMAINS_ROOT = Path(__file__).resolve().parents[1] / "app" / "domains"


def _domain_of(path: Path) -> str:
    return path.relative_to(DOMAINS_ROOT).parts[0]


def _domain_module_parts(dotted: str) -> list[str] | None:
    if not dotted.startswith("app.domains."):
        return None
    parts = dotted.split(".")
    if len(parts) < 3:
        return None
    return parts


def _find_internal_cross_domain_imports(tree: ast.AST, own_domain: str) -> set[str]:
    violations = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module:
            parts = _domain_module_parts(n.module)
            if parts is None:
                continue
            other = parts[2]
            is_internal = len(parts) > 3
            if other != own_domain and is_internal:
                violations.add(other)
        if isinstance(n, ast.Import):
            for alias in n.names:
                parts = _domain_module_parts(alias.name)
                if parts is None:
                    continue
                other = parts[2]
                is_internal = len(parts) > 3
                if other != own_domain and is_internal:
                    violations.add(other)
    return violations


def test_no_domain_imports_another_domains_internals():
    violations = []
    for py_file in DOMAINS_ROOT.rglob("*.py"):
        own_domain = _domain_of(py_file)
        tree = ast.parse(py_file.read_text(), filename=str(py_file))
        for other in _find_internal_cross_domain_imports(tree, own_domain):
            violations.append((str(py_file), other))
    assert not violations, f"Cross-domain internal imports found: {violations}"


def test_public_interface_import_is_allowed():
    source = "from app.domains.verification import SomePublicThing\n"
    tree = ast.parse(source)
    violations = _find_internal_cross_domain_imports(tree, own_domain="identity")
    assert violations == set()


def test_internal_implementation_import_is_rejected():
    source = "from app.domains.verification.internal_module import SomeInternalThing\n"
    tree = ast.parse(source)
    violations = _find_internal_cross_domain_imports(tree, own_domain="identity")
    assert violations == {"verification"}


def test_same_domain_internal_import_is_never_flagged():
    source = "from app.domains.identity.internal_module import Thing\n"
    tree = ast.parse(source)
    violations = _find_internal_cross_domain_imports(tree, own_domain="identity")
    assert violations == set()
