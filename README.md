# Tony Shrimp API

Backend API for the Tony Shrimp system.

## Tech Direction

- Python 3.13
- FastAPI
- Uvicorn
- Pydantic v2
- pydantic-settings
- SQLAlchemy 2.x async
- psycopg 3
- PostgreSQL
- Alembic
- PyJWT or equivalent session token library
- pwdlib[argon2]
- httpx
- pytest
- Ruff
- mypy or Pyright
- uv
- Docker + Docker Compose
- Caddy or Nginx for production

Dependencies will be added incrementally as each feature needs them.

## Project Architecture

The project uses a `src` layout. Application code lives in `src/app`:

```text
src/
`-- app/
    |-- api/
    |   |-- dependencies.py
    |   `-- routes/
    |       |-- products.py
    |       |-- orders.py
    |       |-- customers.py
    |       `-- auth.py
    |
    |-- services/
    |   |-- product_service.py
    |   |-- order_service.py
    |   |-- customer_service.py
    |   `-- auth_service.py
    |
    |-- repositories/
    |   |-- product_repository.py
    |   |-- order_repository.py
    |   `-- customer_repository.py
    |
    |-- schemas/
    |   |-- product.py
    |   |-- order.py
    |   |-- customer.py
    |   `-- auth.py
    |
    |-- models/
    |   |-- product.py
    |   |-- order.py
    |   `-- user.py
    |
    |-- db/
    |   |-- session.py
    |   `-- base.py
    |
    |-- core/
    |   |-- config.py
    |   |-- security.py
    |   |-- exceptions.py
    |   `-- logging.py
    |
    `-- main.py
```

## Layer Responsibilities

- `api`: HTTP route handlers and request dependencies.
- `services`: Business logic and use cases.
- `repositories`: Data access and database queries.
- `schemas`: Pydantic request and response models.
- `models`: SQLAlchemy ORM models.
- `db`: Database engine, session, and base metadata.
- `core`: Configuration, security, exception handling, and logging.
