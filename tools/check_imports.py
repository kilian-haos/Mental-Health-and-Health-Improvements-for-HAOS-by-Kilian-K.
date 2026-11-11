"""Check every `from homeassistant… import name` of the integration against a HA core checkout.

    git clone --depth 1 --filter=blob:none --sparse https://github.com/home-assistant/core.git ha-core
    cd ha-core && git sparse-checkout set --no-cone 'homeassistant/*.py' homeassistant/helpers homeassistant/util \
        homeassistant/components/{frontend,panel_custom,http,websocket_api,recorder,repairs,persistent_notification,sensor,binary_sensor,switch,button,select}
    python tools/check_imports.py ha-core custom_components/mental_health

A name counts as found when the target module defines it (def/class/assignment/import) or
re-exports it. Prints every import with OK / MISSING and exits 1 on problems.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path


def module_path(core: Path, mod: str) -> Path | None:
    base = core / Path(*mod.split("."))
    if (base / "__init__.py").exists():
        return base / "__init__.py"
    if base.with_suffix(".py").exists():
        return base.with_suffix(".py")
    return None


def defined_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, (ast.AnnAssign,)) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                names.add(a.asname or a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.TypeAlias) if hasattr(ast, "TypeAlias") else False:
            names.add(node.name.id)
    return names


def main() -> int:
    core = Path(sys.argv[1]).resolve()
    integ = Path(sys.argv[2]).resolve()
    problems = 0
    checked = 0
    for py in sorted(integ.rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("homeassistant"):
                mp = module_path(core, node.module)
                for a in node.names:
                    checked += 1
                    sub = module_path(core, f"{node.module}.{a.name}")
                    if mp is None and sub is None:
                        print(f"MISSING module {node.module}  ({py.relative_to(integ)})")
                        problems += 1
                        continue
                    if sub is not None:
                        continue
                    if a.name not in defined_names(mp):
                        print(f"MISSING {node.module}.{a.name}  ({py.relative_to(integ)})")
                        problems += 1
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.startswith("homeassistant"):
                        checked += 1
                        if module_path(core, a.name) is None:
                            print(f"MISSING module {a.name}  ({py.relative_to(integ)})")
                            problems += 1
    print(f"{checked} imports checked, {problems} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
