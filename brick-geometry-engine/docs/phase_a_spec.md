# Phase A Specification — Core Geometry Engine

Phase A established the foundational geometry layer. Everything built in
Phases B and C extends this layer without breaking its contracts.

## Scope

Phase A delivered:

- LDU unit system and coordinate convention
- Core geometric primitives (`Vector3D`, `Point3D`, `BoundingBox`)
- Rotation restricted to 90° increments; `Pose` (position + rotation)
- Part metadata model (`PartMetadata`, `PartDimensions`, `PartCatalog`)
- 14 standard bricks and 21 standard plates
- Connector model (`STUD`, `ANTI_STUD`) with formation rules
- Two-phase AABB collision detection (spatial hash + exact test)
- Assembly graph (node/bond multigraph), graph traversal, validation
- `PlacementEngine` — suggests and scores valid placements
- 231 tests covering all of the above

---

## Unit System

All lengths throughout the engine are in **LDU** (LEGO Drawing Unit).

```
1 LDU = 0.4 mm
```

| Physical quantity | LDU | mm |
|-------------------|-----|----|
| Stud centre-to-centre pitch | 20 | 8.0 |
| Stud outer diameter | 12 | 4.8 |
| Stud protrusion above top face | 4 | 1.6 |
| Anti-stud (tube) inner diameter | 10.8 | 4.32 |
| Plate height | 8 | 3.2 |
| Brick height (= 3 plates) | 24 | 9.6 |

Floating-point comparisons use `POSITION_TOLERANCE_LDU = 0.01`.

---

## Coordinate Convention

The engine uses the **LDraw right-hand coordinate system**:

- **+X** → right
- **+Y** → up
- **+Z** → toward the viewer

Part origins sit at the **bottom-left-front corner** of the part's AABB in
local space. Connector positions are expressed relative to this origin.

---

## Core Primitives

### `Vector3D(x, y, z)`

A 3-component vector supporting full arithmetic (`+`, `-`, `*`, `/`, negation).
Equality is tolerance-based (`< POSITION_TOLERANCE_LDU` on each axis).

Key methods:

| Method | Returns | Description |
|--------|---------|-------------|
| `magnitude()` | `float` | Euclidean length |
| `normalize()` | `Vector3D` | Unit vector; raises on zero-length input |
| `dot(other)` | `float` | Dot product |
| `cross(other)` | `Vector3D` | Cross product |
| `angle_to(other)` | `float` | Angle in radians |
| `is_zero()` | `bool` | True if magnitude² < tolerance² |

Static constructors: `zero()`, `unit_x()`, `unit_y()`, `unit_z()`.

### `Point3D(x, y, z)`

A position in 3-D space. Arithmetic mixes with `Vector3D`:

```python
p2 = p1 + v           # Point3D + Vector3D → Point3D
v  = p2 - p1          # Point3D - Point3D  → Vector3D
```

Key methods: `distance_to()`, `distance_sq_to()`, `translate()`,
`vector_to()`, `as_vector()`.

### `BoundingBox(min_point, max_point)`

Axis-aligned bounding box. `min_point.x ≤ max_point.x` is enforced on all
axes; construction raises `ValueError` otherwise.

Key methods:

| Method | Description |
|--------|-------------|
| `intersects(other)` | Strict overlap — touching faces return `False` |
| `contains(point)` | Tolerance-inclusive point-in-box test |
| `expanded(amount)` | New box grown by `amount` on all six faces |
| `translated(v)` | New box shifted by vector `v` |

Properties: `size` (`Vector3D`), `center` (`Point3D`).

---

## Rotation and Pose

### `Rotation`

Stored as a 3×3 integer matrix (flat 9-tuple). Because all entries are
integers, composition never accumulates floating-point error.

**Construction:**

```python
Rotation.identity()                          # no rotation
Rotation.from_axis_angle_90("y", steps=1)   # 90° CCW around Y
Rotation.from_axis_angle_90("x", steps=3)   # 270° CCW around X
```

`steps` is taken modulo 4; all 24 orientations of a cube are representable.

**Composition and inversion:**

```python
r_total = r1.compose(r2)   # first r1 then r2
r_inv   = r.inverse()      # transpose (valid for orthogonal matrices)
```

### `Pose`

A rigid-body transform: `position: Point3D` + `rotation: Rotation`.

