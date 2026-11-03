"""Checkout entry point; resolve the implementation in src without installation.

Setuptools packages src/benchmate only. This shim lets the offline verifier run
from the root of a fresh clone without installing the experiment dependencies.
"""
from pathlib import Path

__path__ = [str(Path(__file__).resolve().parent.parent / "src" / "benchmate")]
__version__ = "0.1.0"
