import datetime
import sqlite3
import sys
from typing import Dict, List, Optional, Tuple


DATABASE = 'sqlite3.db'

# TODO: minutes DEFAULT 360?
SQL_TASK = """CREATE TABLE IF NOT EXISTS task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT DEFAULT NULL,
    url TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1,
    last_update INTEGER DEFAULT NULL,
    last_status_code INTEGER DEFAULT NULL,
    last_status_text TEXT DEFAULT NULL,
    last_error TEXT DEFAULT NULL
);"""

SQL_PRODUCTS = """CREATE TABLE IF NOT EXISTS products (
    title TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    currency TEXT NOT NULL DEFAULT 'EUR',
    base_price INTEGER NOT NULL,
    last_price INTEGER NOT NULL,
    last_update INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (title) REFERENCES task(title)
);"""

SQL_PRICES = """CREATE TABLE IF NOT EXISTS price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    task_id INTEGER NOT NULL,
    created INTEGER NOT NULL,
    price INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'EUR',
    offers INTEGER NOT NULL,
    status_code INTEGER NOT NULL,
    status_text TEXT NOT NULL,
    error TEXT DEFAULT NULL,
    FOREIGN KEY (product_id) REFERENCES products(title),
    FOREIGN KEY (task_id) REFERENCES task(id)
);"""


def create_db():
    # Create database
    _conn = sqlite3.connect(DATABASE)
    _cursor = _conn.cursor()
    _cursor.execute(SQL_TASK)
    _conn.commit()
    _cursor.execute(SQL_PRODUCTS)
    _conn.commit()
    _cursor.execute(SQL_PRICES)
    _conn.commit()
    _conn.close()

def prune_prices():
    _conn = sqlite3.connect(DATABASE)
    _cursor = _conn.cursor()

    _cursor.execute("SELECT * FROM price ORDER BY created DESC;")
    _prices: List[Tuple] = _cursor.fetchall()

    _prune: Dict[Tuple[str, str], List[int]] = {}
    for _price in _prices:
        _price_dt_uniform = datetime.datetime.fromtimestamp(_price[3]).replace(hour=0, minute=0, second=0, microsecond=0)

        if (_price[1], str(_price_dt_uniform)) not in _prune:
            _prune[(_price[1], str(_price_dt_uniform))] = []
            continue

        _prune[(_price[1], str(_price_dt_uniform))].append(_price[0])
    _prune = {_k:_vs for _k, _vs in _prune.items() if _vs}

    for _k, _vs in _prune.items():
        for _v in _vs:
            print('Pruning', _k, _v)
            _cursor.execute("DELETE FROM price WHERE id=?;", (_v,))

    _conn.commit()
    _conn.close()

def add_task(_title: Optional[str], _url: str):
    print('Adding task', _title, _url)

    _conn = sqlite3.connect(DATABASE)
    _cursor = _conn.cursor()

    try:
        _cursor.execute("INSERT INTO task (title, url, active) VALUES (?, ?, 1);", (_title, _url))
    except Exception as e:
        _cursor.execute("UPDATE task SET title=COALESCE(title, ?), active=1 WHERE url=?;", (_title, _url))

    _conn.commit()
    _conn.close()

if __name__ == '__main__':
    create_db()
    prune_prices()

    if (len(sys.argv) == 2) and (sys.argv[1].startswith('http')):
        add_task(None, sys.argv[1])

    if (len(sys.argv) == 3) and (sys.argv[2].startswith('http')):
        add_task(sys.argv[1], sys.argv[2])
