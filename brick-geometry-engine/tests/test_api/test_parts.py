"""
Tests for /api/v1/parts endpoints.

Covers:
- GET /api/v1/parts              — list all parts (pagination, category filter)
- GET /api/v1/parts/{part_id}   — get specific part
- Error cases: 404 on unknown part_id
"""

import pytest

BASE = "/api/v1/parts"

# Known part IDs that must be present from common_parts.py
KNOWN_PART_ID = "brick_2x4"
KNOWN_CATEGORY = "BRICK"


# ---------------------------------------------------------------------------
# GET /api/v1/parts  (list)
# ---------------------------------------------------------------------------

class TestListParts:
    def test_returns_200(self, client):
        resp = client.get(BASE)
        assert resp.status_code == 200

    def test_response_shape(self, client):
        body = client.get(BASE).json()
        assert "total" in body
        assert "items" in body
        assert isinstance(body["total"], int)
        assert isinstance(body["items"], list)

    def test_catalog_is_non_empty(self, client):
        body = client.get(BASE).json()
        assert body["total"] > 0
        assert len(body["items"]) > 0

    def test_part_schema_fields(self, client):
        item = client.get(BASE).json()["items"][0]
        assert "part_id" in item
        assert "category" in item
        assert "dimensions" in item
        dims = item["dimensions"]
        for field in ("studs_x", "studs_z", "height_ldu", "width_ldu", "depth_ldu"):
            assert field in dims, f"Missing dimension field: {field}"

    def test_filter_by_category_brick(self, client):
        body = client.get(BASE, params={"category": "BRICK"}).json()
        assert body["total"] > 0
        for item in body["items"]:
            assert item["category"] == "BRICK"

    def test_filter_by_category_plate(self, client):
        body = client.get(BASE, params={"category": "PLATE"}).json()
        assert body["total"] > 0
        for item in body["items"]:
            assert item["category"] == "PLATE"

    def test_filter_by_category_case_insensitive(self, client):
        lower = client.get(BASE, params={"category": "brick"}).json()
        upper = client.get(BASE, params={"category": "BRICK"}).json()
        assert lower["total"] == upper["total"]

    def test_filter_unknown_category_returns_empty(self, client):
        body = client.get(BASE, params={"category": "NONEXISTENT"}).json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_pagination_limit(self, client):
        total = client.get(BASE).json()["total"]
        if total < 2:
            pytest.skip("Catalog has fewer than 2 parts")
        body = client.get(BASE, params={"limit": 1}).json()
        assert len(body["items"]) == 1
        assert body["total"] == total  # total is unaffected by limit

    def test_pagination_skip(self, client):
        total = client.get(BASE).json()["total"]
        if total < 2:
            pytest.skip("Catalog has fewer than 2 parts")
        all_ids = [p["part_id"] for p in client.get(BASE).json()["items"]]
        skipped_ids = [
            p["part_id"]
            for p in client.get(BASE, params={"skip": 1}).json()["items"]
        ]
        assert skipped_ids == all_ids[1:]

    def test_skip_beyond_total_returns_empty_items(self, client):
        total = client.get(BASE).json()["total"]
        body = client.get(BASE, params={"skip": total + 100}).json()
        assert body["items"] == []
        assert body["total"] == total

    def test_invalid_limit_zero_returns_422(self, client):
        resp = client.get(BASE, params={"limit": 0})
        assert resp.status_code == 422

    def test_invalid_limit_above_max_returns_422(self, client):
        resp = client.get(BASE, params={"limit": 501})
        assert resp.status_code == 422

    def test_dimensions_are_positive(self, client):
        for item in client.get(BASE).json()["items"]:
            dims = item["dimensions"]
            assert dims["studs_x"] > 0
            assert dims["studs_z"] > 0
            assert dims["height_ldu"] > 0
            assert dims["width_ldu"] > 0
            assert dims["depth_ldu"] > 0


# ---------------------------------------------------------------------------
# GET /api/v1/parts/{part_id}
# ---------------------------------------------------------------------------

class TestGetPart:
    def test_get_known_part(self, client):
        resp = client.get(f"{BASE}/{KNOWN_PART_ID}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["part_id"] == KNOWN_PART_ID
        assert body["category"] == KNOWN_CATEGORY

    def test_get_part_dimensions_correct_for_2x4(self, client):
        body = client.get(f"{BASE}/{KNOWN_PART_ID}").json()
        dims = body["dimensions"]
        assert dims["studs_x"] == 2
        assert dims["studs_z"] == 4

    def test_get_part_response_has_all_fields(self, client):
        body = client.get(f"{BASE}/{KNOWN_PART_ID}").json()
        assert "part_id" in body
        assert "category" in body
        assert "dimensions" in body

    def test_get_plate_1x1(self, client):
        resp = client.get(f"{BASE}/plate_1x1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["category"] == "PLATE"
        assert body["dimensions"]["studs_x"] == 1
        assert body["dimensions"]["studs_z"] == 1

    def test_get_unknown_part_returns_404(self, client):
        resp = client.get(f"{BASE}/does_not_exist_xyz")
        assert resp.status_code == 404

    def test_get_all_listed_parts_individually(self, client):
        """Every part returned by the list endpoint must be retrievable by ID."""
        items = client.get(BASE, params={"limit": 500}).json()["items"]
        for item in items:
            resp = client.get(f"{BASE}/{item['part_id']}")
            assert resp.status_code == 200, (
                f"Part '{item['part_id']}' listed but not retrievable"
            )

    def test_part_id_consistent_between_list_and_get(self, client):
        listed = client.get(BASE).json()["items"][0]
        fetched = client.get(f"{BASE}/{listed['part_id']}").json()
        assert listed["part_id"] == fetched["part_id"]
        assert listed["category"] == fetched["category"]
        assert listed["dimensions"] == fetched["dimensions"]
