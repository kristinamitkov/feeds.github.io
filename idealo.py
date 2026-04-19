import datetime
import hashlib # TODO:  hashlib.sha256(_item_raw['title'].encode("utf-8")).hexdigest()
import pprint
import re
import sqlite3
import time
import urllib.parse
from typing import Any, Dict

import bs4
import database
import requests


def idealo_get(_url: str):
    assert _url.startswith('https://www.idealo.de/')
    assert _url.endswith('.html')

    # 1) Create session
    _session = requests.Session()

    # 2) Set cookies
    _session.cookies.set('consentStatus', 'false')

    # 3) Create headers
    _headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:149.0) Gecko/20100101 Firefox/149.0'
    }

    # 4) GET request
    _response = _session.get(_url, headers=_headers)

    # 5) Return data
    _data = _response.text

    # 6) Save data
    # 6.1) Parse URL
    _url_parsed = urllib.parse.urlparse(_url)

    # 6.2) Create save path
    _path = _url_parsed.netloc + _url_parsed.path[:-5]
    _path = re.sub(r'[^a-zA-Z0-9]', '_', _path)
    _path = re.sub(r'__+', '_', _path)
    _path = 'data/' + _path + '_' + datetime.datetime.now().strftime("%Y%m%d") + '.html'

    # 6.3) Save data
    with open(_path, mode='w') as _file:
        _file.write(_data)

    return _response

def idealo_parse(_data: str, _url: str) -> Dict[str, Any]:
    # 0) Helper convert element to text and strip separator characters
    def _idealo_parsed_text(_data_parsed: bs4.BeautifulSoup):
        _data_parsed_text = _data_parsed.get_text()
        _data_parsed_text = _data_parsed_text.replace('\xad', '')
        return re.sub(r'\s+', ' ', re.sub(r'[\s\n\r\t]+', ' ', _data_parsed_text).strip()).strip()

    # 1) Parse HTML data
    _soup = bs4.BeautifulSoup(_data, 'html.parser')

    # 2) Get elements
    _title = _soup.find('h1', id='oopStage-title')

    _meta = _soup.find('div', class_='oopStage-metaInfo')
    _meta_offers = _meta.find('span', class_='oopStage-priceRangeOffers')
    _meta_price = _meta.find('span', class_='oopStage-priceRangePrice')
    _meta_grade = _meta.find('span', class_='oopStage-metaInfoItemTestsReportGrade')

    _variants = _soup.find('h2', class_='text-sm')

    _offers = _soup.find('div', id='offerList')
    _offers_titles = _offers.find_all('div', class_='productOffers-listItemTitleWrapper')
    _offers_prices = _offers.find_all('div', class_='price-column')
    _offers_shop = _offers.find_all('div', class_='productOffers-listItemOfferShopV2Block')
    _offers_shop_url = _offers.find_all('a', class_='productOffers-listItemOfferCtaLeadout')

    assert(len(_offers_titles) == len(_offers_prices))
    assert(len(_offers_prices) == len(_offers_shop))
    assert(len(_offers_shop) == len(_offers_shop_url))

    # 3) Return data as a JSON dict
    return {
        'title': _idealo_parsed_text(_title),
        'url': _url,
        'timestamp': time.time(),
        'offers': _idealo_parsed_text(_meta_offers).rstrip(':'),
        'prices': _idealo_parsed_text(_meta_price),
        'grade': _idealo_parsed_text(_meta_grade),
        'variants': _idealo_parsed_text(_variants),
        'items': [
            {
                'title': _idealo_parsed_text(_entry[0]),
                'price': _idealo_parsed_text(_entry[1]),
                'shop': _idealo_parsed_text(_entry[2]),
                'url': 'https://www.idealo.de' + _entry[3]['href'].strip()
            }
            for _entry in zip(_offers_titles, _offers_prices, _offers_shop, _offers_shop_url)
        ]
    }

def idealo_store(_response: requests.Response, _data: Dict[str, Any]):
    # 0) Pre-process some data
    _data_offers = int(re.search(r'[0-9]+', _data['offers']).group())
    _data_price = int(re.search(r'[0-9]+', _data['prices']).group())

    _conn = sqlite3.connect(database.DATABASE)
    _cursor = _conn.cursor()

    # 1) Create or update product
    try:
        _cursor.execute(
            "INSERT INTO products VALUES (?, ?, ?, ?);",
            (_data['title'], _data['url'], 'EUR', 1)
        )
    except Exception:
        _cursor.execute(
            "UPDATE products SET currency='EUR', active=1 WHERE title=? AND url=?;",
            (_data['title'], _data['url'])
        )
    _conn.commit()

    # 2) Update task
    _cursor.execute(
        "UPDATE task SET last=? WHERE product_id=? AND url=?;",
        (_data['timestamp'], _data['title'], _data['url'])
    )
    _conn.commit()

    # 3) Get or create task
    try:
        _cursor.execute(
            "INSERT INTO task (product_id, url, last) VALUES (?, ?, ?) RETURNING id;",
            (_data['title'], _data['url'], _data['timestamp'])
        )
    except Exception as e:
        _cursor.execute(
            "UPDATE task SET last = ? WHERE product_id = ? AND url = ? RETURNING id;",
            (_data['timestamp'], _data['title'], _data['url'])
        )
    _task = _cursor.fetchone()[0]
    assert(bool(_task))
    _conn.commit()

    # 4) Add price point
    _cursor.execute(
        """INSERT INTO price (product_id, task_id, created, price, currency, offers, status_code, status_text, error)
            VALUES (?, ?, ?, ?, 'EUR', ?, ?, ?, ?);
        """,
        (_data['title'], _task, _data['timestamp'], _data_price, _data_offers, _response.status_code, _response.reason, (None if _response.ok else (_response.text or _response.reason)))
    )
    _conn.commit()

    _conn.close()

def idealo(URL: str):
    RESPONSE = idealo_get(URL)
    DATA_PARSED = idealo_parse(RESPONSE.text, URL)
    idealo_store(RESPONSE, DATA_PARSED)
