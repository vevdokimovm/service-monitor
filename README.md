# Service Monitor

ДЗ по «Разработке приложений на Python» (МИСИС, осень 2026), Евдокимов В. М., МИВТ-26-5-2.

Мониторинг доступности веб-сервисов. Сервер на FastAPI по расписанию опрашивает добавленные адреса
и сохраняет каждую проверку в PostgreSQL. Клиент на Tkinter показывает, какой сервис жив, аптайм и историю проверок.

## Как запустить

```bash
cp .env.example .env                  # вписать POSTGRES_PASSWORD (и API_TOKEN, если нужен закрытый API)
docker compose up -d --build --wait   # поднимет базу, сервер на :8000 и два тестовых сервиса (:9101, :9102)
python client/monitor_client.py       # клиент, можно указать --server URL и --token TOKEN
```

Добавить сервис можно из формы в клиенте или через API:

```bash
curl -X POST localhost:8000/api/targets -H 'Content-Type: application/json' \
  -d '{"name":"billing","url":"http://billing:9101/","interval_seconds":5}'
curl localhost:9101/toggle            # тестовый сервис начнёт отвечать 503, в клиенте он станет DOWN
```

## API

- `GET /api/health` — сервер жив (без токена);
- `GET /api/targets`, `POST /api/targets` — список сервисов и добавление (409 если имя занято, 422 если кривой URL);
- `DELETE /api/targets/{id}` — удалить сервис вместе с историей;
- `GET /api/status` — UP/DOWN/PENDING, последняя задержка и аптайм по каждому;
- `GET /api/targets/{id}/history?limit=N` — последние N проверок (от 1 до 200);
- `GET /api/audit?limit=N` — журнал, кто что добавлял и удалял.

Swagger открывается на http://localhost:8000/docs.

## Тесты

```bash
pip install -r requirements-dev.txt
pytest -q && flake8 --max-line-length=120 server client demo tests
```

Без Docker сервер можно запустить на SQLite:
`cd server && DATABASE_URL=sqlite+aiosqlite:///./monitor.db uvicorn app.main:app --reload`.

## Про безопасность

Сервер сам ходит по адресам, которые ему добавили, поэтому через него можно стучаться во внутреннюю сеть (SSRF).
Лучше держать его в доверенной сети или задать API_TOKEN, тогда добавлять сервисы сможет только клиент с токеном.
