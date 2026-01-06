"""Shim package for the vendored scrcpy Python client.

The actual implementation lives in `vendored/scrcpy-client/` (kept as-is for repo layout).
This shim makes `import scrcpy` work for both runtime and Pylance.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_VENDORED_DIR = Path(__file__).resolve().parents[1] / "vendored" / "scrcpy-client"

if not _VENDORED_DIR.is_dir():
    raise ImportError(f"Vendored scrcpy client not found at: {_VENDORED_DIR}")


def _load_module(name: str, file_name: str):
    module_path = _VENDORED_DIR / file_name
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {name} from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Load const first, then export its constants on the package module so
# vendored modules can reference `scrcpy.SOME_CONSTANT` during import.
const = _load_module(__name__ + ".const", "const.py")

_pkg = sys.modules[__name__]
for _name, _value in vars(const).items():
    if _name.isupper() and not hasattr(_pkg, _name):
        setattr(_pkg, _name, _value)

control = _load_module(__name__ + ".control", "control.py")
core = _load_module(__name__ + ".core", "core.py")

# Re-export primary API.
Client = core.Client

__all__ = ["Client", "const", "control", "core"]
