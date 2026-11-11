"""A simple quality checker for Primavera P6 .xer schedule files."""

from .parser import parse_xer, XerFile  # noqa: F401
from .checks import run_all_checks  # noqa: F401

__version__ = "0.1.0"
