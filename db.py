import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "history.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker       TEXT NOT NULL,
                name         TEXT NOT NULL,
                sector       TEXT,
                industry     TEXT,
                market_cap   TEXT,
                exchange     TEXT,
                description  TEXT,
                revenue_json TEXT,
                risks_json   TEXT,
                news_json    TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_search(data: dict) -> int:
    with _connect() as conn:
        cur = conn.execute("""
            INSERT INTO searches
                (ticker, name, sector, industry, market_cap, exchange,
                 description, revenue_json, risks_json, news_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["ticker"], data["name"], data["sector"], data["industry"],
            data["market_cap"], data["exchange"], data["description"],
            json.dumps(data["revenue_results"]),
            json.dumps(data["risk_results"]),
            json.dumps(data["news"]),
        ))
        return cur.lastrowid


def get_history() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, ticker, name, sector, market_cap, created_at "
            "FROM searches ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_search(search_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM searches WHERE id = ?", (search_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["revenue_results"] = json.loads(d.pop("revenue_json"))
        d["risk_results"] = json.loads(d.pop("risks_json"))
        d["news"] = json.loads(d.pop("news_json"))
        return d