```python
Pose.identity()                        # origin, no rotation
Pose.from_xyz(x, y, z)                 # translation only
pose.transform_point(local_point)      # rotate then translate
pose.transform_vector(local_vec)       # rotate only (no translation)
pose.transform_bounding_box(local_bb)  # produces tight AABB in world space
pose.compose(other)                    # T_self * T_other
pose.inverse()                         # invert the rigid transform
pose.relative_to(reference)            # express in local frame of reference
```

Because rotation is constrained to 90° steps, `transform_bounding_box` always
produces an axis-aligned result — no OBB is needed.

---

## Part Model

### `PartDimensions`

```
studs_x  — footprint along X (integer stud count)
studs_z  — footprint along Z (integer stud count)
height_ldu — total height including stud protrusion (float)

width_ldu  = studs_x × 20   (computed)
depth_ldu  = studs_z × 20   (computed)
```

The AABB for a part in local space spans `[0, width] × [0, height] × [0, depth]`.

### `PartMetadata`

Core record. Immutable in normal use. Key attributes:

```
part_id         str           unique identifier
name            str           human-readable label
category        PartCategory  BRICK | PLATE | TILE | SLOPE | TECHNIC | OTHER
dimensions      PartDimensions
ldraw_id        str?          LDraw part number
slope_geometry  SlopeGeometry?    Phase B extension
technic_geometry TechnicGeometry? Phase B extension
```

Serializes to/from a plain Python `dict` via `to_dict()` / `from_dict()`.

### Phase A part catalog

**14 bricks** (`PartCategory.BRICK`, height = 24 LDU):
`brick_1x1`, `1x2`, `1x3`, `1x4`, `1x6`, `1x8`, `2x2`, `2x3`, `2x4`,
`2x6`, `2x8`, `2x10`, `4x4`, `4x6`.

**21 plates** (`PartCategory.PLATE`, height = 8 LDU):
`plate_1x1` through `plate_8x8` (see `common_parts.py`).

---

## Connector Model

### Connector

| Attribute | Type | Description |
|-----------|------|-------------|
| `connector_id` | `str` | Unique within the node, e.g. `"stud_0_0"` |
| `connector_type` | `ConnectorType` | `STUD` or `ANTI_STUD` in Phase A |
| `position` | `Point3D` | World-space centre of the connector |
| `normal` | `Vector3D` | Unit vector pointing away from the part body |
| `state` | `ConnectorState` | `FREE` or `OCCUPIED` |

Phase A connector geometry:

- **STUD**: normal = (0, +1, 0); diameter = 12 LDU; protrudes 4 LDU
- **ANTI_STUD**: normal = (0, −1, 0); diameter = 10.8 LDU; flush with face

### Connector generation

For a part with footprint `studs_x × studs_z`, connectors are generated at:

```
for col in 0..studs_x:
    for row in 0..studs_z:
        local_x = (col + 0.5) × 20
        local_z = (row + 0.5) × 20

        stud     at y = height_ldu,  normal = +Y  → id "stud_{col}_{row}"
        anti_stud at y = 0,           normal = −Y  → id "anti_stud_{col}_{row}"
```

All positions are then transformed to world space using the part's `Pose`.

### Connection rules

A `STUD ↔ ANTI_STUD` bond is valid iff:

1. Types are compatible (`STUD` ↔ `ANTI_STUD`).
2. Position distance ≤ `CONNECTION_POSITION_TOLERANCE`.
3. `stud.normal · anti_stud.normal ≈ −1` (anti-parallel normals).
4. Both connectors are `FREE`.

`ConnectionRules.form_connection(conn_a, conn_b)` validates and returns a
`ConnectorPair`; both connectors are marked `OCCUPIED`. `break_connection(pair)`
releases both back to `FREE`.

---

## Collision Detection

### Design

`CollisionDetector` is **decoupled from the assembly graph**. It can be used
standalone to validate placements, and is also called by `Assembly.place_part`.

### Broad phase — spatial hash grid

Parts are hashed to integer grid cells by dividing their AABB extents by a
configurable cell size (default: 40 LDU = 2 stud pitches). Collision
candidates are pairs of parts sharing at least one cell.

This reduces the average-case complexity from O(n²) pair checks to O(n × k)
where k is the average number of parts per cell — typically small for sparse
assemblies.

### Narrow phase

Exact AABB intersection via `BoundingBox.intersects()`. Two AABBs that only
share a face plane (`intersects` returns `False`) are **not** a collision —
stacked bricks share a boundary but do not penetrate.

