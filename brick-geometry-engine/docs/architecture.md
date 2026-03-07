# Architecture

## Overview

Brick Geometry Engine is a Python library for computing the geometry of LEGO
assemblies, paired with a REST API for persisting and querying builds. The
library is intentionally dependency-free (pure stdlib); the API layer adds
FastAPI, SQLAlchemy, and PostgreSQL on top.

```
┌──────────────────────────────────────────────────────────────┐
│                        REST API  (api/)                       │
│  FastAPI + Uvicorn   →   routes/   →   SQLAlchemy / Postgres  │
└───────────────────────────────┬──────────────────────────────┘
                                │ imports
┌───────────────────────────────▼──────────────────────────────┐
│                  Geometry Engine  (brick_geometry/)           │
│  core/   parts/   connectors/   collision/   assembly/        │
└──────────────────────────────────────────────────────────────┘
```

## Coordinate System

The engine follows the **LDraw coordinate convention**:

| Axis | Direction |
|------|-----------|
| X    | right      |
| Y    | up         |
| Z    | toward viewer |

All lengths are in **LDU** (LEGO Drawing Units). Key constants:

| Quantity | LDU | mm |
|----------|-----|----|
| Stud centre-to-centre spacing | 20 | 8.0 |
| Plate height | 8 | 3.2 |
| Brick height (3 plates) | 24 | 9.6 |
| Stud outer diameter | 12 | 4.8 |
| Stud protrusion | 4 | 1.6 |

## Package Layout

```
brick_geometry/
├── core/
│   ├── constants.py        LDU conversion factors and physical constants
│   ├── geometry.py         Vector3D, Point3D, BoundingBox primitives
│   └── transforms.py       Rotation (90° integer matrix), Pose
│
├── parts/
│   ├── part_metadata.py    PartMetadata, PartDimensions, SlopeGeometry,
│   │                       TechnicGeometry, factory helpers (make_brick, …)
│   ├── part_catalog.py     PartCatalog — in-memory registry with query API
│   ├── common_parts.py     14 bricks + 21 plates (Phase A)
│   ├── slope_parts.py      10 slope variants (Phase B)
│   └── technic_parts.py    9 Technic beams (Phase B)
│
├── connectors/
│   ├── connector_model.py  ConnectorType, ConnectorState, Connector,
│   │                       ConnectorPair
│   ├── connector_rules.py  ConnectionRules — validates and forms bonds
│   └── connector_generation.py  Generates connector lists for each part type
│
├── collision/
│   ├── bounding_box.py     world_box() — transforms local AABB to world space
│   ├── convex_shape.py     ConvexShape, SAT intersection (slopes)
│   └── collision_detection.py  CollisionDetector — spatial hash + narrow phase
│
└── assembly/
    ├── assembly_node.py    AssemblyNode — one placed part instance
    ├── assembly_graph.py   Assembly — multigraph of nodes and bonds
    └── placement_engine.py PlacementEngine — suggests valid placements

api/
├── main.py                 FastAPI app, CORS middleware, lifespan
├── database.py             SQLAlchemy engine + SessionLocal + get_db
├── models.py               AssemblyRecord ORM model
├── schemas.py              Pydantic request/response schemas
└── routes/
    ├── assemblies.py       CRUD endpoints for stored assemblies
    └── parts.py            Read-only part catalog endpoints
```

## Core Layer (`brick_geometry/core/`)

### `Vector3D` and `Point3D`

Immutable-ish dataclasses with arithmetic operators. Equality uses a floating-
point tolerance of `POSITION_TOLERANCE_LDU = 0.01 LDU`.

```
Vector3D — direction or displacement (no position semantics)
Point3D  — position in world or local space
```

Key operations: `dot`, `cross`, `normalize`, `magnitude`, `angle_to`,
`distance_to`, `translate`.

### `BoundingBox`

Axis-aligned bounding box (AABB) defined by `min_point` and `max_point`.
Methods: `intersects`, `contains`, `expanded`, `translated`.

Touching faces (`intersects` returns `False`) are legal — two stacked bricks
share a face plane but do not overlap.

### `Rotation`

Stored as a 3×3 integer matrix to avoid floating-point drift through repeated
compositions. Only multiples of 90° are representable.

```python
rot = Rotation.from_axis_angle_90("y", steps=2)  # 180° around Y
rot.apply(v)          # rotate a Vector3D
rot.inverse()         # transpose of an orthogonal matrix
```

### `Pose`

Combines a `Point3D` position with a `Rotation`. Supports composition,
inversion, point/vector transformation, and AABB transformation.

```python
pose = Pose.from_xyz(40, 0, 0)
world_point = pose.transform_point(local_point)
```

## Parts Layer (`brick_geometry/parts/`)

### `PartDimensions`

Stores the stud footprint (`studs_x`, `studs_z`) and `height_ldu`. Computed
properties `width_ldu` and `depth_ldu` derive from the stud count:

```
width_ldu  = studs_x × 20
depth_ldu  = studs_z × 20
```

### `PartMetadata`

The canonical record for a single part. Key fields:

| Field | Type | Description |
|-------|------|-------------|
| `part_id` | `str` | Unique key, e.g. `"brick_2x4"` |
| `category` | `PartCategory` | `BRICK`, `PLATE`, `SLOPE`, `TECHNIC`, `TILE`, `OTHER` |
| `dimensions` | `PartDimensions` | Physical size |
| `ldraw_id` | `str?` | LDraw part number (e.g. `"3001"`) |
| `slope_geometry` | `SlopeGeometry?` | Phase B: slope profile |
| `technic_geometry` | `TechnicGeometry?` | Phase B: axle hole positions |

