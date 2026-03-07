"""
LDraw file reader for the LEGO geometry engine (Phase C).

LDraw format overview
---------------------
Each line in an .ldr file begins with a *line type* digit (0–5):

  0  Comment / META command  (``0 STEP``, ``0 FILE name``, ``0 Author: …``)
  1  Sub-file reference — a placed part:
     ``1 <colour> <x> <y> <z> <a> <b> <c> <d> <e> <f> <g> <h> <i> <filename>``
  2  Line primitive       (ignored)
  3  Triangle primitive   (ignored)
  4  Quad primitive       (ignored)
  5  Optional line        (ignored)

Type-1 lines are the only ones the reader cares about: they define where each
part is placed and how it is oriented.

Coordinate-system conventions
------------------------------
LDraw convention: positive Y points **downward**.
Engine convention: positive Y points **upward**.

When parsing, the reader applies a Y-axis flip:
  - ``engine_y = -ldraw_y``
  - The rotation matrix rows are transformed by F·M·F where F = diag(1,−1,1).
    Element-wise: negate column 1 and row 1 of the 3×3 matrix.

Only rotation matrices whose entries are all 0 / ±1 (i.e., pure 90° step
rotations) are accepted.  Non-conforming matrices produce a warning and the
placement falls back to the identity rotation.

Catalog-aware parsing
---------------------
When a ``PartCatalog`` is supplied, the reader attempts to map each LDraw
filename to a ``PartMetadata`` record:
  1. Strip the file extension and try ``catalog.by_ldraw_id(stem)``.
  2. Fall back to a direct ``catalog.get_or_none(stem)``.
  3. If still unresolved, ``LDrawRecord.part`` is ``None``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from ..core.geometry import Point3D
from ..core.transforms import Pose, Rotation
from ..core.constants import POSITION_TOLERANCE_LDU
from ..parts.part_catalog import PartCatalog
from ..parts.part_metadata import PartMetadata


# ---------------------------------------------------------------------------
# Y-axis conversion helpers
# ---------------------------------------------------------------------------

def _ldraw_to_engine_pos(lx: float, ly: float, lz: float) -> Point3D:
    """Convert LDraw position (Y-down) to engine position (Y-up)."""
    return Point3D(lx, -ly, lz)


def _ldraw_to_engine_matrix(
    a: int, b: int, c: int,
    d: int, e: int, f: int,
    g: int, h: int, i: int,
) -> Tuple[int, ...]:
    """
    Apply Y-flip (F = diag(1,−1,1)) to convert a LDraw rotation matrix to
    the engine's Y-up convention.

    Derivation: M_engine = F · M_ldraw · F
    Element mapping: negate elements where *exactly one* index is the
    Y (middle) row or column.

      a  b  c       a  -b   c
      d  e  f  →   -d   e  -f
      g  h  i       g  -h   i
    """
    return (a, -b, c, -d, e, -f, g, -h, i)


# ---------------------------------------------------------------------------
# Rotation matrix validation
# ---------------------------------------------------------------------------

_VALID_ENTRIES = frozenset({-1, 0, 1})


def _parse_rotation(
    floats: List[float], line_number: int, errors: List[str]
) -> Optional[Rotation]:
    """
    Round *floats* (9 values) to integers and validate as a 90° rotation.

    Returns a ``Rotation`` on success, appends to *errors* and returns
    ``None`` on failure.
    """
    rounded = [round(v) for v in floats]

    if not all(v in _VALID_ENTRIES for v in rounded):
        errors.append(
            f"Line {line_number}: rotation matrix has non-90° entries "
            f"{floats} — using identity."
        )
        return None

    # Each row and each column must have exactly one non-zero entry.
    for axis in range(3):
        row = rounded[axis * 3: axis * 3 + 3]
        col = [rounded[j * 3 + axis] for j in range(3)]
        if sum(1 for v in row if v != 0) != 1:
            errors.append(
                f"Line {line_number}: rotation matrix row {axis} is invalid "
                f"({row}) — using identity."
            )
            return None
        if sum(1 for v in col if v != 0) != 1:
            errors.append(
                f"Line {line_number}: rotation matrix column {axis} is "
                f"invalid — using identity."
            )
            return None

    ldraw_mat = tuple(rounded)
    engine_mat = _ldraw_to_engine_matrix(*ldraw_mat)
    return Rotation(engine_mat)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# LDrawRecord
# ---------------------------------------------------------------------------

@dataclass
class LDrawRecord:
    """
    A single parsed type-1 line from an LDraw file.

    Coordinates and rotation are in the engine's Y-up convention.

    Attributes
    ----------
    colour:
        LDraw colour code (e.g. 16 = main/current colour).
    pose:
        World-space pose in engine coordinates.
    ldraw_filename:
        Original filename token from the type-1 line (e.g. ``"3001.dat"``).
    part:
        Resolved ``PartMetadata``, or ``None`` if not found in the catalog.
    step:
        0-based build step index (increments at each ``0 STEP`` command).
    line_number:
        1-based line number in the source file.
    """
    colour: int
    pose: Pose
    ldraw_filename: str
    part: Optional[PartMetadata]
    step: int
    line_number: int


# ---------------------------------------------------------------------------
# LDrawParseResult
# ---------------------------------------------------------------------------

@dataclass
class LDrawParseResult:
    """
    The complete result of parsing one LDraw file.

    Attributes
    ----------
    records:
        All successfully parsed type-1 placements.
    title:
        Value of the ``0 FILE`` or ``0 Name:`` meta (may be empty).
    author:
        Value of the ``0 Author:`` meta (may be empty).
    errors:
        Non-fatal issues (e.g. skipped non-90° rotations, unknown parts).
    warnings:
        Advisory messages (e.g. unknown colour codes, unknown filenames).
    """
    records: List[LDrawRecord] = field(default_factory=list)
    title: str = ""
    author: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """True when there are no errors or warnings."""
        return not self.errors and not self.warnings

    def __repr__(self) -> str:
        return (
            f"LDrawParseResult({len(self.records)} records, "
            f"{len(self.errors)} errors, {len(self.warnings)} warnings)"
        )


# ---------------------------------------------------------------------------
# LDrawReader
# ---------------------------------------------------------------------------

class LDrawReader:
    """
    Parses LDraw .ldr and .mpd files.

    Usage
    -----
    reader = LDrawReader()
    result = reader.read_file("my_model.ldr", catalog=PartCatalog.default())
    for record in result.records:
        print(record.pose, record.part)
    """

    def read_file(
        self,
        path: str | Path,
        catalog: Optional[PartCatalog] = None,
    ) -> LDrawParseResult:
        """Parse the file at *path* and return an ``LDrawParseResult``."""
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        return self.read_string(text, catalog=catalog)

    def read_string(
        self,
        content: str,
        catalog: Optional[PartCatalog] = None,
    ) -> LDrawParseResult:
        """Parse LDraw-format *content* (a multi-line string)."""
        result = LDrawParseResult()
        step = 0

        for lineno, raw in enumerate(content.splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue

            parts = line.split()
            if not parts:
                continue

            try:
                line_type = int(parts[0])
            except ValueError:
                continue

            if line_type == 0:
                self._handle_meta(parts[1:], lineno, step, result)
                if len(parts) >= 2 and parts[1].upper() == "STEP":
                    step += 1

            elif line_type == 1:
                self._handle_type1(
                    parts[1:], lineno, step, catalog, result
                )
            # Types 2–5 are geometry primitives; skip.

        return result

    # -----------------------------------------------------------------------
    # Private: meta line handling
    # -----------------------------------------------------------------------

    # Keywords that start recognised META commands — bare comment lines
    # that don't begin with one of these are treated as the model title
    # (first occurrence only).
    _META_KEYWORDS: frozenset = frozenset({
        "FILE", "NAME", "NAME:", "AUTHOR", "AUTHOR:",
        "STEP", "NOFILE", "!LICENSE", "WRITE", "PRINT",
        "CLEAR", "PAUSE", "SAVE", "BFC", "COLOUR",
        "!HISTORY", "!HELP", "!KEYWORDS", "!CATEGORY",
        "!CMDLINE", "!LDRAW_ORG",
    })

    def _handle_meta(
        self,
        tokens: List[str],
        lineno: int,
        step: int,
        result: LDrawParseResult,
    ) -> None:
        if not tokens:
            return
        keyword = tokens[0].upper()

        if keyword in ("FILE", "NAME:") and len(tokens) > 1:
            if not result.title:
                result.title = " ".join(tokens[1:])
        elif keyword == "NAME" and len(tokens) > 1:
            if not result.title:
                result.title = " ".join(tokens[1:])
        elif keyword == "AUTHOR:" and len(tokens) > 1:
            result.author = " ".join(tokens[1:])
        elif keyword == "AUTHOR" and len(tokens) > 1:
            result.author = " ".join(tokens[1:])
        elif keyword not in self._META_KEYWORDS and not result.title:
            # First bare comment line → model title (standard LDraw convention)
            result.title = " ".join(tokens)

    # -----------------------------------------------------------------------
    # Private: type-1 line handling
    # -----------------------------------------------------------------------

    def _handle_type1(
        self,
        tokens: List[str],
        lineno: int,
        step: int,
        catalog: Optional[PartCatalog],
        result: LDrawParseResult,
    ) -> None:
        # Expected: colour x y z a b c d e f g h i filename
        if len(tokens) < 14:
            result.errors.append(
                f"Line {lineno}: type-1 line has too few tokens ({len(tokens)+1} total)."
            )
            return

        try:
            colour = int(tokens[0])
            x, y, z = float(tokens[1]), float(tokens[2]), float(tokens[3])
            mat_floats = [float(tokens[4 + k]) for k in range(9)]
        except ValueError as exc:
            result.errors.append(
                f"Line {lineno}: could not parse numeric fields — {exc}."
            )
            return

        # Filename may have spaces (rare, but spec allows it)
        filename = " ".join(tokens[13:])

        # Convert position
        pos = _ldraw_to_engine_pos(x, y, z)

        # Parse and validate rotation
        rotation = _parse_rotation(mat_floats, lineno, result.errors)
        if rotation is None:
            rotation = Rotation.identity()

        pose = Pose(position=pos, rotation=rotation)

        # Resolve part
        part = self._resolve_part(filename, catalog, lineno, result)

        result.records.append(LDrawRecord(
            colour=colour,
            pose=pose,
            ldraw_filename=filename,
            part=part,
            step=step,
            line_number=lineno,
        ))

    # -----------------------------------------------------------------------
    # Private: catalog lookup
    # -----------------------------------------------------------------------

    @staticmethod
    def _resolve_part(
        filename: str,
        catalog: Optional[PartCatalog],
        lineno: int,
        result: LDrawParseResult,
    ) -> Optional[PartMetadata]:
        if catalog is None:
            return None

        # Strip path separators (MPD sub-files may include paths)
        stem = Path(filename).stem  # removes .dat / .ldr extension

        # 1. Match by LDraw ID
        part = catalog.by_ldraw_id(stem)
        if part is not None:
            return part

        # 2. Match by part_id directly
        part = catalog.get_or_none(stem)
        if part is not None:
            return part

        result.warnings.append(
            f"Line {lineno}: part {filename!r} not found in catalog."
        )
        return None
