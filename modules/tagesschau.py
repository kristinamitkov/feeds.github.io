import re
import sqlite3
import xml.etree.ElementTree

import database
import requests
import utils


def tagesschau():
    # 1) Create session
    _session = requests.Session()

    # 2) Create headers
    _headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:149.0) Gecko/20100101 Firefox/149.0'
    }

    # 3) GET request
    _response = _session.get('https://www.tagesschau.de/index~rss2.xml', headers=_headers)

    # 4) Save data
    # 4.1) Create save path
    _path_1 = 'www.tagesschau.de/'
    _path_1 = re.sub(r'[^a-zA-Z0-9]', '_', _path_1)
    _path_1 = re.sub(r'__+', '_', _path_1)

    _path_2 = 'data/' + _path_1 + '.rss'

    # 4.2) Save data
    with open(_path_2, mode='wb') as _file:
        _file.write(_response.content)

    # 5) Process data
    _data = xml.etree.ElementTree.parse(_path_2)
    _root = _data.getroot()
    _pubDate_parsed = _root.find('./channel/pubDate')
    assert(_pubDate_parsed is not None)
    _pubDate = _pubDate_parsed.text
    assert(_pubDate is not None)
    _pubDate = utils.parse_date(_pubDate, '%a, %d %b %Y %H:%M:%S %z')

    # 6) Save data
    _path_1 = 'data/' + _path_1 + utils.parse_timestamp(_pubDate, '%Y%m%d') + '.rss'

    # 7) Save data locally in DB
    _conn = sqlite3.connect(database.DATABASE)
    _cursor = _conn.cursor()

    # 8) Create or update task
    try:
        _cursor.execute(
            "INSERT INTO task (title, url, active, last_update, last_status_code, last_status_text, last_error) VALUES (?, ?, 1, ?, ?, ?, ?);",
            ('Tagesschau', 'https://www.tagesschau.de/', _pubDate, _response.status_code, _response.reason, (None if _response.ok else (_response.text or _response.reason)))
        )
    except Exception:
        _cursor.execute(
            "UPDATE task SET title=COALESCE(title, ?), last_update=?, last_status_code=?, last_status_text=?, last_error=?, active=1, priority=(priority+1) WHERE url=?;",
            ('Tagesschau', _pubDate, _response.status_code, _response.reason, (None if _response.ok else (_response.text or _response.reason)), 'https://www.tagesschau.de/')
        )

    _conn.commit()
    _conn.close()