### API

```python
detector = CollisionDetector()

# Register a placed part
detector.register(instance_id, part, pose)

# Check the new part against all existing parts
hits = detector.check_against_all(instance_id, part, pose)
# → list[CollisionResult], where each result has id_a, id_b, box_a, box_b

# Check every pair in the detector
all_hits = detector.check_all()

# Remove a part
detector.unregister(instance_id)
```

---

## Assembly Graph

### `AssemblyNode`

Created by `Assembly.place_part`. Owns its connectors in world space.

```python
node.instance_id        # str UUID
node.part               # PartMetadata
node.pose               # Pose in world space
node.connectors         # list[Connector] (world-space)
node.get_connector(id)  # look up by connector_id
```

### `Assembly`

Directed multigraph. Node key is `instance_id` (UUID string). Bond key is a
separate UUID (`bond_id`).

**Placement:**

```python
node = assembly.place_part(part, pose, instance_id=None, check_collision=True)
# Raises ValueError on collision or duplicate instance_id.
```

**Connection:**

```python
pair = assembly.connect(node_a_id, conn_a_id, node_b_id, conn_b_id)
# Raises ValueError if the connection is geometrically invalid.
```

**Disconnection:**

```python
assembly.disconnect(bond_id)               # break one bond
assembly.disconnect_nodes(a_id, b_id)      # break all bonds between two nodes
```

**Traversal:**

```python
for node in assembly.bfs(start_id): ...
for node in assembly.dfs(start_id): ...
components = assembly.connected_components()   # list[list[AssemblyNode]]
path = assembly.find_path(start_id, end_id)    # BFS shortest path or None
```

**Validation:**

```python
report = assembly.validate()
report.is_valid    # True if no errors
report.errors      # list[str] — collisions, broken bond state
report.warnings    # list[str] — isolated nodes
```

### `ValidationReport` error categories

| Category | Condition | Severity |
|----------|-----------|----------|
| Collision | Any two nodes overlap (AABB intersection) | Error |
| Bond integrity | A bond's connector is unexpectedly FREE | Error |
| Isolation | A node has no bonds (only reported when `len > 1`) | Warning |

---

## Placement Engine

`PlacementEngine` is stateless and operates on a provided `Assembly`.

```python
engine = PlacementEngine()
suggestions = engine.suggest_placements(assembly, candidate_part)
```

**Algorithm (per free ANTI_STUD on existing nodes):**

1. For each free STUD on the candidate part, compute the `Pose` that aligns
   the stud tip with the anti-stud position with opposing normals.
2. Validate: no collision with any existing part.
3. Compute a quality score based on the number of additional bond pairs that
   would form naturally at that pose.
4. Return all valid placements as `PlacementSuggestion` objects sorted by
   descending score.

### `PlacementSuggestion`

| Attribute | Type | Description |
|-----------|------|-------------|
| `part` | `PartMetadata` | Part to be placed |
| `pose` | `Pose` | Computed world-space pose |
| `anchor_node_id` | `str` | Existing node providing the anchor connector |
| `anchor_connector_id` | `str` | The free anti-stud on the anchor |
| `candidate_connector_id` | `str` | The stud on the candidate that mates |
| `score` | `int` | Number of connector bonds that would form |

---

## Test Coverage (Phase A)

231 tests organized across:

| Module | Tests |
|--------|-------|
| `test_core/test_geometry.py` | `Vector3D`, `Point3D`, `BoundingBox` |
| `test_core/test_transforms.py` | `Rotation`, `Pose`, AABB transform |
| `test_core/test_coordinates.py` | LDU constants, unit conversions |
| `test_parts/test_part_metadata.py` | `PartMetadata`, `PartDimensions`, factories |
| `test_parts/test_part_catalog.py` | `PartCatalog` CRUD, queries, serialization |
| `test_connectors/test_connector_model.py` | `Connector`, `ConnectorPair` |
| `test_connectors/test_connector_rules.py` | `ConnectionRules` validation |
| `test_collision/test_bounding_box.py` | AABB world transform |
| `test_collision/test_collision_detection.py` | Broad + narrow phase |
| `test_assembly/test_assembly_node.py` | Node construction, connector gen |
| `test_assembly/test_assembly_graph.py` | Assembly operations, graph traversal |
| `integration/test_basic_assembly.py` | End-to-end placement + connection |
| `integration/test_complex_builds.py` | Multi-part builds, rotation, path-finding |
