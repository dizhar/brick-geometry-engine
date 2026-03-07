# API Reference

Base URL: `http://localhost:8000`

All resource endpoints are prefixed with `/api/v1`. The server also exposes
`/health` and the auto-generated docs at `/docs` (Swagger UI) and `/redoc`.

---

## Health

### `GET /health`

Returns server status. Useful for liveness probes.

**Response `200`**

```json
{ "status": "ok" }
```

---

## Assemblies

An assembly is stored as a JSON snapshot of an `Assembly.to_dict()` call.
The `data` field is a free-form JSON object — the engine does not validate its
schema, so any valid JSON object can be stored. The canonical format produced
by `Assembly.to_dict()` is:

```json
{
  "name": "my_build",
  "nodes": [
    {
      "instance_id": "...",
      "part_id": "brick_2x4",
      "pose": { "position": [0, 0, 0], "rotation": [[1,0,0],[0,1,0],[0,0,1]] }
    }
  ],
  "bonds": [
    {
      "bond_id": "...",
      "node_a": "...",
      "node_b": "...",
      "stud_connector": "stud_0_0",
      "anti_stud_connector": "anti_stud_0_0"
    }
  ]
}
```

---

### `GET /api/v1/assemblies`

List stored assemblies, ordered newest first.

**Query parameters**

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `skip` | integer | `0` | ≥ 0 | Number of records to skip |
| `limit` | integer | `50` | 1 – 200 | Maximum records to return |

**Response `200`**

```json
{
  "total": 3,
  "items": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "name": "Tower Build",
      "data": { "name": "Tower Build", "nodes": [], "bonds": [] },
      "created_at": "2026-03-07T12:00:00Z",
      "updated_at": "2026-03-07T12:00:00Z"
    }
  ]
}
```

`total` reflects the full count before pagination; `items` contains the current
page.

---

### `POST /api/v1/assemblies`

Create a new assembly record.

**Request body**

