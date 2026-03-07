"""
brick-geometry-engine — LEGO Geometry Engine (Phase A–C)

Quick-start
-----------
from brick_geometry import Assembly, PlacementEngine, PartCatalog, BRICK_2x4, Pose

catalog = PartCatalog.default()
assembly = Assembly("my_build")
engine = PlacementEngine(assembly)

base = assembly.place_part(BRICK_2x4, Pose.from_xyz(0, 0, 0))
suggestion = engine.find_best_placement(BRICK_2x4, anchor_node_id=base.instance_id)
if suggestion:
    engine.commit_placement(suggestion)
"""

# core primitives
from .core import (
    Point3D, Vector3D, BoundingBox,
    Pose, Rotation,
    GridPosition,
    LDU_TO_MM, MM_TO_LDU,
    STUD_SPACING_LDU, PLATE_HEIGHT_LDU, BRICK_HEIGHT_LDU,
    POSITION_TOLERANCE_LDU,
    ldu_to_mm, mm_to_ldu,
    studs_to_ldu, ldu_to_studs,
    plates_to_ldu, ldu_to_plates,
    snap_position, is_valid_grid_position,
)

# parts
from .parts import (
    PartCategory, PartDimensions, PartMetadata,
    make_brick, make_plate,
    PartCatalog,
    ALL_PARTS, BRICKS, PLATES,
    get_part, get_parts_by_footprint,
    BRICK_1x1, BRICK_1x2, BRICK_1x4, BRICK_2x2, BRICK_2x4, BRICK_2x8,
    PLATE_1x1, PLATE_1x2, PLATE_1x4, PLATE_2x2, PLATE_2x4, PLATE_2x8,
)

# connectors
from .connectors import (
    Connector, ConnectorPair, ConnectorType, ConnectorState,
    ConnectionRules, DEFAULT_RULES, ValidationResult,
)

# collision
from .collision import (
    CollisionDetector, CollisionResult,
    local_box_for_part, world_box,
)

# assembly
from .assembly import (
    AssemblyNode, Assembly, ValidationReport,
    PlacementEngine, PlacementSuggestion,
)

# io (Phase C)
from .io import (
    LDrawReader, LDrawRecord, LDrawParseResult,
    LDrawWriter,
    SceneExporter,
)

# analysis (Phase C)
from .analysis import (
    StabilityAnalyzer, StabilityReport, NodeStatus,
)

# utilities
from .utils import (
    approx_equal, clamp, lerp,
    snap_to_grid, snap_to_90,
    validated,
)

__version__ = "0.3.0"

__all__ = [
    # core
    "Point3D", "Vector3D", "BoundingBox",
    "Pose", "Rotation", "GridPosition",
    "LDU_TO_MM", "MM_TO_LDU",
    "STUD_SPACING_LDU", "PLATE_HEIGHT_LDU", "BRICK_HEIGHT_LDU",
    "POSITION_TOLERANCE_LDU",
    "ldu_to_mm", "mm_to_ldu",
    "studs_to_ldu", "ldu_to_studs",
    "plates_to_ldu", "ldu_to_plates",
    "snap_position", "is_valid_grid_position",
    # parts
    "PartCategory", "PartDimensions", "PartMetadata",
    "make_brick", "make_plate", "PartCatalog",
    "ALL_PARTS", "BRICKS", "PLATES",
    "get_part", "get_parts_by_footprint",
    "BRICK_1x1", "BRICK_1x2", "BRICK_1x4",
    "BRICK_2x2", "BRICK_2x4", "BRICK_2x8",
    "PLATE_1x1", "PLATE_1x2", "PLATE_1x4",
    "PLATE_2x2", "PLATE_2x4", "PLATE_2x8",
    # connectors
    "Connector", "ConnectorPair", "ConnectorType", "ConnectorState",
    "ConnectionRules", "DEFAULT_RULES", "ValidationResult",
    # collision
    "CollisionDetector", "CollisionResult",
    "local_box_for_part", "world_box",
    # assembly
    "AssemblyNode", "Assembly", "ValidationReport",
    "PlacementEngine", "PlacementSuggestion",
    # io (Phase C)
    "LDrawReader", "LDrawRecord", "LDrawParseResult",
    "LDrawWriter",
    "SceneExporter",
    # analysis (Phase C)
    "StabilityAnalyzer", "StabilityReport", "NodeStatus",
    # utils
    "approx_equal", "clamp", "lerp",
    "snap_to_grid", "snap_to_90", "validated",
    # version
    "__version__",
]
