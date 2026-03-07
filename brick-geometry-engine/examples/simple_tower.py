"""
simple_tower.py — build a 2×2 tower programmatically.

Stacks 8 layers of Brick 2×2, alternating between two 90°-offset
orientations for interlocking bond strength, then runs stability analysis
and exports the result to LDraw + JSON.

Usage
-----
    python examples/simple_tower.py
    python examples/simple_tower.py --layers 12 --out /tmp/tower
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from brick_geometry.assembly.assembly_graph import Assembly
from brick_geometry.assembly.placement_engine import PlacementEngine
from brick_geometry.analysis.stability import StabilityAnalyzer
from brick_geometry.core.transforms import Pose, Rotation
from brick_geometry.core.constants import BRICK_HEIGHT_LDU
from brick_geometry.io.ldraw_writer import LDrawWriter
from brick_geometry.io.scene_export import SceneExporter
from brick_geometry.parts.common_parts import BRICK_2x2


def build_tower(layers: int = 8) -> Assembly:
    """
    Construct a freestanding 2×2 tower *layers* bricks tall.

    Odd layers are placed in the default orientation; even layers are
    rotated 90° around Y so each course interlocks with the one below.
    """
    asm = Assembly("simple_tower")
    engine = PlacementEngine(asm)

    # Place the base brick at the origin
    rot_0 = Rotation.identity()
    rot_90 = Rotation.from_axis_angle_90("y", 1)

    base = asm.place_part(BRICK_2x2, Pose(rotation=rot_0))
    prev = base

    for layer in range(1, layers):
        rotation = rot_90 if layer % 2 else rot_0
        y = layer * BRICK_HEIGHT_LDU

        suggestion = engine.find_best_placement(BRICK_2x2, anchor_node_id=prev.instance_id)
        if suggestion is None:
            # Fallback: place directly above with explicit pose
            new_node = asm.place_part(
                BRICK_2x2,
                Pose.from_xyz(0, y, 0, rotation=rotation),
            )
            asm.connect(prev.instance_id, "stud_0_0", new_node.instance_id, "anti_stud_0_0")
        else:
            new_node = engine.commit_placement(suggestion)

        prev = new_node

    return asm


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a simple 2×2 brick tower.")
    parser.add_argument("--layers", type=int, default=8, help="Number of brick layers (default: 8)")
    parser.add_argument("--out", type=str, default=None, help="Output directory (default: none)")
    args = parser.parse_args()

    print(f"Building {args.layers}-layer tower…")
    asm = build_tower(args.layers)

    print(f"  Parts placed : {len(asm)}")
    print(f"  Bonds formed : {asm.bond_count()}")

    # Stability analysis
    report = StabilityAnalyzer().analyse(asm)
    status = "STABLE" if report.is_stable else f"UNSTABLE ({report.floating_count()} floating)"
    print(f"  Stability    : {status}")
    print(f"  Grounded     : {report.grounded_count()} node(s)")
    if report.warnings:
        for w in report.warnings:
            print(f"  Warning: {w}")

    # Optional export
    if args.out:
        out = pathlib.Path(args.out)
        out.mkdir(parents=True, exist_ok=True)

        ldr_path = out / "tower.ldr"
        LDrawWriter().write_file(asm, ldr_path, title="Simple Tower", author="BrickVisionAI")
        print(f"\n  LDraw  → {ldr_path}")

        json_path = out / "tower.json"
        SceneExporter().export_json(asm, json_path)
        print(f"  Scene  → {json_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
