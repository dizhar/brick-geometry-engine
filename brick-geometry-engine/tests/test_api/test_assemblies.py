"""
Tests for /api/v1/assemblies endpoints.

Covers:
- POST   /api/v1/assemblies              — create (with & without explicit data)
- GET    /api/v1/assemblies              — list with pagination
- GET    /api/v1/assemblies/{id}         — retrieve by ID
- PUT    /api/v1/assemblies/{id}         — update name and/or data
- DELETE /api/v1/assemblies/{id}         — delete; confirm 404 afterwards
- Error cases: 404 on unknown ID, 422 on bad payloads
"""

import uuid

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE = "/api/v1/assemblies"

SAMPLE_DATA = {
    "name": "test-assembly",
    "nodes": [],
    "bonds": [],
}


def _create(client, name="My Assembly", data=None):
    """Create an assembly and return the response JSON."""
    payload = {"name": name}
    if data is not None:
        payload["data"] = data
    resp = client.post(BASE, json=payload)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# POST /api/v1/assemblies
# ---------------------------------------------------------------------------

class TestCreateAssembly:
    def test_create_minimal(self, client):
        """POST with just a name creates a default-data assembly."""
        resp = client.post(BASE, json={"name": "Widget"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Widget"
        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body
        # Default data scaffold
        assert body["data"]["nodes"] == []
        assert body["data"]["bonds"] == []

    def test_create_with_explicit_data(self, client):
        """POST with explicit data stores the provided JSON verbatim."""
        data = {"name": "my-build", "nodes": [{"id": "n1"}], "bonds": []}
        resp = client.post(BASE, json={"name": "my-build", "data": data})
        assert resp.status_code == 201
        assert resp.json()["data"] == data

    def test_create_returns_valid_uuid(self, client):
        body = _create(client, "UUID Test")
        # Should not raise
        uuid.UUID(body["id"])

    def test_create_missing_name_returns_422(self, client):
        resp = client.post(BASE, json={})
        assert resp.status_code == 422

    def test_create_multiple_assemblies(self, client):
        _create(client, "Alpha")
        _create(client, "Beta")
        _create(client, "Gamma")
        resp = client.get(BASE)
        assert resp.json()["total"] == 3


# ---------------------------------------------------------------------------
# GET /api/v1/assemblies  (list)
# ---------------------------------------------------------------------------

class TestListAssemblies:
    def test_empty_list(self, client):
        resp = client.get(BASE)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_list_after_creates(self, client):
        _create(client, "A")
        _create(client, "B")
        resp = client.get(BASE)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2

    def test_list_pagination_skip(self, client):
        for i in range(5):
            _create(client, f"Assembly {i}")
        resp = client.get(BASE, params={"skip": 3})
        body = resp.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2

    def test_list_pagination_limit(self, client):
        for i in range(5):
            _create(client, f"Assembly {i}")
        resp = client.get(BASE, params={"limit": 2})
        body = resp.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2

    def test_list_contains_all_created_ids(self, client):
        a = _create(client, "First")
        b = _create(client, "Second")
        ids = {item["id"] for item in client.get(BASE).json()["items"]}
        assert a["id"] in ids
        assert b["id"] in ids

    def test_list_invalid_limit_returns_422(self, client):
        resp = client.get(BASE, params={"limit": 0})
        assert resp.status_code == 422

    def test_list_limit_above_max_returns_422(self, client):
        resp = client.get(BASE, params={"limit": 201})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/assemblies/{id}
# ---------------------------------------------------------------------------

class TestGetAssembly:
    def test_get_existing(self, client):
        created = _create(client, "Fetch Me", data=SAMPLE_DATA)
        resp = client.get(f"{BASE}/{created['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == created["id"]
        assert body["name"] == "Fetch Me"
        assert body["data"] == SAMPLE_DATA

    def test_get_unknown_id_returns_404(self, client):
        resp = client.get(f"{BASE}/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_get_bad_uuid_returns_422(self, client):
        resp = client.get(f"{BASE}/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/v1/assemblies/{id}
# ---------------------------------------------------------------------------

class TestUpdateAssembly:
    def test_update_name(self, client):
        created = _create(client, "Old Name")
        resp = client.put(f"{BASE}/{created['id']}", json={"name": "New Name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_update_data(self, client):
        created = _create(client, "My Build")
        new_data = {"name": "My Build", "nodes": [{"id": "abc"}], "bonds": []}
        resp = client.put(f"{BASE}/{created['id']}", json={"data": new_data})
        assert resp.status_code == 200
        assert resp.json()["data"] == new_data

    def test_update_name_and_data(self, client):
        created = _create(client, "Original")
        new_data = {"name": "Renamed", "nodes": [], "bonds": [{"id": "b1"}]}
        resp = client.put(
            f"{BASE}/{created['id']}",
            json={"name": "Renamed", "data": new_data},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Renamed"
        assert body["data"] == new_data

    def test_update_empty_body_is_no_op(self, client):
        created = _create(client, "Stable", data=SAMPLE_DATA)
        resp = client.put(f"{BASE}/{created['id']}", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Stable"
        assert body["data"] == SAMPLE_DATA

    def test_update_persists_on_subsequent_get(self, client):
        created = _create(client, "Before")
        client.put(f"{BASE}/{created['id']}", json={"name": "After"})
        body = client.get(f"{BASE}/{created['id']}").json()
        assert body["name"] == "After"

    def test_update_unknown_id_returns_404(self, client):
        resp = client.put(f"{BASE}/{uuid.uuid4()}", json={"name": "X"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/assemblies/{id}
# ---------------------------------------------------------------------------

class TestDeleteAssembly:
    def test_delete_existing(self, client):
        created = _create(client, "Doomed")
        resp = client.delete(f"{BASE}/{created['id']}")
        assert resp.status_code == 204
        assert resp.content == b""

    def test_delete_then_get_returns_404(self, client):
        created = _create(client, "Gone")
        client.delete(f"{BASE}/{created['id']}")
        resp = client.get(f"{BASE}/{created['id']}")
        assert resp.status_code == 404

    def test_delete_reduces_list_count(self, client):
        a = _create(client, "Keep")
        b = _create(client, "Delete Me")
        client.delete(f"{BASE}/{b['id']}")
        body = client.get(BASE).json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == a["id"]

    def test_delete_unknown_id_returns_404(self, client):
        resp = client.delete(f"{BASE}/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_double_delete_returns_404(self, client):
        created = _create(client, "Once")
        client.delete(f"{BASE}/{created['id']}")
        resp = client.delete(f"{BASE}/{created['id']}")
        assert resp.status_code == 404
