# Getting Started

## Prerequisites

- Python 3.12+
- PostgreSQL (for the REST API only; not required for the geometry library)

## Installation

```bash
git clone <repo-url>
cd brick-geometry-engine
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .                 # editable install so imports resolve everywhere
```

## Using the Geometry Library

The library has no runtime dependencies — it is pure Python stdlib. No database
is needed.

### Place and connect parts

```python
from brick_geometry.parts.common_parts import BRICK_2x4, PLATE_2x4
from brick_geometry.core.transforms import Pose
from brick_geometry.assembly.assembly_graph import Assembly

assembly = Assembly("my_build")

# Place a 2×4 plate at the origin
plate = assembly.place_part(PLATE_2x4, Pose.identity())

# Place a 2×4 brick directly on top (Y offset = plate height = 8 LDU)
brick = assembly.place_part(BRICK_2x4, Pose.from_xyz(0, 8, 0))

# Connect the first stud of the plate to the matching anti-stud of the brick
assembly.connect(
    plate.instance_id, "stud_0_0",
    brick.instance_id, "anti_stud_0_0",
)

print(assembly)           # Assembly('my_build', 2 nodes, 1 bonds)
print(assembly.validate())    # ValidationReport(VALID, 0 warning(s))
```

### Serialize an assembly

```python
import json

snapshot = assembly.to_dict()   # plain Python dict — JSON-safe
print(json.dumps(snapshot, indent=2))
```

### Query the part catalog

```python
from brick_geometry.parts.part_catalog import PartCatalog
from brick_geometry.parts.common_parts import ALL_PARTS
from brick_geometry.parts.slope_parts import ALL_SLOPES
from brick_geometry.parts.technic_parts import ALL_TECHNIC
from brick_geometry.parts.part_metadata import PartCategory

catalog = PartCatalog(name="full")
catalog.register_many(list(ALL_PARTS.values()))
catalog.register_many(list(ALL_SLOPES.values()))
catalog.register_many(list(ALL_TECHNIC.values()))

brick = catalog.get("brick_2x4")
print(brick.dimensions)          # PartDimensions(2×4, h=24.0 LDU)

slopes = catalog.by_category(PartCategory.SLOPE)
print(len(slopes))               # 10
```

### Suggest placements

```python
from brick_geometry.assembly.placement_engine import PlacementEngine

engine = PlacementEngine()
suggestions = engine.suggest_placements(assembly, BRICK_2x4)

for s in suggestions[:3]:
    print(s.pose.position, "score:", s.score)
```

### Use rotations

Rotations are restricted to multiples of 90° (LDraw convention):

```python
from brick_geometry.core.transforms import Pose, Rotation

rot_90y = Rotation.from_axis_angle_90("y", steps=1)   # 90° around Y
pose = Pose(position=Point3D(40, 24, 0), rotation=rot_90y)
```

## Running the REST API

### 1. Configure environment

Create `brick-geometry-engine/.env`:

```
DATABASE_URL=postgresql://user:password@localhost:5432/brickdb
```

### 2. Apply migrations

```bash
cd brick-geometry-engine
alembic upgrade head
```

For the very first run without existing migrations, generate the initial one:

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 3. Start the server

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

On first startup the server calls `Base.metadata.create_all` automatically
(convenient for development). In production, always use Alembic.

## Running Tests

No PostgreSQL required — the test suite uses an in-memory SQLite database.

```bash
cd brick-geometry-engine

# Full suite (489 tests, ~1 second)
python -m pytest tests/ -v

# API tests only
python -m pytest tests/test_api/ -v

# Geometry engine tests only
python -m pytest tests/ --ignore=tests/test_api/ -v
```
