import datetime
import sqlite3
from typing import Dict, List, Tuple


DATABASE = 'sqlite3.db'

SQL_PRODUCTS = """CREATE TABLE IF NOT EXISTS products (
    title TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    currency TEXT NOT NULL DEFAULT 'EUR',
    active INTEGER NOT NULL DEFAULT 1
);"""

# TODO: minutes DEFAULT 360?
SQL_TASK = """CREATE TABLE IF NOT EXISTS task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT DEFAULT NULL,
    url TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1,
    last INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(title)
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
    _cursor.execute(SQL_PRODUCTS)
    _conn.commit()
    _cursor.execute(SQL_TASK)
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

    for _, _vs in _prune.items():
        for _v in _vs:
            _cursor.execute("DELETE FROM price WHERE id=?;", (_v,))

    _conn.commit()
    _conn.close()

if __name__ == '__main__':
    create_db()
    prune_prices()
