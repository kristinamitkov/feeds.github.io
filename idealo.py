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
import utils


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

def idealo_parse(_data: str, _link: str) -> Dict[str, Any]:
    # 1) Parse HTML data
    _soup = bs4.BeautifulSoup(_data, 'html.parser')

    # 2) Get elements
    _title = _soup.find('h1', id='oopStage-title')

    _meta = _soup.find('div', class_='oopStage-metaInfo')
    _meta_offers = _meta.find('span', class_='oopStage-priceRangeOffers')
    _meta_price = _meta.find('span', class_='oopStage-priceRangePrice')
    _meta_grade = _meta.find('span', class_='oopStage-metaInfoItemTestsReportGrade')

    _pubDate = _soup.find('li', class_='productOffers-listItemImportTime')

    _variants = _soup.find('h2', class_='text-sm')

    _offers = _soup.find('div', id='offerList')
    _offers_titles = _offers.find_all('div', class_='productOffers-listItemTitleWrapper')
    _offers_prices = _offers.find_all('div', class_='price-column')
    _offers_shop = _offers.find_all('div', class_='productOffers-listItemOfferShopV2Block')
    _offers_shop_link = _offers.find_all('a', class_='productOffers-listItemOfferCtaLeadout')

    assert(len(_offers_titles) == len(_offers_prices))
    assert(len(_offers_prices) == len(_offers_shop))
    assert(len(_offers_shop) == len(_offers_shop_link))

    # 3) Return data as a JSON dict
    return {
        'title': utils.clear_text(_title.get_text()),
        'link': _link,
        'pubDate': utils.clear_text(_pubDate.get_text()),
        'offers': utils.clear_text(_meta_offers.get_text()).rstrip(':'),
        'prices': utils.clear_text(_meta_price.get_text()),
        'grade': utils.clear_text(_meta_grade.get_text()),
        'variants': utils.clear_text(_variants.get_text()),
        'items': [
            {
                'title': utils.clear_text(_entry[0].get_text()),
                'price': utils.clear_text(_entry[1].get_text()),
                'shop': utils.clear_text(_entry[2].get_text()),
                'link': 'https://www.idealo.de' + _entry[3]['href'].strip(),
                'pubDate': utils.clear_text(_pubDate.get_text()),
            }
            for _entry in zip(_offers_titles, _offers_prices, _offers_shop, _offers_shop_link)
        ]
    }

def idealo_store(_response: requests.Response, _data: Dict[str, Any]):
    def _idealo_date(_date: str) -> float:
        _date = re.search(r'\d{2}\.\d{2}\.\d{4}', _date.strip()).group()
        _dt = datetime.datetime.strptime(_date, "%d.%m.%Y")
        return _dt.timestamp()

    # 0) Pre-process some data
    _data_offers = int(re.search(r'[0-9]+', _data['offers']).group())
    _data_price = int(re.search(r'[0-9]+', _data['prices']).group())

    _conn = sqlite3.connect(database.DATABASE)
    _cursor = _conn.cursor()

    _pubDate = _idealo_date(_data['pubDate'])

    # 1) Get or create task
    try:
        _cursor.execute(
            "INSERT INTO task (title, url, active, last_update, last_status_code, last_status_text, last_error) VALUES (?, ?, 1, ?, ?, ?, ?) RETURNING id;",
            (_data['title'], _data['link'], _pubDate, _response.status_code, _response.reason, (None if _response.ok else (_response.text or _response.reason)))
        )
    except Exception as e:
        _cursor.execute(
            "UPDATE task SET title=COALESCE(title, ?), last_update = ?, last_status_code=?, last_status_text=?, last_error=?, active=1, priority=(priority + 1) WHERE url = ? RETURNING id;",
            (_data['title'], _pubDate, _response.status_code, _response.reason, (None if _response.ok else (_response.text or _response.reason)), _data['link'])
        )
    _task = _cursor.fetchone()[0]
    _conn.commit()

    # 2) Create or update product
    try:
        _cursor.execute(
            "INSERT INTO products (title, url, currency, base_price, last_price, last_update, active) VALUES (?, ?, 'EUR', ?, ?, ?, 1);",
            (_data['title'], _data['link'], _data_price, _data_price, _pubDate)
        )
    except Exception:
        _cursor.execute(
            "UPDATE products SET currency='EUR', active=1, last_price=?, last_update=? WHERE url=?;",
            (_data_price, _pubDate, _data['link'])
        )
    _conn.commit()

    # 3) Add price point
    _cursor.execute(
        """INSERT INTO price (product_id, task_id, created, price, currency, offers, status_code, status_text, error)
            VALUES (?, ?, ?, ?, 'EUR', ?, ?, ?, ?);
        """,
        (_data['title'], _task, _pubDate, _data_price, _data_offers, _response.status_code, _response.reason, (None if _response.ok else (_response.text or _response.reason)))
    )
    _conn.commit()

    _conn.close()

def idealo(_url: str):
    _response = idealo_get(_url)
    _data_parsed = idealo_parse(_response.text, _url)
    idealo_store(_response, _data_parsed)
