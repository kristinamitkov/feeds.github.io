import pprint
import sqlite3
import urllib.parse
from typing import List

import database
import finanztip
import idealo

if __name__ == '__main__':
    _conn = sqlite3.connect(database.DATABASE)
    _cursor = _conn.cursor()
    _cursor.execute('SELECT url FROM task;')
    _urls: List[str] = [_row[0] for _row in _cursor.fetchall()]
    _conn.close()

    for _url in _urls:
        pprint.pprint(_url)
        _url_parsed = urllib.parse.urlparse(_url)

        if _url_parsed.netloc == 'www.idealo.de':
            idealo.idealo(_url)

        if _url_parsed.netloc == 'www.finanztip.de':
            finanztip.finanztip()
