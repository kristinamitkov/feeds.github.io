import sqlite3


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

if __name__ == '__main__':
    _conn = sqlite3.connect(DATABASE)
    _cursor = _conn.cursor()
    _cursor.execute(SQL_PRODUCTS)
    _conn.commit()
    _cursor.execute(SQL_TASK)
    _conn.commit()
    _cursor.execute(SQL_PRICES)
    _conn.commit()
    _conn.close()
