"""
brick_geometry.analysis — Phase C structural analysis

Modules
-------
stability — detect floating parts and validate structurally sound assemblies
"""

from .stability import StabilityAnalyzer, StabilityReport, NodeStatus

__all__ = ["StabilityAnalyzer", "StabilityReport", "NodeStatus"]
