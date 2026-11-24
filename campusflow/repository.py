from __future__ import annotations

import sqlite3
from pathlib import Path

from .domain import Event, Registration, RegistrationStatus


class SQLiteCampusFlowRepository:
    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.connection = sqlite3.connect(str(db_path))
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                capacity INTEGER NOT NULL,
                owner_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES events(id)
            );
            """
        )
        self.connection.commit()

    def create_event(self, title: str, capacity: int, owner_id: str) -> Event:
        cursor = self.connection.execute(
            "INSERT INTO events(title, capacity, owner_id) VALUES (?, ?, ?)",
            (title, capacity, owner_id),
        )
        self.connection.commit()
        return Event(int(cursor.lastrowid), title, capacity, owner_id)

    def get_event(self, event_id: int) -> Event | None:
        row = self.connection.execute(
            "SELECT id, title, capacity, owner_id FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        if row is None:
            return None
        return Event(row["id"], row["title"], row["capacity"], row["owner_id"])

    def list_events(self) -> list[Event]:
        rows = self.connection.execute(
            "SELECT id, title, capacity, owner_id FROM events ORDER BY id"
        ).fetchall()
        return [Event(r["id"], r["title"], r["capacity"], r["owner_id"]) for r in rows]

    def add_registration(
        self, event_id: int, user_id: str, status: RegistrationStatus
    ) -> Registration:
        cursor = self.connection.execute(
            "INSERT INTO registrations(event_id, user_id, status) VALUES (?, ?, ?)",
            (event_id, user_id, status.name),
        )
        self.connection.commit()
        return Registration(event_id, user_id, status, int(cursor.lastrowid))

    def count_registrations(
        self, event_id: int, status: RegistrationStatus | None = None
    ) -> int:
        if status is None:
            query = "SELECT COUNT(*) AS count FROM registrations WHERE event_id = ?"
            params = (event_id,)
        else:
            query = (
                "SELECT COUNT(*) AS count FROM registrations "
                "WHERE event_id = ? AND status = ?"
            )
            params = (event_id, status.name)

        row = self.connection.execute(query, params).fetchone()
        return int(row["count"])

    def has_registration(self, event_id: int, user_id: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM registrations WHERE event_id = ? AND user_id = ? LIMIT 1",
            (event_id, user_id),
        ).fetchone()
        return row is not None

    def remove_registration(self, event_id: int, user_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM registrations WHERE event_id = ? AND user_id = ?",
            (event_id, user_id),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def list_registrations(self, event_id: int) -> list[Registration]:
        query = (
            "SELECT id, event_id, user_id, status FROM registrations "
            "WHERE event_id = ? ORDER BY id"
        )
        rows = self.connection.execute(query, (event_id,)).fetchall()
        return [
            Registration(r["event_id"], r["user_id"], RegistrationStatus[r["status"]], r["id"])
            for r in rows
        ]

    def get_next_waitlisted(self, event_id: int) -> Registration | None:
        query = (
            "SELECT id, event_id, user_id, status FROM registrations "
            "WHERE event_id = ? AND status = 'WAITLISTED' ORDER BY id ASC LIMIT 1"
        )
        row = self.connection.execute(query, (event_id,)).fetchone()
        if row is None:
            return None
        return Registration(
            row["event_id"], row["user_id"], RegistrationStatus[row["status"]], row["id"]
        )

    def update_registration_status(self, registration_id: int, status: RegistrationStatus) -> None:
        self.connection.execute(
            "UPDATE registrations SET status = ? WHERE id = ?", (status.name, registration_id)
        )
        self.connection.commit()
