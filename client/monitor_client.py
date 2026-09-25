"""Настольный клиент мониторинга на Tkinter. Вся логика на сервере, клиент только вызывает API.

запуск: python monitor_client.py [--server http://127.0.0.1:8000]
"""

import argparse
import json
import os
import tkinter as tk
import urllib.error
import urllib.request
from tkinter import messagebox, ttk

REFRESH_MS = 3000
STATE_COLORS = {"UP": "#1b7f3b", "DOWN": "#c62828", "PENDING": "#8a6d00"}


class ApiClient:
    """Обёртка над API сервера: запросы и ответы в JSON."""

    def __init__(self, base_url: str, token: str = "") -> None:
        self.base = base_url.rstrip("/") + "/api"
        self.headers = {"Content-Type": "application/json"}
        if token:
            self.headers["X-API-Token"] = token

    def _call(self, method: str, path: str, payload: dict | None = None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            detail = json.loads(exc.read() or b"{}").get("detail", exc.reason)
            raise RuntimeError(f"{exc.code}: {detail}") from exc

    def status(self) -> list[dict]:
        return self._call("GET", "/status")

    def history(self, target_id: int) -> list[dict]:
        return self._call("GET", f"/targets/{target_id}/history?limit=15")

    def add(self, name: str, url: str, interval: int) -> dict:
        return self._call("POST", "/targets", {"name": name, "url": url, "interval_seconds": interval})

    def delete(self, target_id: int) -> None:
        self._call("DELETE", f"/targets/{target_id}")


class MonitorApp(tk.Tk):
    """Главное окно: таблица состояния, форма добавления и удаления, история проверок выбранного сервиса."""

    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self.api = api
        self.title("Service Monitor — клиент")
        self.geometry("1100x620")
        self._build()
        self.refresh()

    def _build(self) -> None:
        form = ttk.LabelFrame(self, text="Новая цель мониторинга", padding=8)
        form.pack(fill="x", padx=10, pady=(10, 5))
        self.name_var = tk.StringVar()
        self.url_var = tk.StringVar(value="http://")
        self.interval_var = tk.IntVar(value=5)
        for col, (label, var, width) in enumerate([("Имя", self.name_var, 16), ("URL", self.url_var, 40),
                                                   ("Интервал, с", self.interval_var, 6)]):
            ttk.Label(form, text=label).grid(row=0, column=col * 2, padx=(0, 4))
            ttk.Entry(form, textvariable=var, width=width).grid(row=0, column=col * 2 + 1, padx=(0, 10))
        ttk.Button(form, text="Добавить", command=self.add_target).grid(row=0, column=6)
        ttk.Button(form, text="Удалить выбранную", command=self.delete_target).grid(row=0, column=7, padx=(10, 0))

        cols = ("name", "state", "latency", "uptime", "checks", "last", "url")
        heads = ("Имя", "Состояние", "Задержка, мс", "Uptime, %", "Проверок", "Последняя проверка", "URL")
        self.table = ttk.Treeview(self, columns=cols, show="headings", height=9)
        for c, h, w in zip(cols, heads, (110, 90, 100, 80, 80, 160, 300)):
            self.table.heading(c, text=h)
            self.table.column(c, width=w, anchor="w")
        for state, color in STATE_COLORS.items():
            self.table.tag_configure(state, foreground=color)
        self.table.pack(fill="x", padx=10, pady=5)
        self.table.bind("<<TreeviewSelect>>", lambda _: self.show_history())

        hist = ttk.LabelFrame(self, text="История проверок выбранной цели", padding=6)
        hist.pack(fill="both", expand=True, padx=10, pady=5)
        self.history_box = tk.Text(hist, height=12, font=("Menlo", 11))
        self.history_box.pack(fill="both", expand=True)
        self.status_bar = ttk.Label(self, text="", anchor="w")
        self.status_bar.pack(fill="x", padx=10, pady=(0, 8))

    def refresh(self) -> None:
        """Обновляет таблицу состояния и сам ставит следующее обновление."""
        try:
            rows = self.api.status()
            selected = self.table.selection()
            self.table.delete(*self.table.get_children())
            for r in rows:
                self.table.insert("", "end", iid=str(r["id"]), tags=(r["state"],), values=(
                    r["name"], r["state"],
                    "—" if r["last_latency_ms"] is None else f"{r['last_latency_ms']:.1f}",
                    "—" if r["uptime_percent"] is None else f"{r['uptime_percent']:.1f}",
                    r["checks_total"], (r["last_checked_at"] or "—")[:19].replace("T", " "), r["url"]))
            if selected and self.table.exists(selected[0]):
                self.table.selection_set(selected[0])
            up = sum(r["state"] == "UP" for r in rows)
            self.status_bar.config(text=f"Сервер: {self.api.base} · целей: {len(rows)} · UP: {up} · "
                                        f"автообновление каждые {REFRESH_MS // 1000} с")
        except (OSError, RuntimeError) as exc:
            self.status_bar.config(text=f"Нет связи с сервером: {exc}")
        self.after(REFRESH_MS, self.refresh)

    def show_history(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        try:
            rows = self.api.history(int(selected[0]))
        except (OSError, RuntimeError) as exc:
            messagebox.showerror("Ошибка", str(exc))
            return
        self.history_box.delete("1.0", "end")
        self.history_box.insert("end", f"{'время (UTC)':<20} {'итог':<6} {'код':<5} {'мс':>7}  ошибка\n")
        for r in rows:
            latency = "" if r["latency_ms"] is None else f"{r['latency_ms']:.1f}"
            self.history_box.insert("end", f"{r['checked_at'][:19].replace('T', ' '):<20} "
                                           f"{'UP' if r['is_up'] else 'DOWN':<6} {r['status_code'] or '—'!s:<5} "
                                           f"{latency:>7}  {r['error'] or ''}\n")

    def add_target(self) -> None:
        try:
            self.api.add(self.name_var.get().strip(), self.url_var.get().strip(), int(self.interval_var.get()))
            self.name_var.set("")
            self.refresh()
        except (OSError, RuntimeError, tk.TclError, ValueError) as exc:
            messagebox.showerror("Не удалось добавить", str(exc))

    def delete_target(self) -> None:
        selected = self.table.selection()
        if selected and messagebox.askyesno("Удаление", "Удалить цель и её историю?"):
            try:
                self.api.delete(int(selected[0]))
                self.history_box.delete("1.0", "end")
                self.refresh()
            except (OSError, RuntimeError) as exc:
                messagebox.showerror("Ошибка", str(exc))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default=os.environ.get("MONITOR_API_TOKEN", ""),
                        help="value of X-API-Token if the server requires it")
    args = parser.parse_args()
    MonitorApp(ApiClient(args.server, args.token)).mainloop()


if __name__ == "__main__":
    main()
