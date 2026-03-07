"""
LDraw file writer for the LEGO geometry engine (Phase C).

Produces well-formed LDraw .ldr files from an ``Assembly``.

Coordinate-system conventions
------------------------------
The engine uses Y-up; LDraw uses Y-down.  The writer applies the same
Y-axis flip used by the reader (see ``ldraw_reader.py``):

  ldraw_y  = −engine_y
  M_ldraw  = F · M_engine · F   where F = diag(1, −1, 1)

Element-wise for the flat 3×3 matrix (a,b,c, d,e,f, g,h,i):

  a   b   c        a  −b   c
  d   e   f   →   −d   e  −f
  g   h   i        g  −h   i

Colour codes
------------
LDraw colour 16 is the ``main`` / current-colour sentinel used by most
exported models.  Callers can supply a per-instance colour map to override.

File structure
--------------
  0 <title>
  0 Name: <title>.ldr
  0 Author: <author>
  0 !LICENSE CC BY 4.0
  0 BrickVisionAI v<version>
  [1-line per node]
  0 STEP
  0 NOFILE
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Dict, Optional

from ..assembly.assembly_graph import Assembly
from ..assembly.assembly_node import AssemblyNode
from ..core.transforms import Pose


# ---------------------------------------------------------------------------
# Y-axis conversion helpers
# ---------------------------------------------------------------------------

def _engine_to_ldraw_pos(pose: Pose):
    """Return (x, y, z) in LDraw (Y-down) from an engine Pose."""
    p = pose.position
    return (p.x, -p.y, p.z)


def _engine_to_ldraw_matrix(pose: Pose):
    """
    Convert the engine rotation matrix to LDraw convention.

    Returns a flat 9-tuple (a,b,c, d,e,f, g,h,i) with Y-flip applied.
    All entries are integers (0 or ±1) because Phase A/B only allow 90°
    step rotations.
    """
    m = pose.rotation._mat  # type: ignore[attr-defined]  # flat 9-tuple
    a, b, c, d, e, f, g, h, i = m
    return (a, -b, c, -d, e, -f, g, -h, i)


# ---------------------------------------------------------------------------
# LDrawWriter
# ---------------------------------------------------------------------------

_LDR_VERSION = "1.0"
_NEWLINE = "\r\n"  # LDraw spec requires CRLF


class LDrawWriter:
    """
    Serialises an ``Assembly`` to LDraw .ldr format.

    Parameters
    ----------
    default_colour:
        LDraw colour code applied to every part unless *colour_map* overrides
        it.  Colour 16 is the ``main`` sentinel (inherits from parent).
    """

    def __init__(self, default_colour: int = 16) -> None:
        self.default_colour = default_colour

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def write_assembly(
        self,
        assembly: Assembly,
        title: str = "",
        author: str = "",
        colour_map: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        Serialise *assembly* to an LDraw string.

        Parameters
        ----------
        assembly:
            The assembly to export.
        title:
            Model title written to the header META lines.
        author:
            Author name written to the ``0 Author:`` META line.
        colour_map:
            Optional dict mapping ``instance_id → LDraw colour code``.
            Instance IDs absent from the map use ``self.default_colour``.

        Returns
        -------
        str
            Complete LDraw file content (CRLF line endings).
        """
        colour_map = colour_map or {}
        model_name = (title or assembly.name or "model") + ".ldr"
        lines = self._header(model_name, title or assembly.name, author)

        for node in assembly.nodes():
            colour = colour_map.get(node.instance_id, self.default_colour)
            lines.append(self._type1_line(node, colour))

        lines += self._footer()
        return _NEWLINE.join(lines) + _NEWLINE

    def write_file(
        self,
        assembly: Assembly,
        path: str | Path,
        title: str = "",
        author: str = "",
        colour_map: Optional[Dict[str, int]] = None,
    ) -> None:
        """Write *assembly* to an LDraw file at *path*."""
        content = self.write_assembly(
            assembly, title=title, author=author, colour_map=colour_map
        )
        Path(path).write_text(content, encoding="utf-8")

    # -----------------------------------------------------------------------
    # Private: line builders
    # -----------------------------------------------------------------------

    @staticmethod
    def _header(filename: str, title: str, author: str) -> list:
        now = datetime.date.today().isoformat()
        lines = [
            f"0 {title or 'Untitled'}",
            f"0 Name: {filename}",
        ]
        if author:
            lines.append(f"0 Author: {author}")
        lines += [
            f"0 !LICENSE CC BY 4.0",
            f"0 BrickVisionAI Phase C — exported {now}",
            "0",
        ]
        return lines

    @staticmethod
    def _footer() -> list:
        return ["0 STEP", "0 NOFILE"]

    @staticmethod
    def _type1_line(node: AssemblyNode, colour: int) -> str:
        """
        Format one LDraw type-1 sub-file reference line.

        Format:
          1 <colour> <x> <y> <z> <a> <b> <c> <d> <e> <f> <g> <h> <i> <filename>
        """
        lx, ly, lz = _engine_to_ldraw_pos(node.pose)
        a, b, c, d, e, f, g, h, i = _engine_to_ldraw_matrix(node.pose)

        # Choose filename: prefer LDraw ID, fall back to part_id
        part = node.part
        if part.ldraw_id:
            filename = f"{part.ldraw_id}.dat"
        else:
            filename = f"{part.part_id}.dat"

        def _fmt(v: float) -> str:
            # Emit clean integers where possible (most LDU values are whole)
            if v == int(v):
                return str(int(v))
            return f"{v:.4f}"

        mat_str = f"{a} {b} {c} {d} {e} {f} {g} {h} {i}"
        return (
            f"1 {colour} "
            f"{_fmt(lx)} {_fmt(ly)} {_fmt(lz)} "
            f"{mat_str} "
            f"{filename}"
        )
