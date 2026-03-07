"""
random_build.py — grow a random valid LEGO assembly.

Starting from a single base plate, the builder repeatedly picks a random
free stud on the existing assembly and places a randomly chosen part from
the catalog there.  Only placements that pass collision detection are
accepted; invalid attempts are skipped (up to a retry budget).

Usage
-----
    python examples/random_build.py
    python examples/random_build.py --parts 20 --seed 42 --out /tmp/random
"""

from __future__ import annotations

import argparse
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from brick_geometry.assembly.assembly_graph import Assembly
from brick_geometry.assembly.placement_engine import PlacementEngine
from brick_geometry.analysis.stability import StabilityAnalyzer
from brick_geometry.core.transforms import Pose
from brick_geometry.io.ldraw_writer import LDrawWriter
from brick_geometry.io.scene_export import SceneExporter
from brick_geometry.parts.common_parts import BRICK_1x2, BRICK_1x4, BRICK_2x2, BRICK_2x4, PLATE_2x4
from brick_geometry.parts.part_metadata import PartMetadata


# Parts available for random placement
_PART_POOL: list[PartMetadata] = [
    BRICK_1x2,
    BRICK_1x4,
    BRICK_2x2,
    BRICK_2x4,
    PLATE_2x4,
]


def random_build(
    target_parts: int = 15,
    seed: int | None = None,
    max_retries_per_step: int = 30,
) -> Assembly:
    """
    Grow a random assembly up to *target_parts* bricks.

    Parameters
    ----------
    target_parts:
        Maximum number of parts to place (including the base).
    seed:
        RNG seed for reproducibility.
    max_retries_per_step:
        How many placement attempts to make before giving up on a step.
    """
    rng = random.Random(seed)
    asm = Assembly("random_build")
    engine = PlacementEngine(asm)

    # Place a 2×4 base brick as the anchor
    base = asm.place_part(BRICK_2x4, Pose.identity())
    placed = 1
    total_attempts = 0

    while placed < target_parts:
        # Pick a random free stud anywhere in the assembly
        all_nodes = asm.nodes()
        rng.shuffle(all_nodes)

        placed_this_round = False
        for anchor_node in all_nodes:
            free_studs = [
                c for c in anchor_node.connectors
                if c.connector_type.name == "STUD" and c.is_free
            ]
            if not free_studs:
                continue

            # Try random parts on this anchor
            for _ in range(max_retries_per_step):
                part = rng.choice(_PART_POOL)
                suggestions = engine.suggest_placements(
                    part,
                    anchor_node_id=anchor_node.instance_id,
                    max_suggestions=10,
                )
                if not suggestions:
                    total_attempts += 1
                    continue

                suggestion = rng.choice(suggestions)
                try:
                    engine.commit_placement(suggestion)
                    placed += 1
                    placed_this_round = True
                    total_attempts += 1
                    break
                except ValueError:
                    total_attempts += 1
                    continue

            if placed_this_round:
                break

        if not placed_this_round:
            # No valid placement found anywhere — stop early
            break

    return asm


def main() -> None:
    parser = argparse.ArgumentParser(description="Grow a random valid LEGO assembly.")
    parser.add_argument("--parts", type=int, default=15,
                        help="Target number of parts (default: 15)")
    parser.add_argument("--seed", type=int, default=None,
                        help="RNG seed for reproducibility (default: random)")
    parser.add_argument("--out", type=str, default=None,
                        help="Output directory (default: none)")
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else random.randint(0, 99999)
    print(f"Random build — target: {args.parts} parts, seed: {seed}")

    asm = random_build(target_parts=args.parts, seed=seed)

    print(f"  Parts placed : {len(asm)}")
    print(f"  Bonds formed : {asm.bond_count()}")

    report = StabilityAnalyzer().analyse(asm)
    status = "STABLE" if report.is_stable else f"UNSTABLE ({report.floating_count()} floating)"
    print(f"  Stability    : {status}")
    print(f"  Grounded     : {report.grounded_count()} node(s)")
    print(f"  Supported    : {len(report.supported_nodes)} node(s)")

    # Part breakdown
    counts: dict[str, int] = {}
    for node in asm.nodes():
        counts[node.part.part_id] = counts.get(node.part.part_id, 0) + 1
    print(f"\n  Part breakdown:")
    for pid, cnt in sorted(counts.items()):
        print(f"    {pid}: {cnt}")

    validation = asm.validate()
    print(f"\n  Validation   : {'OK' if validation.is_valid else 'ERRORS'}")
    for err in validation.errors:
        print(f"    ERROR: {err}")

    if args.out:
        out = pathlib.Path(args.out)
        out.mkdir(parents=True, exist_ok=True)

        ldr_path = out / "random_build.ldr"
        LDrawWriter().write_file(asm, ldr_path, title=f"Random Build (seed={seed})", author="BrickVisionAI")
        print(f"\n  LDraw  → {ldr_path}")

        json_path = out / "random_build.json"
        SceneExporter().export_json(asm, json_path)
        print(f"  Scene  → {json_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
