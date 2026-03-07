"""
Scene export for the LEGO geometry engine (Phase C).

Produces a JSON-serialisable dictionary (and optionally a file) that describes
a complete ``Assembly`` in a format suitable for Blender and other 3-D tools.

Output structure
----------------
::

    {
      "metadata": {
        "name":          "<assembly name>",
        "engine":        "BrickVisionAI",
        "phase":         "C",
        "version":       "1.0",
        "exported_at":   "<ISO-8601 timestamp>",
        "ldu_to_mm":     0.4,
        "part_count":    <int>,
        "bond_count":    <int>
      },
      "coordinate_system": {
        "convention":    "Y_UP",
        "unit":          "LDU",
        "ldu_per_mm":    2.5,
        "blender_note":  "swap Y↔Z to use in Blender's Z-up world"
      },
      "parts": [
        {
          "instance_id":       "<uuid>",
          "part_id":           "<part_id>",
          "ldraw_id":          "<ldraw_id or null>",
          "name":              "<human name>",
          "category":          "<BRICK|PLATE|SLOPE|TECHNIC|…>",
          "colour_code":       <int>,
          "position_ldu":      [x, y, z],
          "position_mm":       [x, y, z],
          "rotation_matrix":   [a,b,c, d,e,f, g,h,i],
          "matrix_4x4":        [[…], …],   // homogeneous 4×4 (col-major Blender style)
          "bounding_box_ldu":  {"min": [x,y,z], "max": [x,y,z]},
          "bounding_box_mm":   {"min": [x,y,z], "max": [x,y,z]},
          "dimensions_ldu":    {"width": w, "height": h, "depth": d},
          "dimensions_mm":     {"width": w, "height": h, "depth": d}
        },
        …
      ],
      "bonds": [
        {
          "bond_id":              "<uuid>",
          "node_a_id":            "<uuid>",
          "node_b_id":            "<uuid>",
          "stud_connector_id":    "<connector_id>",
          "anti_stud_connector_id": "<connector_id>"
        },
        …
      ]
    }

Blender integration
-------------------
The ``blender_script()`` method returns a self-contained Python string that,
when run inside Blender's scripting console, creates a box mesh per part.
Axes are remapped to Blender's Z-up convention:

  Blender X = Engine X
  Blender Y = Engine Z      (depth/forward)
  Blender Z = Engine Y      (up)

Dimensions are converted to metres (LDU × 0.4 mm × 0.001 = LDU × 0.0004 m).
"""

from __future__ import annotations

import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..assembly.assembly_graph import Assembly
from ..collision.bounding_box import world_box
from ..core.constants import LDU_TO_MM


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ENGINE_VERSION = "1.0"
_ENGINE_NAME = "BrickVisionAI"
_PHASE = "C"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pt_ldu(pt) -> List[float]:
    return [pt.x, pt.y, pt.z]


def _pt_mm(pt) -> List[float]:
    return [pt.x * LDU_TO_MM, pt.y * LDU_TO_MM, pt.z * LDU_TO_MM]


def _mat4x4(pose) -> List[List[float]]:
    """
    Build a column-major 4×4 homogeneous matrix from *pose*.

    Blender's ``Matrix`` constructor expects column-major (list of columns).
    Column i is the world-space image of local axis i.
    """
    m = pose.rotation._mat  # type: ignore[attr-defined]
    p = pose.position
    # Columns: X-axis, Y-axis, Z-axis, translation
    return [
        [float(m[0]), float(m[3]), float(m[6]), 0.0],
        [float(m[1]), float(m[4]), float(m[7]), 0.0],
        [float(m[2]), float(m[5]), float(m[8]), 0.0],
        [p.x, p.y, p.z, 1.0],
    ]


# ---------------------------------------------------------------------------
# SceneExporter
# ---------------------------------------------------------------------------