```json
{
  "name": "Tower Build",
  "data": { "name": "Tower Build", "nodes": [], "bonds": [] }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Human-readable label |
| `data` | object | no | Assembly snapshot. If omitted, a default empty scaffold is stored: `{"name": <name>, "nodes": [], "bonds": []}` |

**Response `201`**

```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "name": "Tower Build",
  "data": { "name": "Tower Build", "nodes": [], "bonds": [] },
  "created_at": "2026-03-07T12:00:00Z",
  "updated_at": "2026-03-07T12:00:00Z"
}
```

**Errors**

| Status | Condition |
|--------|-----------|
| `422` | `name` is missing or body is malformed |

---

### `GET /api/v1/assemblies/{assembly_id}`

Fetch a single assembly by its UUID.

**Path parameter**

| Parameter | Type | Description |
|-----------|------|-------------|
| `assembly_id` | UUID | Assembly identifier |

**Response `200`** — same schema as a single item in the list response.

**Errors**

| Status | Condition |
|--------|-----------|
| `404` | No assembly with the given ID |
| `422` | `assembly_id` is not a valid UUID |

---

### `PUT /api/v1/assemblies/{assembly_id}`

Update an existing assembly. All fields are optional; only provided fields are
changed. An empty body `{}` is a valid no-op.

**Path parameter**

| Parameter | Type | Description |
|-----------|------|-------------|
| `assembly_id` | UUID | Assembly identifier |

**Request body**

```json
{
  "name": "Renamed Build",
  "data": { "name": "Renamed Build", "nodes": [ /* ... */ ], "bonds": [] }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | no | New label |
| `data` | object | no | Replacement snapshot |

**Response `200`** — updated assembly record.

**Errors**

| Status | Condition |
|--------|-----------|
| `404` | No assembly with the given ID |
| `422` | `assembly_id` is not a valid UUID, or body is malformed |

---

### `DELETE /api/v1/assemblies/{assembly_id}`

Permanently delete an assembly.

**Path parameter**

| Parameter | Type | Description |
|-----------|------|-------------|
| `assembly_id` | UUID | Assembly identifier |

**Response `204`** — empty body.

**Errors**

| Status | Condition |
|--------|-----------|
| `404` | No assembly with the given ID |
| `422` | `assembly_id` is not a valid UUID |

---

## Parts

Parts are served from the in-memory catalog built at server startup from
`common_parts.py`, `slope_parts.py`, and `technic_parts.py`. The catalog is
read-only via the API.

---

### `GET /api/v1/parts`

List parts from the catalog with optional category filtering and pagination.

**Query parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | string | — | Filter by category name (case-insensitive): `BRICK`, `PLATE`, `SLOPE`, `TECHNIC`, `TILE`, `OTHER` |
| `skip` | integer | `0` | Records to skip (≥ 0) |
| `limit` | integer | `100` | Maximum records to return (1 – 500) |

**Response `200`**

```json
{
  "total": 35,
  "items": [
    {
      "part_id": "brick_2x4",
      "category": "BRICK",
      "description": "Brick 2×4",
      "dimensions": {
        "studs_x": 2,
        "studs_z": 4,
        "height_ldu": 24.0,
        "width_ldu": 40.0,
        "depth_ldu": 80.0
      }
    }
  ]
}
```

`total` reflects the count after category filtering but before pagination.

**Errors**

| Status | Condition |
|--------|-----------|
| `422` | `limit` is 0 or > 500, or `skip` is negative |

---

### `GET /api/v1/parts/{part_id}`

Fetch a single part by its ID.

**Path parameter**

| Parameter | Type | Description |
|-----------|------|-------------|
| `part_id` | string | Part identifier, e.g. `brick_2x4` |

**Response `200`**

```json
{
  "part_id": "brick_2x4",
  "category": "BRICK",
  "description": "Brick 2×4",
  "dimensions": {
    "studs_x": 2,
    "studs_z": 4,
    "height_ldu": 24.0,
    "width_ldu": 40.0,
    "depth_ldu": 80.0
  }
}
```

**Errors**

| Status | Condition |
|--------|-----------|
| `404` | No part with the given ID in the catalog |

---

## Part Catalog Reference

### Bricks (category: `BRICK`, height: 24 LDU)

| part_id | LDraw ID | Footprint |
|---------|----------|-----------|
| `brick_1x1` | 3005 | 1×1 |
| `brick_1x2` | 3004 | 1×2 |
| `brick_1x3` | 3622 | 1×3 |
| `brick_1x4` | 3010 | 1×4 |
| `brick_1x6` | 3009 | 1×6 |
| `brick_1x8` | 3008 | 1×8 |
| `brick_2x2` | 3003 | 2×2 |
| `brick_2x3` | 3002 | 2×3 |
| `brick_2x4` | 3001 | 2×4 |
| `brick_2x6` | 2456 | 2×6 |
| `brick_2x8` | 3007 | 2×8 |
| `brick_2x10` | 3006 | 2×10 |
| `brick_4x4` | 2344 | 4×4 |
| `brick_4x6` | 2356 | 4×6 |

### Plates (category: `PLATE`, height: 8 LDU)

| part_id | LDraw ID | Footprint |
|---------|----------|-----------|
| `plate_1x1` | 3024 | 1×1 |
| `plate_1x2` | 3023 | 1×2 |
| `plate_1x3` | 3623 | 1×3 |
| `plate_1x4` | 3710 | 1×4 |
| `plate_1x6` | 3666 | 1×6 |
| `plate_1x8` | 3460 | 1×8 |
| `plate_2x2` | 3022 | 2×2 |
| `plate_2x3` | 3021 | 2×3 |
| `plate_2x4` | 3020 | 2×4 |
| `plate_2x6` | 3795 | 2×6 |
| `plate_2x8` | 3034 | 2×8 |
| `plate_2x10` | 3832 | 2×10 |
| `plate_4x4` | 3031 | 4×4 |
| `plate_4x6` | 3032 | 4×6 |
| `plate_4x8` | 3035 | 4×8 |
| `plate_6x6` | 3958 | 6×6 |
| `plate_6x8` | 3036 | 6×8 |
| `plate_6x10` | 3033 | 6×10 |
| `plate_8x8` | 41539 | 8×8 |

### Slopes (category: `SLOPE`)

| part_id | Footprint | Low height (LDU) | High height (LDU) |
|---------|-----------|------------------|-------------------|
| `slope_1x1_steep` | 1×1 | 0 | 24 |
| `slope_1x2_45` | 1×2 | 0 | 24 |
| `slope_1x2_30` | 1×2 | 8 | 24 |
| `slope_1x2_inv` | 1×2 | 24 | 8 |
| `slope_2x2_45` | 2×2 | 0 | 24 |
| `slope_2x3_45` | 2×3 | 0 | 24 |
| `slope_2x4_45` | 2×4 | 0 | 24 |
| `slope_2x4_18` | 2×4 | 8 | 24 |
| `slope_2x2_inv` | 2×2 | 24 | 8 |
| `slope_2x4_inv` | 2×4 | 24 | 8 |

### Technic Bricks (category: `TECHNIC`, height: 24 LDU)

Holes run along the X axis (`hole_axis="x"`) unless otherwise noted.

| part_id | Footprint |
|---------|-----------|
| `technic_1x1` | 1×1 |
| `technic_1x2` | 1×2 |
| `technic_1x4` | 1×4 |
| `technic_1x6` | 1×6 |
| `technic_1x8` | 1×8 |
| `technic_1x10` | 1×10 |
| `technic_1x12` | 1×12 |
| `technic_2x2` | 2×2 |
| `technic_2x4` | 2×4 |
