"""Scheduler and prober against a fake HTTP transport — no network needed."""

import httpx


def fake_transport(codes: dict[str, int]):
    def handler(request: httpx.Request) -> httpx.Response:
        code = codes.get(request.url.host)
        if code is None:
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(code)
    return httpx.MockTransport(handler)


async def test_tick_records_up_down_and_errors(app_env, client):
    _, database = app_env
    from app.services.monitor_service import Prober, Scheduler

    for name, host in [("ok", "ok.local"), ("broken", "broken.local"), ("dead", "dead.local")]:
        await client.post("/api/targets", json={"name": name, "url": f"http://{host}/", "interval_seconds": 60})
    transport = fake_transport({"ok.local": 200, "broken.local": 503})
    async with httpx.AsyncClient(transport=transport) as http:
        checked = await Scheduler(database.SessionLocal).tick(Prober(http))
        again = await Scheduler(database.SessionLocal).tick(Prober(http))
    states = {r["name"]: r["state"] for r in (await client.get("/api/status")).json()}
    assert checked == 3 and again == 0          # second tick: interval not elapsed yet
    assert states == {"ok": "UP", "broken": "DOWN", "dead": "DOWN"}
    [dead] = [r for r in (await client.get("/api/targets/3/history")).json()]
    assert dead["error"] == "ConnectError"


async def test_uptime_percent(app_env, client):
    _, database = app_env
    from app.models.orm import CheckResult
    from app.repositories.monitor_repository import MonitorRepository

    tid = (await client.post("/api/targets", json={"name": "x", "url": "http://x.local/"})).json()["id"]
    async with database.SessionLocal() as s:
        repo = MonitorRepository(s)
        for up in (True, True, True, False):
            await repo.add_check(CheckResult(target_id=tid, is_up=up, status_code=200 if up else 500))
    [row] = (await client.get("/api/status")).json()
    assert row["uptime_percent"] == 75.0 and row["checks_total"] == 4
