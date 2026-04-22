import argparse
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
    priority INTEGER NOT NULL DEFAULT 25,
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
    url TEXT NOT NULL,
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
    print('Initializing database')

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
        _price_dt_uniform = datetime.datetime.fromtimestamp(_price[4]).replace(hour=0, minute=0, second=0, microsecond=0)

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

def import_prices(_import: str):
    try:
        with open(_import, mode='r') as _file:
            _prices: List[Tuple] = [tuple(_entry.split(',')) for _entry in _file.readlines()[1:]]
    except Exception as e:
        return

    _conn = sqlite3.connect(DATABASE)
    _cursor = _conn.cursor()

    for _price in _prices:
        _cursor.execute(
            """INSERT INTO price (product_id, task_id, url, created, price, currency, offers, status_code, status_text, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tuple(_entry if _entry else None for _entry in _price))
        )

    _conn.commit()
    _conn.close()

def export_prices(_url: str, _export: str):
    _conn = sqlite3.connect(DATABASE)
    _cursor = _conn.cursor()

    _cursor.execute('SELECT * FROM price WHERE url=? ORDER BY created ASC;', (_url,))
    _prices: List[str] = [','.join((str(__entry) if __entry is not None else '') for __entry in _entry[1:]) for _entry in _cursor.fetchall()]

    with open(_export, mode='w') as _file:
        _file.write('product_id,task_id,url,created,price,currency,offers,status_code,status_text,error\n')
        _file.write('\n'.join(_prices))

    _conn.commit()
    _conn.close()


if __name__ == '__main__':
    _args_parser = argparse.ArgumentParser()
    _args_parser.add_argument("--init", required=False, default=False, action='store_true')
    _args_parser.add_argument("--prune", required=False, default=False, action='store_true')
    _args_parser.add_argument("--title", required=False, type=str, default='')
    _args_parser.add_argument("--url", required=False, type=str, default='')
    _args_parser.add_argument("--export", required=False, type=str, default='')
    _args_parser.add_argument("--import", required=False, type=str, default='')
    _args = vars(_args_parser.parse_args())

    if _args['init']:
        create_db()

    if _args['import']:
        import_prices(_args['import'])

    if _args['prune']:
        prune_prices()

    if _args['url'] and _args['export']:
        import_prices(_args['export'])
        export_prices(_args['url'], _args['export'])
    elif _args['url']:
        assert(_args['url'].startswith('http://') or _args['url'].startswith('https://'))
        add_task(_args['title'] if _args['title'] else None, _args['url'])