class SceneExporter:
    """
    Export an ``Assembly`` to a JSON-serialisable dictionary.

    Parameters
    ----------
    default_colour:
        LDraw colour code recorded in the export for each part (override via
        ``colour_map`` in :meth:`export`).
    """

    def __init__(self, default_colour: int = 16) -> None:
        self.default_colour = default_colour

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def export(
        self,
        assembly: Assembly,
        colour_map: Optional[Dict[str, int]] = None,
    ) -> dict:
        """
        Build and return the scene dictionary.

        Parameters
        ----------
        assembly:
            The assembly to export.
        colour_map:
            Optional ``{instance_id: colour_code}`` overrides.

        Returns
        -------
        dict
            Fully JSON-serialisable scene description.
        """
        colour_map = colour_map or {}
        bonds_raw = list(assembly._bonds.values())  # type: ignore[attr-defined]

        return {
            "metadata": self._metadata(assembly, bonds_raw),
            "coordinate_system": self._coordinate_system(),
            "parts": [
                self._part_dict(node, colour_map.get(node.instance_id, self.default_colour))
                for node in assembly.nodes()
            ],
            "bonds": [self._bond_dict(b) for b in bonds_raw],
        }

    def export_json(
        self,
        assembly: Assembly,
        path: str | Path,
        indent: int = 2,
        colour_map: Optional[Dict[str, int]] = None,
    ) -> None:
        """Serialise *assembly* and write it to a JSON file at *path*."""
        data = self.export(assembly, colour_map=colour_map)
        Path(path).write_text(
            json.dumps(data, indent=indent, ensure_ascii=False),
            encoding="utf-8",
        )

    def blender_script(
        self,
        assembly: Assembly,
        colour_map: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        Return a self-contained Blender Python script that creates one box
        mesh object per assembly part.

        Axes are remapped to Blender's Z-up convention:
          bx = engine_x,   by = engine_z,   bz = engine_y
        Units are converted to metres (multiply LDU by 0.0004).
        """
        data = self.export(assembly, colour_map=colour_map)
        parts_json = json.dumps(data["parts"], indent=4)

        return f'''\
"""
Blender import script generated by {_ENGINE_NAME} Phase C.
Run this inside Blender's Scripting workspace (Text > Run Script).
"""

import bpy, json

LDU_TO_M = 0.0004          # 1 LDU = 0.4 mm = 0.0004 m
PARTS = json.loads("""
{parts_json}
""")

# Clear existing mesh objects (optional)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False, confirm=False)

for part in PARTS:
    ex, ey, ez = part["position_ldu"]
    w = part["dimensions_ldu"]["width"]
    h = part["dimensions_ldu"]["height"]
    d = part["dimensions_ldu"]["depth"]

    # Engine Y-up → Blender Z-up axis remap
    bx, by, bz = ex * LDU_TO_M, ez * LDU_TO_M, ey * LDU_TO_M
    bw, bh, bd = w * LDU_TO_M, d * LDU_TO_M, h * LDU_TO_M

    # Centre of the box
    cx, cy, cz = bx + bw / 2, by + bd / 2, bz + bh / 2

    bpy.ops.mesh.primitive_cube_add(location=(cx, cy, cz))
    obj = bpy.context.active_object
    obj.scale = (bw / 2, bd / 2, bh / 2)
    obj.name = part["instance_id"][:16]

    # Store metadata as custom properties
    obj["part_id"]   = part["part_id"]
    obj["ldraw_id"]  = part.get("ldraw_id") or ""
    obj["category"]  = part["category"]

print(f"Imported {{len(PARTS)}} parts from {assembly.name!r}")
'''

    # -----------------------------------------------------------------------
    # Private: dict builders
    # -----------------------------------------------------------------------

    @staticmethod
    def _metadata(assembly: Assembly, bonds_raw: list) -> dict:
        return {
            "name": assembly.name,
            "engine": _ENGINE_NAME,
            "phase": _PHASE,
            "version": _ENGINE_VERSION,
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "ldu_to_mm": LDU_TO_MM,
            "part_count": len(assembly),
            "bond_count": len(bonds_raw),
        }

    @staticmethod
    def _coordinate_system() -> dict:
        return {
            "convention": "Y_UP",
            "unit": "LDU",
            "ldu_per_mm": 1.0 / LDU_TO_MM,
            "blender_note": "swap Y\u2195Z to use in Blender's Z-up world",
        }

    @staticmethod
    def _part_dict(node, colour: int) -> dict:
        part = node.part
        dims = part.dimensions
        pose = node.pose
        box = world_box(part, pose)

        rot_flat = [int(v) for v in pose.rotation._mat]  # type: ignore[attr-defined]

        return {
            "instance_id": node.instance_id,
            "part_id": part.part_id,
            "ldraw_id": part.ldraw_id,
            "name": part.name,
            "category": part.category.name,
            "colour_code": colour,
            "position_ldu": _pt_ldu(pose.position),
            "position_mm": _pt_mm(pose.position),
            "rotation_matrix": rot_flat,
            "matrix_4x4": _mat4x4(pose),
            "bounding_box_ldu": {
                "min": _pt_ldu(box.min_point),
                "max": _pt_ldu(box.max_point),
            },
            "bounding_box_mm": {
                "min": _pt_mm(box.min_point),
                "max": _pt_mm(box.max_point),
            },
            "dimensions_ldu": {
                "width": dims.width_ldu,
                "height": dims.height_ldu,
                "depth": dims.depth_ldu,
            },
            "dimensions_mm": {
                "width": dims.width_ldu * LDU_TO_MM,
                "height": dims.height_ldu * LDU_TO_MM,
                "depth": dims.depth_ldu * LDU_TO_MM,
            },
        }

    @staticmethod
    def _bond_dict(bond) -> dict:
        return {
            "bond_id": bond.bond_id,
            "node_a_id": bond.node_a_id,
            "node_b_id": bond.node_b_id,
            "stud_connector_id": bond.pair.stud.connector_id,
            "anti_stud_connector_id": bond.pair.anti_stud.connector_id,
        }
