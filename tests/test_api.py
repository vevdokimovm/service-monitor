"""API behaviour: validation, uniqueness, 404, audit log."""

TARGET = {"name": "web", "url": "http://127.0.0.1:9101/", "interval_seconds": 5}


async def test_create_and_list(client):
    created = await client.post("/api/targets", json=TARGET)
    assert created.status_code == 201
    assert [t["name"] for t in (await client.get("/api/targets")).json()] == ["web"]


async def test_duplicate_name_is_409(client):
    await client.post("/api/targets", json=TARGET)
    assert (await client.post("/api/targets", json=TARGET)).status_code == 409


async def test_invalid_url_is_422(client):
    bad = {**TARGET, "url": "not-a-url"}
    assert (await client.post("/api/targets", json=bad)).status_code == 422


async def test_unknown_target_is_404(client):
    assert (await client.get("/api/targets/99/history")).status_code == 404
    assert (await client.delete("/api/targets/99")).status_code == 404


async def test_status_pending_before_first_check(client):
    await client.post("/api/targets", json=TARGET)
    [row] = (await client.get("/api/status")).json()
    assert row["state"] == "PENDING" and row["checks_total"] == 0


async def test_actions_are_logged(client):
    tid = (await client.post("/api/targets", json=TARGET)).json()["id"]
    await client.delete(f"/api/targets/{tid}")
    actions = [a["action"] for a in (await client.get("/api/audit")).json()]
    assert actions == ["target_deleted", "target_created"]
