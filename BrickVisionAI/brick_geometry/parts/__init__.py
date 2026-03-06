from .part_metadata import (
    PartCategory,
    PartDimensions,
    PartMetadata,
    HeightUnit,
    make_brick,
    make_plate,
)
from .part_catalog import PartCatalog
from .common_parts import (
    ALL_PARTS,
    BRICKS,
    PLATES,
    get_part,
    get_parts_by_footprint,
    get_parts_by_ldraw_id,
    # common brick constants
    BRICK_1x1, BRICK_1x2, BRICK_1x3, BRICK_1x4,
    BRICK_1x6, BRICK_1x8,
    BRICK_2x2, BRICK_2x3, BRICK_2x4, BRICK_2x6,
    BRICK_2x8, BRICK_2x10,
    BRICK_4x4, BRICK_4x6,
    # common plate constants
    PLATE_1x1, PLATE_1x2, PLATE_1x3, PLATE_1x4,
    PLATE_1x6, PLATE_1x8,
    PLATE_2x2, PLATE_2x3, PLATE_2x4, PLATE_2x6,
    PLATE_2x8, PLATE_2x10,
    PLATE_4x4, PLATE_4x6, PLATE_4x8,
    PLATE_6x6, PLATE_6x8, PLATE_6x10,
    PLATE_8x8,
)

__all__ = [
    # metadata
    "PartCategory", "PartDimensions", "PartMetadata", "HeightUnit",
    "make_brick", "make_plate",
    # catalog
    "PartCatalog",
    # registry helpers
    "ALL_PARTS", "BRICKS", "PLATES",
    "get_part", "get_parts_by_footprint", "get_parts_by_ldraw_id",
    # bricks
    "BRICK_1x1", "BRICK_1x2", "BRICK_1x3", "BRICK_1x4",
    "BRICK_1x6", "BRICK_1x8",
    "BRICK_2x2", "BRICK_2x3", "BRICK_2x4", "BRICK_2x6",
    "BRICK_2x8", "BRICK_2x10",
    "BRICK_4x4", "BRICK_4x6",
    # plates
    "PLATE_1x1", "PLATE_1x2", "PLATE_1x3", "PLATE_1x4",
    "PLATE_1x6", "PLATE_1x8",
    "PLATE_2x2", "PLATE_2x3", "PLATE_2x4", "PLATE_2x6",
    "PLATE_2x8", "PLATE_2x10",
    "PLATE_4x4", "PLATE_4x6", "PLATE_4x8",
    "PLATE_6x6", "PLATE_6x8", "PLATE_6x10",
    "PLATE_8x8",
]
