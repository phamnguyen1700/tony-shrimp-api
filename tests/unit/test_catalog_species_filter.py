import asyncio
import inspect
from decimal import Decimal

from sqlalchemy.dialects import postgresql

from app.api.routes import catalog, owner_catalog
from app.models.catalog import CatalogStatus
from app.repositories.catalog import shrimp_repository
from app.services.catalog import shrimp_service


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

    async def fake_list_shrimp_catalog_items(db, **kwargs):
        captured["db"] = db
        captured["kwargs"] = kwargs
        return []

    monkeypatch.setattr(
        owner_catalog,
        "list_shrimp_catalog_items",
        fake_list_shrimp_catalog_items,
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


def test_repository_filters_public_caridina_with_exact_match() -> None:
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
    assert "shrimp.species = %(species_1)s" in sql
    assert "lower(shrimp.species)" not in sql
    assert "ILIKE" not in sql.upper()


def test_repository_filters_public_neocaridina_with_exact_match() -> None:
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
    assert "shrimp.species = %(species_1)s" in sql
    assert db.statement.compile().params["species_1"] == "Neocaridina"


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
    assert "shrimp.species = %(species_1)s" in sql
    assert "shrimp.rarity = %(rarity_1)s" in sql
    assert "LIMIT %(param_1)s OFFSET %(param_2)s" in sql
    assert params["species_1"] == "Caridina"
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
    assert "shrimp.species = %(species_1)s" in sql
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
    assert "shrimp.species = %(species_1)s" in sql
    assert params["catalog_status_1"] == CatalogStatus.INACTIVE.value
    assert params["species_1"] == "Neocaridina"
