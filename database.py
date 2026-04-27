import argparse
import datetime
import sqlite3
from typing import Callable, Dict, List, Optional, Tuple


DATABASE = 'sqlite3.db'

MODULES: Dict[str, Callable] = {}
def run_modules():
    from modules.finanztip import finanztip
    from modules.idealo import idealo
    from modules.tagesschau import tagesschau

    MODULES["www.idealo.de"] = idealo
    MODULES["https://www.finanztip.de/daily/"] = finanztip
    MODULES["https://www.tagesschau.de/"] = tagesschau

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

SQL_PRODUCT = """CREATE TABLE IF NOT EXISTS product (
    title TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    currency TEXT NOT NULL DEFAULT 'EUR',
    base_price INTEGER NOT NULL,
    last_price INTEGER NOT NULL,
    last_update INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (title) REFERENCES task(title)
);"""

SQL_PRICE = """CREATE TABLE IF NOT EXISTS price (
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
    FOREIGN KEY (product_id) REFERENCES product(title),
    FOREIGN KEY (task_id) REFERENCES task(id)
);"""


def create_db():
    print('Initializing database')

    _conn = sqlite3.connect(DATABASE)
    _cursor = _conn.cursor()

    _cursor.execute(SQL_TASK)
    _conn.commit()

    _cursor.execute(SQL_PRODUCT)
    _conn.commit()

    _cursor.execute(SQL_PRICE)
    _conn.commit()

    _conn.close()

def prune_prices():
    print('Pruning DB')

    _conn = sqlite3.connect(DATABASE)
    _cursor = _conn.cursor()

    _cursor.execute("SELECT * FROM price ORDER BY created DESC, id DESC;")
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

def add_task(_title: Optional[str], _url: str, _last_update: Optional[float], _last_status_code: Optional[int], _last_status_text: Optional[str], _last_error: Optional[str]) -> int:
    _conn = sqlite3.connect(DATABASE)
    _cursor = _conn.cursor()

    try:
        _cursor.execute(
            "INSERT INTO task (title, url, last_update, last_status_code, last_status_text, last_error) VALUES (?, ?, ?, ?, ?, ?) RETURNING id;",
            (_title, _url, _last_update, _last_status_code, _last_status_text, _last_error)
        )
    except Exception as e:
        _cursor.execute(
            "UPDATE task SET title=COALESCE(title, ?), last_update=?, last_status_code=?, last_status_text=?, last_error=?, active=1, priority=(priority+1) WHERE url=? RETURNING id;",
            (_title, _last_update, _last_status_code, _last_status_text, _last_error, _url)
        )

    _task: int = int(_cursor.fetchone()[0])

    _conn.commit()
    _conn.close()

    return _task

def add_product(_title: str, _url: str, _currency: str, _last_price: int, _last_update: float) -> str:
    _conn = sqlite3.connect(DATABASE)
    _cursor = _conn.cursor()

    try:
        _cursor.execute(
            "INSERT INTO product (title, url, currency, base_price, last_price, last_update) VALUES (?, ?, ?, ?, ?, ?) RETURNING base_price;",
            (_title, _url, _currency, _last_price, _last_price, _last_update)
        )
    except Exception as e:
        _cursor.execute(
            "UPDATE product SET active=1, last_price=?, last_update=? WHERE url=? RETURNING base_price;",
            (_last_price, _last_update, _url)
        )

    _base_price: int = int(_cursor.fetchone()[0])

    _conn.commit()

    if bool(_base_price) and (abs((_last_price - _base_price)/_base_price) >= 0.05):
        _conn.close()
        return _title

    _cursor.execute("UPDATE product SET base_price=last_price WHERE url=?;", (_url,))
    _cursor.execute("UPDATE task SET priority=25 WHERE url=?;", (_url,))

    _conn.commit()
    _conn.close()

    return _title

def add_price(_title: str, _task: int, _url: str, _created: float, _price: int, _currency: str, _offers: int, _status_code: int, _status_text: str, _error: Optional[str]):
    _task = add_task(_title, _url, _created, _status_code, _status_text, _error)
    add_product(_title, _url, _currency, int(_price), _created)

    _conn = sqlite3.connect(DATABASE)
    _cursor = _conn.cursor()

    _cursor.execute(
        """INSERT INTO price (product_id, task_id, url, created, price, currency, offers, status_code, status_text, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (_title, _task, _url, _created, _price, _currency, _offers, _status_code, _status_text, _error)
    )

    _conn.commit()
    _conn.close()

def import_prices(_url: str, _import: str):
    print('Importing to DB', _import)

    try:
        with open(_import, mode='r') as _file:
            _prices: List[Tuple] = [tuple(_entry.strip().split(',')) for _entry in _file.readlines()[1:] if _entry.strip()]
    except Exception as e:
        return

    for _price in _prices:
        _price: Tuple = tuple((_entry if _entry else None) for _entry in _price)
        add_price(*((_price[0], 0) + _price[1:]))

def export_prices(_url: str, _export: str):
    print('Exporting DB', _url, _export)

    _conn = sqlite3.connect(DATABASE)
    _cursor = _conn.cursor()

    _cursor.execute('SELECT * FROM price WHERE url=? ORDER BY created ASC;', (_url,))
    _prices: List[str] = [','.join((str(__entry) if __entry is not None else '') for __entry in (_entry[1],) + _entry[3:]) for _entry in _cursor.fetchall() if _entry]

    with open(_export, mode='w') as _file:
        _file.write('product_id,url,created,price,currency,offers,status_code,status_text,error\n')
        _file.write('\n'.join(_prices))
        _file.write('\n')

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

    if _args['url'] and _args['import']:
        import_prices( _args['url'], _args['import'])

    if _args['prune']:
        prune_prices()

    if _args['url'] and _args['export']:
        export_prices(_args['url'], _args['export'])
