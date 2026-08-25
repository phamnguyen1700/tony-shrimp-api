import asyncio
import inspect
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from app.api.routes import catalog, owner_catalog
from app.models.catalog import CatalogStatus
from app.repositories.catalog import shrimp_repository
from app.services.catalog import options_service, shrimp_service


def run(coro):
    return asyncio.run(coro)


def test_public_catalog_route_exposes_and_threads_species(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_list_shrimp_catalog_items(db, **kwargs):
        captured["db"] = db
        captured["kwargs"] = kwargs
        return []

    monkeypatch.setattr(
        catalog,
        "list_shrimp_catalog_items",
        fake_list_shrimp_catalog_items,
    )

    signature = inspect.signature(catalog.list_shrimp)

    assert "species" in signature.parameters

    result = run(
        catalog.list_shrimp(
            search=None,
            species="Caridina",
            line=None,
            color=None,
            grade=None,
            rarity="rare",
            trait=None,
            min_price=None,
            max_price=None,
            in_stock=True,
            limit=24,
            offset=0,
            db=object(),
        )
    )

    assert result == []
    assert captured["kwargs"] == {
        "catalog_status": CatalogStatus.ACTIVE.value,
        "search": None,
        "species": "Caridina",
        "line": None,
        "color": None,
        "grade": None,
        "rarity": "rare",
        "trait": None,
        "min_price": None,
        "max_price": None,
        "in_stock": True,
        "limit": 24,
        "offset": 0,
    }


def test_owner_catalog_route_exposes_and_threads_species(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_list_owner_shrimp_catalog_items(db, **kwargs):
        captured["db"] = db
        captured["kwargs"] = kwargs
        return []

    monkeypatch.setattr(
        owner_catalog,
        "list_owner_shrimp_catalog_items",
        fake_list_owner_shrimp_catalog_items,
    )

    signature = inspect.signature(owner_catalog.list_owner_shrimp)

    assert "species" in signature.parameters

    result = run(
        owner_catalog.list_owner_shrimp(
            catalog_status=CatalogStatus.INACTIVE,
            search=None,
            species="Neocaridina",
            line=None,
            color=None,
            grade=None,
            rarity=None,
            trait=None,
            min_price=None,
            max_price=None,
            in_stock=None,
            limit=20,
            offset=5,
            db=object(),
            current_user=object(),
        )
    )

    assert result == []
    assert captured["kwargs"] == {
        "catalog_status": CatalogStatus.INACTIVE.value,
        "search": None,
        "species": "Neocaridina",
        "line": None,
        "color": None,
        "grade": None,
        "rarity": None,
        "trait": None,
        "min_price": None,
        "max_price": None,
        "in_stock": None,
        "limit": 20,
        "offset": 5,
    }


def test_service_threads_species_to_repository(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_list_shrimp(db, **kwargs):
        captured["db"] = db
        captured["kwargs"] = kwargs
        return []

    monkeypatch.setattr(shrimp_service, "list_shrimp", fake_list_shrimp)

    result = run(
        shrimp_service.list_shrimp_catalog_items(
            object(),
            catalog_status=CatalogStatus.ACTIVE.value,
            species="Caridina",
            rarity="rare",
            in_stock=True,
            limit=24,
            offset=12,
        )
    )

    assert result == []
    assert captured["kwargs"]["species"] == "Caridina"
    assert captured["kwargs"]["rarity"] == "rare"
    assert captured["kwargs"]["in_stock"] is True
    assert captured["kwargs"]["limit"] == 24
    assert captured["kwargs"]["offset"] == 12


def test_public_filter_options_route_exposes_scope_without_pagination(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_get_catalog_filter_options(db, **kwargs):
        captured["db"] = db
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            species=[],
            lines=[],
            colors=[],
            grades=[],
            rarities=[],
            traits=[],
            availability=[],
        )

    monkeypatch.setattr(
        catalog,
        "get_catalog_filter_options",
        fake_get_catalog_filter_options,
    )

    signature = inspect.signature(catalog.get_public_shrimp_filter_options)

    assert "species" in signature.parameters
    assert "rarity" in signature.parameters
    assert "limit" not in signature.parameters
    assert "offset" not in signature.parameters

    run(
        catalog.get_public_shrimp_filter_options(
            search="boa",
            species="Caridina",
            line=None,
            color=None,
            grade=None,
            rarity="rare,extremely rare",
            trait=None,
            min_price=None,
            max_price=None,
            in_stock=True,
            db=object(),
        )
    )

    assert captured["kwargs"] == {
        "search": "boa",
        "species": "Caridina",
        "line": None,
        "color": None,
        "grade": None,
        "rarity": "rare,extremely rare",
        "trait": None,
        "min_price": None,
        "max_price": None,
        "in_stock": True,
    }


def test_filter_options_service_returns_values_from_scoped_active_shrimp(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}
    shrimp_items = [
        SimpleNamespace(
            species="Caridina sp.",
            line="Calceo Bee",
            colors=["Black", "Gold"],
            grade=None,
            rarity="rare",
            traits=["Calceo", "Metallic"],
            variants=[
                SimpleNamespace(is_active=True, stock_quantity=4),
            ],
        ),
        SimpleNamespace(
            species="Caridina cantonensis",
            line="Ocean",
            colors=["Blue", "Black"],
            grade="SSS",
            rarity="extremely rare",
            traits=["Metallic"],
            variants=[
                SimpleNamespace(is_active=True, stock_quantity=0),
            ],
        ),
    ]

    async def fake_list_shrimp_for_filter_options(db, **kwargs):
        captured["db"] = db
        captured["kwargs"] = kwargs
        return shrimp_items

    monkeypatch.setattr(
        options_service,
        "list_shrimp_for_filter_options",
        fake_list_shrimp_for_filter_options,
    )

    result = run(
        options_service.get_catalog_filter_options(
            object(),
            species="Caridina",
            rarity="rare,extremely rare",
            in_stock=None,
        )
    )

    assert captured["kwargs"]["catalog_status"] == CatalogStatus.ACTIVE.value
    assert captured["kwargs"]["species"] == "Caridina"
    assert captured["kwargs"]["rarity"] == "rare,extremely rare"
    assert result.species == ["Caridina cantonensis", "Caridina sp."]
    assert result.lines == ["Calceo Bee", "Ocean"]
    assert result.colors == ["Black", "Blue", "Gold"]
    assert result.grades == ["SSS"]
    assert result.rarities == ["extremely rare", "rare"]
    assert result.traits == ["Calceo", "Metallic"]
    assert result.availability == ["in-stock", "out-of-stock"]


class FakeScalars:
    def all(self):
        return []


class FakeResult:
    def scalars(self):
        return FakeScalars()


class FakeDb:
    statement = None

    async def execute(self, statement):
        self.statement = statement
        return FakeResult()


def compile_statement(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


def test_repository_filters_public_caridina_with_prefix_match() -> None:
    db = FakeDb()

    result = run(
        shrimp_repository.list_shrimp(
            db,
            catalog_status=CatalogStatus.ACTIVE.value,
            species="Caridina",
        )
    )

    sql = compile_statement(db.statement)

    assert result == []
    assert "shrimp.catalog_status = %(catalog_status_1)s" in sql
    assert "shrimp.species ILIKE %(species_1)s" in sql
    assert db.statement.compile().params["species_1"] == "Caridina%"


def test_repository_filters_public_neocaridina_with_prefix_match() -> None:
    db = FakeDb()

    result = run(
        shrimp_repository.list_shrimp(
            db,
            catalog_status=CatalogStatus.ACTIVE.value,
            species="Neocaridina",
        )
    )

    sql = compile_statement(db.statement)

    assert result == []
    assert "shrimp.catalog_status = %(catalog_status_1)s" in sql
    assert "shrimp.species ILIKE %(species_1)s" in sql
    assert db.statement.compile().params["species_1"] == "Neocaridina%"


def test_repository_combines_species_with_rarity_and_pagination() -> None:
    db = FakeDb()

    result = run(
        shrimp_repository.list_shrimp(
            db,
            catalog_status=CatalogStatus.ACTIVE.value,
            species="Caridina",
            rarity="rare",
            limit=24,
            offset=24,
        )
    )

    sql = compile_statement(db.statement)
    params = db.statement.compile().params

    assert result == []
    assert "shrimp.species ILIKE %(species_1)s" in sql
    assert "shrimp.rarity = %(rarity_1)s" in sql
    assert "LIMIT %(param_1)s OFFSET %(param_2)s" in sql
    assert params["species_1"] == "Caridina%"
    assert params["rarity_1"] == "rare"
    assert params["param_1"] == 24
    assert params["param_2"] == 24


def test_repository_combines_species_with_in_stock_filter() -> None:
    db = FakeDb()

    result = run(
        shrimp_repository.list_shrimp(
            db,
            species="Caridina",
            in_stock=True,
            min_price=Decimal("20.00"),
        )
    )

    sql = compile_statement(db.statement)

    assert result == []
    assert "shrimp.species ILIKE %(species_1)s" in sql
    assert "EXISTS" in sql
    assert "shrimp_variants.stock_quantity > %(stock_quantity_1)s" in sql
    assert "shrimp_variants.price >= %(price_1)s" in sql


def test_repository_owner_combines_species_with_catalog_status() -> None:
    db = FakeDb()

    result = run(
        shrimp_repository.list_shrimp(
            db,
            catalog_status=CatalogStatus.INACTIVE.value,
            species="Neocaridina",
        )
    )

    sql = compile_statement(db.statement)
    params = db.statement.compile().params

    assert result == []
    assert "shrimp.catalog_status = %(catalog_status_1)s" in sql
    assert "shrimp.species ILIKE %(species_1)s" in sql
    assert params["catalog_status_1"] == CatalogStatus.INACTIVE.value
    assert params["species_1"] == "Neocaridina%"


def test_repository_supports_collection_rarity_list() -> None:
    db = FakeDb()

    result = run(
        shrimp_repository.list_shrimp(
            db,
            catalog_status=CatalogStatus.ACTIVE.value,
            rarity="rare,extremely rare",
            limit=24,
        )
    )

    sql = compile_statement(db.statement)
    params = db.statement.compile().params

    assert result == []
    assert "shrimp.rarity IN (__[POSTCOMPILE_rarity_1])" in sql
    assert params["rarity_1"] == ["rare", "extremely rare"]
    assert params["param_1"] == 24


def test_repository_supports_collection_grade_list() -> None:
    db = FakeDb()

    result = run(
        shrimp_repository.list_shrimp(
            db,
            catalog_status=CatalogStatus.ACTIVE.value,
            grade="High Grade,SS,SSS",
            limit=24,
        )
    )

    sql = compile_statement(db.statement)
    params = db.statement.compile().params

    assert result == []
    assert "shrimp.grade IN (__[POSTCOMPILE_grade_1])" in sql
    assert params["grade_1"] == ["High Grade", "SS", "SSS"]
    assert params["param_1"] == 24


def test_repository_filter_options_uses_scope_without_pagination() -> None:
    db = FakeDb()

    result = run(
        shrimp_repository.list_shrimp_for_filter_options(
            db,
            catalog_status=CatalogStatus.ACTIVE.value,
            species="Caridina",
            rarity="rare,extremely rare",
        )
    )

    sql = compile_statement(db.statement)

    assert result == []
    assert "shrimp.catalog_status = %(catalog_status_1)s" in sql
    assert "shrimp.species ILIKE %(species_1)s" in sql
    assert "shrimp.rarity IN (__[POSTCOMPILE_rarity_1])" in sql
    assert "LIMIT" not in sql.upper()
    assert "OFFSET" not in sql.upper()
