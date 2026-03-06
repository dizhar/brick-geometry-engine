import json
import pytest
import tempfile
from pathlib import Path
from brick_geometry.parts.part_catalog import PartCatalog
from brick_geometry.parts.part_metadata import PartCategory, make_brick, make_plate
from brick_geometry.parts.common_parts import ALL_PARTS, BRICK_2x4, PLATE_1x1


class TestPartCatalogBasic:
    def test_default_catalog_has_parts(self):
        catalog = PartCatalog.default()
        assert len(catalog) == len(ALL_PARTS)

    def test_register_and_get(self):
        catalog = PartCatalog()
        catalog.register(BRICK_2x4)
        assert catalog.get("brick_2x4") is BRICK_2x4

    def test_register_duplicate_raises(self):
        catalog = PartCatalog()
        catalog.register(BRICK_2x4)
        with pytest.raises(ValueError):
            catalog.register(BRICK_2x4)

    def test_register_overwrite(self):
        catalog = PartCatalog()
        catalog.register(BRICK_2x4)
        catalog.register(BRICK_2x4, overwrite=True)  # no error

    def test_contains(self):
        catalog = PartCatalog.default()
        assert "brick_2x4" in catalog
        assert "nonexistent" not in catalog

    def test_get_missing_raises(self):
        catalog = PartCatalog()
        with pytest.raises(KeyError):
            catalog.get("nonexistent")

    def test_get_or_none(self):
        catalog = PartCatalog()
        assert catalog.get_or_none("brick_2x4") is None
        catalog.register(BRICK_2x4)
        assert catalog.get_or_none("brick_2x4") is BRICK_2x4

    def test_unregister(self):
        catalog = PartCatalog()
        catalog.register(BRICK_2x4)
        catalog.unregister("brick_2x4")
        assert "brick_2x4" not in catalog

    def test_unregister_missing_raises(self):
        catalog = PartCatalog()
        with pytest.raises(KeyError):
            catalog.unregister("nonexistent")

    def test_iter(self):
        catalog = PartCatalog.default()
        ids = {p.part_id for p in catalog}
        assert "brick_2x4" in ids


class TestPartCatalogQueries:
    def setup_method(self):
        self.catalog = PartCatalog.default()

    def test_by_category_brick(self):
        bricks = self.catalog.by_category(PartCategory.BRICK)
        assert all(p.category == PartCategory.BRICK for p in bricks)
        assert len(bricks) > 0

    def test_by_category_plate(self):
        plates = self.catalog.by_category(PartCategory.PLATE)
        assert all(p.category == PartCategory.PLATE for p in plates)

    def test_by_footprint(self):
        parts = self.catalog.by_footprint(2, 4)
        assert any(p.part_id == "brick_2x4" for p in parts)
        assert any(p.part_id == "plate_2x4" for p in parts)

    def test_by_footprint_symmetric(self):
        # 2x4 and 4x2 should return same set
        parts_24 = self.catalog.by_footprint(2, 4)
        parts_42 = self.catalog.by_footprint(4, 2)
        assert {p.part_id for p in parts_24} == {p.part_id for p in parts_42}

    def test_by_ldraw_id(self):
        part = self.catalog.by_ldraw_id("3001")
        assert part is not None
        assert part.part_id == "brick_2x4"

    def test_by_ldraw_id_missing(self):
        assert self.catalog.by_ldraw_id("99999") is None

    def test_where(self):
        results = self.catalog.where(lambda p: p.dimensions.studs_x == 1)
        assert all(p.dimensions.studs_x == 1 for p in results)


class TestPartCatalogPersistence:
    def test_save_and_load_json(self):
        catalog = PartCatalog.default()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            catalog.save_json(path)
            loaded = PartCatalog.load_json(path)
            assert len(loaded) == len(catalog)
            assert "brick_2x4" in loaded
        finally:
            path.unlink()

    def test_merge(self):
        c1 = PartCatalog()
        c1.register(BRICK_2x4)
        c2 = PartCatalog()
        c2.register(PLATE_1x1)
        c1.merge(c2)
        assert "plate_1x1" in c1
        assert "brick_2x4" in c1