Supports `to_dict()` / `from_dict()` round-trip serialization.

Factory helpers: `make_brick()`, `make_plate()`, `make_slope()`,
`make_technic_brick()`.

### `PartCatalog`

An in-memory registry supporting:
- `register(part)` / `register_many(parts)`
- `get(part_id)` — raises `KeyError` if not found
- `by_category(category)`, `by_footprint(sx, sz)`, `by_ldraw_id(id)`
- `where(predicate)` — arbitrary filter
- `save_json()` / `load_json()` persistence

## Connectors Layer (`brick_geometry/connectors/`)

### Connector types

| Type | Role | Normal direction |
|------|------|-----------------|
| `STUD` | Male, top face | +Y |
| `ANTI_STUD` | Female, bottom face | −Y |
| `TECHNIC_PIN` | Male, horizontal (Phase B) | along hole axis |
| `TECHNIC_HOLE` | Female, horizontal (Phase B) | along hole axis |
| `TECHNIC_AXLE` | Male, smooth axle (Phase B) | along hole axis |
| `TECHNIC_AXLE_HOLE` | Female, axle socket (Phase B) | along hole axis |

### Connection rules

A bond is valid when:

1. The connector types are a compatible pair: `STUD↔ANTI_STUD`,
   `TECHNIC_PIN↔TECHNIC_HOLE`, or `TECHNIC_AXLE↔TECHNIC_AXLE_HOLE`.
2. Positions are within `CONNECTION_POSITION_TOLERANCE`.
3. Normals satisfy the orientation check:
   - STUD/ANTI_STUD: **anti-parallel** (dot ≈ −1)
   - Technic pairs: **co-axial** (|dot| ≈ 1)
4. Both connectors are `FREE`.

### Connector generation

Connectors are auto-generated per part at placement time by
`generate_connectors()` in `assembly_node.py`:

- **Standard parts** (brick/plate/tile): `studs_x × studs_z` studs on the
  top face and an equal number of anti-studs on the bottom face, at grid
  positions `(col + 0.5) × 20 LDU`.
- **Slopes**: anti-studs on the full bottom grid; studs only on the
  `flat_rows_at_high_end` rear rows.
- **Technic**: standard studs/anti-studs plus two `TECHNIC_HOLE` connectors
  per hole position (±axis direction).

## Collision Layer (`brick_geometry/collision/`)

The `CollisionDetector` uses a **two-phase** strategy:

### Broad phase — spatial hash grid

Parts are mapped to grid cells using their AABB extent. Only pairs that share
at least one cell are passed to the narrow phase. This gives O(1) average-case
insertion and O(k) query where k is the number of nearby parts.

### Narrow phase

- **Bricks / plates / tiles / Technic**: exact AABB intersection test.
  Touching faces (shared boundary) are not considered a collision.
- **Slopes**: SAT (Separating Axis Theorem) test against the trapezoidal prism
  shape derived from `SlopeGeometry`. This eliminates the AABB false positives
  that would otherwise flag the empty wedge under a slope face.

## Assembly Layer (`brick_geometry/assembly/`)

### `AssemblyNode`

Represents a single placed part. Owns:
- `PartMetadata` (what part)
- `Pose` (where in world space)
- World-space connector list (generated at construction)
- Set of active `ConnectorPair` bonds

### `Assembly`

A **directed multigraph** where nodes are `AssemblyNode` instances and edges
are `_Bond` records (wrapping a `ConnectorPair`). Multiple bonds between the
same pair of nodes are allowed (e.g. a 2×4 brick on a 2×4 plate shares up to
8 bonds).

Key operations:

| Method | Description |
|--------|-------------|
| `place_part(part, pose)` | Add a node; runs collision check by default |
| `remove_part(instance_id)` | Remove node and all its bonds |
| `connect(a_id, conn_a, b_id, conn_b)` | Form a bond |
| `disconnect(bond_id)` | Break a single bond |
| `bfs(start_id)` / `dfs(start_id)` | Graph traversal |
| `connected_components()` | List of connected subgraphs |
| `validate()` | Full integrity check (collision + bond state + isolation) |
| `to_dict()` | JSON-serializable snapshot |

### `PlacementEngine`

Stateless helper. For a given part and assembly, it enumerates all free
ANTI_STUD connectors on existing nodes, computes the pose that would align a
candidate STUD to each anchor, validates the placement for collisions, and
returns a ranked list of `PlacementSuggestion` objects.

## REST API Layer (`api/`)

### Data model

Assemblies are stored as a single PostgreSQL row:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated |
| `name` | VARCHAR(255) | Human-readable label |
| `data` | JSON | Full `Assembly.to_dict()` snapshot |
| `created_at` | TIMESTAMPTZ | Server-side default |
| `updated_at` | TIMESTAMPTZ | Updated on each PUT |

Parts are served from the in-memory catalog; no database table is used.

### Dependency injection

`get_db()` in `database.py` yields a `SessionLocal` and closes it on teardown.
Tests override it with a SQLite in-memory session via
`app.dependency_overrides[get_db]`.

### Lifespan

On startup, `Base.metadata.create_all(bind=engine)` ensures tables exist.
In production, this is superseded by Alembic migrations (`alembic upgrade head`).
