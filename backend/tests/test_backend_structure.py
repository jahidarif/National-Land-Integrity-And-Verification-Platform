"""Enforce the one-class/one-operation convention on the v4 modules.

Project A's retained chat/auth compatibility modules are intentionally kept intact;
new platform modules and the shared domain/support/adapter layers are checked here.
"""
import ast
from pathlib import Path

APP = Path(__file__).parents[1] / "app"
CHECKED = (
    APP / "domain" / "base.py",
    APP / "domain" / "timestamped.py",
    APP / "domain" / "value_objects",
    APP / "domain" / "ports",
    APP / "application" / "support",
    APP / "application" / "use_cases",
    APP / "infrastructure" / "adapters",
    APP / "infrastructure" / "adapters" / "noop_land_change_publisher.py",
    APP / "presentation" / "schemas",
)


def test_v4_modules_use_one_class_and_one_public_method_per_file():
    files = []
    for path in CHECKED:
        files.extend([path] if path.is_file() else path.rglob("*.py"))
    for file in files:
        if file.name == "__init__.py":
            continue
        tree = ast.parse(file.read_text(encoding="utf-8"))
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        assert len(classes) <= 1, f"More than one class in {file}"
        for cls in classes:
            public = [node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_")]
            declarative = [node for node in public if any(isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "field_validator" for dec in node.decorator_list)]
            methods = [node.name for node in public if node not in declarative]
            assert len(methods) <= 1, f"More than one public method in {file}: {methods}"
