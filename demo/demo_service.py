"""Локальный тестовый сервис для мониторинга: отвечает 200, а по команде 503 или медленно.

запуск: python demo_service.py --port 9101 [--name billing]
управление: GET /toggle переключает рабочий/сломанный, GET /slow — ответы по 1,5 с
"""

import argparse
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class DemoHandler(BaseHTTPRequestHandler):
    """Простой HTTP-сервис, который можно переключать в режим сбоя."""

    state = {"broken": False, "slow": False, "name": "demo"}

    def do_GET(self) -> None:  # noqa: N802 — имя метода задаёт http.server
        if self.path == "/toggle":
            self.state["broken"] = not self.state["broken"]
            return self._reply(200, f"broken={self.state['broken']}")
        if self.path == "/slow":
            self.state["slow"] = not self.state["slow"]
            return self._reply(200, f"slow={self.state['slow']}")
        if self.state["slow"]:
            time.sleep(1.5)
        if self.state["broken"]:
            return self._reply(503, "service unavailable")
        return self._reply(200, f"{self.state['name']} ok")

    def _reply(self, code: int, text: str) -> None:
        body = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_) -> None:
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9101)
    parser.add_argument("--name", default="demo")
    args = parser.parse_args()
    DemoHandler.state["name"] = args.name
    ThreadingHTTPServer(("0.0.0.0", args.port), DemoHandler).serve_forever()


if __name__ == "__main__":
    main()
