"""Checkout entry point: ``import benchmate`` from the repository root resolves to ``src/benchmate``.

Setuptools packages ``src/benchmate`` only. This shim lets ``python3 -S -m benchmate verify``
run from the root of a fresh clone without installing anything. It hands the import over to
the real package, so ``__file__`` and ``importlib.resources.files('benchmate')`` point at
``src/benchmate`` (a bare ``__path__`` redirect left resources pointing here).
"""
import sys as _sys
from pathlib import Path as _Path

_src = str(_Path(__file__).resolve().parent.parent / "src")
# src must come before the repository root on sys.path, whatever an editable install appended.
_sys.path[:] = [_src] + [p for p in _sys.path if p != _src]
_sys.modules.pop(__name__, None)
import importlib as _importlib
_real = _importlib.import_module(__name__)
if getattr(_real, "__file__", "") == __file__:
    raise ImportError("benchmate shim: src/benchmate was not found ahead of the repository root")
_sys.modules[__name__] = _real
