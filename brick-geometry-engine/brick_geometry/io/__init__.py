"""
brick_geometry.io — Phase C file I/O

Modules
-------
ldraw_reader  — parse .ldr / .mpd LDraw files into engine types
ldraw_writer  — serialise an Assembly to LDraw .ldr format
scene_export  — export an Assembly to JSON for Blender and other tools
"""

from .ldraw_reader import LDrawReader, LDrawRecord, LDrawParseResult
from .ldraw_writer import LDrawWriter
from .scene_export import SceneExporter

__all__ = [
    "LDrawReader", "LDrawRecord", "LDrawParseResult",
    "LDrawWriter",
    "SceneExporter",
]
