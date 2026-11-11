"""Make the pure logic importable as `logic.*` without putting the integration folder on sys.path.

(The integration has modules named like stdlib modules – select.py, http.py – so the folder itself
must never be on sys.path.) The tools folder is added for gen_sleep_data.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INT = ROOT / "custom_components" / "mental_health"


def _load(name: str, path: Path, package: bool = False):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, path / "__init__.py" if package else path, submodule_search_locations=[str(path)] if package else None)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_load("logic", INT / "logic", package=True)
for p in (ROOT / "tools", ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
