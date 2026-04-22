import time
import sqlite3
import urllib.parse
from typing import List, Tuple

import database
import finanztip
import idealo
import tagesschau


def check_update_priority(_row: Tuple):
    _delta = (time.time() - _row[5]) // 10000

    _priority: int = _row[4]
    if (1 >= _row[4] >= 24) and (_delta >= 1):
        return True

    if (25 >= _row[4] >= 36) and (_delta >= 6):
        return True

    if (37 >= _row[4] >= 50) and (_delta >= 12):
        return True

    if (_row[4] >= 51) and (_delta >= 24):
        return True

    return False


if __name__ == '__main__':
    _conn = sqlite3.connect(database.DATABASE)
    _cursor = _conn.cursor()
    _cursor.execute('SELECT * FROM task;')
    _rows: List[Tuple] = _cursor.fetchall()
    _conn.close()

    for _row in _rows:
        if bool(_row[5]) and (not check_update_priority(_row)):
            continue

        print('Scraping', _row[1], _row[2])

        _url: str = _row[2]
        _url_parsed = urllib.parse.urlparse(_url)

        if _url_parsed.netloc == 'www.idealo.de':
            idealo.idealo(_url)

        if _url == 'https://www.finanztip.de/daily/':
            finanztip.finanztip()

        if _url == 'https://www.tagesschau.de/':
            tagesschau.tagesschau()
