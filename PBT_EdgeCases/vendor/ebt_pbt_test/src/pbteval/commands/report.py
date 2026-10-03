"""Generate comparison reports between EBT and PBT tests.

This module has been refactored into a package structure.
All functionality is now available through the report package.
"""

from __future__ import annotations

# Import main functionality from the refactored package
from .report.main import ReportGenerator, handle_report_command

__all__ = ["ReportGenerator", "handle_report_command"]
