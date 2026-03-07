"""
basic_wall.py — build a running-bond brick wall.

Constructs a W×H stud wall using Brick 2×4, with each course offset by
2 studs (running bond / stretcher bond) for structural integrity.
Each layer is bonded to the one below.

Usage
-----
    python examples/basic_wall.py
    python examples/basic_wall.py --width 8 --height 4 --out /tmp/wall
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from brick_geometry.assembly.assembly_graph import Assembly
from brick_geometry.analysis.stability import StabilityAnalyzer
from brick_geometry.core.transforms import Pose
from brick_geometry.core.constants import BRICK_HEIGHT_LDU, STUD_SPACING_LDU
from brick_geometry.io.ldraw_writer import LDrawWriter
from brick_geometry.io.scene_export import SceneExporter
from brick_geometry.parts.common_parts import BRICK_2x4

# Brick 2×4 is 4 studs long in Z — wall runs along Z axis
_BRICK_LENGTH_STUDS = 4
_BOND_OFFSET_STUDS = 2  # running bond: offset every other course by 2 studs


def build_wall(width_studs: int = 8, height_layers: int = 4) -> Assembly:
    """
    Build a running-bond wall *width_studs* wide and *height_layers* tall.

    All bricks are oriented with their long axis along Z.
    Odd courses are offset by *_BOND_OFFSET_STUDS* to create interlocking.
    """
    asm = Assembly("basic_wall")
    # layer_nodes[layer][col] — for bond formation
    layer_nodes: list[list] = []

    for layer in range(height_layers):
        y = layer * BRICK_HEIGHT_LDU
        # Running-bond offset: shift odd layers by half a brick
        offset_studs = _BOND_OFFSET_STUDS if layer % 2 else 0
        offset_ldu = offset_studs * STUD_SPACING_LDU

        row_nodes = []
        col_stud = 0
        while col_stud * STUD_SPACING_LDU - offset_ldu < width_studs * STUD_SPACING_LDU:
            x = col_stud * STUD_SPACING_LDU - offset_ldu
            node = asm.place_part(BRICK_2x4, Pose.from_xyz(x, y, 0), check_collision=False)
            row_nodes.append(node)
            col_stud += _BRICK_LENGTH_STUDS

        layer_nodes.append(row_nodes)

    # Bond each layer to the one below where studs align
    for layer in range(1, height_layers):
        for top_node in layer_nodes[layer]:
            top_anti_studs = [
                c for c in top_node.connectors
                if c.connector_type.name == "ANTI_STUD" and c.is_free
            ]
            for bot_node in layer_nodes[layer - 1]:
                bot_studs = [
                    c for c in bot_node.connectors
                    if c.connector_type.name == "STUD" and c.is_free
                ]
                for anti in top_anti_studs:
                    for stud in bot_studs:
                        # Bond if positions match (within tolerance)
                        dx = abs(anti.position.x - stud.position.x)
                        dz = abs(anti.position.z - stud.position.z)
                        if dx < 0.1 and dz < 0.1:
                            try:
                                asm.connect(
                                    bot_node.instance_id, stud.connector_id,
                                    top_node.instance_id, anti.connector_id,
                                )
                            except (ValueError, KeyError):
                                pass

    return asm


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a running-bond brick wall.")
    parser.add_argument("--width", type=int, default=8,
                        help="Wall width in studs (must be multiple of 4, default: 8)")
    parser.add_argument("--height", type=int, default=4,
                        help="Wall height in brick layers (default: 4)")
    parser.add_argument("--out", type=str, default=None,
                        help="Output directory (default: none)")
    args = parser.parse_args()

    print(f"Building {args.width}-stud-wide × {args.height}-layer wall…")
    asm = build_wall(width_studs=args.width, height_layers=args.height)

    print(f"  Parts placed : {len(asm)}")
    print(f"  Bonds formed : {asm.bond_count()}")

    report = StabilityAnalyzer().analyse(asm)
    status = "STABLE" if report.is_stable else f"UNSTABLE ({report.floating_count()} floating)"
    print(f"  Stability    : {status}")
    print(f"  Grounded     : {report.grounded_count()} node(s)")

    # Show layer summary
    print(f"\n  Layers:")
    nodes = asm.nodes()
    layer_counts: dict[int, int] = {}
    for node in nodes:
        layer = round(node.pose.position.y / BRICK_HEIGHT_LDU)
        layer_counts[layer] = layer_counts.get(layer, 0) + 1
    for lyr in sorted(layer_counts):
        offset = "(offset)" if lyr % 2 else ""
        print(f"    Layer {lyr}: {layer_counts[lyr]} brick(s) {offset}")

    if args.out:
        out = pathlib.Path(args.out)
        out.mkdir(parents=True, exist_ok=True)

        ldr_path = out / "wall.ldr"
        LDrawWriter().write_file(asm, ldr_path, title="Basic Wall", author="BrickVisionAI")
        print(f"\n  LDraw  → {ldr_path}")

        json_path = out / "wall.json"
        SceneExporter().export_json(asm, json_path)
        print(f"  Scene  → {json_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
