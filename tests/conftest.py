"""Test fixtures: a fresh SQLite database per test and an API client without the background loop."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))


@pytest.fixture()
async def app_env(tmp_path):
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    for mod in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod]
    from app.core import database
    from app.main import create_app

    await database.init_db()
    yield create_app(run_scheduler=False), database
    await database.engine.dispose()


@pytest.fixture()
async def client(app_env):
    import httpx

    app, _ = app_env
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
